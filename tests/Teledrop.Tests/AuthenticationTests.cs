using System.Net;
using System.Globalization;
using System.Security.Claims;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class AuthenticationTests
{
    [Fact]
    public async Task UnauthenticatedHomeRequestRedirectsToLogin()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);

        using var response = await client.GetAsync("/");

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        AssertRedirectLocation(response, "/login?ReturnUrl=%2F");
    }

    [Fact]
    public async Task LoginRejectsWrongPasswordAndAcceptsCorrectPassword()
    {
        const string rejectedPassword = "entered-secret-<do-not-echo>";
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);

        using (var failedLogin = await PostLoginAsync(client, rejectedPassword))
        {
            Assert.Equal(HttpStatusCode.OK, failedLogin.StatusCode);
            var body = await failedLogin.Content.ReadAsStringAsync();
            Assert.Contains(
                "사용자 ID 또는 비밀번호가 올바르지 않습니다.",
                WebUtility.HtmlDecode(body),
                StringComparison.Ordinal);
            Assert.DoesNotContain(rejectedPassword, WebUtility.HtmlDecode(body));
            AssertPasswordInputIsEmpty(body);
        }

        using (var homeAfterFailedLogin = await client.GetAsync("/"))
        {
            Assert.Equal(HttpStatusCode.Redirect, homeAfterFailedLogin.StatusCode);
        }

        using (var successfulLogin = await PostLoginAsync(
                   client,
                   TeledropWebApplicationFactory.WebPassword))
        {
            Assert.Equal(HttpStatusCode.Redirect, successfulLogin.StatusCode);
            AssertRedirectLocation(successfulLogin, "/");
        }

        using var homeAfterSuccessfulLogin = await client.GetAsync("/");
        Assert.Equal(HttpStatusCode.OK, homeAfterSuccessfulLogin.StatusCode);
    }

    [Fact]
    public async Task PasswordChangeRejectsExistingSessionOnNextRequest()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);

        using (var successfulLogin = await PostLoginAsync(
                   client,
                   TeledropWebApplicationFactory.WebPassword))
        {
            Assert.Equal(HttpStatusCode.Redirect, successfulLogin.StatusCode);
        }

        factory.ChangeWebPassword();

        using var response = await client.GetAsync("/");

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        AssertRedirectLocation(response, "/login?ReturnUrl=%2F");
    }

    [Theory]
    [InlineData("other-owner")]
    [InlineData("Admin")]
    public async Task CorrectPasswordCannotAuthenticateADifferentUsername(string username)
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);

        using var response = await PostLoginAsync(client,
            TeledropWebApplicationFactory.WebPassword, username);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = WebUtility.HtmlDecode(await response.Content.ReadAsStringAsync());
        Assert.Contains("사용자 ID 또는 비밀번호가 올바르지 않습니다.", body);
        AssertPasswordInputIsEmpty(body);
        using var home = await client.GetAsync("/");
        Assert.Equal(HttpStatusCode.Redirect, home.StatusCode);
        AssertRedirectLocation(home, "/login?ReturnUrl=%2F");
    }

    [Theory]
    [InlineData(null, "entered-secret-must-not-return")]
    [InlineData("   ", "entered-secret-must-not-return")]
    [InlineData("admin", null)]
    [InlineData("admin", "   ")]
    public async Task MissingLoginFieldsKeepTheSessionAnonymousAndClearThePassword(
        string? username, string? password)
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);

        using var response = await PostLoginAsync(client, password, username);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = WebUtility.HtmlDecode(await response.Content.ReadAsStringAsync());
        Assert.Contains("사용자 ID와 비밀번호를 입력하세요.", body);
        AssertPasswordInputIsEmpty(body);
        Assert.DoesNotContain("entered-secret-must-not-return", body);
        using var home = await client.GetAsync("/");
        Assert.Equal(HttpStatusCode.Redirect, home.StatusCode);
    }

    [Theory]
    [InlineData("/drops/target?tab=details", "/drops/target?tab=details")]
    [InlineData("https://example.com/steal", "/")]
    [InlineData("//example.com/steal", "/")]
    public async Task SuccessfulLoginOnlyRedirectsToLocalReturnUrls(
        string returnUrl, string expected)
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);

        using var response = await PostLoginAsync(client,
            TeledropWebApplicationFactory.WebPassword, returnUrl: returnUrl);

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        AssertRedirectLocation(response, expected);
        using var home = await client.GetAsync("/");
        Assert.Equal(HttpStatusCode.OK, home.StatusCode);
    }

    [Theory]
    [InlineData("/drops/target", "/drops/target")]
    [InlineData("https://example.com/steal", "/")]
    public async Task AuthenticatedLoginPageOnlyRedirectsToLocalReturnUrls(
        string returnUrl, string expected)
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);

        using var response = await client.GetAsync($"/login?ReturnUrl={Uri.EscapeDataString(returnUrl)}");

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        AssertRedirectLocation(response, expected);
    }

    [Fact]
    public async Task LoginWithoutAntiforgeryDoesNotCreateAnOwnerSession()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);

        using var response = await PostLoginAsync(client,
            TeledropWebApplicationFactory.WebPassword, includeAntiforgery: false);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        using var home = await client.GetAsync("/");
        Assert.Equal(HttpStatusCode.Redirect, home.StatusCode);
        AssertRedirectLocation(home, "/login?ReturnUrl=%2F");
    }

    [Theory]
    [InlineData(null)]
    [InlineData("obsolete-fingerprint")]
    public async Task SessionWithMissingOrInvalidPasswordFingerprintIsRejectedAndDeleted(
        string? fingerprint)
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory, handleCookies: false);
        const string scheme = CookieAuthenticationDefaults.AuthenticationScheme;
        var options = factory.Services.GetRequiredService<IOptionsMonitor<CookieAuthenticationOptions>>()
            .Get(scheme);
        var claims = new List<Claim> { new(ClaimTypes.Name, TeledropWebApplicationFactory.WebUsername) };
        if (fingerprint is not null)
            claims.Add(new Claim("teledrop:owner-session-password-fingerprint", fingerprint));
        var principal = new ClaimsPrincipal(new ClaimsIdentity(claims, scheme));
        var ticket = new AuthenticationTicket(principal, new AuthenticationProperties
        {
            IssuedUtc = DateTimeOffset.UtcNow,
            ExpiresUtc = DateTimeOffset.UtcNow.AddHours(1),
            IsPersistent = true,
        }, scheme);
        var cookieName = options.Cookie.Name!;
        using var request = new HttpRequestMessage(HttpMethod.Get, "/");
        request.Headers.Add("Cookie", $"{cookieName}={options.TicketDataFormat.Protect(ticket)}");

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        AssertRedirectLocation(response, "/login?ReturnUrl=%2F");
        var deleted = Assert.Single(response.Headers.GetValues("Set-Cookie"),
            value => value.StartsWith(cookieName + "=", StringComparison.Ordinal));
        Assert.StartsWith(cookieName + "=;", deleted);
        var expiry = Regex.Match(deleted, "expires=([^;]+)", RegexOptions.IgnoreCase).Groups[1].Value;
        Assert.True(DateTimeOffset.Parse(expiry, CultureInfo.InvariantCulture) <= DateTimeOffset.UtcNow);
    }

    [Fact]
    public async Task OwnerSessionLastsThirtyDaysAndRenewsAfterHalfItsLifetime()
    {
        var clock = new SessionClock();
        using var factory = new TeledropWebApplicationFactory(timeProvider: clock);
        using var loginClient = CreateClient(factory);
        using var login = await PostLoginAsync(loginClient, TeledropWebApplicationFactory.WebPassword);
        Assert.Equal(HttpStatusCode.Redirect, login.StatusCode);
        var options = factory.Services.GetRequiredService<IOptionsMonitor<CookieAuthenticationOptions>>()
            .Get(CookieAuthenticationDefaults.AuthenticationScheme);
        var cookieName = options.Cookie.Name!;
        var originalCookie = SessionCookie(login, cookieName);
        var original = ReadTicket(originalCookie);
        Assert.True(original.Properties.IsPersistent);
        Assert.Equal(clock.GetUtcNow(), original.Properties.IssuedUtc);
        Assert.Equal(clock.GetUtcNow().AddDays(30), original.Properties.ExpiresUtc);

        // Keep cookies explicit: a renewed ticket must not silently replace the
        // original when checking the old ticket's expiry.
        using var client = CreateClient(factory, handleCookies: false);
        clock.Advance(TimeSpan.FromDays(15));
        using var halfway = await ReadHomeAsync(originalCookie);
        Assert.Equal(HttpStatusCode.OK, halfway.StatusCode);
        Assert.False(halfway.Headers.TryGetValues("Set-Cookie", out var cookies)
            && cookies.Any(value => value.StartsWith(cookieName + "=", StringComparison.Ordinal)));

        clock.Advance(TimeSpan.FromSeconds(1));
        using var renewedResponse = await ReadHomeAsync(originalCookie);
        Assert.Equal(HttpStatusCode.OK, renewedResponse.StatusCode);
        var renewedCookie = SessionCookie(renewedResponse, cookieName);
        var renewed = ReadTicket(renewedCookie);
        Assert.Equal(clock.GetUtcNow(), renewed.Properties.IssuedUtc);
        Assert.Equal(clock.GetUtcNow().AddDays(30), renewed.Properties.ExpiresUtc);

        clock.Advance(TimeSpan.FromDays(15));
        using var expiredOriginal = await ReadHomeAsync(originalCookie);
        Assert.Equal(HttpStatusCode.Redirect, expiredOriginal.StatusCode);
        AssertRedirectLocation(expiredOriginal, "/login?ReturnUrl=%2F");
        using var stillValid = await ReadHomeAsync(renewedCookie);
        Assert.Equal(HttpStatusCode.OK, stillValid.StatusCode);

        clock.Advance(TimeSpan.FromDays(15) + TimeSpan.FromSeconds(1));
        using var expiredRenewal = await ReadHomeAsync(renewedCookie);
        Assert.Equal(HttpStatusCode.Redirect, expiredRenewal.StatusCode);
        AssertRedirectLocation(expiredRenewal, "/login?ReturnUrl=%2F");

        AuthenticationTicket ReadTicket(string cookie) => Assert.IsType<AuthenticationTicket>(
            options.TicketDataFormat.Unprotect(cookie[(cookie.IndexOf('=') + 1)..]));

        async Task<HttpResponseMessage> ReadHomeAsync(string cookie)
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, "/");
            request.Headers.Add("Cookie", cookie);
            return await client.SendAsync(request);
        }
    }

    private static string SessionCookie(HttpResponseMessage response, string name)
        => Assert.Single(response.Headers.GetValues("Set-Cookie"),
            value => value.StartsWith(name + "=", StringComparison.Ordinal)).Split(';', 2)[0];

    private sealed class SessionClock : TimeProvider
    {
        private DateTimeOffset now = new(2026, 10, 18, 0, 0, 0, TimeSpan.Zero);
        public override DateTimeOffset GetUtcNow() => now;
        internal void Advance(TimeSpan elapsed) => now += elapsed;
    }

    private static async Task<HttpResponseMessage> PostLoginAsync(
        HttpClient client,
        string? password,
        string? username = TeledropWebApplicationFactory.WebUsername,
        string returnUrl = "/",
        bool includeAntiforgery = true)
    {
        using var loginPage = await client.GetAsync("/login?ReturnUrl=%2F");
        loginPage.EnsureSuccessStatusCode();
        var pageBody = await loginPage.Content.ReadAsStringAsync();
        var verificationValue = ExtractAntiforgery(pageBody);

        var formValues = new Dictionary<string, string>
        {
            ["ReturnUrl"] = returnUrl,
        };
        if (username is not null) formValues["Username"] = username;
        if (password is not null) formValues["Password"] = password;
        if (includeAntiforgery) formValues["__RequestVerificationToken"] = verificationValue;

        using var content = new FormUrlEncodedContent(formValues);
        return await client.PostAsync("/login", content);
    }

    private static void AssertPasswordInputIsEmpty(string html)
    {
        var input = Regex.Match(html, "<input\\b[^>]*\\bname=\"Password\"[^>]*>", RegexOptions.IgnoreCase);
        Assert.True(input.Success, "The login password input is missing.");
        var value = Regex.Match(input.Value, "\\bvalue=\"([^\"]*)\"", RegexOptions.IgnoreCase);
        Assert.True(!value.Success || value.Groups[1].Value.Length == 0,
            "A failed login must not return a password value.");
    }

    private static void AssertRedirectLocation(
        HttpResponseMessage response,
        string expectedPathAndQuery)
    {
        var location = Assert.IsType<Uri>(response.Headers.Location);
        var pathAndQuery = location.IsAbsoluteUri
            ? location.PathAndQuery
            : location.OriginalString;

        Assert.Equal(expectedPathAndQuery, pathAndQuery);
    }

}
