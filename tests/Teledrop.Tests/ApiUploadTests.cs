using System.Net;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Xunit;

namespace Teledrop.Tests;

public sealed class ApiUploadTests
{
    [Fact]
    public async Task MissingApiKeyReturns401WithApiKeyChallenge()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        using var multipart = CreateMultipart();

        using var response = await client.PostAsync(
            "/api/upload",
            multipart);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        var challenge = Assert.Single(
            response.Headers.WwwAuthenticate);
        Assert.Equal("ApiKey", challenge.Scheme);
    }

    [Fact]
    public async Task WrongApiKeyReturns401()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        client.DefaultRequestHeaders.Add(
            "X-API-Key",
            "wrong-api-key");
        using var multipart = CreateMultipart();

        using var response = await client.PostAsync(
            "/api/upload",
            multipart);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task CorrectApiKeyCreatesPrivateDropAndReturnsUploadDetails()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        client.DefaultRequestHeaders.Add(
            "X-API-Key",
            TeledropWebApplicationFactory.ApiKey);
        var fileBytes = "api-upload-payload"u8.ToArray();
        using var multipart = CreateMultipart(
            fileBytes,
            title: "API title",
            description: "API description");

        using var response = await client.PostAsync(
            "/api/upload",
            multipart);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        await using var responseBody =
            await response.Content.ReadAsStreamAsync();
        using var document = await JsonDocument.ParseAsync(responseBody);
        var root = document.RootElement;
        var slug = Assert.IsType<string>(
            root.GetProperty("slug").GetString());

        Assert.False(string.IsNullOrWhiteSpace(slug));
        Assert.Equal(
            $"/{slug}",
            root.GetProperty("url").GetString());
        Assert.Equal(
            "sample.bin",
            root.GetProperty("fileName").GetString());
        Assert.Equal(
            fileBytes.LongLength,
            root.GetProperty("sizeBytes").GetInt64());

        await using var scope = factory.Services.CreateAsyncScope();
        var dbContext = scope.ServiceProvider
            .GetRequiredService<TeledropDbContext>();
        var drop = await dbContext.Drops.AsNoTracking().SingleAsync();

        Assert.Equal(slug, drop.Slug);
        Assert.Equal("API title", drop.Title);
        Assert.Equal("API description", drop.Description);
        Assert.True(drop.IsPrivate);
        Assert.Equal("sample.bin", drop.FileName);
        Assert.Equal(fileBytes.LongLength, drop.FileSizeBytes);
        Assert.Equal(
            Convert.ToHexStringLower(SHA256.HashData(fileBytes)),
            drop.FileHash);

        var storedPath = Path.Combine(
            factory.ShareDirectory,
            drop.Location);
        Assert.Equal(
            fileBytes,
            await File.ReadAllBytesAsync(storedPath));
    }

    [Fact]
    public async Task UnconfiguredApiKeyRejectsUpload()
    {
        using var factory = new TeledropWebApplicationFactory(
            apiKey: null);
        using var client = CreateClient(factory);
        client.DefaultRequestHeaders.Add(
            "X-API-Key",
            "well-formed-api-key");
        using var multipart = CreateMultipart();

        using var response = await client.PostAsync(
            "/api/upload",
            multipart);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task OwnerSessionCookieWithoutApiKeyReturns401()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        await LogInAsync(client);
        using var multipart = CreateMultipart();

        using var response = await client.PostAsync(
            "/api/upload",
            multipart);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    private static MultipartFormDataContent CreateMultipart(
        byte[]? fileBytes = null,
        string? title = null,
        string? description = null)
    {
        var multipart = new MultipartFormDataContent();

        if (title is not null)
        {
            multipart.Add(new StringContent(title), "title");
        }

        if (description is not null)
        {
            multipart.Add(
                new StringContent(description),
                "description");
        }

        var fileContent = new ByteArrayContent(
            fileBytes ?? "api-upload"u8.ToArray());
        fileContent.Headers.ContentType =
            new MediaTypeHeaderValue("application/octet-stream");
        multipart.Add(fileContent, "file", "sample.bin");

        return multipart;
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
        using var loginPage = await client.GetAsync("/login");
        loginPage.EnsureSuccessStatusCode();
        var pageBody = await loginPage.Content.ReadAsStringAsync();
        var verificationValue = ExtractAntiforgeryValue(pageBody);
        var formValues = new Dictionary<string, string>
        {
            ["Username"] = TeledropWebApplicationFactory.WebUsername,
            ["Password"] = TeledropWebApplicationFactory.WebPassword,
            ["ReturnUrl"] = "/",
            ["__RequestVerificationToken"] = verificationValue,
        };

        using var content = new FormUrlEncodedContent(formValues);
        using var response = await client.PostAsync("/login", content);
        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
    }

    private static string ExtractAntiforgeryValue(string pageBody)
    {
        const string nameMarker =
            "name=\"__RequestVerificationToken\"";
        const string valueMarker = "value=\"";

        var namePosition = pageBody.IndexOf(
            nameMarker,
            StringComparison.Ordinal);
        Assert.True(
            namePosition >= 0,
            "The login form has no antiforgery field.");

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
        Assert.True(
            valueEnd > valueStart,
            "The antiforgery value is empty.");

        return WebUtility.HtmlDecode(input[valueStart..valueEnd]);
    }
}
