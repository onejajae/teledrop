using System.Net;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class UiRegressionTests
{
    [Theory]
    [InlineData("Favorite", "IsFavorite", "true", "drop-favorite", true)]
    [InlineData("Favorite", "IsFavorite", "true", "drop-favorite", false)]
    [InlineData("Visibility", "IsPrivate", "false", "drop-visibility", true)]
    [InlineData("Visibility", "IsPrivate", "false", "drop-visibility", false)]
    public async Task ExplicitStateChangesAreIdempotentAndSupportBothResponses(
        string handler, string field, string value, string fragment, bool htmx)
    {
        using var factory = new TeledropWebApplicationFactory();
        await AddDropsAsync(factory, "source");
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);
        var token = await GetAntiforgeryAsync(client, "/drops/source");
        for (var attempt = 0; attempt < 2; attempt++)
        {
            using var request = new HttpRequestMessage(HttpMethod.Post, $"/drops/source?handler={handler}")
            {
                Content = new FormUrlEncodedContent(new Dictionary<string, string>
                {
                    [field] = value, ["__RequestVerificationToken"] = token,
                }),
            };
            if (htmx) request.Headers.Add("HX-Request", "true");
            using var response = await client.SendAsync(request);
            if (htmx)
            {
                Assert.Equal(HttpStatusCode.OK, response.StatusCode);
                Assert.Equal("changed", Assert.Single(response.Headers.GetValues("X-Drop-Outcome")));
                var body = await response.Content.ReadAsStringAsync();
                Assert.Contains($"id=\"{fragment}\"", body);
                Assert.DoesNotContain("<html", body);
                Assert.DoesNotContain("<video", body);
                Assert.DoesNotContain("id=\"drop-list\"", body);
            }
            else
            {
                Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
                Assert.Equal("/drops/source", response.Headers.Location!.ToString());
            }
        }
        await using var scope = factory.Services.CreateAsyncScope();
        var drop = await scope.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops.SingleAsync();
        Assert.Equal(bool.Parse(value), handler == "Favorite" ? drop.IsFavorite : drop.IsPrivate);
    }

    [Theory]
    [InlineData("Favorite", "IsFavorite", "true")]
    [InlineData("Visibility", "IsPrivate", "false")]
    public async Task PartialChangesStillRequireAntiforgery(string handler, string field, string value)
    {
        using var factory = new TeledropWebApplicationFactory();
        await AddDropsAsync(factory, "source");
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);
        using var request = new HttpRequestMessage(HttpMethod.Post, $"/drops/source?handler={handler}")
        {
            Content = new FormUrlEncodedContent(new Dictionary<string, string> { [field] = value }),
        };
        request.Headers.Add("HX-Request", "true");
        using var response = await client.SendAsync(request);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Theory]
    [InlineData("sort=title&direction=asc&pageNumber=2", "drop-21", "drop-01")]
    [InlineData("sort=title&direction=desc&pageNumber=1", "drop-21", "drop-01")]
    [InlineData("search=drop-07&sort=title&direction=asc", "drop-07", "drop-08")]
    public async Task ListFragmentAppliesFiltersWithoutRenderingThePage(
        string query, string includedSlug, string excludedSlug)
    {
        using var factory = new TeledropWebApplicationFactory();
        await AddDropsAsync(factory, Enumerable.Range(1, IndexModel.PageSize + 1)
            .Select(index => $"drop-{index:D2}").ToArray());
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);
        using var request = new HttpRequestMessage(HttpMethod.Get,
            $"/?handler=DropList&currentSlug={includedSlug}&{query}");
        request.Headers.Add("HX-Request", "true");

        using var response = await client.SendAsync(request);

        response.EnsureSuccessStatusCode();
        var body = WebUtility.HtmlDecode(await response.Content.ReadAsStringAsync());
        Assert.Contains("id=\"drop-list\"", body);
        Assert.Contains($"Drop {includedSlug}", body);
        Assert.DoesNotContain($"Drop {excludedSlug}", body);
        Assert.Contains("aria-current=\"page\"", body);
        Assert.DoesNotContain("<html", body, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("id=\"upload-form\"", body);
        Assert.True(response.Headers.CacheControl?.NoStore);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task ListFragmentRequiresLogin(bool htmx)
    {
        using var factory = new TeledropWebApplicationFactory();
        await AddDropsAsync(factory, "private-file");
        using var client = CreateClient(factory);
        using var request = new HttpRequestMessage(HttpMethod.Get, "/?handler=DropList");
        if (htmx) request.Headers.Add("HX-Request", "true");

        using var response = await client.SendAsync(request);

        if (htmx)
        {
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            Assert.Equal("/login", Assert.Single(response.Headers.GetValues("HX-Redirect")));
        }
        else
        {
            Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
            Assert.Contains("/login", response.Headers.Location!.ToString());
        }
        Assert.DoesNotContain("private-file", await response.Content.ReadAsStringAsync());
    }

    [Theory]
    [InlineData("GET", "/tickets", HttpStatusCode.NotFound)]
    [InlineData("GET", "/u/ab2c", HttpStatusCode.NotFound)]
    [InlineData("POST", "/u/ab2c", HttpStatusCode.MethodNotAllowed)]
    public async Task RemovedUploadTicketRoutesAreUnavailable(
        string method,
        string path,
        HttpStatusCode expectedStatus)
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);

        using var request = new HttpRequestMessage(new HttpMethod(method), path);
        using var response = await client.SendAsync(request);

        Assert.Equal(expectedStatus, response.StatusCode);
    }

    [Fact]
    public async Task UploadPageRendersExplicitMultipleFileDropRejection()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);

        using var ownerResponse = await client.GetAsync("/");

        ownerResponse.EnsureSuccessStatusCode();
        AssertMultipleFileDropRejection(
            await ownerResponse.Content.ReadAsStringAsync());
    }

    [Theory]
    [InlineData(
        "INVALID!",
        "slug는 영문 소문자 또는 숫자로 시작하고")]
    [InlineData("duplicate", "이미 사용 중인 slug입니다.")]
    public async Task SlugValidationErrorOpensUrlDialog(
        string slugInput,
        string expectedError)
    {
        using var factory = new TeledropWebApplicationFactory();
        await AddDropsAsync(factory, "source", "duplicate");
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);
        var verificationValue = await GetAntiforgeryAsync(
            client,
            "/drops/source");

        using var content = new FormUrlEncodedContent(
            new Dictionary<string, string>
            {
                ["SlugInput"] = slugInput,
                ["__RequestVerificationToken"] = verificationValue,
            });
        using var response = await client.PostAsync(
            "/drops/source?handler=Slug",
            content);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = WebUtility.HtmlDecode(
            await response.Content.ReadAsStringAsync());
        Assert.Contains(expectedError, body, StringComparison.Ordinal);
        AssertDialogIsOpen(body, "url-dialog");
        AssertDialogIsClosed(body, "password-dialog");
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task SlugTakenAfterOpeningTheFormKeepsOriginalLinksAndSupportsRetry(bool htmx)
    {
        using var factory = new TeledropWebApplicationFactory();
        await AddDropsAsync(factory, "source");
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);
        var token = await GetAntiforgeryAsync(client, "/drops/source");
        // Another request takes the desired Slug after this form was opened.
        await AddDropsAsync(factory, "taken");
        using var request = SlugRequest("taken", token, htmx);

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = WebUtility.HtmlDecode(await response.Content.ReadAsStringAsync());
        Assert.Contains("이미 사용 중인 slug입니다.", body);
        AssertDialogIsOpen(body, "url-dialog");
        Assert.Contains("action=\"/drops/source?handler=Slug\"", body);
        Assert.Contains("hx-post=\"/drops/source?handler=Slug\"", body);
        Assert.Contains("value=\"https://localhost/source\"", body);
        Assert.DoesNotContain("value=\"https://localhost/taken\"", body);
        if (htmx)
        {
            Assert.Equal("invalid", Assert.Single(response.Headers.GetValues("X-Drop-Outcome")));
            Assert.DoesNotContain("<html", body);
        }
        await using (var scope = factory.Services.CreateAsyncScope())
        {
            var saved = await scope.ServiceProvider.GetRequiredService<TeledropDbContext>()
                .Drops.SingleAsync(drop => drop.Slug == "source");
            Assert.Null(saved.UpdatedAt);
        }

        using var retry = SlugRequest("available", ExtractAntiforgery(body), htmx);
        using var retried = await client.SendAsync(retry);
        if (htmx)
        {
            Assert.Equal(HttpStatusCode.NoContent, retried.StatusCode);
            Assert.Equal("/drops/available", Assert.Single(retried.Headers.GetValues("HX-Redirect")));
        }
        else
        {
            Assert.Equal(HttpStatusCode.Redirect, retried.StatusCode);
            Assert.Equal("/drops/available", retried.Headers.Location!.ToString());
        }
        await using var finalScope = factory.Services.CreateAsyncScope();
        var drops = finalScope.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops;
        Assert.False(await drops.AnyAsync(drop => drop.Slug == "source"));
        Assert.Equal("Drop source", (await drops.SingleAsync(drop => drop.Slug == "available")).Title);
        Assert.True(await drops.AnyAsync(drop => drop.Slug == "taken"));
    }

    private static HttpRequestMessage SlugRequest(string slug, string token, bool htmx)
    {
        var request = new HttpRequestMessage(HttpMethod.Post, "/drops/source?handler=Slug")
        {
            Content = new FormUrlEncodedContent(new Dictionary<string, string>
            {
                ["SlugInput"] = slug,
                ["__RequestVerificationToken"] = token,
            }),
        };
        if (htmx) request.Headers.Add("HX-Request", "true");
        return request;
    }

    [Fact]
    public async Task PasswordValidationErrorOpensPasswordDialog()
    {
        using var factory = new TeledropWebApplicationFactory();
        await AddDropsAsync(factory, "source");
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);
        var verificationValue = await GetAntiforgeryAsync(
            client,
            "/drops/source");

        using var content = new FormUrlEncodedContent(
            new Dictionary<string, string>
            {
                ["NewDropPassword"] = string.Empty,
                ["__RequestVerificationToken"] = verificationValue,
            });
        using var response = await client.PostAsync(
            "/drops/source?handler=Password",
            content);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = WebUtility.HtmlDecode(
            await response.Content.ReadAsStringAsync());
        Assert.Contains(
            "새 드롭 비밀번호를 입력하세요.",
            body,
            StringComparison.Ordinal);
        AssertDialogIsOpen(body, "password-dialog");
        AssertDialogIsClosed(body, "url-dialog");
    }

    [Fact]
    public async Task RefreshLinkPreservesCurrentPage()
    {
        using var factory = new TeledropWebApplicationFactory();
        await AddDropsAsync(
            factory,
            Enumerable.Range(1, IndexModel.PageSize + 1)
                .Select(index => $"drop-{index:D2}")
                .ToArray());
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);

        using var response = await client.GetAsync("/?pageNumber=2");

        response.EnsureSuccessStatusCode();
        var body = WebUtility.HtmlDecode(
            await response.Content.ReadAsStringAsync());
        var markerPosition = body.IndexOf(
            "aria-label=\"목록 새로고침\"",
            StringComparison.Ordinal);
        Assert.True(markerPosition >= 0, "The refresh link is missing.");
        var anchorStart = body.LastIndexOf(
            "<a",
            markerPosition,
            StringComparison.Ordinal);
        var anchorEnd = body.IndexOf('>', markerPosition);
        Assert.True(
            anchorStart >= 0 && anchorEnd > anchorStart,
            "The refresh link is malformed.");
        var refreshAnchor = body[anchorStart..anchorEnd];
        Assert.Contains(
            "pageNumber=2",
            refreshAnchor,
            StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("Favorite", false)]
    [InlineData("Favorite", true)]
    [InlineData("Delete", false)]
    [InlineData("Delete", true)]
    public async Task RemovedIndexMutationsReturn404WithoutChangingTheDrop(string handler, bool htmx)
    {
        using var factory = new TeledropWebApplicationFactory();
        var bytes = "unchanged file"u8.ToArray();
        var drop = await SeedDropAsync(factory, "source", bytes);
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);
        var token = await GetAntiforgeryAsync(client, "/");
        using var request = new HttpRequestMessage(HttpMethod.Post, $"/?handler={handler}")
        {
            Content = new FormUrlEncodedContent(new Dictionary<string, string>
            {
                ["slug"] = drop.Slug,
                ["IsFavorite"] = "true",
                ["__RequestVerificationToken"] = token,
            }),
        };
        if (htmx) request.Headers.Add("HX-Request", "true");

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        await using var scope = factory.Services.CreateAsyncScope();
        var saved = await scope.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops.SingleAsync();
        Assert.Equal(drop.Id, saved.Id);
        Assert.Equal(drop.Title, saved.Title);
        Assert.False(saved.IsFavorite);
        Assert.True(saved.IsPrivate);
        Assert.Null(saved.UpdatedAt);
        Assert.Equal(bytes, await File.ReadAllBytesAsync(Path.Combine(factory.ShareDirectory, saved.Location)));
    }

    [Fact]
    public async Task HomeIgnoresOldUploadedStateAndKeepsDeleteNoticeAndLogout()
    {
        using var factory = new TeledropWebApplicationFactory();
        await SeedDropAsync(factory, "source", [0]);
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);

        var body = WebUtility.HtmlDecode(await client.GetStringAsync("/?uploaded=source&deleted=true"));

        Assert.Contains("id=\"upload-form\"", body);
        Assert.Contains("드롭을 삭제했습니다.", body);
        Assert.DoesNotContain("업로드가 완료되었습니다.", body);
        Assert.Contains("id=\"drop-list\"", body);
        using var content = new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["__RequestVerificationToken"] = ExtractAntiforgery(body),
        });
        using var logout = await client.PostAsync("/?handler=Logout", content);
        Assert.Equal(HttpStatusCode.Redirect, logout.StatusCode);
        Assert.Equal("/login", logout.Headers.Location!.ToString());
        using var home = await client.GetAsync("/");
        Assert.Equal(HttpStatusCode.Redirect, home.StatusCode);
        var location = home.Headers.Location!;
        Assert.StartsWith("/login?ReturnUrl=",
            location.IsAbsoluteUri ? location.PathAndQuery : location.OriginalString);
    }

    private static void AssertMultipleFileDropRejection(string pageBody)
    {
        var body = WebUtility.HtmlDecode(pageBody);
        Assert.Contains(
            "droppedFiles.length > 1",
            body,
            StringComparison.Ordinal);
        Assert.Contains(
            "fileInput.value = \"\"",
            body,
            StringComparison.Ordinal);
        Assert.Contains(
            "파일은 한 번에 하나만 업로드할 수 있습니다.",
            body,
            StringComparison.Ordinal);
    }

    private static void AssertDialogIsOpen(string pageBody, string id)
    {
        Assert.Contains(" open", GetDialogStartTag(pageBody, id), StringComparison.Ordinal);
    }

    private static void AssertDialogIsClosed(string pageBody, string id)
    {
        Assert.DoesNotContain(" open", GetDialogStartTag(pageBody, id), StringComparison.Ordinal);
    }

    private static string GetDialogStartTag(string pageBody, string id)
    {
        var start = pageBody.IndexOf($"<dialog id=\"{id}\"", StringComparison.Ordinal);
        Assert.True(start >= 0, $"The '{id}' dialog is missing.");
        return pageBody[start..pageBody.IndexOf('>', start)];
    }

    private static async Task AddDropsAsync(
        TeledropWebApplicationFactory factory, params string[] slugs)
    {
        var createdAt = DateTime.UtcNow;
        for (var index = 0; index < slugs.Length; index++)
            await SeedDropAsync(factory, slugs[index], [0],
                drop => drop.CreatedAt = createdAt.AddSeconds(-index));
    }
}
