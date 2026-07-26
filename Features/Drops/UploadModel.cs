using System.Buffers;
using System.Security.Cryptography;
using System.Text;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.AspNetCore.WebUtilities;
using Microsoft.Extensions.Options;
using Microsoft.Net.Http.Headers;
using Teledrop.Data;

namespace Teledrop.Features.Drops;

// Automatic Razor Pages antiforgery validation reads Request.Form and buffers files.
// This page validates the first multipart section manually before opening the file.
[IgnoreAntiforgeryToken]
public sealed class UploadModel(
    TeledropDbContext dbContext,
    IAntiforgery antiforgery,
    IOptions<AntiforgeryOptions> antiforgeryOptions,
    IOptions<FormOptions> formOptions,
    IOptions<TeledropOptions> teledropOptions,
    ILogger<UploadModel> logger)
    : PageModel
{
    private const int CopyBufferSize = 64 * 1024;

    public IActionResult OnGet()
    {
        return RedirectToPage("/Index");
    }

    public async Task<IActionResult> OnPostAsync()
    {
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

        string? title = null;
        string? description = null;
        string? storedFilePath = null;
        StoredFile? storedFile = null;
        var antiforgeryValidated = false;
        var sectionCount = 0;
        var formValueCount = 0;
        var persisted = false;

        try
        {
            MultipartSection? section;
            while ((section = await reader.ReadNextSectionAsync(requestAborted)) is not null)
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
                        || storedFile is not null
                        || !string.Equals(fieldName, "File", StringComparison.Ordinal))
                    {
                        return BadRequest();
                    }

                    var fileName = GetOriginalFileName(contentDisposition);
                    if (string.IsNullOrWhiteSpace(fileName))
                    {
                        return BadRequest();
                    }

                    var location = Guid.NewGuid().ToString("N");
                    storedFilePath = Path.GetFullPath(
                        Path.Combine(
                            teledropOptions.Value.ShareDirectory,
                            location));
                    storedFile = await StoreFileAsync(
                        section.Body,
                        storedFilePath,
                        location,
                        fileName,
                        string.IsNullOrWhiteSpace(section.ContentType)
                            ? "application/octet-stream"
                            : section.ContentType,
                        teledropOptions.Value.MaxUploadBytes,
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
                else if (string.Equals(fieldName, "Title", StringComparison.Ordinal))
                {
                    title = EmptyToNull(value);
                }
                else if (string.Equals(
                             fieldName,
                             "Description",
                             StringComparison.Ordinal))
                {
                    description = EmptyToNull(value);
                }
            }

            if (!antiforgeryValidated || storedFile is null)
            {
                return BadRequest();
            }

            var drop = new Drop
            {
                Id = Guid.NewGuid(),
                Slug = Guid.NewGuid().ToString("N"),
                Title = title,
                Description = description,
                IsPrivate = true,
                FileName = storedFile.FileName,
                FileHash = storedFile.FileHash,
                FileSizeBytes = storedFile.FileSizeBytes,
                ContentType = storedFile.ContentType,
                Location = storedFile.Location,
                CreatedAt = DateTime.UtcNow,
            };

            dbContext.Drops.Add(drop);
            await dbContext.SaveChangesAsync(requestAborted);
            persisted = true;

            var redirectLocation = Url.Page(
                    "/Index",
                    values: new { uploaded = drop.Slug })
                ?? $"/?uploaded={drop.Slug}";

            if (string.Equals(
                    Request.Headers["HX-Request"],
                    "true",
                    StringComparison.OrdinalIgnoreCase))
            {
                Response.Headers["HX-Redirect"] = redirectLocation;
                return new StatusCodeResult(StatusCodes.Status204NoContent);
            }

            return RedirectToPage("/Index", new { uploaded = drop.Slug });
        }
        catch (UploadTooLargeException)
        {
            return StatusCode(StatusCodes.Status413PayloadTooLarge);
        }
        catch (InvalidUploadException)
        {
            return BadRequest();
        }
        catch (InvalidDataException)
        {
            return BadRequest();
        }
        finally
        {
            if (!persisted && storedFilePath is not null)
            {
                TryDeleteIncompleteFile(storedFilePath);
            }
        }
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
                    throw new InvalidUploadException();
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

    private static async Task<StoredFile> StoreFileAsync(
        Stream source,
        string filePath,
        string location,
        string fileName,
        string contentType,
        long maxUploadBytes,
        CancellationToken cancellationToken)
    {
        await using var destination = new FileStream(
            filePath,
            FileMode.CreateNew,
            FileAccess.Write,
            FileShare.None,
            CopyBufferSize,
            FileOptions.Asynchronous | FileOptions.SequentialScan);
        using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);

        var buffer = ArrayPool<byte>.Shared.Rent(CopyBufferSize);
        long fileSizeBytes = 0;

        try
        {
            int read;
            while ((read = await source.ReadAsync(
                       buffer.AsMemory(0, buffer.Length),
                       cancellationToken)) > 0)
            {
                if (read > maxUploadBytes - fileSizeBytes)
                {
                    throw new UploadTooLargeException();
                }

                await destination.WriteAsync(
                    buffer.AsMemory(0, read),
                    cancellationToken);
                hash.AppendData(buffer, 0, read);
                fileSizeBytes += read;
            }

            await destination.FlushAsync(cancellationToken);
        }
        finally
        {
            ArrayPool<byte>.Shared.Return(buffer);
        }

        return new StoredFile(
            location,
            fileName,
            contentType,
            fileSizeBytes,
            Convert.ToHexStringLower(hash.GetHashAndReset()));
    }

    private void TryDeleteIncompleteFile(string filePath)
    {
        try
        {
            System.IO.File.Delete(filePath);
        }
        catch (Exception exception)
        {
            logger.LogWarning(
                exception,
                "Incomplete upload file at {FilePath} could not be deleted.",
                filePath);
        }
    }

    private static string? EmptyToNull(string value)
    {
        return value.Length == 0 ? null : value;
    }

    private sealed record StoredFile(
        string Location,
        string FileName,
        string ContentType,
        long FileSizeBytes,
        string FileHash);

    private sealed class InvalidUploadException : Exception;

    private sealed class UploadTooLargeException : Exception;
}
