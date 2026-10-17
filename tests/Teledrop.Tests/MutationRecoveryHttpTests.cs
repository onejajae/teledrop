using System.Net;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class MutationRecoveryHttpTests
{
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task RecoveryReadsTheOriginalIdentityAndNeverMutatesAReusedSlug(bool deleted)
    {
        using var factory = new TeledropWebApplicationFactory();
        var original = await SeedDropAsync(factory, "original", [1], drop => drop.IsPrivate = false);
        await using (var scope = factory.Services.CreateAsyncScope())
        {
            if (deleted)
                Assert.Equal(DropCommandResult.Succeeded,
                    await scope.ServiceProvider.GetRequiredService<DropUseCases>().DeleteAsync("original", default));
            else
                Assert.Equal(ChangeDropSlugStatus.Succeeded,
                    (await scope.ServiceProvider.GetRequiredService<DropSlugs>().ChangeAsync("original", "renamed", default)).Status);
        }
        var replacement = await SeedDropAsync(factory, "original", [2], drop => drop.Description = "Must remain unchanged");
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);

        using var response = await client.GetAsync($"/drops/original?handler=RecoveryState&id={original.Id}");

        Assert.True(response.Headers.CacheControl?.NoStore);
        Assert.Equal(deleted ? HttpStatusCode.NoContent : HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(deleted ? "false" : "true", Assert.Single(response.Headers.GetValues("X-Drop-Exists")));
        Assert.Equal(deleted ? "/?deleted=True" : "/drops/renamed", Assert.Single(response.Headers.GetValues("X-Drop-Location")));
        var body = await response.Content.ReadAsStringAsync();
        Assert.DoesNotContain("<html", body);
        Assert.DoesNotContain("Must remain unchanged", body);
        if (deleted) Assert.Empty(body);
        else
        {
            Assert.Contains("data-access-level=\"public\"", body);
            Assert.Contains("/renamed", body);
        }
        await using var verification = factory.Services.CreateAsyncScope();
        var db = verification.ServiceProvider.GetRequiredService<TeledropDbContext>();
        var savedReplacement = await db.Drops.SingleAsync(drop => drop.Slug == "original");
        Assert.Equal(replacement.Id, savedReplacement.Id);
        Assert.True(savedReplacement.IsPrivate);
        Assert.Equal("Must remain unchanged", savedReplacement.Description);
        Assert.Equal(new byte[] { 2 }, await File.ReadAllBytesAsync(Path.Combine(factory.ShareDirectory, replacement.Location)));
        Assert.Equal(deleted ? 1 : 2, await db.Drops.CountAsync());
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task RecoveryStillRequiresTheOwnerSession(bool htmx)
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await SeedDropAsync(factory, "hidden", [1]);
        using var client = CreateClient(factory);
        using var request = new HttpRequestMessage(HttpMethod.Get, $"/drops/hidden?handler=RecoveryState&id={drop.Id}");
        if (htmx) request.Headers.Add("HX-Request", "true");

        using var response = await client.SendAsync(request);

        if (htmx) Assert.Equal("/login", Assert.Single(response.Headers.GetValues("HX-Redirect")));
        else Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        Assert.False(response.Headers.Contains("X-Drop-Exists"));
        Assert.False(response.Headers.Contains("X-Drop-Location"));
        Assert.DoesNotContain("hidden.bin", await response.Content.ReadAsStringAsync());
    }

    [Theory]
    [InlineData("")]
    [InlineData("not-a-guid")]
    [InlineData("00000000-0000-0000-0000-000000000000")]
    public async Task RecoveryRejectsAnInvalidIdentity(string id)
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);

        using var response = await client.GetAsync($"/drops/ignored?handler=RecoveryState&id={id}");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.False(response.Headers.Contains("X-Drop-Location"));
    }
}
