using System.Net;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Tests;

public sealed class FileCoreTests
{
    [Fact]
    public async Task AuthenticatedMultipartUploadCreatesPrivateDropFileAndHash()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        await LogInAsync(client);

        var homeBody = await client.GetStringAsync("/");
        var verificationValue = ExtractAntiforgeryValue(homeBody);
        var fileBytes = "teledrop-streaming-upload"u8.ToArray();

        using var multipart = new MultipartFormDataContent();
        multipart.Add(
            new StringContent(verificationValue),
            "__RequestVerificationToken");
        multipart.Add(new StringContent("Upload title"), "Title");
        multipart.Add(new StringContent("Upload description"), "Description");

        using var fileContent = new ByteArrayContent(fileBytes);
        fileContent.Headers.ContentType =
            new MediaTypeHeaderValue("application/octet-stream");
        multipart.Add(fileContent, "File", "sample.bin");

        using var response = await client.PostAsync("/upload", multipart);

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);

        await using var scope = factory.Services.CreateAsyncScope();
        var dbContext = scope.ServiceProvider
            .GetRequiredService<TeledropDbContext>();
        var drop = await dbContext.Drops.AsNoTracking().SingleAsync();

        var storedPath = Path.Combine(factory.ShareDirectory, drop.Location);
        Assert.True(File.Exists(storedPath));

        var storedBytes = await File.ReadAllBytesAsync(storedPath);
        Assert.Equal(fileBytes, storedBytes);
        Assert.Equal(
            Convert.ToHexStringLower(SHA256.HashData(storedBytes)),
            drop.FileHash);
        Assert.Equal(fileBytes.LongLength, drop.FileSizeBytes);
        Assert.True(drop.IsPrivate);
    }

    [Fact]
    public async Task DeletingDropWithMissingPhysicalFileRemovesRowWithoutServerError()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        await LogInAsync(client);

        var drop = await AddDropAsync(factory, "missing-file", null);
        var homeBody = await client.GetStringAsync("/");
        var verificationValue = ExtractAntiforgeryValue(homeBody);
        var formValues = new Dictionary<string, string>
        {
            ["slug"] = drop.Slug,
            ["__RequestVerificationToken"] = verificationValue,
        };

        using var content = new FormUrlEncodedContent(formValues);
        using var response = await client.PostAsync(
            "/?handler=Delete",
            content);

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);

        await using var scope = factory.Services.CreateAsyncScope();
        var dbContext = scope.ServiceProvider
            .GetRequiredService<TeledropDbContext>();
        Assert.False(await dbContext.Drops.AnyAsync(
            candidate => candidate.Id == drop.Id));
    }

    [Fact]
    public async Task DownloadRangeReturnsRequestedFirstFourBytes()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        await LogInAsync(client);

        var fileBytes = "0123456789"u8.ToArray();
        var drop = await AddDropAsync(factory, "range-download", fileBytes);
        using var request = new HttpRequestMessage(
            HttpMethod.Get,
            $"/d/{drop.Slug}");
        request.Headers.Range = new RangeHeaderValue(0, 3);

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.PartialContent, response.StatusCode);
        Assert.Equal(
            fileBytes[..4],
            await response.Content.ReadAsByteArrayAsync());
    }

    [Fact]
    public async Task UnauthenticatedDownloadRedirectsToLogin()
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await AddDropAsync(factory, "private-download", null);
        using var client = CreateClient(factory);

        using var response = await client.GetAsync($"/d/{drop.Slug}");

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        var location = Assert.IsType<Uri>(response.Headers.Location);
        var pathAndQuery = location.IsAbsoluteUri
            ? location.PathAndQuery
            : location.OriginalString;
        Assert.StartsWith("/login?ReturnUrl=", pathAndQuery);
    }

    private static async Task<Drop> AddDropAsync(
        TeledropWebApplicationFactory factory,
        string slug,
        byte[]? fileBytes)
    {
        var location = Guid.NewGuid().ToString("N");
        var drop = new Drop
        {
            Id = Guid.NewGuid(),
            Slug = slug,
            IsPrivate = true,
            FileName = $"{slug}.bin",
            FileHash = Convert.ToHexStringLower(
                SHA256.HashData(fileBytes ?? [])),
            FileSizeBytes = fileBytes?.LongLength ?? 0,
            ContentType = "application/octet-stream",
            Location = location,
            CreatedAt = DateTime.UtcNow,
        };

        await using (var scope = factory.Services.CreateAsyncScope())
        {
            var dbContext = scope.ServiceProvider
                .GetRequiredService<TeledropDbContext>();
            dbContext.Drops.Add(drop);
            await dbContext.SaveChangesAsync();
        }

        if (fileBytes is not null)
        {
            await File.WriteAllBytesAsync(
                Path.Combine(factory.ShareDirectory, location),
                fileBytes);
        }

        return drop;
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
        const string nameMarker = "name=\"__RequestVerificationToken\"";
        const string valueMarker = "value=\"";

        var namePosition = pageBody.IndexOf(
            nameMarker,
            StringComparison.Ordinal);
        Assert.True(
            namePosition >= 0,
            "The page has no antiforgery field.");

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
