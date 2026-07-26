namespace Teledrop.Features.UploadTickets;

public sealed class UploadTicket
{
    public Guid Id { get; set; }

    public required string Path { get; set; }

    public required string Code { get; set; }

    public DateTime CreatedAt { get; set; }

    public DateTime ExpiresAtUtc { get; set; }

    public DateTime? FirstUsedAtUtc { get; set; }

    public DateTime? ConsumedAtUtc { get; set; }

    public DateTime? RevokedAtUtc { get; set; }

    public int FailedCodeAttempts { get; set; }

    public Guid? CreatedDropId { get; set; }

    public bool CanAcceptUpload(DateTime utcNow)
    {
        return RevokedAtUtc is null
            && ConsumedAtUtc is null
            && utcNow < ExpiresAtUtc
            && (FirstUsedAtUtc is null
                || utcNow < FirstUsedAtUtc.Value.AddMinutes(30));
    }
}
