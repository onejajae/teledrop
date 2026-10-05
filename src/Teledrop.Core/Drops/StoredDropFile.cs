namespace Teledrop.Features.Drops;

public sealed record StoredDropFile(
    string Location,
    string FileName,
    string ContentType,
    long FileSizeBytes,
    string FileHash);
