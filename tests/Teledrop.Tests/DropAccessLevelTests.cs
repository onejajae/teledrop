using System.Net;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class DropAccessLevelTests
{
    [Fact]
    public async Task DatabaseRejectsAPrivateDropWithAPassword()
    {
        using var factory = new TeledropWebApplicationFactory();

        await Assert.ThrowsAsync<DbUpdateException>(() => SeedDropAsync(factory, "hidden", [1], drop =>
        {
            drop.IsPrivate = true;
            drop.DropPasswordHash = "hash";
        }));
    }

    [Fact]
    public async Task ListShowsOneIconForTheAccessLevel()
    {
        using var factory = new TeledropWebApplicationFactory();
        await SeedDropAsync(factory, "hidden", [1]);
        await SeedDropAsync(factory, "shared", [2], drop => drop.IsPrivate = false);
        await SeedDropAsync(factory, "locked", [3], drop =>
        {
            drop.IsPrivate = false;
            drop.DropPasswordHash = "hash";
        });
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);

        var body = WebUtility.HtmlDecode(await client.GetStringAsync("/"));

        string Row(string slug)
        {
            var start = body.IndexOf($"data-drop-slug=\"{slug}\"", StringComparison.Ordinal);
            return body[start..body.IndexOf("</a>", start, StringComparison.Ordinal)];
        }
        Assert.DoesNotContain("td-row-status", Row("hidden"));
        Assert.Contains("aria-label=\"링크 공개\"", Row("shared"));
        Assert.DoesNotContain("비밀번호 공개", Row("shared"));
        Assert.Contains("aria-label=\"비밀번호 공개\"", Row("locked"));
        Assert.DoesNotContain("링크 공개", Row("locked"));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("hidden")]
    [InlineData("7")]
    public async Task AccessHandlerRejectsUnknownLevels(string? level)
    {
        using var factory = new TeledropWebApplicationFactory();
        await SeedDropAsync(factory, "source", [1]);
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);
        var form = new Dictionary<string, string>
        {
            ["__RequestVerificationToken"] = await GetAntiforgeryAsync(client, "/drops/source"),
        };
        if (level is not null) form["Access"] = level;

        using var response = await client.PostAsync("/drops/source?handler=Access", new FormUrlEncodedContent(form));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        await using var scope = factory.Services.CreateAsyncScope();
        var drop = await scope.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops.SingleAsync();
        Assert.Equal(DropAccessLevel.Private, drop.AccessLevel);
    }
}
