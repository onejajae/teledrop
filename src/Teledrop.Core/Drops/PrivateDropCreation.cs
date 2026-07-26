namespace Teledrop.Features.Drops;

public sealed class PrivateDropFactory(
    DropSlugGenerator dropSlugGenerator,
    TimeProvider timeProvider)
{
    public async Task<Drop> CreateAsync(
        StoredDropFile storedFile,
        string? title,
        string? description,
        Guid? uploadTicketId,
        CancellationToken cancellationToken)
    {
        return new Drop
        {
            Id = Guid.NewGuid(),
            Slug = await dropSlugGenerator.GenerateUniqueSlugAsync(
                cancellationToken),
            Title = title,
            Description = description,
            IsPrivate = true,
            FileName = storedFile.FileName,
            FileHash = storedFile.FileHash,
            FileSizeBytes = storedFile.FileSizeBytes,
            ContentType = storedFile.ContentType,
            Location = storedFile.Location,
            CreatedAt = timeProvider.GetUtcNow().UtcDateTime,
            UploadTicketId = uploadTicketId,
        };
    }
}

public sealed class CreatePrivateDrop(
    PrivateDropFactory privateDropFactory,
    IDropCommandStore dropStore,
    IStoredDropFileCleanup fileCleanup)
{
    public async Task<Drop> ExecuteAsync(
        StoredDropFile storedFile,
        string? title,
        string? description,
        CancellationToken cancellationToken)
    {
        try
        {
            var drop = await privateDropFactory.CreateAsync(
                storedFile,
                title,
                description,
                uploadTicketId: null,
                cancellationToken);
            await dropStore.AddAsync(drop, cancellationToken);
            return drop;
        }
        catch
        {
            fileCleanup.TryDelete(storedFile.Location);
            throw;
        }
    }
}
