using System.Net;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Tests;

internal static class HttpTestSupport
{
    internal static HttpClient CreateClient(
        WebApplicationFactory<Program> app, bool handleCookies = true)
        => app.CreateClient(new WebApplicationFactoryClientOptions
        {
            AllowAutoRedirect = false,
            BaseAddress = new Uri("https://localhost"),
            HandleCookies = handleCookies,
        });

    internal static async Task LogInOwnerAsync(HttpClient client)
    {
        var token = await GetAntiforgeryAsync(client, "/login");
        using var body = new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["Username"] = TeledropWebApplicationFactory.WebUsername,
            ["Password"] = TeledropWebApplicationFactory.WebPassword,
            ["__RequestVerificationToken"] = token,
        });
        using var response = await client.PostAsync("/login", body);
        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
    }

    internal static async Task<string> GetAntiforgeryAsync(HttpClient client, string path)
    {
        using var response = await client.GetAsync(path);
        response.EnsureSuccessStatusCode();
        return ExtractAntiforgery(await response.Content.ReadAsStringAsync());
    }

    internal static string ExtractAntiforgery(string html)
    {
        const RegexOptions options = RegexOptions.IgnoreCase | RegexOptions.CultureInvariant;
        foreach (Match input in Regex.Matches(html, @"<input\b[^>]*>", options))
        {
            if (!Regex.IsMatch(input.Value,
                    @"\sname\s*=\s*([""'])__RequestVerificationToken\1", options))
                continue;

            var value = Regex.Match(input.Value, @"\svalue\s*=\s*([""'])(.*?)\1", options);
            Assert.True(value.Success && value.Groups[2].Length > 0,
                "The antiforgery input has no value.");
            return WebUtility.HtmlDecode(value.Groups[2].Value);
        }

        throw new Xunit.Sdk.XunitException("The response has no antiforgery input.");
    }

    // Use the selected host for both Services and its storage configuration,
    // including a factory derived through WithWebHostBuilder.
    internal static async Task<Drop> SeedDropAsync(
        WebApplicationFactory<Program> app,
        string slug,
        byte[]? fileBytes,
        Action<Drop>? configure = null)
    {
        await using var scope = app.Services.CreateAsyncScope();
        var services = scope.ServiceProvider;
        var drop = new Drop
        {
            Id = Guid.NewGuid(),
            Slug = slug,
            Title = $"Drop {slug}",
            IsPrivate = true,
            FileName = $"{slug}.bin",
            FileHash = Convert.ToHexStringLower(SHA256.HashData(fileBytes ?? [])),
            FileSizeBytes = fileBytes?.LongLength ?? 0,
            ContentType = "application/octet-stream",
            Location = Guid.NewGuid().ToString("N"),
            CreatedAt = services.GetRequiredService<TimeProvider>().GetUtcNow().UtcDateTime,
        };
        configure?.Invoke(drop);

        var options = services.GetRequiredService<IOptions<TeledropOptions>>().Value;
        var path = Path.Combine(options.ShareDirectory, drop.Location);
        var createdFile = false;
        try
        {
            // Null explicitly means a missing physical file; [] is an empty file.
            if (fileBytes is not null)
            {
                await using var file = new FileStream(path, FileMode.CreateNew, FileAccess.Write);
                createdFile = true;
                await file.WriteAsync(fileBytes);
            }

            var db = services.GetRequiredService<TeledropDbContext>();
            db.Drops.Add(drop);
            await db.SaveChangesAsync();
            return drop;
        }
        catch
        {
            if (createdFile) File.Delete(path);
            throw;
        }
    }
}
