using System.Buffers;
using System.Text;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.WebUtilities;
using Microsoft.Extensions.Options;
using Microsoft.Net.Http.Headers;

namespace Teledrop.Features.Drops;

public sealed class DropUploadReceiver(
    DropFileStore fileStore,
    DropSlugs dropSlugs,
    IOptions<FormOptions> formOptions,
    IAntiforgery antiforgery,
    IOptions<AntiforgeryOptions> antiforgeryOptions)
{
    // Owner Session authorization runs before this entry point. The first section
    // must validate CSRF before any file is opened, without buffering Request.Form.
    public Task<Drop> ReceiveWebAsync(HttpContext context, CancellationToken cancellationToken)
        => ReceiveAsync(context.Request, context, cancellationToken);

    // The caller validates the API key before invoking this entry point.
    public Task<Drop> ReceiveApiAsync(HttpRequest request, CancellationToken cancellationToken)
        => ReceiveAsync(request, webContext: null, cancellationToken);

    private async Task<Drop> ReceiveAsync(
        HttpRequest request, HttpContext? webContext, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (!TryGetMultipartBoundary(request, out var boundary))
            throw new InvalidUploadException();

        var reader = new MultipartReader(boundary, request.Body)
        {
            HeadersCountLimit = formOptions.Value.MultipartHeadersCountLimit,
            HeadersLengthLimit = formOptions.Value.MultipartHeadersLengthLimit,
        };
        var isWeb = webContext is not null;
        var comparison = isWeb ? StringComparison.Ordinal : StringComparison.OrdinalIgnoreCase;
        var csrfValidated = false;
        var sectionCount = 0;
        var valueCount = 0;
        string? title = null;
        string? description = null;
        StoredDropFile? ownedFile = null;

        try
        {
            // Limit exception translation to multipart parsing. Persistence and
            // disk failures must not be mistaken for invalid client input.
            try
            {
                MultipartSection? section;
                while ((section = await ReadSectionAsync(reader, cancellationToken)) is not null)
                {
                    sectionCount++;
                    if (!TryGetContentDisposition(section, out var disposition, out var name))
                        throw new InvalidUploadException();

                    var isFile = disposition.FileName.HasValue || disposition.FileNameStar.HasValue;
                    var isCsrf = isWeb && string.Equals(name,
                        antiforgeryOptions.Value.FormFieldName, StringComparison.Ordinal);
                    if (isWeb && sectionCount == 1 && (isFile || !isCsrf))
                        throw new InvalidUploadException();

                    if (isFile)
                    {
                        if ((isWeb && !csrfValidated) || ownedFile is not null
                            || !string.Equals(name, isWeb ? "File" : "file", comparison))
                            throw new InvalidUploadException();
                        var fileName = GetOriginalFileName(disposition);
                        if (string.IsNullOrWhiteSpace(fileName)) throw new InvalidUploadException();

                        using var input = new MultipartInputStream(section.Body);
                        ownedFile = await fileStore.StoreAsync(input, fileName,
                            string.IsNullOrWhiteSpace(section.ContentType)
                                ? "application/octet-stream" : section.ContentType,
                            cancellationToken);
                        continue;
                    }

                    if (++valueCount > formOptions.Value.ValueCountLimit)
                        throw new InvalidUploadException();
                    if (isWeb && (!isCsrf || csrfValidated)) throw new InvalidUploadException();
                    var isTitle = !isWeb && string.Equals(name, "title", comparison);
                    var isDescription = !isWeb && string.Equals(name, "description", comparison);
                    if (!isCsrf && !isTitle && !isDescription) throw new InvalidUploadException();

                    using var valueInput = new MultipartInputStream(section.Body);
                    var value = await ReadFormValueAsync(valueInput,
                        formOptions.Value.ValueLengthLimit, cancellationToken);
                    if (isCsrf)
                    {
                        if (string.IsNullOrEmpty(value)
                            || !await ValidateAntiforgeryTokenAsync(webContext!, value))
                            throw new InvalidUploadException();
                        csrfValidated = true;
                    }
                    else if (isTitle) title = EmptyToNull(value);
                    else description = EmptyToNull(value);
                }
            }
            catch (InvalidDataException exception)
            {
                throw new InvalidUploadException(exception);
            }

            if (ownedFile is null || (isWeb && !csrfValidated)) throw new InvalidUploadException();
            cancellationToken.ThrowIfCancellationRequested();

            // Ownership passes to DropSlugs, which compensates if
            // Drop creation fails. Before that point this receiver owns cleanup.
            var fileToPersist = ownedFile;
            ownedFile = null;
            return await dropSlugs.CreatePrivateAsync(fileToPersist, title, description, cancellationToken);
        }
        finally
        {
            if (ownedFile is not null) fileStore.TryDelete(ownedFile);
        }
    }

    private static async Task<MultipartSection?> ReadSectionAsync(
        MultipartReader reader, CancellationToken cancellationToken)
    {
        try
        {
            return await reader.ReadNextSectionAsync(cancellationToken);
        }
        catch (IOException exception) when (exception is not BadHttpRequestException
            && !cancellationToken.IsCancellationRequested)
        {
            throw new InvalidUploadException(exception);
        }
    }

    // MultipartReader signals truncated input with IOException. Translate only
    // reads from that input, never FileStream writes or persistence failures.
    // Disposing this view leaves the section stream owned by MultipartReader.
    private sealed class MultipartInputStream(Stream inner) : Stream
    {
        public override bool CanRead => true;
        public override bool CanSeek => false;
        public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException();
        public override long Position
        {
            get => throw new NotSupportedException();
            set => throw new NotSupportedException();
        }
        public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        public override void Flush() => throw new NotSupportedException();
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();

        public override async ValueTask<int> ReadAsync(
            Memory<byte> buffer, CancellationToken cancellationToken = default)
        {
            try
            {
                return await inner.ReadAsync(buffer, cancellationToken);
            }
            catch (IOException exception) when (exception is not BadHttpRequestException
                && !cancellationToken.IsCancellationRequested)
            {
                throw new InvalidUploadException(exception);
            }
        }
    }

    private bool TryGetMultipartBoundary(HttpRequest request, out string boundary)
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

    private async Task<bool> ValidateAntiforgeryTokenAsync(HttpContext context, string token)
    {
        var headerName = antiforgeryOptions.Value.HeaderName;
        if (string.IsNullOrEmpty(headerName))
        {
            return false;
        }

        context.Request.Headers[headerName] = token;

        try
        {
            await antiforgery.ValidateRequestAsync(context);
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

}

public sealed class InvalidUploadException : Exception
{
    public InvalidUploadException() { }
    public InvalidUploadException(Exception innerException)
        : base("The multipart upload is invalid.", innerException) { }
}
