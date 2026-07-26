using System.Buffers;
using System.Security.Cryptography;
using System.Text;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.WebUtilities;
using Microsoft.Extensions.Options;
using Microsoft.Net.Http.Headers;
using Teledrop.Data;
using Teledrop.Features.Drops;

namespace Teledrop.Features.Api;

public static class ApiUploadEndpoint
{
    private const string ApiKeyHeaderName = "X-API-Key";

    public static RouteHandlerBuilder MapApiUpload(
        this IEndpointRouteBuilder endpoints)
    {
        return endpoints
            .MapPost("/api/upload", HandleAsync)
            .AllowAnonymous()
            .DisableAntiforgery();
    }

    private static async Task<IResult> HandleAsync(
        HttpContext httpContext,
        TeledropDbContext dbContext,
        DropSlugGenerator dropSlugGenerator,
        DropFileStore dropFileStore,
        IOptions<TeledropOptions> teledropOptions,
        IOptions<FormOptions> formOptions)
    {
        if (!HasValidApiKey(httpContext.Request, teledropOptions.Value))
        {
            httpContext.Response.Headers[HeaderNames.WWWAuthenticate] =
                "ApiKey";
            return Results.Unauthorized();
        }

        if (!TryGetMultipartBoundary(
                httpContext.Request,
                formOptions.Value,
                out var boundary))
        {
            return Results.BadRequest();
        }

        var requestAborted = httpContext.RequestAborted;
        var reader = new MultipartReader(boundary, httpContext.Request.Body)
        {
            HeadersCountLimit = formOptions.Value.MultipartHeadersCountLimit,
            HeadersLengthLimit = formOptions.Value.MultipartHeadersLengthLimit,
        };

        string? title = null;
        string? description = null;
        StoredDropFile? storedFile = null;
        var formValueCount = 0;
        var persisted = false;

        try
        {
            MultipartSection? section;
            while ((section = await reader.ReadNextSectionAsync(
                       requestAborted)) is not null)
            {
                if (!TryGetContentDisposition(
                        section,
                        out var contentDisposition,
                        out var fieldName))
                {
                    return Results.BadRequest();
                }

                var isFile = contentDisposition.FileName.HasValue
                    || contentDisposition.FileNameStar.HasValue;

                if (isFile)
                {
                    if (storedFile is not null
                        || !string.Equals(
                            fieldName,
                            "file",
                            StringComparison.OrdinalIgnoreCase))
                    {
                        return Results.BadRequest();
                    }

                    var fileName = GetOriginalFileName(contentDisposition);
                    if (string.IsNullOrWhiteSpace(fileName))
                    {
                        return Results.BadRequest();
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
                    return Results.BadRequest();
                }

                var value = await ReadFormValueAsync(
                    section.Body,
                    formOptions.Value.ValueLengthLimit,
                    requestAborted);

                if (string.Equals(
                        fieldName,
                        "title",
                        StringComparison.OrdinalIgnoreCase))
                {
                    title = EmptyToNull(value);
                }
                else if (string.Equals(
                             fieldName,
                             "description",
                             StringComparison.OrdinalIgnoreCase))
                {
                    description = EmptyToNull(value);
                }
                else
                {
                    return Results.BadRequest();
                }
            }

            if (storedFile is null)
            {
                return Results.BadRequest();
            }

            var drop = new Drop
            {
                Id = Guid.NewGuid(),
                Slug = await dropSlugGenerator.GenerateUniqueSlugAsync(
                    requestAborted),
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

            return Results.Ok(new ApiUploadResponse(
                drop.Slug,
                $"/{drop.Slug}",
                drop.FileName,
                drop.FileSizeBytes));
        }
        catch (DropUploadTooLargeException)
        {
            return Results.StatusCode(StatusCodes.Status413PayloadTooLarge);
        }
        catch (InvalidApiUploadException)
        {
            return Results.BadRequest();
        }
        catch (InvalidDataException)
        {
            return Results.BadRequest();
        }
        finally
        {
            if (!persisted && storedFile is not null)
            {
                dropFileStore.TryDelete(storedFile);
            }
        }
    }

    private static bool HasValidApiKey(
        HttpRequest request,
        TeledropOptions options)
    {
        if (string.IsNullOrWhiteSpace(options.ApiKey)
            || !request.Headers.TryGetValue(
                ApiKeyHeaderName,
                out var providedApiKeys)
            || providedApiKeys.Count != 1)
        {
            return false;
        }

        return ApiKeysMatch(
            options.ApiKey,
            providedApiKeys[0] ?? string.Empty);
    }

    private static bool ApiKeysMatch(
        string expectedApiKey,
        string providedApiKey)
    {
        var expectedHash = SHA256.HashData(
            Encoding.UTF8.GetBytes(expectedApiKey));
        var providedHash = SHA256.HashData(
            Encoding.UTF8.GetBytes(providedApiKey));

        return CryptographicOperations.FixedTimeEquals(
            expectedHash,
            providedHash);
    }

    private static bool TryGetMultipartBoundary(
        HttpRequest request,
        FormOptions formOptions,
        out string boundary)
    {
        boundary = string.Empty;

        if (!MediaTypeHeaderValue.TryParse(
                request.ContentType,
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
                <= formOptions.MultipartBoundaryLengthLimit;
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
                    throw new InvalidApiUploadException();
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

    private sealed record ApiUploadResponse(
        string Slug,
        string Url,
        string FileName,
        long SizeBytes);

    private sealed class InvalidApiUploadException : Exception;
}
