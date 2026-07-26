namespace Teledrop.Features.UploadTickets;

public sealed class UploadTicket
{
    public const int MaximumFailedCodeAttempts = 10;

    public static readonly TimeSpan InitialLifetime = TimeSpan.FromHours(24);

    public static readonly TimeSpan RetryWindow = TimeSpan.FromMinutes(30);

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
                || utcNow < FirstUsedAtUtc.Value.Add(RetryWindow));
    }

    public static UploadTicket Issue(
        Guid id,
        string path,
        string code,
        DateTime utcNow)
    {
        return new UploadTicket
        {
            Id = id,
            Path = path,
            Code = code,
            CreatedAt = utcNow,
            ExpiresAtUtc = utcNow.Add(InitialLifetime),
        };
    }

    public bool RecordFirstSuccessfulCode(DateTime utcNow)
    {
        if (!CanAcceptUpload(utcNow))
        {
            return false;
        }

        FirstUsedAtUtc ??= utcNow;
        return true;
    }

    public bool RecordFailedCodeAttempt(DateTime utcNow)
    {
        if (!CanAcceptUpload(utcNow)
            || FailedCodeAttempts >= MaximumFailedCodeAttempts)
        {
            return false;
        }

        FailedCodeAttempts++;
        if (FailedCodeAttempts == MaximumFailedCodeAttempts)
        {
            RevokedAtUtc = utcNow;
        }

        return true;
    }

    public bool TryConsume(
        Guid dropId,
        DateTime requestStartedAtUtc,
        DateTime consumedAtUtc)
    {
        if (!CanAcceptUpload(requestStartedAtUtc))
        {
            return false;
        }

        ConsumedAtUtc = consumedAtUtc;
        CreatedDropId = dropId;
        return true;
    }

    public bool Revoke(DateTime utcNow)
    {
        if (!CanAcceptUpload(utcNow))
        {
            return false;
        }

        RevokedAtUtc = utcNow;
        return true;
    }
}
