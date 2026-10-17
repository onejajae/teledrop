using System.Net;
using System.Text.RegularExpressions;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class SecurityHeadersTests
{
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task EachResponseHasAFreshNonceMatchingAllItsInlineScripts(bool owner)
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        if (owner) await LogInOwnerAsync(client);
        string? previousNonce = null;

        for (var attempt = 0; attempt < 2; attempt++)
        {
            using var response = await client.GetAsync(owner ? "/" : "/login");
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            var policy = Assert.Single(response.Headers.GetValues("Content-Security-Policy"));
            var nonceMatch = Assert.Single(Regex.Matches(policy, "'nonce-([^']+)'").Cast<Match>());
            var nonce = nonceMatch.Groups[1].Value;
            Assert.NotEmpty(nonce);
            Assert.NotEqual(previousNonce, nonce);
            previousNonce = nonce;

            var html = await response.Content.ReadAsStringAsync();
            const RegexOptions options = RegexOptions.IgnoreCase | RegexOptions.CultureInvariant;
            var inlineScripts = Regex.Matches(html, @"<script\b[^>]*>", options).Cast<Match>()
                .Where(script => !Regex.IsMatch(script.Value, @"\ssrc\s*=", options)).ToArray();
            Assert.NotEmpty(inlineScripts);
            foreach (var script in inlineScripts)
            {
                var attribute = Regex.Match(script.Value, @"\snonce\s*=\s*([""'])(.*?)\1", options);
                Assert.True(attribute.Success, $"An inline script is missing its CSP nonce: {script.Value}");
                Assert.Equal(nonce, WebUtility.HtmlDecode(attribute.Groups[2].Value));
            }
        }
    }
}
