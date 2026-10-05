using Microsoft.Net.Http.Headers;

namespace Teledrop.Features.Drops;

public static class DropPreviewPolicy
{
    public static DropPreviewDecision Evaluate(string? contentType)
    {
        if (!MediaTypeHeaderValue.TryParse(contentType, out var parsed)
            || string.IsNullOrEmpty(parsed?.MediaType.Value))
        {
            return new(DropPreviewKind.None, false);
        }

        var mediaType = parsed.MediaType.Value;
        if (string.Equals(mediaType, "image/svg+xml", StringComparison.OrdinalIgnoreCase))
            return new(DropPreviewKind.None, false);
        if (mediaType.StartsWith("image/", StringComparison.OrdinalIgnoreCase))
            return new(DropPreviewKind.Image, true);
        if (mediaType.StartsWith("video/", StringComparison.OrdinalIgnoreCase))
            return new(DropPreviewKind.Video, true);
        if (mediaType.StartsWith("audio/", StringComparison.OrdinalIgnoreCase))
            return new(DropPreviewKind.Audio, true);
        if (string.Equals(mediaType, "application/pdf", StringComparison.OrdinalIgnoreCase))
            return new(DropPreviewKind.Pdf, true);

        return new(DropPreviewKind.None,
            string.Equals(mediaType, "text/plain", StringComparison.OrdinalIgnoreCase));
    }
}

public readonly record struct DropPreviewDecision(DropPreviewKind Kind, bool AllowInline);

public enum DropPreviewKind
{
    None,
    Image,
    Video,
    Audio,
    Pdf,
}
