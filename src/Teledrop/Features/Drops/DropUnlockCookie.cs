using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.DataProtection;

namespace Teledrop.Features.Drops;

public sealed class DropUnlockCookie
{
    private const string CookieNamePrefix = "teledrop.unlock.";
    private static readonly TimeSpan Lifetime = TimeSpan.FromHours(1);

    private readonly IDataProtector protector;

    public DropUnlockCookie(IDataProtectionProvider dataProtectionProvider)
    {
        protector = dataProtectionProvider.CreateProtector(
            "Teledrop.Features.Drops.DropUnlockCookie");
    }

    public bool IsValid(HttpRequest request, Drop drop)
    {
        if (drop.DropPasswordHash is null
            || !request.Cookies.TryGetValue(
                GetCookieName(drop.Slug),
                out var protectedValue)
            || string.IsNullOrEmpty(protectedValue))
        {
            return false;
        }

        UnlockCookiePayload? payload;

        try
        {
            var serializedPayload = protector.Unprotect(protectedValue);
            payload = JsonSerializer.Deserialize<UnlockCookiePayload>(
                serializedPayload);
        }
        catch (CryptographicException)
        {
            return false;
        }
        catch (FormatException)
        {
            return false;
        }
        catch (JsonException)
        {
            return false;
        }

        if (payload is null
            || !string.Equals(
                payload.Slug,
                drop.Slug,
                StringComparison.Ordinal)
            || payload.ExpiresAtUtc <= DateTimeOffset.UtcNow)
        {
            return false;
        }

        return FingerprintsMatch(
            payload.DropPasswordFingerprint,
            CreateDropPasswordFingerprint(drop.DropPasswordHash));
    }

    public void Append(HttpResponse response, Drop drop)
    {
        ArgumentNullException.ThrowIfNull(drop.DropPasswordHash);

        var expiresAtUtc = DateTimeOffset.UtcNow.Add(Lifetime);
        var payload = new UnlockCookiePayload(
            drop.Slug,
            CreateDropPasswordFingerprint(drop.DropPasswordHash),
            expiresAtUtc);
        var protectedValue = protector.Protect(
            JsonSerializer.Serialize(payload));

        response.Cookies.Append(
            GetCookieName(drop.Slug),
            protectedValue,
            new CookieOptions
            {
                HttpOnly = true,
                SameSite = SameSiteMode.Lax,
                Secure = response.HttpContext.Request.IsHttps,
                IsEssential = true,
                Path = "/",
                Expires = expiresAtUtc,
            });
    }

    private static string GetCookieName(string slug)
    {
        return $"{CookieNamePrefix}{slug}";
    }

    private static string CreateDropPasswordFingerprint(
        string encodedDropPasswordHash)
    {
        var fingerprint = SHA256.HashData(
            Encoding.UTF8.GetBytes(encodedDropPasswordHash));
        return Convert.ToHexString(fingerprint);
    }

    private static bool FingerprintsMatch(string stored, string current)
    {
        var storedBytes = Encoding.ASCII.GetBytes(stored);
        var currentBytes = Encoding.ASCII.GetBytes(current);

        return storedBytes.Length == currentBytes.Length
            && CryptographicOperations.FixedTimeEquals(
                storedBytes,
                currentBytes);
    }

    private sealed record UnlockCookiePayload(
        string Slug,
        string DropPasswordFingerprint,
        DateTimeOffset ExpiresAtUtc);
}
