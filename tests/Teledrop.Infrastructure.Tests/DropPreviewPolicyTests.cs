using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Infrastructure.Tests;

public sealed class DropPreviewPolicyTests
{
    [Theory]
    [InlineData(null, DropPreviewKind.None, false)]
    [InlineData("", DropPreviewKind.None, false)]
    [InlineData("not a mime", DropPreviewKind.None, false)]
    [InlineData("application/pdf; =", DropPreviewKind.None, false)]
    [InlineData("IMAGE/JPEG; charset=binary", DropPreviewKind.Image, true)]
    [InlineData(" image/png ", DropPreviewKind.Image, true)]
    [InlineData("image/x-custom", DropPreviewKind.Image, true)]
    [InlineData("VIDEO/WEBM; codecs=vp8", DropPreviewKind.Video, true)]
    [InlineData("audio/ogg", DropPreviewKind.Audio, true)]
    [InlineData("application/pdf", DropPreviewKind.Pdf, true)]
    [InlineData("APPLICATION/PDF; charset=binary", DropPreviewKind.Pdf, true)]
    [InlineData("text/plain; charset=utf-8", DropPreviewKind.None, true)]
    [InlineData("IMAGE/SVG+XML; charset=utf-8", DropPreviewKind.None, false)]
    [InlineData("text/html", DropPreviewKind.None, false)]
    [InlineData("application/octet-stream", DropPreviewKind.None, false)]
    [InlineData("application/x-unknown", DropPreviewKind.None, false)]
    public void DecidesPreviewAndInlineTogether(string? contentType, DropPreviewKind kind, bool allowInline)
    {
        var result = DropPreviewPolicy.Evaluate(contentType);

        Assert.Equal(kind, result.Kind);
        Assert.Equal(allowInline, result.AllowInline);
    }
}
