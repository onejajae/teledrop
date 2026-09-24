namespace Teledrop.Features.Drops;

public sealed class DropSlugs(
    IDropCommandStore dropStore,
    IStoredDropFileCleanup fileCleanup,
    TimeProvider timeProvider)
{
    // File ownership transfers on entry. A collision retries the same Drop;
    // only a terminal failure releases its stored file.
    public async Task<Drop> CreatePrivateAsync(
        StoredDropFile storedFile,
        string? title,
        string? description,
        CancellationToken cancellationToken)
    {
        try
        {
            cancellationToken.ThrowIfCancellationRequested();
            var drop = new Drop
            {
                Id = Guid.NewGuid(),
                Slug = string.Empty,
                Title = title,
                Description = description,
                IsPrivate = true,
                FileName = storedFile.FileName,
                FileHash = storedFile.FileHash,
                FileSizeBytes = storedFile.FileSizeBytes,
                ContentType = storedFile.ContentType,
                Location = storedFile.Location,
                CreatedAt = timeProvider.GetUtcNow().UtcDateTime,
            };

            foreach (var candidate in DropSlugGenerator.CreateCandidates())
            {
                cancellationToken.ThrowIfCancellationRequested();
                drop.Slug = candidate;
                if (await dropStore.TryAddAsync(drop, cancellationToken)
                    == DropSlugWriteResult.Succeeded)
                {
                    return drop;
                }
            }

            throw new InvalidOperationException(
                "A unique drop slug could not be generated.");
        }
        catch
        {
            fileCleanup.TryDelete(storedFile.Location);
            throw;
        }
    }

    public async Task<ChangeDropSlugResult> ChangeAsync(
        string currentSlug,
        string? requestedSlug,
        CancellationToken cancellationToken)
    {
        var drop = string.IsNullOrWhiteSpace(currentSlug)
            ? null
            : await dropStore.FindBySlugAsync(currentSlug, cancellationToken);
        if (drop is null)
        {
            return ChangeDropSlugResult.NotFound();
        }

        if (!DropSlugGenerator.TryNormalizeCustomSlug(
                requestedSlug, out var normalizedSlug, out var validationError))
        {
            return ChangeDropSlugResult.Invalid(normalizedSlug, validationError);
        }

        if (string.Equals(drop.Slug, normalizedSlug, StringComparison.Ordinal))
        {
            return ChangeDropSlugResult.Succeeded(normalizedSlug);
        }

        var result = await dropStore.TryChangeSlugAsync(
            drop, normalizedSlug, timeProvider.GetUtcNow().UtcDateTime, cancellationToken);
        return result == DropSlugWriteResult.SlugConflict
            ? ChangeDropSlugResult.AlreadyExists(normalizedSlug)
            : ChangeDropSlugResult.Succeeded(normalizedSlug);
    }
}

public sealed record ChangeDropSlugResult(
    ChangeDropSlugStatus Status,
    string NormalizedSlug,
    DropSlugValidationError ValidationError)
{
    public static ChangeDropSlugResult Succeeded(string normalizedSlug)
    {
        return new(
            ChangeDropSlugStatus.Succeeded,
            normalizedSlug,
            DropSlugValidationError.None);
    }

    public static ChangeDropSlugResult NotFound()
    {
        return new(
            ChangeDropSlugStatus.NotFound,
            string.Empty,
            DropSlugValidationError.None);
    }

    public static ChangeDropSlugResult Invalid(
        string normalizedSlug,
        DropSlugValidationError validationError)
    {
        return new(
            ChangeDropSlugStatus.Invalid,
            normalizedSlug,
            validationError);
    }

    public static ChangeDropSlugResult AlreadyExists(string normalizedSlug)
    {
        return new(
            ChangeDropSlugStatus.AlreadyExists,
            normalizedSlug,
            DropSlugValidationError.None);
    }
}

public enum ChangeDropSlugStatus
{
    Succeeded,
    NotFound,
    Invalid,
    AlreadyExists,
}
