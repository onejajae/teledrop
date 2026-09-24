using System.Net;
using Isopoh.Cryptography.Argon2;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class DropAccessTests
{
    private const string DropPassword = "drop-password";

    [Fact]
    public async Task LockedPublicDropReturns401WithoutMetadata()
    {
        using var factory = new TeledropWebApplicationFactory();
        var fileBytes = Enumerable.Repeat((byte)0x2a, 37).ToArray();
        var drop = await SeedDropAsync(
            factory, "locked-metadata", fileBytes, seed =>
            {
                seed.IsPrivate = false;
                seed.DropPasswordHash = Argon2.Hash(DropPassword);
                seed.Title = "hidden-title";
                seed.FileName = "hidden-file.bin";
            });
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
        var drop = await SeedDropAsync(
            factory, "private-access", "private file"u8.ToArray(), seed =>
            {
                seed.IsPrivate = true;
                seed.DropPasswordHash = null;
                seed.Title = "private title";
                seed.FileName = "private.bin";
            });
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
        var drop = await SeedDropAsync(
            factory, "password-check", fileBytes, seed =>
            {
                seed.IsPrivate = false;
                seed.DropPasswordHash = Argon2.Hash(DropPassword);
                seed.Title = "unlocked title";
                seed.FileName = "unlocked.bin";
                seed.ContentType = "image/png";
            });
        using var client = CreateClient(factory);

        using var lockedPage = await client.GetAsync($"/{drop.Slug}");
        Assert.Equal(HttpStatusCode.Unauthorized, lockedPage.StatusCode);
        var lockedBody = await lockedPage.Content.ReadAsStringAsync();
        var verificationValue = ExtractAntiforgery(lockedBody);

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
            verificationValue = ExtractAntiforgery(lockedBody);
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
            Assert.Contains("secure", setCookie, StringComparison.OrdinalIgnoreCase);
            Assert.Contains("path=/", setCookie, StringComparison.OrdinalIgnoreCase);
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
            var drop = await SeedDropAsync(
                factory, slug, fileBytes, seed =>
                {
                    seed.IsPrivate = false;
                    seed.DropPasswordHash = null;
                    seed.Title = "unsafe inline content";
                    seed.FileName = $"{slug}.html";
                    seed.ContentType = contentType;
                });

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
        var firstDrop = await SeedDropAsync(
            factory, "first-locked-drop", "first"u8.ToArray(), seed =>
            {
                seed.IsPrivate = false;
                seed.DropPasswordHash = sharedDropPasswordHash;
                seed.Title = "first title";
                seed.FileName = "first.bin";
            });
        var secondDrop = await SeedDropAsync(
            factory, "second-locked-drop", "second"u8.ToArray(), seed =>
            {
                seed.IsPrivate = false;
                seed.DropPasswordHash = sharedDropPasswordHash;
                seed.Title = "second title";
                seed.FileName = "second.bin";
            });
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
        var drop = await SeedDropAsync(
            factory, "changed-drop-password", "changed password"u8.ToArray(), seed =>
            {
                seed.IsPrivate = false;
                seed.DropPasswordHash = Argon2.Hash(DropPassword);
                seed.Title = "changed password title";
                seed.FileName = "changed-password.bin";
            });
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
        var drop = await SeedDropAsync(
            factory, "open-public-drop", fileBytes, seed =>
            {
                seed.IsPrivate = false;
                seed.DropPasswordHash = null;
                seed.Title = "public title";
                seed.FileName = "public.bin";
            });
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

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task MissingDropIsHiddenFromAnonymousButNotOwner(bool owner)
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        if (owner) await LogInOwnerAsync(client);
        var token = await GetAntiforgeryAsync(client, owner ? "/" : "/login");

        using var page = await client.GetAsync("/missing");
        using var download = await client.GetAsync("/d/missing");
        using var unlock = await PostUnlockAsync(client, "missing", DropPassword, token);

        foreach (var response in new[] { page, download, unlock })
        {
            if (owner) Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
            else AssertLoginRedirect(response);
            AssertNoUnlockCookie(response);
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task OwnerCanReadAndUnlockProtectedDropsWithoutAGrant(bool isPrivate)
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await AddProtectedDropAsync(factory, isPrivate);
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);

        await AssertReadStatusAsync(client, drop.Slug, HttpStatusCode.OK);
        var token = await GetAntiforgeryAsync(client, $"/drops/{drop.Slug}");
        using var response = await PostUnlockAsync(client, drop.Slug, "wrong-password", token);

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        Assert.Equal($"/{drop.Slug}", GetPathAndQuery(response));
        AssertNoUnlockCookie(response);
    }

    [Fact]
    public async Task PublicDropWithoutPasswordDoesNotIssueAGrantOnUnlock()
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await SeedDropAsync(
            factory, "open", "open"u8.ToArray(), seed =>
            {
                seed.IsPrivate = false;
                seed.DropPasswordHash = null;
                seed.Title = "Open Drop";
                seed.FileName = "open.bin";
            });
        using var client = CreateClient(factory);
        var token = await GetAntiforgeryAsync(client, "/login");

        using var response = await PostUnlockAsync(client, drop.Slug, "anything", token);

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        Assert.Equal($"/{drop.Slug}", GetPathAndQuery(response));
        AssertNoUnlockCookie(response);
        await AssertReadStatusAsync(client, drop.Slug, HttpStatusCode.OK);
    }

    [Fact]
    public async Task PrivateDropDoesNotAcceptAnExistingGrantOrItsPassword()
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await AddProtectedDropAsync(factory);
        using var client = CreateClient(factory);
        await UnlockDropAsync(client, drop.Slug, DropPassword);
        await using (var scope = factory.Services.CreateAsyncScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<TeledropDbContext>();
            (await db.Drops.SingleAsync()).IsPrivate = true;
            await db.SaveChangesAsync();
        }
        var token = await GetAntiforgeryAsync(client, "/login");

        using var page = await client.GetAsync($"/{drop.Slug}");
        using var download = await client.GetAsync($"/d/{drop.Slug}");
        using var unlock = await PostUnlockAsync(client, drop.Slug, DropPassword, token);

        foreach (var response in new[] { page, download, unlock })
        {
            AssertLoginRedirect(response);
            AssertNoUnlockCookie(response);
        }
    }

    [Theory]
    [InlineData("")]
    [InlineData("wrong-password")]
    public async Task ExistingGrantDoesNotBypassSubmittedPasswordAndIsNotRevoked(string password)
    {
        var clock = new ManualTimeProvider();
        using var factory = new TeledropWebApplicationFactory(timeProvider: clock);
        var drop = await AddProtectedDropAsync(factory);
        using var client = CreateClient(factory);
        await UnlockDropAsync(client, drop.Slug, DropPassword);
        clock.Advance(TimeSpan.FromMinutes(30));
        var token = await GetAntiforgeryAsync(client, "/login");

        using var response = await PostUnlockAsync(client, drop.Slug, password, token);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        var body = WebUtility.HtmlDecode(await response.Content.ReadAsStringAsync());
        Assert.Contains("드롭 비밀번호가 올바르지 않습니다.", body);
        if (password.Length > 0) Assert.DoesNotContain($"value=\"{password}\"", body);
        Assert.DoesNotContain(drop.Title!, body);
        Assert.DoesNotContain(drop.FileName, body);
        AssertNoUnlockCookie(response);
        await AssertReadStatusAsync(client, drop.Slug, HttpStatusCode.OK);

        clock.Advance(TimeSpan.FromMinutes(30));
        await AssertReadStatusAsync(client, drop.Slug, HttpStatusCode.Unauthorized);
    }

    [Fact]
    public async Task GrantExpiresAtOneHourAndReadsDoNotRenewIt()
    {
        var clock = new ManualTimeProvider();
        using var factory = new TeledropWebApplicationFactory(timeProvider: clock);
        var drop = await AddProtectedDropAsync(factory);
        using var client = CreateClient(factory);
        await UnlockDropAsync(client, drop.Slug, DropPassword);

        clock.Advance(TimeSpan.FromHours(1) - TimeSpan.FromTicks(1));
        await AssertReadStatusAsync(client, drop.Slug, HttpStatusCode.OK);
        clock.Advance(TimeSpan.FromTicks(1));
        await AssertReadStatusAsync(client, drop.Slug, HttpStatusCode.Unauthorized);
        clock.Advance(TimeSpan.FromMinutes(1));
        await AssertReadStatusAsync(client, drop.Slug, HttpStatusCode.Unauthorized);
    }

    [Fact]
    public async Task CorrectPasswordSubmissionRenewsAnExistingGrant()
    {
        var clock = new ManualTimeProvider();
        using var factory = new TeledropWebApplicationFactory(timeProvider: clock);
        var drop = await AddProtectedDropAsync(factory);
        using var client = CreateClient(factory);
        await UnlockDropAsync(client, drop.Slug, DropPassword);
        clock.Advance(TimeSpan.FromMinutes(30));
        var token = await GetAntiforgeryAsync(client, "/login");

        using var response = await PostUnlockAsync(client, drop.Slug, DropPassword, token);

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        Assert.StartsWith("teledrop.unlock.", Assert.Single(response.Headers.GetValues("Set-Cookie")));
        clock.Advance(TimeSpan.FromMinutes(30) + TimeSpan.FromTicks(1));
        await AssertReadStatusAsync(client, drop.Slug, HttpStatusCode.OK);
        clock.Advance(TimeSpan.FromMinutes(30) - TimeSpan.FromTicks(1));
        await AssertReadStatusAsync(client, drop.Slug, HttpStatusCode.Unauthorized);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task MalformedOrTamperedGrantCannotReadTheDrop(bool tamper)
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await AddProtectedDropAsync(factory);
        using var unlockedClient = CreateClient(factory);
        var cookie = await UnlockDropAsync(unlockedClient, drop.Slug, DropPassword);
        var valueStart = cookie.IndexOf('=') + 1;
        var invalidCookie = tamper
            ? cookie[..valueStart] + (cookie[valueStart] == 'A' ? 'B' : 'A') + cookie[(valueStart + 1)..]
            : cookie[..valueStart] + "not-a-protected-cookie";
        using var client = CreateClient(factory, handleCookies: false);
        client.DefaultRequestHeaders.Add("Cookie", invalidCookie);

        await AssertReadStatusAsync(client, drop.Slug, HttpStatusCode.Unauthorized);
        // The original, unmodified grant still works.
        await AssertReadStatusAsync(unlockedClient, drop.Slug, HttpStatusCode.OK);
    }

    [Fact]
    public async Task GrantRemainsBoundToItsOriginalSlug()
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await AddProtectedDropAsync(factory);
        using var client = CreateClient(factory);
        await UnlockDropAsync(client, drop.Slug, DropPassword);
        await using (var scope = factory.Services.CreateAsyncScope())
        {
            var slugs = scope.ServiceProvider.GetRequiredService<DropSlugs>();
            Assert.Equal(ChangeDropSlugStatus.Succeeded,
                (await slugs.ChangeAsync(drop.Slug, "renamed", default)).Status);
        }

        await AssertReadStatusAsync(client, "renamed", HttpStatusCode.Unauthorized);
        using var oldLink = await client.GetAsync($"/{drop.Slug}");
        AssertLoginRedirect(oldLink);

        // Renaming does not create revocation state. Restoring the old Slug
        // with the same password hash restores the still-unexpired grant.
        await using (var scope = factory.Services.CreateAsyncScope())
        {
            var slugs = scope.ServiceProvider.GetRequiredService<DropSlugs>();
            Assert.Equal(ChangeDropSlugStatus.Succeeded,
                (await slugs.ChangeAsync("renamed", drop.Slug, default)).Status);
        }
        await AssertReadStatusAsync(client, drop.Slug, HttpStatusCode.OK);
    }

    [Fact]
    public async Task UnlockStillRequiresAntiforgeryBeforeIssuingAGrant()
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await AddProtectedDropAsync(factory);
        using var client = CreateClient(factory);
        using var body = new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["DropPassword"] = DropPassword,
        });

        using var response = await client.PostAsync($"/{drop.Slug}?handler=Unlock", body);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        AssertNoUnlockCookie(response);
        await AssertReadStatusAsync(client, drop.Slug, HttpStatusCode.Unauthorized);
    }

    private static Task<Drop> AddProtectedDropAsync(TeledropWebApplicationFactory factory, bool isPrivate = false)
        => SeedDropAsync(
            factory, "protected", "protected bytes"u8.ToArray(), seed =>
            {
                seed.IsPrivate = isPrivate;
                seed.DropPasswordHash = Argon2.Hash(DropPassword);
                seed.Title = "Protected title";
                seed.FileName = "protected.bin";
            });

    private static async Task AssertReadStatusAsync(HttpClient client, string slug, HttpStatusCode expected)
    {
        using var page = await client.GetAsync($"/{slug}");
        using var download = await client.GetAsync($"/d/{slug}");
        Assert.Equal(expected, page.StatusCode);
        Assert.Equal(expected, download.StatusCode);
        AssertNoUnlockCookie(page);
        AssertNoUnlockCookie(download);
        if (expected == HttpStatusCode.Unauthorized)
            Assert.Empty(await download.Content.ReadAsByteArrayAsync());
    }

    private static void AssertNoUnlockCookie(HttpResponseMessage response)
    {
        if (response.Headers.TryGetValues("Set-Cookie", out var cookies))
            Assert.DoesNotContain(cookies, cookie => cookie.StartsWith("teledrop.unlock.", StringComparison.Ordinal));
    }

    private sealed class ManualTimeProvider : TimeProvider
    {
        private DateTimeOffset now = DateTimeOffset.UtcNow;
        public override DateTimeOffset GetUtcNow() => now;
        internal void Advance(TimeSpan elapsed) => now += elapsed;
    }

    private static async Task<string> UnlockDropAsync(
        HttpClient client,
        string slug,
        string dropPassword)
    {
        using var lockedPage = await client.GetAsync($"/{slug}");
        Assert.Equal(HttpStatusCode.Unauthorized, lockedPage.StatusCode);
        var body = await lockedPage.Content.ReadAsStringAsync();
        var verificationValue = ExtractAntiforgery(body);

        using var response = await PostUnlockAsync(
            client,
            slug,
            dropPassword,
            verificationValue);
        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        return Assert.Single(response.Headers.GetValues("Set-Cookie")).Split(';', 2)[0];
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

}
