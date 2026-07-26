using System.Buffers;
using System.Security.Cryptography;
using System.Text;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.AspNetCore.WebUtilities;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Microsoft.Net.Http.Headers;
using Teledrop.Data;
using Teledrop.Features.Drops;

namespace Teledrop.Features.UploadTickets;

[AllowAnonymous]
[IgnoreAntiforgeryToken]
public sealed class GuestUploadModel(
    TeledropDbContext dbContext,
    DropSlugGenerator dropSlugGenerator,
    DropFileStore dropFileStore,
    IAntiforgery antiforgery,
    IOptions<AntiforgeryOptions> antiforgeryOptions,
    IOptions<FormOptions> formOptions,
    TimeProvider timeProvider)
    : PageModel
{
    private const int MaximumFailedCodeAttempts = 10;

    public bool IsUnavailable { get; private set; }

    public bool UploadSucceeded { get; private set; }

    public string? UploadedFileName { get; private set; }

    public long UploadedFileSizeBytes { get; private set; }

    public string? TicketCodeError { get; private set; }

    public async Task<IActionResult> OnGetAsync()
    {
        SetGuestResponseHeaders();

        var path = RouteData.Values["path"]?.ToString();
        if (path is null)
        {
            return NotFound();
        }

        var uploadTicket = await FindUploadTicketAsync(
            path,
            asTracking: false,
            HttpContext.RequestAborted);
        if (uploadTicket is null)
        {
            return NotFound();
        }

        if (!uploadTicket.CanAcceptUpload(
                timeProvider.GetUtcNow().UtcDateTime))
        {
            return ShowUnavailable();
        }

        return Page();
    }

    public async Task<IActionResult> OnPostAsync()
    {
        SetGuestResponseHeaders();

        var path = RouteData.Values["path"]?.ToString();
        if (path is null)
        {
            return NotFound();
        }

        var cancellationToken = HttpContext.RequestAborted;
        var requestStartedAtUtc = timeProvider.GetUtcNow().UtcDateTime;
        var uploadTicket = await FindUploadTicketAsync(
            path,
            asTracking: true,
            cancellationToken);
        if (uploadTicket is null)
        {
            return NotFound();
        }

        if (!uploadTicket.CanAcceptUpload(requestStartedAtUtc))
        {
            return ShowUnavailable();
        }

        await RecordFirstPostAsync(uploadTicket, requestStartedAtUtc);
        if (!uploadTicket.CanAcceptUpload(requestStartedAtUtc))
        {
            return ShowUnavailable();
        }

        if (!TryGetMultipartBoundary(out var boundary))
        {
            return BadRequest();
        }

        var requestAborted = HttpContext.RequestAborted;
        var reader = new MultipartReader(boundary, Request.Body)
        {
            HeadersCountLimit = formOptions.Value.MultipartHeadersCountLimit,
            HeadersLengthLimit = formOptions.Value.MultipartHeadersLengthLimit,
        };

        StoredDropFile? storedFile = null;
        var antiforgeryValidated = false;
        var ticketCodeValidated = false;
        var ticketCodeSeen = false;
        var sectionCount = 0;
        var formValueCount = 0;
        var persisted = false;

        try
        {
            MultipartSection? section;
            while ((section = await reader.ReadNextSectionAsync(
                       requestAborted)) is not null)
            {
                sectionCount++;

                if (!TryGetContentDisposition(
                        section,
                        out var contentDisposition,
                        out var fieldName))
                {
                    return BadRequest();
                }

                var isFile = contentDisposition.FileName.HasValue
                    || contentDisposition.FileNameStar.HasValue;

                if (sectionCount == 1
                    && (isFile
                        || !string.Equals(
                            fieldName,
                            antiforgeryOptions.Value.FormFieldName,
                            StringComparison.Ordinal)))
                {
                    return BadRequest();
                }

                if (isFile)
                {
                    if (!antiforgeryValidated
                        || !ticketCodeValidated
                        || storedFile is not null
                        || !string.Equals(
                            fieldName,
                            "File",
                            StringComparison.Ordinal))
                    {
                        return BadRequest();
                    }

                    var fileName = GetOriginalFileName(contentDisposition);
                    if (string.IsNullOrWhiteSpace(fileName))
                    {
                        return BadRequest();
                    }

                    storedFile = await dropFileStore.StoreAsync(
                        section.Body,
                        fileName,
                        string.IsNullOrWhiteSpace(section.ContentType)
                            ? "application/octet-stream"
                            : section.ContentType,
                        requestAborted);
                    continue;
                }

                formValueCount++;
                if (formValueCount > formOptions.Value.ValueCountLimit)
                {
                    return BadRequest();
                }

                var value = await ReadFormValueAsync(
                    section.Body,
                    formOptions.Value.ValueLengthLimit,
                    requestAborted);

                if (string.Equals(
                        fieldName,
                        antiforgeryOptions.Value.FormFieldName,
                        StringComparison.Ordinal))
                {
                    if (antiforgeryValidated
                        || storedFile is not null
                        || string.IsNullOrEmpty(value)
                        || !await ValidateAntiforgeryTokenAsync(value))
                    {
                        return BadRequest();
                    }

                    antiforgeryValidated = true;
                }
                else if (string.Equals(
                             fieldName,
                             "TicketCode",
                             StringComparison.Ordinal))
                {
                    if (!antiforgeryValidated
                        || ticketCodeSeen
                        || storedFile is not null)
                    {
                        return BadRequest();
                    }

                    ticketCodeSeen = true;
                    if (!TicketCodesMatch(uploadTicket.Code, value))
                    {
                        await RecordFailedCodeAttemptAsync(
                            uploadTicket,
                            requestStartedAtUtc);

                        if (!uploadTicket.CanAcceptUpload(
                                requestStartedAtUtc))
                        {
                            return ShowUnavailable();
                        }

                        TicketCodeError =
                            "Ticket Code가 올바르지 않습니다.";
                        Response.StatusCode =
                            StatusCodes.Status400BadRequest;
                        return Page();
                    }

                    ticketCodeValidated = true;
                }
                else
                {
                    return BadRequest();
                }
            }

            if (!antiforgeryValidated
                || !ticketCodeValidated
                || storedFile is null)
            {
                return BadRequest();
            }

            var dropId = Guid.NewGuid();
            var drop = new Drop
            {
                Id = dropId,
                Slug = await dropSlugGenerator.GenerateUniqueSlugAsync(
                    requestAborted),
                IsPrivate = true,
                FileName = storedFile.FileName,
                FileHash = storedFile.FileHash,
                FileSizeBytes = storedFile.FileSizeBytes,
                ContentType = storedFile.ContentType,
                Location = storedFile.Location,
                CreatedAt = timeProvider.GetUtcNow().UtcDateTime,
                UploadTicketId = uploadTicket.Id,
            };

            await using var transaction =
                await dbContext.Database.BeginTransactionAsync(
                    requestAborted);

            dbContext.Drops.Add(drop);
            await dbContext.SaveChangesAsync(requestAborted);

            var consumedAtUtc =
                timeProvider.GetUtcNow().UtcDateTime;
            var activeWindowStartUtc =
                requestStartedAtUtc.AddMinutes(-30);
            var affectedTickets = await dbContext.UploadTickets
                .Where(ticket =>
                    ticket.Id == uploadTicket.Id
                    && ticket.RevokedAtUtc == null
                    && ticket.ConsumedAtUtc == null
                    && requestStartedAtUtc < ticket.ExpiresAtUtc
                    && (ticket.FirstUsedAtUtc == null
                        || activeWindowStartUtc
                            < ticket.FirstUsedAtUtc))
                .ExecuteUpdateAsync(
                    setters => setters
                        .SetProperty(
                            ticket => ticket.ConsumedAtUtc,
                            consumedAtUtc)
                        .SetProperty(
                            ticket => ticket.CreatedDropId,
                            dropId),
                    requestAborted);

            if (affectedTickets != 1)
            {
                await transaction.RollbackAsync(requestAborted);
                return ShowUnavailable();
            }

            await transaction.CommitAsync(requestAborted);
            persisted = true;

            UploadSucceeded = true;
            UploadedFileName = storedFile.FileName;
            UploadedFileSizeBytes = storedFile.FileSizeBytes;
            return Page();
        }
        catch (DropUploadTooLargeException)
        {
            return StatusCode(StatusCodes.Status413PayloadTooLarge);
        }
        catch (InvalidGuestUploadException)
        {
            return BadRequest();
        }
        catch (InvalidDataException)
        {
            return BadRequest();
        }
        finally
        {
            if (!persisted && storedFile is not null)
            {
                dropFileStore.TryDelete(storedFile);
            }
        }
    }

    private async Task<UploadTicket?> FindUploadTicketAsync(
        string path,
        bool asTracking,
        CancellationToken cancellationToken)
    {
        if (!UploadTicketCredentialGenerator.TryNormalizeTicketPath(
                path,
                out var normalizedPath))
        {
            return null;
        }

        IQueryable<UploadTicket> query = dbContext.UploadTickets;
        if (!asTracking)
        {
            query = query.AsNoTracking();
        }

        return await query.SingleOrDefaultAsync(
            ticket => ticket.Path == normalizedPath,
            cancellationToken);
    }

    private async Task RecordFirstPostAsync(
        UploadTicket uploadTicket,
        DateTime requestStartedAtUtc)
    {
        await dbContext.UploadTickets
            .Where(ticket =>
                ticket.Id == uploadTicket.Id
                && ticket.FirstUsedAtUtc == null
                && ticket.RevokedAtUtc == null
                && ticket.ConsumedAtUtc == null
                && requestStartedAtUtc < ticket.ExpiresAtUtc)
            .ExecuteUpdateAsync(
                setters => setters.SetProperty(
                    ticket => ticket.FirstUsedAtUtc,
                    requestStartedAtUtc),
                CancellationToken.None);

        await dbContext.Entry(uploadTicket)
            .ReloadAsync(CancellationToken.None);
    }

    private async Task RecordFailedCodeAttemptAsync(
        UploadTicket uploadTicket,
        DateTime requestStartedAtUtc)
    {
        var activeWindowStartUtc = requestStartedAtUtc.AddMinutes(-30);

        await dbContext.UploadTickets
            .Where(ticket =>
                ticket.Id == uploadTicket.Id
                && ticket.RevokedAtUtc == null
                && ticket.ConsumedAtUtc == null
                && requestStartedAtUtc < ticket.ExpiresAtUtc
                && (ticket.FirstUsedAtUtc == null
                    || activeWindowStartUtc < ticket.FirstUsedAtUtc))
            .ExecuteUpdateAsync(
                setters => setters
                    .SetProperty(
                        ticket => ticket.FailedCodeAttempts,
                        ticket => ticket.FailedCodeAttempts + 1)
                    .SetProperty(
                        ticket => ticket.RevokedAtUtc,
                        ticket => ticket.FailedCodeAttempts
                                >= MaximumFailedCodeAttempts - 1
                            ? requestStartedAtUtc
                            : ticket.RevokedAtUtc),
                CancellationToken.None);

        await dbContext.Entry(uploadTicket)
            .ReloadAsync(CancellationToken.None);
    }

    private static bool TicketCodesMatch(
        string expectedCode,
        string providedCode)
    {
        Span<byte> expectedBytes =
            stackalloc byte[UploadTicketCredentialGenerator.TicketCodeLength];
        Span<byte> providedBytes =
            stackalloc byte[UploadTicketCredentialGenerator.TicketCodeLength];

        Encoding.ASCII.GetBytes(expectedCode, expectedBytes);
        var isValid = UploadTicketCredentialGenerator.TryNormalizeTicketCode(
            providedCode,
            out var normalizedCode);
        if (isValid)
        {
            Encoding.ASCII.GetBytes(normalizedCode, providedBytes);
        }

        var matches = CryptographicOperations.FixedTimeEquals(
            expectedBytes,
            providedBytes);
        return isValid & matches;
    }

    private bool TryGetMultipartBoundary(out string boundary)
    {
        boundary = string.Empty;

        if (!MediaTypeHeaderValue.TryParse(
                Request.ContentType,
                out var mediaType)
            || !string.Equals(
                mediaType.MediaType.Value,
                "multipart/form-data",
                StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        boundary = HeaderUtilities.RemoveQuotes(mediaType.Boundary).Value
            ?? string.Empty;
        return boundary.Length > 0
            && boundary.Length
                <= formOptions.Value.MultipartBoundaryLengthLimit;
    }

    private static bool TryGetContentDisposition(
        MultipartSection section,
        out ContentDispositionHeaderValue contentDisposition,
        out string fieldName)
    {
        contentDisposition = null!;
        fieldName = string.Empty;

        if (!ContentDispositionHeaderValue.TryParse(
                section.ContentDisposition,
                out var parsedContentDisposition)
            || parsedContentDisposition is null
            || !string.Equals(
                parsedContentDisposition.DispositionType.Value,
                "form-data",
                StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        contentDisposition = parsedContentDisposition;
        fieldName = HeaderUtilities.RemoveQuotes(contentDisposition.Name).Value
            ?? string.Empty;
        return fieldName.Length > 0;
    }

    private static string GetOriginalFileName(
        ContentDispositionHeaderValue contentDisposition)
    {
        var fileNameSegment = contentDisposition.FileNameStar.HasValue
            ? contentDisposition.FileNameStar
            : contentDisposition.FileName;
        var fileName = HeaderUtilities.RemoveQuotes(fileNameSegment).Value
            ?? string.Empty;

        return Path.GetFileName(fileName.Replace('\\', '/'));
    }

    private async Task<bool> ValidateAntiforgeryTokenAsync(string token)
    {
        var headerName = antiforgeryOptions.Value.HeaderName;
        if (string.IsNullOrEmpty(headerName))
        {
            return false;
        }

        Request.Headers[headerName] = token;

        try
        {
            await antiforgery.ValidateRequestAsync(HttpContext);
            return true;
        }
        catch (AntiforgeryValidationException)
        {
            return false;
        }
    }

    private static async Task<string> ReadFormValueAsync(
        Stream source,
        int valueLengthLimit,
        CancellationToken cancellationToken)
    {
        using var reader = new StreamReader(
            source,
            Encoding.UTF8,
            detectEncodingFromByteOrderMarks: true,
            bufferSize: 1024,
            leaveOpen: true);

        var value = new StringBuilder();
        var buffer = ArrayPool<char>.Shared.Rent(1024);

        try
        {
            int read;
            while ((read = await reader.ReadAsync(
                       buffer.AsMemory(0, buffer.Length),
                       cancellationToken)) > 0)
            {
                if (read > valueLengthLimit - value.Length)
                {
                    throw new InvalidGuestUploadException();
                }

                value.Append(buffer, 0, read);
            }
        }
        finally
        {
            ArrayPool<char>.Shared.Return(buffer);
        }

        return value.ToString();
    }

    private IActionResult ShowUnavailable()
    {
        IsUnavailable = true;
        Response.StatusCode = StatusCodes.Status410Gone;
        return Page();
    }

    private void SetGuestResponseHeaders()
    {
        Response.Headers["X-Robots-Tag"] = "noindex, nofollow";
        Response.Headers["Referrer-Policy"] = "no-referrer";
    }

    private sealed class InvalidGuestUploadException : Exception;
}
