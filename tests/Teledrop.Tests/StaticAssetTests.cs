using System.Net;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

namespace Teledrop.Tests;

public sealed class StaticAssetTests
{
    [Fact]
    public async Task RclAssetsKeepRootUrlsAndFingerprintLinksWithoutAuthentication()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = factory.CreateClient(new WebApplicationFactoryClientOptions
        {
            AllowAutoRedirect = false,
        });
        var page = await client.GetStringAsync("/login");
        var paths = new[]
        {
            "/css/app.css", "/js/htmx.min.js", "/js/site.js",
            "/js/drop-list.js", "/js/drop-interactions.js",
            "/fonts/Pretendard-Regular.woff2", "/favicon.ico", "/static/manifest.json",
        };
        foreach (var path in paths)
        {
            using var response = await client.GetAsync(path);
            Assert.True(response.StatusCode == HttpStatusCode.OK, $"{path}: {response.StatusCode}");
            Assert.NotEmpty(await response.Content.ReadAsByteArrayAsync());
        }

        var cssLink = Regex.Match(page, "href=\"([^\"]*/css/app\\.[^\"]*css)\"");
        Assert.True(cssLink.Success, "The Razor layout must resolve its fingerprinted CSS asset.");
        var cssPath = WebUtility.HtmlDecode(cssLink.Groups[1].Value);
        Assert.NotEqual("/css/app.css", cssPath);
        Assert.DoesNotContain("_content/", cssPath);
        using var cssResponse = await client.GetAsync(cssPath);
        Assert.Equal(HttpStatusCode.OK, cssResponse.StatusCode);
    }
}
