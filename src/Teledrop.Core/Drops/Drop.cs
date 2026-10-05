namespace Teledrop.Features.Drops;

public sealed class Drop
{
    public Guid Id { get; set; }

    public required string Slug { get; set; }

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

    public DropAccessLevel AccessLevel => IsPrivate
        ? DropAccessLevel.Private
        : DropPasswordHash is null ? DropAccessLevel.Public : DropAccessLevel.Password;
}

// A private Drop never keeps a Drop Password, so these three levels cover every stored state.
public enum DropAccessLevel
{
    Private,
    Public,
    Password,
}
