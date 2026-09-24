using System.Net;
using System.Net.Http.Headers;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class UploadReceiverTests
{
    [Theory]
    [InlineData("Title", false)]
    [InlineData("Title", true)]
    [InlineData("Description", false)]
    [InlineData("Description", true)]
    [InlineData("unexpected", false)]
    [InlineData("unexpected", true)]
    public async Task WebRejectsAdditionalFieldsBeforeOrAfterFile(string name, bool afterFile)
    {
        using var harness = new Harness();
        var token = await harness.PrepareAsync(web: true);
        using var body = Multipart(token);
        if (!afterFile) body.Add(new StringContent("value"), name);
        AddFile(body, web: true);
        if (afterFile) body.Add(new StringContent("value"), name);
        using var response = await harness.Client.PostAsync("/upload", body);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        await harness.AssertEmptyAsync();
    }

    [Theory]
    [InlineData(true, "missing-file")]
    [InlineData(false, "missing-file")]
    [InlineData(true, "two-files")]
    [InlineData(false, "two-files")]
    [InlineData(true, "empty-filename")]
    [InlineData(false, "empty-filename")]
    [InlineData(true, "wrong-field")]
    [InlineData(false, "wrong-field")]
    [InlineData(true, "invalid-disposition")]
    [InlineData(false, "invalid-disposition")]
    public async Task InvalidFileInputLeavesNoDropOrFile(bool web, string scenario)
    {
        using var harness = new Harness();
        var token = await harness.PrepareAsync(web);
        using var body = Multipart(token);
        if (scenario != "missing-file")
        {
            var field = scenario == "wrong-field" ? (web ? "file" : "wrong") : web ? "File" : "file";
            var file = new ByteArrayContent("payload"u8.ToArray());
            if (scenario == "invalid-disposition")
            {
                file.Headers.ContentDisposition = new ContentDispositionHeaderValue("attachment")
                { Name = field, FileName = "payload.bin" };
                body.Add(file);
            }
            else body.Add(file, field, scenario == "empty-filename" ? "/" : "payload.bin");
        }
        if (scenario == "two-files") AddFile(body, web);
        using var response = await harness.Client.PostAsync(web ? "/upload" : "/api/upload", body);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        await harness.AssertEmptyAsync();
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task MissingMultipartBoundaryIsRejected(bool web)
    {
        using var harness = new Harness();
        await harness.PrepareAsync(web);
        using var body = new StringContent("not multipart");
        body.Headers.ContentType = new MediaTypeHeaderValue("multipart/form-data");
        using var response = await harness.Client.PostAsync(web ? "/upload" : "/api/upload", body);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        await harness.AssertEmptyAsync();
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task TruncatedMultipartIsInvalidInputAndCleansItsPartialFile(bool web)
    {
        using var harness = new Harness();
        var token = await harness.PrepareAsync(web);
        using var multipart = Multipart(token);
        AddFile(multipart, web);
        var bytes = await multipart.ReadAsByteArrayAsync();
        using var body = new ByteArrayContent(bytes[..^20]);
        body.Headers.ContentType = multipart.Headers.ContentType;
        using var response = await harness.Client.PostAsync(web ? "/upload" : "/api/upload", body);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        await harness.AssertEmptyAsync();
    }

    [Theory]
    [InlineData("missing-session", HttpStatusCode.Redirect)]
    [InlineData("missing-key", HttpStatusCode.Unauthorized)]
    [InlineData("wrong-key", HttpStatusCode.Unauthorized)]
    [InlineData("wrong-csrf", HttpStatusCode.BadRequest)]
    [InlineData("late-csrf", HttpStatusCode.BadRequest)]
    [InlineData("duplicate-csrf", HttpStatusCode.BadRequest)]
    public async Task AuthorizationAndCsrfRunBeforeOpeningAFile(string scenario, HttpStatusCode expected)
    {
        using var harness = new Harness();
        var web = !scenario.EndsWith("key", StringComparison.Ordinal);
        string? token = null;
        if (scenario is "wrong-csrf" or "late-csrf" or "duplicate-csrf")
            token = await harness.PrepareAsync(web: true);
        if (scenario == "wrong-key") harness.Client.DefaultRequestHeaders.Add("X-API-Key", "wrong");
        using var body = Multipart(scenario == "wrong-csrf" ? "invalid-token" : scenario == "late-csrf" ? null : token);
        if (scenario == "duplicate-csrf") body.Add(new StringContent(token!), "__RequestVerificationToken");
        AddFile(body, web);
        if (scenario == "late-csrf") body.Add(new StringContent(token!), "__RequestVerificationToken");
        // Opening any file would fail with an IO error. The rejection must happen first.
        Directory.Delete(harness.Factory.ShareDirectory);
        using var response = await harness.Client.PostAsync(web ? "/upload" : "/api/upload", body);
        Assert.Equal(expected, response.StatusCode);
        Assert.False(Directory.Exists(harness.Factory.ShareDirectory));
        await harness.AssertEmptyAsync();
    }

    [Fact]
    public async Task ApiPreservesCaseInsensitiveMetadataLastValueAndEmptySemantics()
    {
        using var harness = new Harness();
        await harness.PrepareAsync(web: false);
        using var body = Multipart(null);
        body.Add(new StringContent("first"), "TITLE");
        body.Add(new ByteArrayContent("payload"u8.ToArray()), "FiLe", "C:\\temp\\payload.bin");
        body.Add(new StringContent(" last "), "title");
        body.Add(new StringContent("old"), "description");
        body.Add(new StringContent(""), "DESCRIPTION");
        using var response = await harness.Client.PostAsync("/api/upload", body);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        using var scope = harness.App.Services.CreateScope();
        var drop = await scope.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops.SingleAsync();
        Assert.Equal(" last ", drop.Title);
        Assert.Null(drop.Description);
        Assert.Equal("payload.bin", drop.FileName);
        Assert.Equal("application/octet-stream", drop.ContentType);
        Assert.True(drop.IsPrivate);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task ApiRejectsUnknownFieldsAndCleansCompletedFile(bool afterFile)
    {
        using var harness = new Harness();
        await harness.PrepareAsync(web: false);
        using var body = Multipart(null);
        if (!afterFile) body.Add(new StringContent("true"), "public");
        AddFile(body, web: false);
        if (afterFile) body.Add(new StringContent("true"), "public");
        using var response = await harness.Client.PostAsync("/api/upload", body);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        await harness.AssertEmptyAsync();
    }

    [Theory]
    [InlineData("text")]
    [InlineData("values")]
    [InlineData("headers")]
    [InlineData("header-length")]
    [InlineData("boundary")]
    public async Task MultipartLimitsAreEnforced(string limit)
    {
        using var harness = new Harness(services => services.Configure<FormOptions>(options =>
        {
            if (limit == "text") options.ValueLengthLimit = 4;
            if (limit == "values") options.ValueCountLimit = 1;
            if (limit == "headers") options.MultipartHeadersCountLimit = 1;
            if (limit == "header-length") options.MultipartHeadersLengthLimit = 8;
            if (limit == "boundary") options.MultipartBoundaryLengthLimit = 4;
        }));
        await harness.PrepareAsync(web: false);
        using var body = Multipart(null);
        var file = new ByteArrayContent("payload"u8.ToArray());
        file.Headers.ContentType = new MediaTypeHeaderValue("application/octet-stream");
        body.Add(file, "file", "payload.bin");
        body.Add(new StringContent("long-value"), "title");
        body.Add(new StringContent("another-value"), "description");
        using var response = await harness.Client.PostAsync("/api/upload", body);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        await harness.AssertEmptyAsync();
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task FileSizeLimitReturns413AndCleansPartialFile(bool web)
    {
        using var harness = new Harness(services => services.Configure<TeledropOptions>(o => o.MaxUploadBytes = 4));
        var token = await harness.PrepareAsync(web);
        using var body = Multipart(token);
        AddFile(body, web);
        using var response = await harness.Client.PostAsync(web ? "/upload" : "/api/upload", body);
        Assert.Equal(HttpStatusCode.RequestEntityTooLarge, response.StatusCode);
        await harness.AssertEmptyAsync();
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task CancellationDuringFileOrLaterMetadataCleansOwnedFile(bool afterFile)
    {
        using var harness = new Harness();
        using var body = Multipart(null);
        body.Add(new ByteArrayContent(new byte[afterFile ? 8 : 131072]), "file", "payload.bin");
        if (afterFile) body.Add(new StringContent(new string('a', 131072)), "title");
        var bytes = await body.ReadAsByteArrayAsync();
        using var cts = new CancellationTokenSource();
        var sawFile = false;
        using var stream = new CancelingStream(bytes, cts, () =>
            sawFile = Directory.EnumerateFiles(harness.Factory.ShareDirectory).Any());
        var context = new DefaultHttpContext();
        context.Request.ContentType = body.Headers.ContentType!.ToString();
        context.Request.Body = stream;
        using var scope = harness.App.Services.CreateScope();
        var receiver = scope.ServiceProvider.GetRequiredService<DropUploadReceiver>();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => receiver.ReceiveApiAsync(context.Request, cts.Token));
        Assert.True(sawFile);
        await harness.AssertEmptyAsync();
    }

    [Fact]
    public async Task PersistenceFailurePropagatesAndCompensatesAfterHandoff()
    {
        var failure = new InvalidDataException("Persistence failure, not a multipart error.");
        using var harness = new Harness(services => services.AddScoped<IDropCommandStore>(_ => new FailingStore(failure)));
        using var body = Multipart(null);
        AddFile(body, web: false);
        var context = new DefaultHttpContext();
        context.Request.ContentType = body.Headers.ContentType!.ToString();
        context.Request.Body = new MemoryStream(await body.ReadAsByteArrayAsync());
        using var scope = harness.App.Services.CreateScope();
        var receiver = scope.ServiceProvider.GetRequiredService<DropUploadReceiver>();
        var thrown = await Assert.ThrowsAsync<InvalidDataException>(() => receiver.ReceiveApiAsync(context.Request, CancellationToken.None));
        Assert.Same(failure, thrown);
        await harness.AssertEmptyAsync();
    }

    [Fact]
    public async Task DiskFailureIsNotReportedAsInvalidInput()
    {
        using var harness = new Harness();
        Directory.Delete(harness.Factory.ShareDirectory);
        using var body = Multipart(null);
        AddFile(body, web: false);
        var context = new DefaultHttpContext();
        context.Request.ContentType = body.Headers.ContentType!.ToString();
        context.Request.Body = new MemoryStream(await body.ReadAsByteArrayAsync());
        using var scope = harness.App.Services.CreateScope();
        var receiver = scope.ServiceProvider.GetRequiredService<DropUploadReceiver>();
        await Assert.ThrowsAsync<DirectoryNotFoundException>(() => receiver.ReceiveApiAsync(context.Request, CancellationToken.None));
        await harness.AssertEmptyAsync();
    }

    private static MultipartFormDataContent Multipart(string? token)
    {
        var result = new MultipartFormDataContent();
        if (token is not null) result.Add(new StringContent(token), "__RequestVerificationToken");
        return result;
    }

    private static void AddFile(MultipartFormDataContent body, bool web)
        => body.Add(new ByteArrayContent("payload"u8.ToArray()), web ? "File" : "file", "payload.bin");

    private sealed class Harness : IDisposable
    {
        internal TeledropWebApplicationFactory Factory { get; } = new();
        internal WebApplicationFactory<Program> App { get; }
        internal HttpClient Client { get; }

        internal Harness(Action<IServiceCollection>? configure = null)
        {
            App = configure is null ? Factory : Factory.WithWebHostBuilder(builder =>
                builder.ConfigureServices(configure));
            Client = CreateClient(App);
        }

        internal async Task<string?> PrepareAsync(bool web)
        {
            if (!web)
            {
                Client.DefaultRequestHeaders.Add("X-API-Key", TeledropWebApplicationFactory.ApiKey);
                return null;
            }
            await LogInOwnerAsync(Client);
            return await GetAntiforgeryAsync(Client, "/");
        }

        internal async Task AssertEmptyAsync()
        {
            using var scope = App.Services.CreateScope();
            Assert.False(await scope.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops.AnyAsync());
            if (Directory.Exists(Factory.ShareDirectory)) Assert.Empty(Directory.EnumerateFiles(Factory.ShareDirectory));
        }

        public void Dispose()
        {
            Client.Dispose();
            if (!ReferenceEquals(App, Factory)) App.Dispose();
            Factory.Dispose();
        }
    }

    private sealed class CancelingStream(byte[] bytes, CancellationTokenSource cancellation, Action beforeCancel)
        : MemoryStream(bytes)
    {
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
        {
            if (Position >= 8192)
            {
                beforeCancel();
                cancellation.Cancel();
                cancellationToken.ThrowIfCancellationRequested();
            }
            return base.ReadAsync(buffer[..Math.Min(buffer.Length, 1024)], cancellationToken);
        }
    }

    private sealed class FailingStore(Exception failure) : IDropCommandStore
    {
        public Task<DropSlugWriteResult> TryAddAsync(Drop drop, CancellationToken cancellationToken) => throw failure;
        public Task<DropSlugWriteResult> TryChangeSlugAsync(Drop drop, string newSlug, DateTime updatedAtUtc, CancellationToken cancellationToken) => throw new NotSupportedException();
        public Task<Drop?> FindBySlugAsync(string slug, CancellationToken cancellationToken) => throw new NotSupportedException();
        public Task UpdateAsync(Drop drop, CancellationToken cancellationToken) => throw new NotSupportedException();
        public Task<Drop?> DeleteBySlugAsync(string slug, CancellationToken cancellationToken) => throw new NotSupportedException();
    }
}
