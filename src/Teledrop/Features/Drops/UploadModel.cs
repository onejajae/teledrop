using System.Buffers;
using System.Text;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.AspNetCore.WebUtilities;
using Microsoft.Extensions.Options;
using Microsoft.Net.Http.Headers;

namespace Teledrop.Features.Drops;

// Automatic Razor Pages antiforgery validation reads Request.Form and buffers files.
// This page validates the first multipart section manually before opening the file.
[IgnoreAntiforgeryToken]
public sealed class UploadModel(
    CreatePrivateDrop createPrivateDrop,
    IAntiforgery antiforgery,
    IOptions<AntiforgeryOptions> antiforgeryOptions,
    IOptions<FormOptions> formOptions,
    DropFileStore dropFileStore)
    : PageModel
{
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
        StoredDropFile? storedFile = null;
        var antiforgeryValidated = false;
        var sectionCount = 0;
        var formValueCount = 0;

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

            var fileToPersist = storedFile;
            storedFile = null;
            var drop = await createPrivateDrop.ExecuteAsync(
                fileToPersist,
                title,
                description,
                requestAborted);

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
        catch (DropUploadTooLargeException)
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
            if (storedFile is not null)
            {
                dropFileStore.TryDelete(storedFile);
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

    private static string? EmptyToNull(string value)
    {
        return value.Length == 0 ? null : value;
    }

    private sealed class InvalidUploadException : Exception;
}
