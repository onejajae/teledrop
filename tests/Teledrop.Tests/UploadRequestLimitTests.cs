using System.Net;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class UploadRequestLimitTests
{
    private const int MaximumBytes = 65536;

    [Theory]
    [InlineData(true, false, false)]
    [InlineData(true, true, false)]
    [InlineData(false, false, false)]
    [InlineData(false, true, false)]
    [InlineData(false, true, true)]
    public async Task OversizedRequestReturnsEmpty413WithoutDropOrFile(
        bool web, bool chunked, bool metadataAfterFile)
    {
        using var factory = new TeledropWebApplicationFactory(maxUploadBytes: MaximumBytes);
        using var client = StartClient(factory);
        var token = await PrepareAsync(client, web);
        using var multipart = CreateMultipart(web, token,
            new byte[metadataAfterFile ? 8192 : MaximumBytes + 16384]);
        if (metadataAfterFile)
            multipart.Add(new StringContent(new string('a', MaximumBytes + 16384)), "description");
        var bytes = await multipart.ReadAsByteArrayAsync();
        Assert.True(bytes.Length > MaximumBytes);
        using var request = new HttpRequestMessage(HttpMethod.Post, web ? "/upload" : "/api/upload")
        {
            Version = HttpVersion.Version11,
            VersionPolicy = HttpVersionPolicy.RequestVersionExact,
            Content = chunked ? new ChunkedContent(bytes) : new ByteArrayContent(bytes),
        };
        request.Content.Headers.ContentType = multipart.Headers.ContentType;
        if (chunked) request.Headers.TransferEncodingChunked = true;

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.RequestEntityTooLarge, response.StatusCode);
        Assert.Empty(await response.Content.ReadAsByteArrayAsync());
        using var scope = factory.Services.CreateScope();
        Assert.False(await scope.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops.AnyAsync());
        Assert.Empty(Directory.EnumerateFiles(factory.ShareDirectory));
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task RequestBelowLimitCreatesPrivateDrop(bool web)
    {
        using var factory = new TeledropWebApplicationFactory(maxUploadBytes: MaximumBytes);
        using var client = StartClient(factory);
        var token = await PrepareAsync(client, web);
        var bytes = "valid upload"u8.ToArray();
        using var multipart = CreateMultipart(web, token, bytes);

        using var response = await client.PostAsync(web ? "/upload" : "/api/upload", multipart);

        Assert.Equal(web ? HttpStatusCode.Redirect : HttpStatusCode.OK, response.StatusCode);
        using var scope = factory.Services.CreateScope();
        var drop = await scope.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops.SingleAsync();
        Assert.True(drop.IsPrivate);
        Assert.Equal(bytes, await File.ReadAllBytesAsync(Path.Combine(factory.ShareDirectory, drop.Location)));
    }

    private static HttpClient StartClient(TeledropWebApplicationFactory factory)
    {
        factory.UseKestrel(0);
        using var serverClient = factory.CreateClient();
        return new HttpClient(new HttpClientHandler { AllowAutoRedirect = false })
        {
            BaseAddress = serverClient.BaseAddress,
        };
    }

    private static async Task<string?> PrepareAsync(HttpClient client, bool web)
    {
        if (!web)
        {
            client.DefaultRequestHeaders.Add("X-API-Key", TeledropWebApplicationFactory.ApiKey);
            return null;
        }
        await LogInOwnerAsync(client);
        return await GetAntiforgeryAsync(client, "/");
    }

    private static MultipartFormDataContent CreateMultipart(bool web, string? token, byte[] bytes)
    {
        var multipart = new MultipartFormDataContent();
        if (token is not null) multipart.Add(new StringContent(token), "__RequestVerificationToken");
        multipart.Add(new ByteArrayContent(bytes), web ? "File" : "file", "payload.bin");
        return multipart;
    }

    // Exercise Kestrel's streaming limit without supplying a Content-Length.
    private sealed class ChunkedContent(byte[] bytes) : HttpContent
    {
        protected override bool TryComputeLength(out long length)
        {
            length = 0;
            return false;
        }

        protected override Task SerializeToStreamAsync(Stream stream, TransportContext? context)
            => stream.WriteAsync(bytes).AsTask();
    }
}
