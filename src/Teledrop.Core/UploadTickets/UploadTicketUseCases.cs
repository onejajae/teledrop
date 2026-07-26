namespace Teledrop.Features.UploadTickets;

public sealed class UploadTicketUseCases(
    IUploadTicketStore uploadTicketStore,
    UploadTicketCredentialGenerator credentialGenerator,
    TimeProvider timeProvider)
{
    public async Task<UploadTicket> IssueAsync(
        CancellationToken cancellationToken)
    {
        var now = timeProvider.GetUtcNow().UtcDateTime;
        var uploadTicket = UploadTicket.Issue(
            Guid.NewGuid(),
            await credentialGenerator.GenerateUniqueTicketPathAsync(
                cancellationToken),
            credentialGenerator.GenerateTicketCode(),
            now);

        await uploadTicketStore.AddAsync(
            uploadTicket,
            cancellationToken);
        return uploadTicket;
    }

    public async Task<UploadTicketCommandResult> RevokeAsync(
        Guid id,
        CancellationToken cancellationToken)
    {
        var uploadTicket = await uploadTicketStore.FindByIdAsync(
            id,
            cancellationToken);
        if (uploadTicket is null)
        {
            return UploadTicketCommandResult.NotFound;
        }

        if (uploadTicket.Revoke(timeProvider.GetUtcNow().UtcDateTime))
        {
            await uploadTicketStore.UpdateAsync(
                uploadTicket,
                cancellationToken);
        }

        return UploadTicketCommandResult.Succeeded;
    }
}

public enum UploadTicketCommandResult
{
    Succeeded,
    NotFound,
}
