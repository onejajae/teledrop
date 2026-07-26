using System.Buffers;
using System.Security.Cryptography;
using Microsoft.Extensions.Options;

namespace Teledrop.Features.Drops;

public sealed class DropFileStore(
    IOptions<TeledropOptions> teledropOptions,
    ILogger<DropFileStore> logger)
    : IStoredDropFileCleanup
{
    private const int CopyBufferSize = 64 * 1024;

    public async Task<StoredDropFile> StoreAsync(
        Stream source,
        string fileName,
        string contentType,
        CancellationToken cancellationToken)
    {
        var location = Guid.NewGuid().ToString("N");
        var filePath = GetFilePath(location);

        try
        {
            await using var destination = new FileStream(
                filePath,
                FileMode.CreateNew,
                FileAccess.Write,
                FileShare.None,
                CopyBufferSize,
                FileOptions.Asynchronous | FileOptions.SequentialScan);
            using var hash =
                IncrementalHash.CreateHash(HashAlgorithmName.SHA256);

            var buffer = ArrayPool<byte>.Shared.Rent(CopyBufferSize);
            long fileSizeBytes = 0;

            try
            {
                int read;
                while ((read = await source.ReadAsync(
                           buffer.AsMemory(0, buffer.Length),
                           cancellationToken)) > 0)
                {
                    if (read
                        > teledropOptions.Value.MaxUploadBytes - fileSizeBytes)
                    {
                        throw new DropUploadTooLargeException();
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

            return new StoredDropFile(
                location,
                fileName,
                contentType,
                fileSizeBytes,
                Convert.ToHexStringLower(hash.GetHashAndReset()));
        }
        catch
        {
            TryDeleteFile(filePath);
            throw;
        }
    }

    public void TryDelete(StoredDropFile storedFile)
    {
        TryDelete(storedFile.Location);
    }

    public void TryDelete(string location)
    {
        TryDeleteFile(GetFilePath(location));
    }

    private string GetFilePath(string location)
    {
        return Path.GetFullPath(
            Path.Combine(
                teledropOptions.Value.ShareDirectory,
                location));
    }

    private void TryDeleteFile(string filePath)
    {
        try
        {
            File.Delete(filePath);
        }
        catch (Exception exception)
        {
            logger.LogWarning(
                exception,
                "Incomplete upload file at {FilePath} could not be deleted.",
                filePath);
        }
    }
}

public sealed class DropUploadTooLargeException : Exception;
