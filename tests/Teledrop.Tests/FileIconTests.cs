using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Tests;

public sealed class FileIconTests
{
    [Theory]
    [InlineData("IMAGE/JPEG; charset=binary", "photo.bin", "file-image")]
    [InlineData("application/pdf", "report.zip", "file-pdf")]
    [InlineData("application/octet-stream", "REPORT.XLSX", "file-xls")]
    [InlineData("text/plain", "settings.json", "file-code")]
    [InlineData("application/octet-stream", "archive.7z", "file-zip")]
    [InlineData("text/plain", "notes", "file-text")]
    [InlineData("application/x-unknown", "unknown.xyz", "file")]
    [InlineData("application/octet-stream", "no-extension", "file")]
    public void SelectsIconWithMimePriorityAndExtensionFallback(
        string contentType, string fileName, string expected)
    {
        Assert.Equal(expected, FileIcon.Select(contentType, fileName));
    }
}
