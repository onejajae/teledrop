using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Infrastructure.Tests;

public sealed class FileIconTests
{
    [Theory]
    [InlineData("IMAGE/JPEG; charset=binary", "photo.bin", "file-image")]
    [InlineData("application/pdf", "report.zip", "file-pdf")]
    [InlineData("VIDEO/WEBM; codecs=vp8", "video.txt", "file-video")]
    [InlineData("audio/ogg", "audio.zip", "file-audio")]
    [InlineData("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "document.bin", "file-doc")]
    [InlineData("application/vnd.ms-excel", "sheet.bin", "file-xls")]
    [InlineData("application/vnd.oasis.opendocument.presentation", "slides.bin", "file-ppt")]
    [InlineData("application/gzip", "archive.bin", "file-zip")]
    [InlineData("text/csv", "table.txt", "file-csv")]
    [InlineData("application/json", "data.txt", "file-code")]
    public void RecognizedMimeSelectsItsIconBeforeTheFileExtension(
        string contentType, string fileName, string expected)
    {
        Assert.Equal(expected, FileIcon.Select(contentType, fileName));
    }

    [Theory]
    [InlineData("application/octet-stream", "REPORT.XLSX", "file-xls")]
    [InlineData("text/plain", "settings.json", "file-code")]
    [InlineData("application/octet-stream", "archive.7z", "file-zip")]
    [InlineData("text/plain", "notes", "file-text")]
    [InlineData("application/x-unknown", "unknown.xyz", "file")]
    public void UnclassifiedMimeUsesTheExtensionThenTextOrGenericFallback(
        string contentType, string fileName, string expected)
    {
        Assert.Equal(expected, FileIcon.Select(contentType, fileName));
    }
}
