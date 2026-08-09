using System.Net;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Teledrop.Features.UploadTickets;
using Xunit;

namespace Teledrop.Tests;

public sealed class UiRegressionTests
{
    [Fact]
    public async Task UploadPagesRenderExplicitMultipleFileDropRejection()
    {
        using var factory = new TeledropWebApplicationFactory();
        await AddUploadTicketAsync(factory);
        using var client = CreateClient(factory);
        await LogInAsync(client);

        using var ownerResponse = await client.GetAsync("/");
        using var guestResponse = await client.GetAsync("/u/ab2c");

        ownerResponse.EnsureSuccessStatusCode();
        guestResponse.EnsureSuccessStatusCode();
        AssertMultipleFileDropRejection(
            await ownerResponse.Content.ReadAsStringAsync());
        AssertMultipleFileDropRejection(
            await guestResponse.Content.ReadAsStringAsync());
    }

    [Theory]
    [InlineData(
        "INVALID!",
        "slug는 영문 소문자 또는 숫자로 시작하고")]
    [InlineData("duplicate", "이미 사용 중인 slug입니다.")]
    public async Task SlugValidationErrorOpensUrlDetails(
        string slugInput,
        string expectedError)
    {
        using var factory = new TeledropWebApplicationFactory();
        await AddDropsAsync(factory, "source", "duplicate");
        using var client = CreateClient(factory);
        await LogInAsync(client);
        var verificationValue = await GetAntiforgeryValueAsync(
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
        AssertDetailsIsOpen(body, "접근 URL 변경");
        AssertDetailsIsClosed(body, "접근 설정");
    }

    [Fact]
    public async Task PasswordValidationErrorOpensAccessDetails()
    {
        using var factory = new TeledropWebApplicationFactory();
        await AddDropsAsync(factory, "source");
        using var client = CreateClient(factory);
        await LogInAsync(client);
        var verificationValue = await GetAntiforgeryValueAsync(
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
        AssertDetailsIsOpen(body, "접근 설정");
        AssertDetailsIsClosed(body, "접근 URL 변경");
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
        await LogInAsync(client);

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

    private static void AssertDetailsIsOpen(
        string pageBody,
        string summaryText)
    {
        var detailsTag = GetDetailsStartTag(pageBody, summaryText);
        Assert.Contains(" open", detailsTag, StringComparison.Ordinal);
    }

    private static void AssertDetailsIsClosed(
        string pageBody,
        string summaryText)
    {
        var detailsTag = GetDetailsStartTag(pageBody, summaryText);
        Assert.DoesNotContain(" open", detailsTag, StringComparison.Ordinal);
    }

    private static string GetDetailsStartTag(
        string pageBody,
        string summaryText)
    {
        var summaryPosition = pageBody.IndexOf(
            $"<summary>{summaryText}</summary>",
            StringComparison.Ordinal);
        Assert.True(
            summaryPosition >= 0,
            $"The '{summaryText}' summary is missing.");
        var detailsStart = pageBody.LastIndexOf(
            "<details",
            summaryPosition,
            StringComparison.Ordinal);
        var detailsEnd = pageBody.IndexOf('>', detailsStart);
        Assert.True(
            detailsStart >= 0 && detailsEnd > detailsStart,
            $"The '{summaryText}' details element is malformed.");
        return pageBody[detailsStart..detailsEnd];
    }

    private static async Task AddDropsAsync(
        TeledropWebApplicationFactory factory,
        params string[] slugs)
    {
        var createdAt = DateTime.UtcNow;
        var drops = slugs.Select((slug, index) => new Drop
        {
            Id = Guid.NewGuid(),
            Slug = slug,
            Title = $"Drop {slug}",
            IsPrivate = true,
            FileName = $"{slug}.bin",
            FileHash = new string('0', 64),
            FileSizeBytes = 1,
            ContentType = "application/octet-stream",
            Location = Guid.NewGuid().ToString("N"),
            CreatedAt = createdAt.AddSeconds(-index),
        });

        await using var scope = factory.Services.CreateAsyncScope();
        var dbContext = scope.ServiceProvider
            .GetRequiredService<TeledropDbContext>();
        dbContext.Drops.AddRange(drops);
        await dbContext.SaveChangesAsync();
    }

    private static async Task AddUploadTicketAsync(
        TeledropWebApplicationFactory factory)
    {
        var now = DateTime.UtcNow;
        var ticket = new UploadTicket
        {
            Id = Guid.NewGuid(),
            Path = "ab2c",
            Code = "defg2345",
            CreatedAt = now,
            ExpiresAtUtc = now.AddHours(1),
        };

        await using var scope = factory.Services.CreateAsyncScope();
        var dbContext = scope.ServiceProvider
            .GetRequiredService<TeledropDbContext>();
        dbContext.UploadTickets.Add(ticket);
        await dbContext.SaveChangesAsync();
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

    private static async Task LogInAsync(HttpClient client)
    {
        var verificationValue = await GetAntiforgeryValueAsync(
            client,
            "/login");
        using var content = new FormUrlEncodedContent(
            new Dictionary<string, string>
            {
                ["Username"] = TeledropWebApplicationFactory.WebUsername,
                ["Password"] = TeledropWebApplicationFactory.WebPassword,
                ["ReturnUrl"] = "/",
                ["__RequestVerificationToken"] = verificationValue,
            });
        using var response = await client.PostAsync("/login", content);
        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
    }

    private static async Task<string> GetAntiforgeryValueAsync(
        HttpClient client,
        string path)
    {
        using var response = await client.GetAsync(path);
        response.EnsureSuccessStatusCode();
        return ExtractAntiforgeryValue(
            await response.Content.ReadAsStringAsync());
    }

    private static string ExtractAntiforgeryValue(string pageBody)
    {
        const string nameMarker = "name=\"__RequestVerificationToken\"";
        const string valueMarker = "value=\"";

        var namePosition = pageBody.IndexOf(
            nameMarker,
            StringComparison.Ordinal);
        Assert.True(namePosition >= 0, "The page has no antiforgery field.");
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
        Assert.True(valueEnd > valueStart, "The antiforgery value is empty.");
        return WebUtility.HtmlDecode(input[valueStart..valueEnd]);
    }
}
