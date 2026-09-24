using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Tests;

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
}
