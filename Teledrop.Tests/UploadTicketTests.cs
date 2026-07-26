using System.Net;
using System.Net.Http.Headers;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Teledrop.Features.UploadTickets;
using Xunit;

namespace Teledrop.Tests;

public sealed class UploadTicketTests
{
    [Fact]
    public async Task MissingTicketPathReturns404()
    {
        using var factory = new TeledropWebApplicationFactory();
        using var client = CreateClient(factory);

        using var response = await client.GetAsync("/u/xxxx");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal(
            "noindex, nofollow",
            Assert.Single(response.Headers.GetValues("X-Robots-Tag")));
        Assert.Equal(
            "no-referrer",
            Assert.Single(response.Headers.GetValues("Referrer-Policy")));
    }

    [Fact]
    public async Task CorrectCodeCreatesPrivateDropConsumesTicketAndStaysWriteOnly()
    {
        using var factory = new TeledropWebApplicationFactory();
        var uploadTicket = await AddUploadTicketAsync(
            factory,
            path: "ab2c",
            code: "defg2345");
        using var client = CreateClient(factory);
        var verificationValue = await GetGuestAntiforgeryValueAsync(
            client,
            "/u/AB-2C");
        var fileBytes = "guest-ticket-upload"u8.ToArray();

        using var response = await PostGuestUploadAsync(
            client,
            "/u/AB-2C",
            "DEFG-2345",
            verificationValue,
            fileBytes,
            "guest-file.bin");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = WebUtility.HtmlDecode(
            await response.Content.ReadAsStringAsync());
        Assert.Contains("받았습니다.", body, StringComparison.Ordinal);
        Assert.Contains("guest-file.bin", body, StringComparison.Ordinal);
        Assert.Contains(
            $"{fileBytes.LongLength} B",
            body,
            StringComparison.Ordinal);

        await using var scope = factory.Services.CreateAsyncScope();
        var dbContext = scope.ServiceProvider
            .GetRequiredService<TeledropDbContext>();
        var drop = await dbContext.Drops.AsNoTracking().SingleAsync();
        var storedTicket = await dbContext.UploadTickets
            .AsNoTracking()
            .SingleAsync(ticket => ticket.Id == uploadTicket.Id);

        Assert.True(drop.IsPrivate);
        Assert.Equal(uploadTicket.Id, drop.UploadTicketId);
        Assert.NotNull(storedTicket.FirstUsedAtUtc);
        Assert.NotNull(storedTicket.ConsumedAtUtc);
        Assert.Equal(drop.Id, storedTicket.CreatedDropId);
        Assert.DoesNotContain(drop.Slug, body, StringComparison.Ordinal);

        var storedFilePath = Path.Combine(
            factory.ShareDirectory,
            drop.Location);
        Assert.Equal(
            fileBytes,
            await File.ReadAllBytesAsync(storedFilePath));
    }

    [Fact]
    public async Task ConsumedTicketCannotBeReused()
    {
        using var factory = new TeledropWebApplicationFactory();
        var uploadTicket = await AddUploadTicketAsync(
            factory,
            path: "bc3d",
            code: "efgh3456");
        using var client = CreateClient(factory);
        var verificationValue = await GetGuestAntiforgeryValueAsync(
            client,
            $"/u/{uploadTicket.Path}");

        using (var firstResponse = await PostGuestUploadAsync(
                   client,
                   $"/u/{uploadTicket.Path}",
                   uploadTicket.Code,
                   verificationValue,
                   "first"u8.ToArray(),
                   "first.bin"))
        {
            Assert.Equal(HttpStatusCode.OK, firstResponse.StatusCode);
        }

        using var secondResponse = await PostGuestUploadAsync(
            client,
            $"/u/{uploadTicket.Path}",
            uploadTicket.Code,
            verificationValue,
            "second"u8.ToArray(),
            "second.bin");

        Assert.Equal(HttpStatusCode.Gone, secondResponse.StatusCode);

        await using var scope = factory.Services.CreateAsyncScope();
        var dbContext = scope.ServiceProvider
            .GetRequiredService<TeledropDbContext>();
        Assert.Equal(1, await dbContext.Drops.CountAsync());
    }

    [Fact]
    public async Task ExpiredTicketShowsNoCodeFormAndRejectsUpload()
    {
        using var factory = new TeledropWebApplicationFactory();
        var uploadTicket = await AddUploadTicketAsync(
            factory,
            path: "cd4e",
            code: "fghj4567",
            expiresAtUtc: DateTime.UtcNow.AddMinutes(-1));
        using var client = CreateClient(factory);

        using var getResponse = await client.GetAsync(
            $"/u/{uploadTicket.Path}");

        Assert.Equal(HttpStatusCode.Gone, getResponse.StatusCode);
        var body = WebUtility.HtmlDecode(
            await getResponse.Content.ReadAsStringAsync());
        Assert.Contains("만료된 링크", body, StringComparison.Ordinal);
        Assert.DoesNotContain(
            "name=\"TicketCode\"",
            body,
            StringComparison.Ordinal);

        using var postResponse = await PostGuestUploadAsync(
            client,
            $"/u/{uploadTicket.Path}",
            uploadTicket.Code,
            verificationValue: null,
            "expired"u8.ToArray(),
            "expired.bin");
        Assert.Equal(HttpStatusCode.Gone, postResponse.StatusCode);

        await AssertNoDropsAsync(factory);
    }

    [Fact]
    public async Task TenthWrongCodeAttemptRevokesTicketAndCorrectCodeThenFails()
    {
        using var factory = new TeledropWebApplicationFactory();
        var uploadTicket = await AddUploadTicketAsync(
            factory,
            path: "de5f",
            code: "ghjk5678");
        using var client = CreateClient(factory);
        var verificationValue = await GetGuestAntiforgeryValueAsync(
            client,
            $"/u/{uploadTicket.Path}");

        for (var attempt = 1; attempt <= 10; attempt++)
        {
            using var response = await PostGuestUploadAsync(
                client,
                $"/u/{uploadTicket.Path}",
                "aaaa-aaaa",
                verificationValue,
                [(byte)attempt],
                "wrong.bin");

            Assert.Equal(
                attempt < 10
                    ? HttpStatusCode.BadRequest
                    : HttpStatusCode.Gone,
                response.StatusCode);
        }

        await using (var scope = factory.Services.CreateAsyncScope())
        {
            var dbContext = scope.ServiceProvider
                .GetRequiredService<TeledropDbContext>();
            var storedTicket = await dbContext.UploadTickets
                .AsNoTracking()
                .SingleAsync(ticket => ticket.Id == uploadTicket.Id);
            Assert.Equal(10, storedTicket.FailedCodeAttempts);
            Assert.NotNull(storedTicket.RevokedAtUtc);
        }

        using var correctCodeResponse = await PostGuestUploadAsync(
            client,
            $"/u/{uploadTicket.Path}",
            uploadTicket.Code,
            verificationValue,
            "correct"u8.ToArray(),
            "correct.bin");

        Assert.Equal(HttpStatusCode.Gone, correctCodeResponse.StatusCode);
        await AssertNoDropsAsync(factory);
    }

    [Fact]
    public async Task GetDoesNotSetFirstUseAndThirtyOneMinuteWindowRejectsPost()
    {
        using var factory = new TeledropWebApplicationFactory();
        var uploadTicket = await AddUploadTicketAsync(
            factory,
            path: "ef6g",
            code: "hjkm6789");
        using var client = CreateClient(factory);

        var verificationValue = await GetGuestAntiforgeryValueAsync(
            client,
            $"/u/{uploadTicket.Path}");

        await using (var scope = factory.Services.CreateAsyncScope())
        {
            var dbContext = scope.ServiceProvider
                .GetRequiredService<TeledropDbContext>();
            var storedTicket = await dbContext.UploadTickets
                .SingleAsync(ticket => ticket.Id == uploadTicket.Id);
            Assert.Null(storedTicket.FirstUsedAtUtc);

            storedTicket.FirstUsedAtUtc = DateTime.UtcNow.AddMinutes(-31);
            await dbContext.SaveChangesAsync();
        }

        using var response = await PostGuestUploadAsync(
            client,
            $"/u/{uploadTicket.Path}",
            uploadTicket.Code,
            verificationValue,
            "late"u8.ToArray(),
            "late.bin");

        Assert.Equal(HttpStatusCode.Gone, response.StatusCode);
        await AssertNoDropsAsync(factory);
    }

    [Fact]
    public async Task RevokedTicketRejectsUpload()
    {
        using var factory = new TeledropWebApplicationFactory();
        var uploadTicket = await AddUploadTicketAsync(
            factory,
            path: "fg7h",
            code: "jkmn789a",
            revokedAtUtc: DateTime.UtcNow.AddMinutes(-1));
        using var client = CreateClient(factory);

        using var getResponse = await client.GetAsync(
            $"/u/{uploadTicket.Path}");
        Assert.Equal(HttpStatusCode.Gone, getResponse.StatusCode);

        using var postResponse = await PostGuestUploadAsync(
            client,
            $"/u/{uploadTicket.Path}",
            uploadTicket.Code,
            verificationValue: null,
            "revoked"u8.ToArray(),
            "revoked.bin");

        Assert.Equal(HttpStatusCode.Gone, postResponse.StatusCode);
        await AssertNoDropsAsync(factory);
    }

    private static async Task<UploadTicket> AddUploadTicketAsync(
        TeledropWebApplicationFactory factory,
        string path,
        string code,
        DateTime? expiresAtUtc = null,
        DateTime? revokedAtUtc = null)
    {
        var now = DateTime.UtcNow;
        var uploadTicket = new UploadTicket
        {
            Id = Guid.NewGuid(),
            Path = path,
            Code = code,
            CreatedAt = now,
            ExpiresAtUtc = expiresAtUtc ?? now.AddHours(24),
            RevokedAtUtc = revokedAtUtc,
        };

        await using var scope = factory.Services.CreateAsyncScope();
        var dbContext = scope.ServiceProvider
            .GetRequiredService<TeledropDbContext>();
        dbContext.UploadTickets.Add(uploadTicket);
        await dbContext.SaveChangesAsync();

        return uploadTicket;
    }

    private static async Task AssertNoDropsAsync(
        TeledropWebApplicationFactory factory)
    {
        await using var scope = factory.Services.CreateAsyncScope();
        var dbContext = scope.ServiceProvider
            .GetRequiredService<TeledropDbContext>();
        Assert.False(await dbContext.Drops.AnyAsync());
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

    private static async Task<string> GetGuestAntiforgeryValueAsync(
        HttpClient client,
        string path)
    {
        using var response = await client.GetAsync(path);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var body = await response.Content.ReadAsStringAsync();
        return ExtractAntiforgeryValue(body);
    }

    private static async Task<HttpResponseMessage> PostGuestUploadAsync(
        HttpClient client,
        string path,
        string ticketCode,
        string? verificationValue,
        byte[] fileBytes,
        string fileName)
    {
        using var multipart = new MultipartFormDataContent();
        if (verificationValue is not null)
        {
            multipart.Add(
                new StringContent(verificationValue),
                "__RequestVerificationToken");
        }

        multipart.Add(new StringContent(ticketCode), "TicketCode");

        using var fileContent = new ByteArrayContent(fileBytes);
        fileContent.Headers.ContentType =
            new MediaTypeHeaderValue("application/octet-stream");
        multipart.Add(fileContent, "File", fileName);

        return await client.PostAsync(path, multipart);
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
            "The guest upload form has no antiforgery field.");

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
