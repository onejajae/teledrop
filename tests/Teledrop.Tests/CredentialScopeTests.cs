using System.Net;
using Isopoh.Cryptography.Argon2;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class CredentialScopeTests
{
    private const string DropPassword = "read-this-drop-only";

    [Theory]
    [InlineData("api-key")]
    [InlineData("drop-grant")]
    public async Task LimitedCredentialsCannotReadPrivateDropsOrOpenManagement(string credential)
    {
        using var factory = new TeledropWebApplicationFactory();
        var shared = await SeedProtectedDropAsync(factory);
        var hidden = await SeedDropAsync(factory, "private-scope", [4, 5, 6]);
        using var client = CreateClient(factory);
        await AuthenticateLimitedCredentialAsync(client, credential, shared.Slug);

        using var management = await client.GetAsync($"/drops/{shared.Slug}");
        AssertLoginRequired(management);
        using var privatePage = await client.GetAsync($"/{hidden.Slug}");
        using var privateDownload = await client.GetAsync($"/d/{hidden.Slug}");
        AssertLoginRequired(privatePage);
        AssertLoginRequired(privateDownload);
        Assert.DoesNotContain(hidden.FileName, await privatePage.Content.ReadAsStringAsync());

        using var sharedPage = await client.GetAsync($"/{shared.Slug}");
        using var sharedDownload = await client.GetAsync($"/d/{shared.Slug}");
        var expected = credential == "drop-grant" ? HttpStatusCode.OK : HttpStatusCode.Unauthorized;
        Assert.Equal(expected, sharedPage.StatusCode);
        Assert.Equal(expected, sharedDownload.StatusCode);
        if (credential == "drop-grant")
            Assert.Equal(new byte[] { 1, 2, 3 }, await sharedDownload.Content.ReadAsByteArrayAsync());
        else
        {
            Assert.Empty(await sharedDownload.Content.ReadAsByteArrayAsync());
            Assert.DoesNotContain(shared.FileName, await sharedPage.Content.ReadAsStringAsync());
        }
    }

    [Theory]
    [InlineData("api-key", "Metadata")]
    [InlineData("api-key", "Access")]
    [InlineData("api-key", "Favorite")]
    [InlineData("api-key", "Slug")]
    [InlineData("api-key", "Delete")]
    [InlineData("drop-grant", "Metadata")]
    [InlineData("drop-grant", "Access")]
    [InlineData("drop-grant", "Favorite")]
    [InlineData("drop-grant", "Slug")]
    [InlineData("drop-grant", "Delete")]
    public async Task LimitedCredentialsCannotChangeADropEvenWithValidAntiforgery(
        string credential, string handler)
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await SeedProtectedDropAsync(factory);
        using var client = CreateClient(factory);
        await AuthenticateLimitedCredentialAsync(client, credential, drop.Slug);
        // Use a real anonymous antiforgery token so a 400 cannot mask an
        // accidental grant of Owner authority.
        using var form = new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["__RequestVerificationToken"] = await GetAntiforgeryAsync(client, "/login"),
            ["DescriptionInput"] = "unauthorized edit",
            ["Access"] = "public",
            ["IsFavorite"] = "true",
            ["SlugInput"] = "unauthorized-rename",
        });

        using var response = await client.PostAsync($"/drops/{drop.Slug}?handler={handler}", form);

        AssertLoginRequired(response);
        await using var scope = factory.Services.CreateAsyncScope();
        var persisted = await scope.ServiceProvider.GetRequiredService<TeledropDbContext>()
            .Drops.AsNoTracking().SingleAsync();
        Assert.Equivalent(drop, persisted, strict: true);
        var file = Assert.Single(Directory.EnumerateFiles(factory.ShareDirectory));
        Assert.Equal(Path.Combine(factory.ShareDirectory, drop.Location), file);
        Assert.Equal(new byte[] { 1, 2, 3 }, await File.ReadAllBytesAsync(file));
    }

    private static Task<Drop> SeedProtectedDropAsync(TeledropWebApplicationFactory factory)
        => SeedDropAsync(factory, "protected-scope", [1, 2, 3], drop =>
        {
            drop.IsPrivate = false;
            drop.DropPasswordHash = Argon2.Hash(DropPassword);
            drop.Description = "unchanged description";
            drop.UpdatedAt = new DateTime(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        });

    private static async Task AuthenticateLimitedCredentialAsync(
        HttpClient client, string credential, string slug)
    {
        if (credential == "api-key")
        {
            client.DefaultRequestHeaders.Add("X-API-Key", TeledropWebApplicationFactory.ApiKey);
            return;
        }

        using var locked = await client.GetAsync($"/{slug}");
        Assert.Equal(HttpStatusCode.Unauthorized, locked.StatusCode);
        using var form = new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["__RequestVerificationToken"] = ExtractAntiforgery(await locked.Content.ReadAsStringAsync()),
            ["DropPassword"] = DropPassword,
        });
        using var unlocked = await client.PostAsync($"/{slug}?handler=Unlock", form);
        Assert.Equal(HttpStatusCode.Redirect, unlocked.StatusCode);
        Assert.Contains(unlocked.Headers.GetValues("Set-Cookie"),
            cookie => cookie.StartsWith("teledrop.unlock.", StringComparison.Ordinal));
    }

    private static void AssertLoginRequired(HttpResponseMessage response)
    {
        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        var location = Assert.IsType<Uri>(response.Headers.Location);
        Assert.StartsWith("/login?ReturnUrl=", location.IsAbsoluteUri ? location.PathAndQuery : location.OriginalString);
    }
}
