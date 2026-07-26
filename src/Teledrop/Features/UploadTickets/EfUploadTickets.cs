using Microsoft.EntityFrameworkCore;
using Teledrop.Data;
using Teledrop.Features.Drops;

namespace Teledrop.Features.UploadTickets;

public sealed class EfUploadTickets(TeledropDbContext dbContext)
    : IUploadTicketStore, IUploadTicketPathIndex, IGuestUploadCommitter
{
    public async Task<UploadTicket?> FindByPathAsync(
        string path,
        CancellationToken cancellationToken)
    {
        return await dbContext.UploadTickets
            .AsNoTracking()
            .SingleOrDefaultAsync(
                uploadTicket => uploadTicket.Path == path,
                cancellationToken);
    }

    public async Task<UploadTicket?> FindByIdAsync(
        Guid id,
        CancellationToken cancellationToken)
    {
        return await dbContext.UploadTickets.SingleOrDefaultAsync(
            uploadTicket => uploadTicket.Id == id,
            cancellationToken);
    }

    public async Task AddAsync(
        UploadTicket uploadTicket,
        CancellationToken cancellationToken)
    {
        dbContext.UploadTickets.Add(uploadTicket);
        await dbContext.SaveChangesAsync(cancellationToken);
    }

    public async Task UpdateAsync(
        UploadTicket uploadTicket,
        CancellationToken cancellationToken)
    {
        _ = uploadTicket;
        await dbContext.SaveChangesAsync(cancellationToken);
    }

    public async Task<bool> ExistsAsync(
        string path,
        CancellationToken cancellationToken)
    {
        return await dbContext.UploadTickets
            .AsNoTracking()
            .AnyAsync(
                uploadTicket => uploadTicket.Path == path,
                cancellationToken);
    }

    public async Task<UploadTicketAttemptUpdate>
        EnsureFirstSuccessfulCodeAsync(
            Guid uploadTicketId,
            DateTime requestStartedAtUtc,
            CancellationToken cancellationToken)
    {
        _ = cancellationToken;

        var affectedTickets = await dbContext.UploadTickets
            .Where(uploadTicket =>
                uploadTicket.Id == uploadTicketId
                && uploadTicket.FirstUsedAtUtc == null
                && uploadTicket.RevokedAtUtc == null
                && uploadTicket.ConsumedAtUtc == null
                && requestStartedAtUtc < uploadTicket.ExpiresAtUtc)
            .ExecuteUpdateAsync(
                setters => setters.SetProperty(
                    uploadTicket => uploadTicket.FirstUsedAtUtc,
                    requestStartedAtUtc),
                CancellationToken.None);

        return new UploadTicketAttemptUpdate(
            affectedTickets == 1,
            await FindByIdWithoutTrackingAsync(uploadTicketId));
    }

    public async Task<UploadTicketAttemptUpdate>
        TryRecordFailedCodeAttemptAsync(
            Guid uploadTicketId,
            DateTime requestStartedAtUtc,
            CancellationToken cancellationToken)
    {
        _ = cancellationToken;

        var activeWindowStartUtc =
            requestStartedAtUtc.Subtract(UploadTicket.RetryWindow);
        var affectedTickets = await dbContext.UploadTickets
            .Where(uploadTicket =>
                uploadTicket.Id == uploadTicketId
                && uploadTicket.RevokedAtUtc == null
                && uploadTicket.ConsumedAtUtc == null
                && uploadTicket.FailedCodeAttempts
                    < UploadTicket.MaximumFailedCodeAttempts
                && requestStartedAtUtc < uploadTicket.ExpiresAtUtc
                && (uploadTicket.FirstUsedAtUtc == null
                    || activeWindowStartUtc
                        < uploadTicket.FirstUsedAtUtc))
            .ExecuteUpdateAsync(
                setters => setters
                    .SetProperty(
                        uploadTicket => uploadTicket.FailedCodeAttempts,
                        uploadTicket =>
                            uploadTicket.FailedCodeAttempts + 1)
                    .SetProperty(
                        uploadTicket => uploadTicket.RevokedAtUtc,
                        uploadTicket =>
                            uploadTicket.FailedCodeAttempts
                                >= UploadTicket.MaximumFailedCodeAttempts - 1
                                ? requestStartedAtUtc
                                : uploadTicket.RevokedAtUtc),
                CancellationToken.None);

        return new UploadTicketAttemptUpdate(
            affectedTickets == 1,
            await FindByIdWithoutTrackingAsync(uploadTicketId));
    }

    public async Task<bool> TryCommitAsync(
        Drop drop,
        Guid uploadTicketId,
        DateTime requestStartedAtUtc,
        DateTime consumedAtUtc,
        CancellationToken cancellationToken)
    {
        await using var transaction =
            await dbContext.Database.BeginTransactionAsync(
                cancellationToken);

        dbContext.Drops.Add(drop);
        await dbContext.SaveChangesAsync(cancellationToken);

        var activeWindowStartUtc =
            requestStartedAtUtc.Subtract(UploadTicket.RetryWindow);
        var affectedTickets = await dbContext.UploadTickets
            .Where(uploadTicket =>
                uploadTicket.Id == uploadTicketId
                && uploadTicket.RevokedAtUtc == null
                && uploadTicket.ConsumedAtUtc == null
                && requestStartedAtUtc < uploadTicket.ExpiresAtUtc
                && (uploadTicket.FirstUsedAtUtc == null
                    || activeWindowStartUtc
                        < uploadTicket.FirstUsedAtUtc))
            .ExecuteUpdateAsync(
                setters => setters
                    .SetProperty(
                        uploadTicket => uploadTicket.ConsumedAtUtc,
                        consumedAtUtc)
                    .SetProperty(
                        uploadTicket => uploadTicket.CreatedDropId,
                        drop.Id),
                cancellationToken);

        if (affectedTickets != 1)
        {
            await transaction.RollbackAsync(cancellationToken);
            return false;
        }

        await transaction.CommitAsync(cancellationToken);
        return true;
    }

    private async Task<UploadTicket?> FindByIdWithoutTrackingAsync(Guid id)
    {
        return await dbContext.UploadTickets
            .AsNoTracking()
            .SingleOrDefaultAsync(uploadTicket => uploadTicket.Id == id);
    }
}
