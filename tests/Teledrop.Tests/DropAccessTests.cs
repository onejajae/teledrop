using System.Net;
using System.Security.Cryptography;
using Isopoh.Cryptography.Argon2;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Tests;

public sealed class DropAccessTests
{
    private const string DropPassword = "drop-password";

    [Fact]
    public async Task LockedPublicDropReturns401WithoutMetadata()
    {
        using var factory = new TeledropWebApplicationFactory();
        var fileBytes = Enumerable.Repeat((byte)0x2a, 37).ToArray();
        var drop = await AddDropAsync(
            factory,
            slug: "locked-metadata",
            isPrivate: false,
            dropPasswordHash: Argon2.Hash(DropPassword),
            title: "hidden-title",
            fileName: "hidden-file.bin",
            fileBytes);
        using var client = CreateClient(factory);

        using var response = await client.GetAsync($"/{drop.Slug}");

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        var body = WebUtility.HtmlDecode(
            await response.Content.ReadAsStringAsync());
        Assert.DoesNotContain(drop.Title!, body, StringComparison.Ordinal);
        Assert.DoesNotContain(drop.FileName, body, StringComparison.Ordinal);
        Assert.DoesNotContain("37 B", body, StringComparison.Ordinal);
    }

    [Fact]
    public async Task AnonymousPrivateDropPageAndDownloadRedirectToLogin()
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await AddDropAsync(
            factory,
            slug: "private-access",
            isPrivate: true,
            dropPasswordHash: null,
            title: "private title",
            fileName: "private.bin",
            "private file"u8.ToArray());
        using var client = CreateClient(factory);

        using var pageResponse = await client.GetAsync($"/{drop.Slug}");
        using var downloadResponse = await client.GetAsync($"/d/{drop.Slug}");

        AssertLoginRedirect(pageResponse);
        AssertLoginRedirect(downloadResponse);
    }

    [Fact]
    public async Task CorrectDropPasswordUnlocksMetadataAndDownload()
    {
        using var factory = new TeledropWebApplicationFactory();
        var fileBytes = "password-protected-file"u8.ToArray();
        var drop = await AddDropAsync(
            factory,
            slug: "password-check",
            isPrivate: false,
            dropPasswordHash: Argon2.Hash(DropPassword),
            title: "unlocked title",
            fileName: "unlocked.bin",
            fileBytes,
            contentType: "image/png");
        using var client = CreateClient(factory);

        using var lockedPage = await client.GetAsync($"/{drop.Slug}");
        Assert.Equal(HttpStatusCode.Unauthorized, lockedPage.StatusCode);
        var lockedBody = await lockedPage.Content.ReadAsStringAsync();
        var verificationValue = ExtractAntiforgeryValue(lockedBody);

        using (var wrongPasswordResponse = await PostUnlockAsync(
                   client,
                   drop.Slug,
                   "wrong-password",
                   verificationValue))
        {
            Assert.Equal(
                HttpStatusCode.Unauthorized,
                wrongPasswordResponse.StatusCode);
            lockedBody = await wrongPasswordResponse.Content.ReadAsStringAsync();
            verificationValue = ExtractAntiforgeryValue(lockedBody);
        }

        using (var correctPasswordResponse = await PostUnlockAsync(
                   client,
                   drop.Slug,
                   DropPassword,
                   verificationValue))
        {
            Assert.Equal(
                HttpStatusCode.Redirect,
                correctPasswordResponse.StatusCode);
            Assert.Equal(
                $"/{drop.Slug}",
                GetPathAndQuery(correctPasswordResponse));
            var setCookie = Assert.Single(
                correctPasswordResponse.Headers.GetValues("Set-Cookie"));
            Assert.Contains("httponly", setCookie, StringComparison.OrdinalIgnoreCase);
            Assert.Contains(
                "samesite=lax",
                setCookie,
                StringComparison.OrdinalIgnoreCase);
        }

        using (var unlockedPage = await client.GetAsync($"/{drop.Slug}"))
        {
            Assert.Equal(HttpStatusCode.OK, unlockedPage.StatusCode);
            var body = WebUtility.HtmlDecode(
                await unlockedPage.Content.ReadAsStringAsync());
            Assert.Contains(drop.Title!, body, StringComparison.Ordinal);
            Assert.Contains(drop.FileName, body, StringComparison.Ordinal);
            Assert.Contains(
                $"{fileBytes.LongLength} B",
                body,
                StringComparison.Ordinal);
        }

        using var downloadResponse = await client.GetAsync($"/d/{drop.Slug}");
        Assert.Equal(HttpStatusCode.OK, downloadResponse.StatusCode);
        Assert.Equal(
            fileBytes,
            await downloadResponse.Content.ReadAsByteArrayAsync());

        using var inlineResponse = await client.GetAsync(
            $"/d/{drop.Slug}?inline=true");
        Assert.Equal(HttpStatusCode.OK, inlineResponse.StatusCode);
        Assert.Equal(
            "inline",
            inlineResponse.Content.Headers.ContentDisposition?.DispositionType);
    }

    [Fact]
    public async Task TextHtmlAndSvgInlineRequestsAreForcedToAttachment()
    {
        using var factory = new TeledropWebApplicationFactory();
        var fileBytes = "<script>document.title='owned'</script>"u8.ToArray();
        using var client = CreateClient(factory);

        foreach (var (slug, contentType) in new[]
                 {
                     ("unsafe-html", "text/html"),
                     ("unsafe-svg", "image/svg+xml"),
                 })
        {
            var drop = await AddDropAsync(
                factory,
                slug,
                isPrivate: false,
                dropPasswordHash: null,
                title: "unsafe inline content",
                fileName: $"{slug}.html",
                fileBytes,
                contentType);

            using var response = await client.GetAsync(
                $"/d/{drop.Slug}?inline=true");

            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            Assert.Equal(
                "attachment",
                response.Content.Headers.ContentDisposition?.DispositionType);
            Assert.Equal(
                "nosniff",
                Assert.Single(
                    response.Headers.GetValues(
                        "X-Content-Type-Options")));

            var contentSecurityPolicy = Assert.Single(
                response.Headers.GetValues("Content-Security-Policy"));
            Assert.Contains(
                "default-src 'self'",
                contentSecurityPolicy,
                StringComparison.Ordinal);
            Assert.Contains(
                "script-src 'self' 'nonce-",
                contentSecurityPolicy,
                StringComparison.Ordinal);
            Assert.Contains(
                "object-src 'none'",
                contentSecurityPolicy,
                StringComparison.Ordinal);
            Assert.Contains(
                "frame-ancestors 'self'",
                contentSecurityPolicy,
                StringComparison.Ordinal);
        }
    }

    [Fact]
    public async Task UnlockCookieForOneDropCannotUnlockAnotherDrop()
    {
        using var factory = new TeledropWebApplicationFactory();
        var sharedDropPasswordHash = Argon2.Hash(DropPassword);
        var firstDrop = await AddDropAsync(
            factory,
            slug: "first-locked-drop",
            isPrivate: false,
            dropPasswordHash: sharedDropPasswordHash,
            title: "first title",
            fileName: "first.bin",
            "first"u8.ToArray());
        var secondDrop = await AddDropAsync(
            factory,
            slug: "second-locked-drop",
            isPrivate: false,
            dropPasswordHash: sharedDropPasswordHash,
            title: "second title",
            fileName: "second.bin",
            "second"u8.ToArray());
        using var client = CreateClient(factory);

        await UnlockDropAsync(client, firstDrop.Slug, DropPassword);

        using var pageResponse = await client.GetAsync($"/{secondDrop.Slug}");
        using var downloadResponse = await client.GetAsync(
            $"/d/{secondDrop.Slug}");

        Assert.Equal(HttpStatusCode.Unauthorized, pageResponse.StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, downloadResponse.StatusCode);
    }

    [Fact]
    public async Task ChangingDropPasswordInvalidatesExistingUnlockCookie()
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await AddDropAsync(
            factory,
            slug: "changed-drop-password",
            isPrivate: false,
            dropPasswordHash: Argon2.Hash(DropPassword),
            title: "changed password title",
            fileName: "changed-password.bin",
            "changed password"u8.ToArray());
        using var client = CreateClient(factory);

        await UnlockDropAsync(client, drop.Slug, DropPassword);

        await using (var scope = factory.Services.CreateAsyncScope())
        {
            var dbContext = scope.ServiceProvider
                .GetRequiredService<TeledropDbContext>();
            var storedDrop = await dbContext.Drops.SingleAsync(
                candidate => candidate.Id == drop.Id);
            storedDrop.DropPasswordHash = Argon2.Hash("new-drop-password");
            storedDrop.UpdatedAt = DateTime.UtcNow;
            await dbContext.SaveChangesAsync();
        }

        using var pageResponse = await client.GetAsync($"/{drop.Slug}");
        using var downloadResponse = await client.GetAsync($"/d/{drop.Slug}");

        Assert.Equal(HttpStatusCode.Unauthorized, pageResponse.StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, downloadResponse.StatusCode);
    }

    [Fact]
    public async Task AnonymousPublicDropWithoutPasswordShowsMetadataAndDownloads()
    {
        using var factory = new TeledropWebApplicationFactory();
        var fileBytes = "public-file"u8.ToArray();
        var drop = await AddDropAsync(
            factory,
            slug: "open-public-drop",
            isPrivate: false,
            dropPasswordHash: null,
            title: "public title",
            fileName: "public.bin",
            fileBytes);
        using var client = CreateClient(factory);

        using (var pageResponse = await client.GetAsync($"/{drop.Slug}"))
        {
            Assert.Equal(HttpStatusCode.OK, pageResponse.StatusCode);
            var body = WebUtility.HtmlDecode(
                await pageResponse.Content.ReadAsStringAsync());
            Assert.Contains(drop.Title!, body, StringComparison.Ordinal);
            Assert.Contains(drop.FileName, body, StringComparison.Ordinal);
        }

        using var downloadResponse = await client.GetAsync($"/d/{drop.Slug}");
        Assert.Equal(HttpStatusCode.OK, downloadResponse.StatusCode);
        Assert.Equal(
            fileBytes,
            await downloadResponse.Content.ReadAsByteArrayAsync());
    }

    private static async Task<Drop> AddDropAsync(
        TeledropWebApplicationFactory factory,
        string slug,
        bool isPrivate,
        string? dropPasswordHash,
        string title,
        string fileName,
        byte[] fileBytes,
        string contentType = "application/octet-stream")
    {
        var location = Guid.NewGuid().ToString("N");
        var drop = new Drop
        {
            Id = Guid.NewGuid(),
            Slug = slug,
            Title = title,
            IsPrivate = isPrivate,
            DropPasswordHash = dropPasswordHash,
            FileName = fileName,
            FileHash = Convert.ToHexStringLower(
                SHA256.HashData(fileBytes)),
            FileSizeBytes = fileBytes.LongLength,
            ContentType = contentType,
            Location = location,
            CreatedAt = DateTime.UtcNow,
        };

        await using (var scope = factory.Services.CreateAsyncScope())
        {
            var dbContext = scope.ServiceProvider
                .GetRequiredService<TeledropDbContext>();
            dbContext.Drops.Add(drop);
            await dbContext.SaveChangesAsync();
        }

        await File.WriteAllBytesAsync(
            Path.Combine(factory.ShareDirectory, location),
            fileBytes);

        return drop;
    }

    private static HttpClient CreateClient(
        TeledropWebApplicationFactory factory)
    {
        return factory.CreateClient(
            new WebApplicationFactoryClientOptions
            {
                AllowAutoRedirect = false,
                BaseAddress = new Uri("https://localhost"),
                HandleCookies = true,
            });
    }

    private static async Task UnlockDropAsync(
        HttpClient client,
        string slug,
        string dropPassword)
    {
        using var lockedPage = await client.GetAsync($"/{slug}");
        Assert.Equal(HttpStatusCode.Unauthorized, lockedPage.StatusCode);
        var body = await lockedPage.Content.ReadAsStringAsync();
        var verificationValue = ExtractAntiforgeryValue(body);

        using var response = await PostUnlockAsync(
            client,
            slug,
            dropPassword,
            verificationValue);
        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
    }

    private static async Task<HttpResponseMessage> PostUnlockAsync(
        HttpClient client,
        string slug,
        string dropPassword,
        string verificationValue)
    {
        var formValues = new Dictionary<string, string>
        {
            ["DropPassword"] = dropPassword,
            ["__RequestVerificationToken"] = verificationValue,
        };
        using var content = new FormUrlEncodedContent(formValues);
        return await client.PostAsync($"/{slug}?handler=Unlock", content);
    }

    private static void AssertLoginRedirect(HttpResponseMessage response)
    {
        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        Assert.StartsWith(
            "/login?ReturnUrl=",
            GetPathAndQuery(response),
            StringComparison.Ordinal);
    }

    private static string GetPathAndQuery(HttpResponseMessage response)
    {
        var location = Assert.IsType<Uri>(response.Headers.Location);
        return location.IsAbsoluteUri
            ? location.PathAndQuery
            : location.OriginalString;
    }

    private static string ExtractAntiforgeryValue(string pageBody)
    {
        const string nameMarker = "name=\"__RequestVerificationToken\"";
        const string valueMarker = "value=\"";

        var namePosition = pageBody.IndexOf(
            nameMarker,
            StringComparison.Ordinal);
        Assert.True(
            namePosition >= 0,
            "The page has no antiforgery field.");

        var inputStart = pageBody.LastIndexOf(
            "<input",
            namePosition,
            StringComparison.Ordinal);
        var inputEnd = pageBody.IndexOf('>', namePosition);
        Assert.True(
            inputStart >= 0 && inputEnd > inputStart,
            "The antiforgery field is malformed.");

        var input = pageBody[inputStart..inputEnd];
        var valuePosition = input.IndexOf(
            valueMarker,
            StringComparison.Ordinal);
        Assert.True(
            valuePosition >= 0,
            "The antiforgery field has no value.");

        var valueStart = valuePosition + valueMarker.Length;
        var valueEnd = input.IndexOf('"', valueStart);
        Assert.True(
            valueEnd > valueStart,
            "The antiforgery value is empty.");

        return WebUtility.HtmlDecode(input[valueStart..valueEnd]);
    }
}
