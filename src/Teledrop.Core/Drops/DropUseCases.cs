namespace Teledrop.Features.Drops;

public sealed class DropUseCases(
    IDropCommandStore dropStore,
    IDropSlugIndex dropSlugIndex,
    IDropPasswordHasher dropPasswordHasher,
    IStoredDropFileCleanup fileCleanup,
    TimeProvider timeProvider)
{
    public async Task<DropCommandResult> UpdateMetadataAsync(
        string slug,
        string? title,
        string? description,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return DropCommandResult.NotFound;
        }

        drop.Title = NormalizeOptionalText(title);
        drop.Description = NormalizeOptionalText(description);
        Touch(drop);
        await dropStore.UpdateAsync(drop, cancellationToken);
        return DropCommandResult.Succeeded;
    }

    public async Task<DropCommandResult> ToggleVisibilityAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return DropCommandResult.NotFound;
        }

        drop.IsPrivate = !drop.IsPrivate;
        Touch(drop);
        await dropStore.UpdateAsync(drop, cancellationToken);
        return DropCommandResult.Succeeded;
    }

    public async Task<SetDropPasswordResult> SetPasswordAsync(
        string slug,
        string newDropPassword,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return SetDropPasswordResult.NotFound;
        }

        if (string.IsNullOrEmpty(newDropPassword))
        {
            return SetDropPasswordResult.PasswordRequired;
        }

        drop.DropPasswordHash = dropPasswordHasher.Hash(newDropPassword);
        Touch(drop);
        await dropStore.UpdateAsync(drop, cancellationToken);
        return SetDropPasswordResult.Succeeded;
    }

    public async Task<DropCommandResult> ClearPasswordAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return DropCommandResult.NotFound;
        }

        drop.DropPasswordHash = null;
        Touch(drop);
        await dropStore.UpdateAsync(drop, cancellationToken);
        return DropCommandResult.Succeeded;
    }

    public async Task<ChangeDropSlugResult> ChangeSlugAsync(
        string slug,
        string? requestedSlug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return ChangeDropSlugResult.NotFound();
        }

        if (!DropSlugGenerator.TryNormalizeCustomSlug(
                requestedSlug,
                out var normalizedSlug,
                out var validationError))
        {
            return ChangeDropSlugResult.Invalid(
                normalizedSlug,
                validationError);
        }

        if (await dropSlugIndex.ExistsAsync(
                normalizedSlug,
                drop.Id,
                cancellationToken))
        {
            return ChangeDropSlugResult.AlreadyExists(normalizedSlug);
        }

        if (!string.Equals(
                drop.Slug,
                normalizedSlug,
                StringComparison.Ordinal))
        {
            drop.Slug = normalizedSlug;
            Touch(drop);
            await dropStore.UpdateAsync(drop, cancellationToken);
        }

        return ChangeDropSlugResult.Succeeded(normalizedSlug);
    }

    public async Task<DropCommandResult> ToggleFavoriteAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return DropCommandResult.NotFound;
        }

        drop.IsFavorite = !drop.IsFavorite;
        await dropStore.UpdateAsync(drop, cancellationToken);
        return DropCommandResult.Succeeded;
    }

    public async Task<DropCommandResult> DeleteAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(slug))
        {
            return DropCommandResult.NotFound;
        }

        var drop = await dropStore.DeleteBySlugAsync(
            slug,
            cancellationToken);
        if (drop is null)
        {
            return DropCommandResult.NotFound;
        }

        fileCleanup.TryDelete(drop.Location);
        return DropCommandResult.Succeeded;
    }

    private async Task<Drop?> FindDropAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        return string.IsNullOrWhiteSpace(slug)
            ? null
            : await dropStore.FindBySlugAsync(slug, cancellationToken);
    }

    private void Touch(Drop drop)
    {
        drop.UpdatedAt = timeProvider.GetUtcNow().UtcDateTime;
    }

    private static string? NormalizeOptionalText(string? value)
    {
        var normalized = value?.Trim();
        return string.IsNullOrEmpty(normalized) ? null : normalized;
    }
}

public enum DropCommandResult
{
    Succeeded,
    NotFound,
}

public enum SetDropPasswordResult
{
    Succeeded,
    NotFound,
    PasswordRequired,
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
