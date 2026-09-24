namespace Teledrop.Features.Drops;

// Presentation only: this classification does not authorize inline previews.
public static class FileIcon
{
    public static string Select(string contentType, string fileName)
    {
        var mime = contentType.Split(';', 2)[0].Trim().ToLowerInvariant();
        if (mime.StartsWith("image/")) return "file-image";
        if (mime.StartsWith("video/")) return "file-video";
        if (mime.StartsWith("audio/")) return "file-audio";

        var icon = mime switch
        {
            "application/pdf" => "file-pdf",
            "application/msword" or
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or
                "application/vnd.oasis.opendocument.text" => "file-doc",
            "application/vnd.ms-excel" or
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" or
                "application/vnd.oasis.opendocument.spreadsheet" => "file-xls",
            "application/vnd.ms-powerpoint" or
                "application/vnd.openxmlformats-officedocument.presentationml.presentation" or
                "application/vnd.oasis.opendocument.presentation" => "file-ppt",
            "application/zip" or "application/x-zip-compressed" or
                "application/x-7z-compressed" or "application/vnd.rar" or
                "application/x-rar-compressed" or "application/gzip" or
                "application/x-tar" => "file-zip",
            "text/csv" => "file-csv",
            "application/json" or "application/xml" or "text/xml" or
                "text/html" or "text/css" or "text/javascript" or
                "application/javascript" => "file-code",
            _ => null,
        };
        if (icon is not null) return icon;

        return Path.GetExtension(fileName).ToLowerInvariant() switch
        {
            ".jpg" or ".jpeg" or ".png" or ".gif" or ".webp" or ".svg" or
                ".avif" or ".bmp" or ".ico" or ".tif" or ".tiff" or ".heic" => "file-image",
            ".mp4" or ".webm" or ".mov" or ".mkv" or ".avi" or ".m4v" => "file-video",
            ".mp3" or ".wav" or ".flac" or ".ogg" or ".m4a" or ".aac" => "file-audio",
            ".pdf" => "file-pdf",
            ".doc" or ".docx" or ".odt" or ".rtf" or ".hwp" or ".hwpx" => "file-doc",
            ".xls" or ".xlsx" or ".ods" => "file-xls",
            ".ppt" or ".pptx" or ".odp" => "file-ppt",
            ".zip" or ".7z" or ".rar" or ".tar" or ".gz" or ".bz2" or ".xz" => "file-zip",
            ".csv" or ".tsv" => "file-csv",
            ".cs" or ".js" or ".jsx" or ".ts" or ".tsx" or ".py" or ".rb" or
                ".go" or ".rs" or ".java" or ".c" or ".cpp" or ".h" or ".php" or
                ".html" or ".css" or ".json" or ".xml" or ".yaml" or ".yml" or
                ".sh" or ".sql" or ".toml" => "file-code",
            ".txt" or ".md" or ".log" => "file-text",
            _ => mime.StartsWith("text/") ? "file-text" : "file",
        };
    }
}
