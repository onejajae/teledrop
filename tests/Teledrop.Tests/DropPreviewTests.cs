using System.Net;
using System.Net.Http.Headers;
using Teledrop.Features.Drops;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class DropPreviewTests
{
    [Theory]
    [InlineData("IMAGE/PNG; charset=binary", DropPreviewKind.Image, true)]
    [InlineData("video/webm", DropPreviewKind.Video, true)]
    [InlineData("audio/ogg", DropPreviewKind.Audio, true)]
    [InlineData("APPLICATION/PDF; charset=binary", DropPreviewKind.Pdf, true)]
    [InlineData("text/plain; charset=utf-8", DropPreviewKind.None, true)]
    [InlineData("IMAGE/SVG+XML; charset=utf-8", DropPreviewKind.None, false)]
    [InlineData("text/html", DropPreviewKind.None, false)]
    [InlineData("application/octet-stream", DropPreviewKind.None, false)]
    public async Task DetailShareLinkAndDownloadAgreeOnMime(
        string contentType, DropPreviewKind kind, bool allowInline)
    {
        using var factory = new TeledropWebApplicationFactory();
        var bytes = "<script>document.title='owned'</script>"u8.ToArray();
        var drop = await SeedDropAsync(factory, "preview", bytes, seed =>
        {
            seed.IsPrivate = false;
            seed.ContentType = contentType;
            seed.FileName = "misleading.pdf"; // Extension does not authorize a preview.
        });
        using var owner = CreateClient(factory);
        await LogInOwnerAsync(owner);
        using var anonymous = CreateClient(factory);

        AssertPreview(await owner.GetStringAsync($"/drops/{drop.Slug}"), kind);
        AssertPreview(await anonymous.GetStringAsync($"/{drop.Slug}"), kind);
        using var inline = await anonymous.GetAsync($"/d/{drop.Slug}?inline=true");
        using var attachment = await anonymous.GetAsync($"/d/{drop.Slug}");

        Assert.Equal(HttpStatusCode.OK, inline.StatusCode);
        Assert.Equal(HttpStatusCode.OK, attachment.StatusCode);
        Assert.Equal(allowInline ? "inline" : "attachment",
            inline.Content.Headers.ContentDisposition?.DispositionType);
        Assert.Equal("attachment", attachment.Content.Headers.ContentDisposition?.DispositionType);
        Assert.Equal("nosniff", Assert.Single(inline.Headers.GetValues("X-Content-Type-Options")));
        var policy = Assert.Single(inline.Headers.GetValues("Content-Security-Policy"));
        Assert.Contains("default-src 'self'", policy);
        Assert.Contains("script-src 'self' 'nonce-", policy);
        Assert.Contains("object-src 'none'", policy);
        Assert.Contains("frame-ancestors 'self'", policy);
        var expectedType = MediaTypeHeaderValue.Parse(contentType).ToString();
        Assert.Equal(expectedType, inline.Content.Headers.ContentType?.ToString(), ignoreCase: true);
        Assert.Equal(expectedType, attachment.Content.Headers.ContentType?.ToString(), ignoreCase: true);
        Assert.Equal(bytes, await inline.Content.ReadAsByteArrayAsync());
        Assert.Equal(bytes, await attachment.Content.ReadAsByteArrayAsync());
    }

    [Fact]
    public async Task InvalidStoredMimeDoesNotProducePreviewMarkup()
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await SeedDropAsync(factory, "invalid", [0], seed =>
        {
            seed.IsPrivate = false;
            seed.ContentType = "not a mime";
        });
        using var owner = CreateClient(factory);
        await LogInOwnerAsync(owner);
        using var anonymous = CreateClient(factory);

        AssertPreview(await owner.GetStringAsync($"/drops/{drop.Slug}"), DropPreviewKind.None);
        AssertPreview(await anonymous.GetStringAsync($"/{drop.Slug}"), DropPreviewKind.None);
        // Corrupt download MIME is not repaired by preview classification.
    }

    [Fact]
    public async Task ParameterizedPdfDownloadKeepsRangeSupport()
    {
        using var factory = new TeledropWebApplicationFactory();
        var bytes = await File.ReadAllBytesAsync(Path.Combine(AppContext.BaseDirectory, "Fixtures/preview.pdf"));
        await SeedDropAsync(factory, "range-pdf", bytes, seed =>
        {
            seed.IsPrivate = false;
            seed.ContentType = "application/pdf; charset=binary";
            seed.FileName = "설계 문서.pdf";
        });
        using var client = CreateClient(factory);
        using var request = new HttpRequestMessage(HttpMethod.Get, "/d/range-pdf?inline=true");
        request.Headers.Range = new RangeHeaderValue(0, 3);

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.PartialContent, response.StatusCode);
        Assert.Equal("inline", response.Content.Headers.ContentDisposition?.DispositionType);
        Assert.Equal("설계 문서.pdf", response.Content.Headers.ContentDisposition?.FileNameStar);
        Assert.Equal("application/pdf; charset=binary", response.Content.Headers.ContentType?.ToString());
        Assert.Equal(bytes[..4], await response.Content.ReadAsByteArrayAsync());
    }

    private static void AssertPreview(string html, DropPreviewKind kind)
    {
        var start = html.IndexOf("<div class=\"td-preview-content\">", StringComparison.Ordinal);
        Assert.True(start >= 0, "The Drop preview content is missing.");
        var end = html.IndexOf("<details class=\"td-file-card\">", start, StringComparison.Ordinal);
        Assert.True(end > start);
        var preview = html[start..end];
        foreach (var (candidate, marker) in new[]
        {
            (DropPreviewKind.Image, "<img "),
            (DropPreviewKind.Video, "<video "),
            (DropPreviewKind.Audio, "<audio "),
            (DropPreviewKind.Pdf, "data-pdf-url="),
        })
            Assert.Equal(kind == candidate, preview.Contains(marker, StringComparison.Ordinal));
        if (kind == DropPreviewKind.Video)
            Assert.Contains("?inline=true#t=0.001\"", preview);
        Assert.Contains("id=\"drop-download\"", html[end..]);
    }
}
