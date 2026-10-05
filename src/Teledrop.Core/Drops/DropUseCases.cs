namespace Teledrop.Features.Drops;

public sealed class DropUseCases(
    IDropCommandStore dropStore,
    IDropPasswordHasher dropPasswordHasher,
    IStoredDropFileCleanup fileCleanup,
    TimeProvider timeProvider)
{
    public async Task<DropCommandResult> UpdateMetadataAsync(
        string slug,
        string? description,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return DropCommandResult.NotFound;
        }

        drop.Description = NormalizeOptionalText(description);
        Touch(drop);
        await dropStore.UpdateAsync(drop, cancellationToken);
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

    // Visibility and the Drop Password change together. Only the Password level
    // keeps a hash, and choosing it always takes a new password.
    public async Task<SetDropAccessResult> SetAccessAsync(
        string slug,
        DropAccessLevel level,
        string? newDropPassword,
        CancellationToken cancellationToken)
    {
        if (!Enum.IsDefined(level)) throw new ArgumentOutOfRangeException(nameof(level));
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null) return SetDropAccessResult.NotFound;

        if (level == DropAccessLevel.Password)
        {
            if (string.IsNullOrEmpty(newDropPassword)) return SetDropAccessResult.PasswordRequired;
            drop.IsPrivate = false;
            drop.DropPasswordHash = dropPasswordHasher.Hash(newDropPassword);
        }
        else
        {
            if (drop.AccessLevel == level) return SetDropAccessResult.Succeeded;
            drop.IsPrivate = level == DropAccessLevel.Private;
            drop.DropPasswordHash = null;
        }

        Touch(drop);
        await dropStore.UpdateAccessAsync(drop, cancellationToken);
        return SetDropAccessResult.Succeeded;
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

public enum SetDropAccessResult
{
    Succeeded,
    NotFound,
    PasswordRequired,
}
