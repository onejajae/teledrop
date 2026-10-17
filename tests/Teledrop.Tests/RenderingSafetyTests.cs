using System.Net;
using System.Text.Encodings.Web;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class RenderingSafetyTests
{
    [Theory]
    [InlineData("/drops/encoded", true, false)]
    [InlineData("/encoded", false, false)]
    [InlineData("/?handler=DropList", true, true)]
    public async Task UntrustedDropTextIsEncodedInOwnerPublicAndListResponses(
        string path, bool owner, bool htmx)
    {
        const string fileName = "<img src=x onerror=alert(1)> & \"name\".txt";
        const string description = "Description <script>alert(1)</script> & \"text\"";
        using var factory = new TeledropWebApplicationFactory();
        await SeedDropAsync(factory, "encoded", [1], drop =>
        {
            drop.IsPrivate = false;
            drop.FileName = fileName;
            drop.Description = description;
        });
        using var client = CreateClient(factory);
        if (owner) await LogInOwnerAsync(client);
        using var request = new HttpRequestMessage(HttpMethod.Get, path);
        if (htmx) request.Headers.Add("HX-Request", "true");

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var html = await response.Content.ReadAsStringAsync();
        Assert.Contains(HtmlEncoder.Default.Encode(fileName), html);
        if (!htmx) Assert.Contains(HtmlEncoder.Default.Encode(description), html);
        Assert.DoesNotContain("<img src=x onerror=alert(1)>", html);
        Assert.DoesNotContain("<script>alert(1)</script>", html);
    }
}
