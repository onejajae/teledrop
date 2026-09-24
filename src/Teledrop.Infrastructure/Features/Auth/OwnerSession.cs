using System.Security.Cryptography;
using System.Text;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.Extensions.Options;

namespace Teledrop.Features.Auth;

internal static class OwnerSession
{
    internal const string PasswordFingerprintClaimType =
        "teledrop:owner-session-password-fingerprint";

    internal static string CreatePasswordFingerprint(string encodedPasswordHash)
    {
        var fingerprint = SHA256.HashData(Encoding.UTF8.GetBytes(encodedPasswordHash));
        return Convert.ToHexString(fingerprint);
    }

    internal static async Task ValidatePrincipalAsync(
        CookieValidatePrincipalContext context)
    {
        var currentOptions = context.HttpContext.RequestServices
            .GetRequiredService<IOptionsMonitor<TeledropOptions>>()
            .CurrentValue;

        var storedFingerprint = context.Principal?
            .FindFirst(PasswordFingerprintClaimType)?
            .Value;
        var currentFingerprint = CreatePasswordFingerprint(currentOptions.WebPassword);

        if (string.Equals(storedFingerprint, currentFingerprint, StringComparison.Ordinal))
        {
            return;
        }

        context.RejectPrincipal();
        await context.HttpContext.SignOutAsync(
            CookieAuthenticationDefaults.AuthenticationScheme);
    }
}
