namespace Teledrop.Features.Drops;

public sealed class DropUseCases(
    IDropCommandStore dropStore,
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

    public async Task<DropCommandResult> SetVisibilityAsync(
        string slug, bool isPrivate, CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null) return DropCommandResult.NotFound;
        if (drop.IsPrivate != isPrivate)
        {
            drop.IsPrivate = isPrivate;
            Touch(drop);
            await dropStore.UpdateAsync(drop, cancellationToken);
        }
        return DropCommandResult.Succeeded;
    }

    public async Task<DropCommandResult> SetFavoriteAsync(
        string slug, bool isFavorite, CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null) return DropCommandResult.NotFound;
        if (drop.IsFavorite != isFavorite)
        {
            drop.IsFavorite = isFavorite;
            await dropStore.UpdateAsync(drop, cancellationToken);
        }
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
