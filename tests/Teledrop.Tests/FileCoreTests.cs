using System.Net;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class FileCoreTests
{
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task AuthenticatedMultipartUploadCreatesPrivateDropFileAndHash(bool htmx)
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);

        var homeBody = await client.GetStringAsync("/");
        var verificationValue = ExtractAntiforgery(homeBody);
        var fileBytes = "teledrop-streaming-upload"u8.ToArray();

        using var multipart = new MultipartFormDataContent();
        multipart.Add(
            new StringContent(verificationValue),
            "__RequestVerificationToken");

        using var fileContent = new ByteArrayContent(fileBytes);
        fileContent.Headers.ContentType =
            new MediaTypeHeaderValue("application/octet-stream");
        multipart.Add(fileContent, "File", "sample.bin");

        if (htmx) client.DefaultRequestHeaders.Add("HX-Request", "true");
        using var response = await client.PostAsync("/upload", multipart);

        Assert.Equal(htmx ? HttpStatusCode.NoContent : HttpStatusCode.Redirect, response.StatusCode);

        await using var scope = factory.Services.CreateAsyncScope();
        var dbContext = scope.ServiceProvider
            .GetRequiredService<TeledropDbContext>();
        var drop = await dbContext.Drops.AsNoTracking().SingleAsync();

        var destination = htmx ? Assert.Single(response.Headers.GetValues("HX-Redirect")) : response.Headers.Location!.ToString();
        Assert.Equal($"/drops/{drop.Slug}", destination);
        var storedPath = Path.Combine(factory.ShareDirectory, drop.Location);
        Assert.True(File.Exists(storedPath));

        var storedBytes = await File.ReadAllBytesAsync(storedPath);
        Assert.Equal(fileBytes, storedBytes);
        Assert.Equal(
            Convert.ToHexStringLower(SHA256.HashData(storedBytes)),
            drop.FileHash);
        Assert.Equal(fileBytes.LongLength, drop.FileSizeBytes);
        Assert.True(drop.IsPrivate);
        Assert.Null(drop.Title);
        Assert.Null(drop.Description);
    }

    [Fact]
    public async Task DeletingDropWithMissingPhysicalFileRemovesRowWithoutServerError()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);

        var drop = await SeedDropAsync(factory, "missing-file", null);
        var homeBody = await client.GetStringAsync("/");
        var verificationValue = ExtractAntiforgery(homeBody);
        var formValues = new Dictionary<string, string>
        {
            ["slug"] = drop.Slug,
            ["__RequestVerificationToken"] = verificationValue,
        };

        using var content = new FormUrlEncodedContent(formValues);
        using var response = await client.PostAsync(
            $"/drops/{drop.Slug}?handler=Delete",
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
        await LogInOwnerAsync(client);

        var fileBytes = "0123456789"u8.ToArray();
        var drop = await SeedDropAsync(factory, "range-download", fileBytes);
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
        var drop = await SeedDropAsync(factory, "private-download", null);
        using var client = CreateClient(factory);

        using var response = await client.GetAsync($"/d/{drop.Slug}");

        Assert.Equal(HttpStatusCode.Redirect, response.StatusCode);
        var location = Assert.IsType<Uri>(response.Headers.Location);
        var pathAndQuery = location.IsAbsoluteUri
            ? location.PathAndQuery
            : location.OriginalString;
        Assert.StartsWith("/login?ReturnUrl=", pathAndQuery);
    }

    [Fact]
    public async Task AuthorizedDownloadOfMissingPhysicalFileReturns404()
    {
        using var factory = new TeledropWebApplicationFactory();
        var drop = await SeedDropAsync(factory, "missing-download", null);
        using var client = CreateClient(factory);
        await LogInOwnerAsync(client);

        using var response = await client.GetAsync($"/d/{drop.Slug}");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task ExistingMigratedDatabaseAndStoredFileRemainReadable()
    {
        using var factory = new TeledropWebApplicationFactory();
        Directory.CreateDirectory(factory.ShareDirectory);

        var fileBytes = "existing-file-data"u8.ToArray();
        const string location = "existing-file";
        var drop = new Drop
        {
            Id = Guid.NewGuid(),
            Slug = "existing-drop",
            Title = "Existing title",
            IsPrivate = false,
            FileName = "existing.bin",
            FileHash = Convert.ToHexStringLower(
                SHA256.HashData(fileBytes)),
            FileSizeBytes = fileBytes.LongLength,
            ContentType = "application/octet-stream",
            Location = location,
            CreatedAt = DateTime.UtcNow.AddDays(-1),
        };

        var databaseOptions =
            new DbContextOptionsBuilder<TeledropDbContext>()
                .UseSqlite($"Data Source={factory.DatabasePath}")
                .Options;
        await using (var existingDatabase =
                     new TeledropDbContext(databaseOptions))
        {
            await existingDatabase.Database.MigrateAsync();
            existingDatabase.Drops.Add(drop);
            await existingDatabase.SaveChangesAsync();
        }

        await File.WriteAllBytesAsync(
            Path.Combine(factory.ShareDirectory, location),
            fileBytes);

        using var client = CreateClient(factory);
        using var pageResponse = await client.GetAsync(
            $"/{drop.Slug}");
        using var downloadResponse = await client.GetAsync(
            $"/d/{drop.Slug}");

        Assert.Equal(HttpStatusCode.OK, pageResponse.StatusCode);
        Assert.Contains(
            drop.Title,
            await pageResponse.Content.ReadAsStringAsync(),
            StringComparison.Ordinal);
        Assert.Equal(HttpStatusCode.OK, downloadResponse.StatusCode);
        Assert.Equal(
            fileBytes,
            await downloadResponse.Content.ReadAsByteArrayAsync());

        await using var scope = factory.Services.CreateAsyncScope();
        var runningDatabase = scope.ServiceProvider
            .GetRequiredService<TeledropDbContext>();
        Assert.Equal(
            drop.Id,
            (await runningDatabase.Drops
                .AsNoTracking()
                .SingleAsync(candidate => candidate.Slug == drop.Slug))
                .Id);
    }

    [Fact]
    public async Task DerivedHostReadsSeededFilesFromItsConfiguredStorage()
    {
        using var factory = new TeledropWebApplicationFactory();
        var storage = Path.Combine(factory.ShareDirectory, "overridden");
        using var app = factory.WithWebHostBuilder(builder => builder.ConfigureServices(
            services => services.Configure<TeledropOptions>(options => options.ShareDirectory = storage)));
        var bytes = "from selected host"u8.ToArray();
        var drop = await SeedDropAsync(app, "selected-host", bytes, seed => seed.IsPrivate = false);
        using var client = CreateClient(app);

        using var response = await client.GetAsync($"/d/{drop.Slug}");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(bytes, await response.Content.ReadAsByteArrayAsync());
        Assert.True(File.Exists(Path.Combine(storage, drop.Location)));
        Assert.False(File.Exists(Path.Combine(factory.ShareDirectory, drop.Location)));
    }
}
