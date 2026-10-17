using System.Security.Cryptography;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Infrastructure.Tests;

public sealed class DropFileStoreTests
{
    [Fact]
    public async Task StoredLocationCanBeResolvedReadAndDeleted()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"teledrop-file-tests-{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        try
        {
            var store = new DropFileStore(
                Options.Create(new TeledropOptions { ShareDirectory = directory }),
                NullLogger<DropFileStore>.Instance);
            var bytes = new byte[] { 1, 2, 3, 4 };
            using var input = new MemoryStream(bytes);
            var stored = await store.StoreAsync(input, "source.bin", "application/octet-stream", default);

            var path = store.FindFilePath(stored.Location);

            Assert.NotNull(path);
            Assert.True(Path.IsPathFullyQualified(path));
            Assert.Equal(bytes, await File.ReadAllBytesAsync(path));
            store.TryDelete(stored.Location);
            Assert.Null(store.FindFilePath(stored.Location));
            Assert.Null(store.FindFilePath("missing"));
        }
        finally
        {
            Directory.Delete(directory, recursive: true);
        }
    }

    [Theory]
    [InlineData(0)]
    [InlineData(65537)]
    public async Task EmptyAndExactLimitFilesKeepTheirBytesSizeAndHash(int size)
    {
        // The nonempty case crosses the copy-buffer boundary by one byte.
        using var fixture = new StoreFixture(maxUploadBytes: 65537);
        var bytes = Enumerable.Range(0, size).Select(index => (byte)index).ToArray();
        using var input = new MemoryStream(bytes);

        var stored = await fixture.Store.StoreAsync(input, "boundary.bin", "application/octet-stream", default);

        Assert.Equal(size, stored.FileSizeBytes);
        Assert.Equal(Convert.ToHexStringLower(SHA256.HashData(bytes)), stored.FileHash);
        var path = fixture.Store.FindFilePath(stored.Location);
        Assert.NotNull(path);
        Assert.Equal(bytes, await File.ReadAllBytesAsync(path));
        Assert.Empty(fixture.Logger.Entries);
    }

    [Fact]
    public async Task OneByteOverTheLimitRemovesThePartiallyWrittenFile()
    {
        using var fixture = new StoreFixture(maxUploadBytes: 65537);
        using var input = new MemoryStream(new byte[65538]);

        await Assert.ThrowsAsync<DropUploadTooLargeException>(() =>
            fixture.Store.StoreAsync(input, "too-large.bin", "application/octet-stream", default));

        Assert.Empty(Directory.EnumerateFileSystemEntries(fixture.DirectoryPath));
        Assert.Empty(fixture.Logger.Entries);
    }

    [Fact]
    public async Task InputFailureKeepsTheOriginalExceptionAndRemovesThePartialFile()
    {
        using var fixture = new StoreFixture();
        var failure = new IOException("Source stopped after the first buffer.");
        using var input = new FailingReadStream(failure);

        var thrown = await Assert.ThrowsAsync<IOException>(() =>
            fixture.Store.StoreAsync(input, "incomplete.bin", "application/octet-stream", default));

        Assert.Same(failure, thrown);
        Assert.Empty(Directory.EnumerateFileSystemEntries(fixture.DirectoryPath));
        Assert.Empty(fixture.Logger.Entries);
    }

    [Fact]
    public void ADeletionFailureIsLoggedWithoutEscapingToTheCaller()
    {
        using var fixture = new StoreFixture();
        var path = Path.Combine(fixture.DirectoryPath, "occupied");
        // File.Delete cannot remove a directory, regardless of user permissions.
        Directory.CreateDirectory(path);

        var thrown = Record.Exception(() => fixture.Store.TryDelete("occupied"));

        Assert.Null(thrown);
        var warning = Assert.Single(fixture.Logger.Entries);
        Assert.Equal(LogLevel.Warning, warning.Level);
        Assert.NotNull(warning.Exception);
        Assert.Contains(path, warning.Message);
        Assert.True(Directory.Exists(path));
    }

    private sealed class StoreFixture : IDisposable
    {
        internal string DirectoryPath { get; } = Path.Combine(
            Path.GetTempPath(), $"teledrop-file-tests-{Guid.NewGuid():N}");
        internal RecordingLogger Logger { get; } = new();
        internal DropFileStore Store { get; }

        internal StoreFixture(long maxUploadBytes = TeledropOptions.DefaultMaxUploadBytes)
        {
            Directory.CreateDirectory(DirectoryPath);
            Store = new DropFileStore(Options.Create(new TeledropOptions
            {
                ShareDirectory = DirectoryPath,
                MaxUploadBytes = maxUploadBytes,
            }), Logger);
        }

        public void Dispose() => Directory.Delete(DirectoryPath, recursive: true);
    }

    private sealed class RecordingLogger : ILogger<DropFileStore>
    {
        internal List<(LogLevel Level, Exception? Exception, string Message)> Entries { get; } = [];
        public IDisposable? BeginScope<TState>(TState state) where TState : notnull => null;
        public bool IsEnabled(LogLevel logLevel) => true;
        public void Log<TState>(LogLevel logLevel, EventId eventId, TState state,
            Exception? exception, Func<TState, Exception?, string> formatter)
            => Entries.Add((logLevel, exception, formatter(state, exception)));
    }

    private sealed class FailingReadStream(Exception failure) : MemoryStream([1, 2, 3, 4])
    {
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
        {
            if (Position > 0) throw failure;
            return base.ReadAsync(buffer, cancellationToken);
        }
    }
}
