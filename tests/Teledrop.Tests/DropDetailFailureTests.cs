using System.Net;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class DropDetailFailureTests
{
    [Theory]
    [InlineData("GET", "")]
    [InlineData("GET", "FavoriteState")]
    [InlineData("GET", "SharedState")]
    [InlineData("POST", "Metadata")]
    [InlineData("POST", "Access")]
    [InlineData("POST", "Favorite")]
    [InlineData("POST", "Slug")]
    [InlineData("POST", "Delete")]
    public async Task ADeletedDropReturns404ForExistingManagementFormsAndReads(string method, string handler)
    {
        using var factory = new TeledropWebApplicationFactory();
        var deleted = await SeedDropAsync(factory, "deleted", [1]);
        var retained = await SeedDropAsync(factory, "retained", [2]);
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);
        var token = await GetAntiforgeryAsync(client, "/drops/deleted");
        await using (var scope = factory.Services.CreateAsyncScope())
        {
            await scope.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops
                .Where(drop => drop.Id == deleted.Id).ExecuteDeleteAsync();
        }

        foreach (var htmx in new[] { false, true })
        {
            using var request = new HttpRequestMessage(new HttpMethod(method), $"/drops/deleted?handler={handler}");
            if (method == "POST") request.Content = new FormUrlEncodedContent(new Dictionary<string, string>
            {
                ["__RequestVerificationToken"] = token,
                ["DescriptionInput"] = "Must not be saved", ["Access"] = "public",
                ["IsFavorite"] = "true", ["SlugInput"] = "renamed",
            });
            if (htmx) request.Headers.Add("HX-Request", "true");

            using var response = await client.SendAsync(request);

            Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
            Assert.False(response.Headers.Contains("HX-Redirect"));
            Assert.False(response.Headers.Contains("X-Drop-Outcome"));
            Assert.DoesNotContain("retained.bin", await response.Content.ReadAsStringAsync());
        }

        await using var verification = factory.Services.CreateAsyncScope();
        var saved = await verification.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops.SingleAsync();
        Assert.Equal(retained.Id, saved.Id);
        Assert.Null(saved.Description);
        Assert.False(saved.IsFavorite);
        Assert.True(saved.IsPrivate);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("maybe")]
    public async Task FavoriteRejectsMissingOrMalformedStateWithoutChangingTheDrop(string? value)
    {
        using var factory = new TeledropWebApplicationFactory();
        await SeedDropAsync(factory, "source", [1]);
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);
        var form = new Dictionary<string, string>
        {
            ["__RequestVerificationToken"] = await GetAntiforgeryAsync(client, "/drops/source"),
        };
        if (value is not null) form["IsFavorite"] = value;
        using var request = new HttpRequestMessage(HttpMethod.Post, "/drops/source?handler=Favorite")
        {
            Content = new FormUrlEncodedContent(form),
        };
        request.Headers.Add("HX-Request", "true");

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        await using var scope = factory.Services.CreateAsyncScope();
        var saved = await scope.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops.SingleAsync();
        Assert.False(saved.IsFavorite);
        Assert.Null(saved.UpdatedAt);
    }

    [Theory]
    [InlineData("not-a-number")]
    [InlineData("2147483648")]
    public async Task InvalidPageQueriesFallBackToTheFirstPage(string pageNumber)
    {
        using var factory = new TeledropWebApplicationFactory();
        await SeedDropAsync(factory, "source", [1]);
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);

        var body = await client.GetStringAsync($"/?handler=DropList&pageNumber={pageNumber}&currentSlug=source");

        var attribute = Regex.Match(body, "data-list-state=\"([^\"]+)\"");
        Assert.True(attribute.Success);
        using var state = JsonDocument.Parse(WebUtility.HtmlDecode(attribute.Groups[1].Value));
        Assert.Equal(1, state.RootElement.GetProperty("pageNumber").GetInt32());
        Assert.Equal("source", state.RootElement.GetProperty("currentSlug").GetString());
        Assert.Contains("source.bin", body);
        Assert.DoesNotContain("<html", body);
    }
}
