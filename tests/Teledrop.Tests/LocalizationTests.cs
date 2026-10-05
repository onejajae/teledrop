using System.Collections;
using System.Globalization;
using System.Net;
using System.Resources;
using System.Text.RegularExpressions;
using Teledrop.Localization;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class LocalizationTests
{
    [Theory]
    [InlineData(null, "en")]
    [InlineData("ko-KR", "ko")]
    [InlineData("en-US", "en")]
    [InlineData("en-GB", "en")]
    [InlineData("ja,ko;q=0.8", "ko")]
    [InlineData("ja,fr;q=0.9,de;q=0.8,ko;q=0.7", "ko")]
    [InlineData("ja,fr;q=0.8", "en")]
    [InlineData("ko;q=0,en;q=0.8", "en")]
    [InlineData("en;q=0.5,ko;q=0.9", "ko")]
    [InlineData("*", "en")]
    public async Task FirstResponseUsesSupportedBrowserLanguage(string? header, string expected)
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory, language: header);
        using var response = await client.GetAsync("/login?culture=ko");
        var html = await response.Content.ReadAsStringAsync();
        Assert.Contains($"<html lang=\"{expected}\"", html);
        Assert.Contains(expected, response.Content.Headers.ContentLanguage);
        Assert.Contains(expected == "en" ? "Sign in - teledrop" : "로그인 - teledrop", WebUtility.HtmlDecode(html));
    }

    [Fact]
    public async Task LanguageChoiceRequiresAntiforgeryAndPersistsForAnonymousPages()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory, language: "ja");
        using var rejected = await client.PostAsync("/settings/language", new FormUrlEncodedContent(new Dictionary<string, string> { ["language"] = "ko" }));
        Assert.Equal(HttpStatusCode.BadRequest, rejected.StatusCode);
        var token = await GetAntiforgeryAsync(client, "/login");
        using var invalid = await client.PostAsync("/settings/language", Form("fr", token));
        Assert.Equal(HttpStatusCode.BadRequest, invalid.StatusCode);
        using var request = new HttpRequestMessage(HttpMethod.Post, "/settings/language") { Content = Form("ko", token) };
        request.Headers.Add("X-Requested-With", "XMLHttpRequest");
        using var response = await client.SendAsync(request);
        Assert.Equal(HttpStatusCode.NoContent, response.StatusCode);
        var cookie = Assert.Single(response.Headers.GetValues("Set-Cookie"));
        Assert.Contains(".AspNetCore.Culture=", cookie);
        Assert.Contains("httponly", cookie, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("samesite=lax", cookie, StringComparison.OrdinalIgnoreCase);
        var expiry = Regex.Match(cookie, "expires=([^;]+)", RegexOptions.IgnoreCase).Groups[1].Value;
        Assert.InRange(DateTimeOffset.Parse(expiry, CultureInfo.InvariantCulture), DateTimeOffset.UtcNow.AddDays(364), DateTimeOffset.UtcNow.AddDays(367));
        Assert.Contains("<html lang=\"ko\"", await client.GetStringAsync("/login"));
        await LogInOwnerAsync(client);
        Assert.Contains("<html lang=\"ko\"", await client.GetStringAsync("/"));
    }

    [Theory]
    [InlineData("/login?ReturnUrl=%2Fdrops%2Ftest", "/login?ReturnUrl=%2Fdrops%2Ftest")]
    [InlineData("https://example.com/", "/")]
    [InlineData("//example.com", "/")]
    public async Task PlainFormReturnsOnlyToLocalPages(string returnUrl, string location)
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        var token = await GetAntiforgeryAsync(client, "/login");
        using var response = await client.PostAsync("/settings/language", Form("en", token, returnUrl));
        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        Assert.Equal(location, response.Headers.Location!.OriginalString);
        Assert.Contains("<html lang=\"en\"", await client.GetStringAsync("/login"));
    }

    [Fact]
    public void CatalogsContainTheSameKeysAndPlaceholders()
    {
        var resources = new ResourceManager("Teledrop.Localization.UiStrings", typeof(UiText).Assembly);
        Dictionary<string, string> Read(CultureInfo culture) => resources.GetResourceSet(culture, true, false)!
            .Cast<DictionaryEntry>().ToDictionary(entry => (string)entry.Key, entry => (string)entry.Value!);
        var english = Read(CultureInfo.InvariantCulture);
        var korean = Read(CultureInfo.GetCultureInfo("ko"));
        Assert.Equal(english.Keys.Order(), korean.Keys.Order());
        foreach (var key in english.Keys)
        {
            Assert.False(string.IsNullOrWhiteSpace(korean[key]));
            Assert.Equal(Regex.Matches(english[key], @"\{\d+\}").Select(m => m.Value).Order(),
                Regex.Matches(korean[key], @"\{\d+\}").Select(m => m.Value).Order());
        }
        Assert.Equal("Sign in", UiText.Catalogs["en"]["Login"]);
        Assert.Equal("로그인", UiText.Catalogs["ko"]["Login"]);
    }

    private static FormUrlEncodedContent Form(string language, string token, string returnUrl = "/login") => new(new Dictionary<string, string>
    {
        ["language"] = language, ["returnUrl"] = returnUrl, ["__RequestVerificationToken"] = token,
    });
}
