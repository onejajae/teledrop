using Teledrop.Features.Drops;

namespace Teledrop.Features.UploadTickets;

public interface IUploadTicketStore
{
    Task<UploadTicket?> FindByPathAsync(
        string path,
        CancellationToken cancellationToken);

    Task<UploadTicket?> FindByIdAsync(
        Guid id,
        CancellationToken cancellationToken);

    Task AddAsync(
        UploadTicket uploadTicket,
        CancellationToken cancellationToken);

    Task UpdateAsync(
        UploadTicket uploadTicket,
        CancellationToken cancellationToken);

    Task<UploadTicketAttemptUpdate> EnsureFirstSuccessfulCodeAsync(
        Guid uploadTicketId,
        DateTime requestStartedAtUtc,
        CancellationToken cancellationToken);

    Task<UploadTicketAttemptUpdate> TryRecordFailedCodeAttemptAsync(
        Guid uploadTicketId,
        DateTime requestStartedAtUtc,
        CancellationToken cancellationToken);
}

public interface IUploadTicketPathIndex
{
    Task<bool> ExistsAsync(
        string path,
        CancellationToken cancellationToken);
}

public interface IGuestUploadCommitter
{
    Task<bool> TryCommitAsync(
        Drop drop,
        Guid uploadTicketId,
        DateTime requestStartedAtUtc,
        DateTime consumedAtUtc,
        CancellationToken cancellationToken);
}

public sealed record UploadTicketAttemptUpdate(
    bool Updated,
    UploadTicket? UploadTicket);
