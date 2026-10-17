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
                seed.Description = "hidden-title";
                seed.FileName = "hidden-file.bin";
            });
        using var client = CreateClient(factory);

        using var response = await client.GetAsync($"/{drop.Slug}");

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        var body = WebUtility.HtmlDecode(
            await response.Content.ReadAsStringAsync());
        Assert.DoesNotContain(drop.Description!, body, StringComparison.Ordinal);
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
                seed.Description = "private title";
                seed.FileName = "private.bin";
            });
        using var client = CreateClient(factory);

        using var pageResponse = await client.GetAsync($"/{drop.Slug}");
        using var downloadResponse = await client.GetAsync($"/d/{drop.Slug}");

        AssertLoginRedirect(pageResponse);
        AssertLoginRedirect(downloadResponse);
    }

    [Fact]
    public async Task PasswordSetThroughOwnerEndpointUnlocksOnlyWithTheSubmittedPassword()
    {
        using var factory = new TeledropWebApplicationFactory();
        var bytes = "newly protected file"u8.ToArray();
        var drop = await SeedDropAsync(factory, "new-password", bytes, seed =>
        {
            seed.FileName = "unlocked.bin";
            seed.Description = "unlocked title";
            seed.ContentType = "image/png";
        });
        const string newPassword = " 새 비밀번호 🔑 ";
        using var owner = CreateClient(factory);
        await LogInOwnerAsync(owner);
        using var accessForm = new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["Access"] = "password",
            ["NewDropPassword"] = newPassword,
            ["__RequestVerificationToken"] = await GetAntiforgeryAsync(owner, $"/drops/{drop.Slug}"),
        });
        using var accessResponse = await owner.PostAsync($"/drops/{drop.Slug}?handler=Access", accessForm);
        Assert.Equal(HttpStatusCode.Redirect, accessResponse.StatusCode);

        // This client has no Owner Session. Its grant must validate the hash
        // produced through the real access-setting endpoint, not a seeded hash.
        using var anonymous = CreateClient(factory);
        using var locked = await anonymous.GetAsync($"/{drop.Slug}");
        Assert.Equal(HttpStatusCode.Unauthorized, locked.StatusCode);
        var token = ExtractAntiforgery(await locked.Content.ReadAsStringAsync());
        using var wrong = await PostUnlockAsync(anonymous, drop.Slug, newPassword.Trim(), token);
        Assert.Equal(HttpStatusCode.Unauthorized, wrong.StatusCode);
        AssertNoUnlockCookie(wrong);
        await AssertReadStatusAsync(anonymous, drop.Slug, HttpStatusCode.Unauthorized);

        using var unlocked = await PostUnlockAsync(anonymous, drop.Slug, newPassword, token);
        Assert.Equal(HttpStatusCode.Redirect, unlocked.StatusCode);
        Assert.Equal($"/{drop.Slug}", GetPathAndQuery(unlocked));
        var cookie = Assert.Single(unlocked.Headers.GetValues("Set-Cookie"));
        Assert.Contains("httponly", cookie, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("secure", cookie, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("path=/", cookie, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("samesite=lax", cookie, StringComparison.OrdinalIgnoreCase);
        using var page = await anonymous.GetAsync($"/{drop.Slug}");
        Assert.Equal(HttpStatusCode.OK, page.StatusCode);
        var html = WebUtility.HtmlDecode(await page.Content.ReadAsStringAsync());
        Assert.Contains(drop.FileName, html);
        Assert.Contains(drop.Description!, html);
        Assert.Contains($"{bytes.LongLength} B", html);
        using var download = await anonymous.GetAsync($"/d/{drop.Slug}");
        Assert.Equal(HttpStatusCode.OK, download.StatusCode);
        Assert.Equal(bytes, await download.Content.ReadAsByteArrayAsync());
        using var inline = await anonymous.GetAsync($"/d/{drop.Slug}?inline=true");
        Assert.Equal(HttpStatusCode.OK, inline.StatusCode);
        Assert.Equal("inline", inline.Content.Headers.ContentDisposition?.DispositionType);
    }

    [Theory]
    [InlineData(false, "public")]
    [InlineData(true, "public")]
    [InlineData(false, "locked")]
    [InlineData(true, "locked")]
    [InlineData(false, "unlocked")]
    [InlineData(true, "unlocked")]
    [InlineData(false, "wrong-password")]
    [InlineData(true, "wrong-password")]
    public async Task PublicPageResponsesPreventCachingForEveryAccessState(bool htmx, string state)
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = state == "public"
            ? await SeedDropAsync(factory, "open", [1], seed => seed.IsPrivate = false)
            : await AddProtectedDropAsync(factory);
        using var client = CreateClient(factory);
        if (state == "unlocked") await UnlockDropAsync(client, drop.Slug, DropPassword);

        using var request = new HttpRequestMessage(HttpMethod.Get, $"/{drop.Slug}");
        if (state == "wrong-password")
        {
            using var locked = await client.GetAsync($"/{drop.Slug}");
            var token = ExtractAntiforgery(await locked.Content.ReadAsStringAsync());
            request.Method = HttpMethod.Post;
            request.RequestUri = new Uri($"/{drop.Slug}?handler=Unlock", UriKind.Relative);
            request.Content = new FormUrlEncodedContent(new Dictionary<string, string>
            {
                ["DropPassword"] = "wrong-password",
                ["__RequestVerificationToken"] = token,
            });
        }
        if (htmx) request.Headers.Add("HX-Request", "true");

        using var response = await client.SendAsync(request);

        Assert.Equal(state is "locked" or "wrong-password"
            ? HttpStatusCode.Unauthorized : HttpStatusCode.OK, response.StatusCode);
        Assert.True(response.Headers.CacheControl?.NoStore);
        var html = await response.Content.ReadAsStringAsync();
        Assert.Contains("id=\"public-drop\"", html);
        Assert.Equal(!htmx, html.Contains("<html", StringComparison.OrdinalIgnoreCase));
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
                seed.Description = "first title";
                seed.FileName = "first.bin";
            });
        var secondDrop = await SeedDropAsync(
            factory, "second-locked-drop", "second"u8.ToArray(), seed =>
            {
                seed.IsPrivate = false;
                seed.DropPasswordHash = sharedDropPasswordHash;
                seed.Description = "second title";
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
                seed.Description = "changed password title";
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
                seed.Description = "public title";
                seed.FileName = "public.bin";
            });
        using var client = CreateClient(factory);

        using (var pageResponse = await client.GetAsync($"/{drop.Slug}"))
        {
            Assert.Equal(HttpStatusCode.OK, pageResponse.StatusCode);
            var body = WebUtility.HtmlDecode(
                await pageResponse.Content.ReadAsStringAsync());
            Assert.Contains(drop.Description!, body, StringComparison.Ordinal);
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

    [Fact]
    public async Task OwnerCanReadAndUnlockProtectedDropsWithoutAGrant()
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await AddProtectedDropAsync(factory);
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
                seed.Description = "Open Drop";
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
    public async Task MakingADropPrivateDropsItsPasswordAndExistingGrants()
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await AddProtectedDropAsync(factory);
        using var client = CreateClient(factory);
        await UnlockDropAsync(client, drop.Slug, DropPassword);
        await SetAccessAsync(factory, drop.Slug, DropAccessLevel.Private);
        await using (var scope = factory.Services.CreateAsyncScope())
        {
            var stored = await scope.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops.SingleAsync();
            Assert.Null(stored.DropPasswordHash);
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

    [Fact]
    public async Task RepublishingWithTheSamePasswordStillNeedsANewUnlock()
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await AddProtectedDropAsync(factory);
        using var client = CreateClient(factory);
        await UnlockDropAsync(client, drop.Slug, DropPassword);
        await SetAccessAsync(factory, drop.Slug, DropAccessLevel.Private);
        await SetAccessAsync(factory, drop.Slug, DropAccessLevel.Password, DropPassword);

        await AssertReadStatusAsync(client, drop.Slug, HttpStatusCode.Unauthorized);
    }

    private static async Task SetAccessAsync(
        TeledropWebApplicationFactory factory, string slug, DropAccessLevel level, string? password = null)
    {
        await using var scope = factory.Services.CreateAsyncScope();
        var result = await scope.ServiceProvider.GetRequiredService<DropUseCases>()
            .SetAccessAsync(slug, level, password, default);
        Assert.Equal(SetDropAccessResult.Succeeded, result);
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
        Assert.DoesNotContain(drop.Description!, body);
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

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task RenamingTheCookieCannotTransferItsGrantToAnotherSlug(bool renameDrop)
    {
        using var factory = new TeledropWebApplicationFactory();
        var source = await AddProtectedDropAsync(factory);
        using var unlocked = CreateClient(factory);
        var cookie = await UnlockDropAsync(unlocked, source.Slug, DropPassword);
        const string targetSlug = "different-slug";
        if (renameDrop)
        {
            await using var scope = factory.Services.CreateAsyncScope();
            var result = await scope.ServiceProvider.GetRequiredService<DropSlugs>()
                .ChangeAsync(source.Slug, targetSlug, default);
            Assert.Equal(ChangeDropSlugStatus.Succeeded, result.Status);
        }
        else
        {
            await SeedDropAsync(factory, targetSlug, "other protected bytes"u8.ToArray(), seed =>
            {
                seed.IsPrivate = false;
                seed.DropPasswordHash = source.DropPasswordHash;
                seed.FileName = source.FileName;
                seed.Description = source.Description;
            });
        }

        // The password fingerprint still matches. Only the protected payload's
        // Slug can reject a grant whose cookie name has been changed by a caller.
        using var client = CreateClient(factory, handleCookies: false);
        client.DefaultRequestHeaders.Add("Cookie",
            $"teledrop.unlock.{targetSlug}{cookie[cookie.IndexOf('=')..]}");
        using var page = await client.GetAsync($"/{targetSlug}");
        using var download = await client.GetAsync($"/d/{targetSlug}");

        Assert.Equal(HttpStatusCode.Unauthorized, page.StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, download.StatusCode);
        var html = WebUtility.HtmlDecode(await page.Content.ReadAsStringAsync());
        Assert.DoesNotContain(source.FileName, html);
        Assert.DoesNotContain(source.Description!, html);
        Assert.Empty(await download.Content.ReadAsByteArrayAsync());
        AssertNoUnlockCookie(page);
        AssertNoUnlockCookie(download);
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

    private static Task<Drop> AddProtectedDropAsync(TeledropWebApplicationFactory factory)
        => SeedDropAsync(
            factory, "protected", "protected bytes"u8.ToArray(), seed =>
            {
                seed.IsPrivate = false;
                seed.DropPasswordHash = Argon2.Hash(DropPassword);
                seed.Description = "Protected title";
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
