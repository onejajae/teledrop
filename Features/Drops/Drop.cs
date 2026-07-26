namespace Teledrop.Features.Drops;

public sealed class Drop
{
    public Guid Id { get; set; }

    public required string Slug { get; set; }

    public string? Title { get; set; }

    public string? Description { get; set; }

    public bool IsPrivate { get; set; } = true;

    public string? DropPasswordHash { get; set; }

    public bool IsFavorite { get; set; } = false;

    public required string FileName { get; set; }

    public required string FileHash { get; set; }

    public long FileSizeBytes { get; set; }

    public required string ContentType { get; set; }

    public required string Location { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public DateTime? UpdatedAt { get; set; }

    public Guid? UploadTicketId { get; set; }
}
