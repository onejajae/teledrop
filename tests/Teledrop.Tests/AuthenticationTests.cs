using System.Net;
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
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);

        using (var failedLogin = await PostLoginAsync(client, "wrong-password"))
        {
            Assert.Equal(HttpStatusCode.OK, failedLogin.StatusCode);
            var body = await failedLogin.Content.ReadAsStringAsync();
            Assert.Contains(
                "사용자 ID 또는 비밀번호가 올바르지 않습니다.",
                WebUtility.HtmlDecode(body),
                StringComparison.Ordinal);
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

    private static async Task<HttpResponseMessage> PostLoginAsync(
        HttpClient client,
        string password)
    {
        using var loginPage = await client.GetAsync("/login?ReturnUrl=%2F");
        loginPage.EnsureSuccessStatusCode();
        var pageBody = await loginPage.Content.ReadAsStringAsync();
        var verificationValue = ExtractAntiforgery(pageBody);

        var formValues = new Dictionary<string, string>
        {
            ["Username"] = TeledropWebApplicationFactory.WebUsername,
            ["Password"] = password,
            ["ReturnUrl"] = "/",
            ["__RequestVerificationToken"] = verificationValue,
        };

        using var content = new FormUrlEncodedContent(formValues);
        return await client.PostAsync("/login", content);
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
