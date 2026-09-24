using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.ChangeTracking;
using Teledrop.Data;

namespace Teledrop.Features.Drops;

public sealed class EfDropStore(TeledropDbContext dbContext)
    : IDropCommandStore
{
    public async Task<Drop?> FindBySlugAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        return await dbContext.Drops.SingleOrDefaultAsync(
            drop => drop.Slug == slug,
            cancellationToken);
    }

    public async Task<DropSlugWriteResult> TryAddAsync(
        Drop drop,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (dbContext.Entry(drop).State != EntityState.Detached)
        {
            throw new InvalidOperationException("Only a new, untracked Drop can be inserted.");
        }

        var entry = dbContext.Drops.Add(drop);
        try
        {
            await dbContext.SaveChangesAsync(cancellationToken);
            return DropSlugWriteResult.Succeeded;
        }
        catch (DbUpdateException exception) when (IsTargetSlugConflict(exception, drop))
        {
            entry.State = EntityState.Detached;
            return DropSlugWriteResult.SlugConflict;
        }
        catch
        {
            entry.State = EntityState.Detached;
            throw;
        }
    }

    public async Task<DropSlugWriteResult> TryChangeSlugAsync(
        Drop drop,
        string newSlug,
        DateTime updatedAtUtc,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        dbContext.ChangeTracker.DetectChanges();
        var entry = RequireTrackedDrop(drop);
        var slug = entry.Property(candidate => candidate.Slug);
        var updatedAt = entry.Property(candidate => candidate.UpdatedAt);
        var previousSlug = slug.CurrentValue;
        var previousUpdatedAt = updatedAt.CurrentValue;
        var slugWasModified = slug.IsModified;
        var updatedAtWasModified = updatedAt.IsModified;

        slug.CurrentValue = newSlug;
        updatedAt.CurrentValue = updatedAtUtc;
        try
        {
            await dbContext.SaveChangesAsync(cancellationToken);
            return DropSlugWriteResult.Succeeded;
        }
        catch (Exception exception)
        {
            // OriginalValues may predate other pending edits in this scope.
            // Restore only this operation's fields and their previous flags.
            slug.CurrentValue = previousSlug;
            updatedAt.CurrentValue = previousUpdatedAt;
            slug.IsModified = slugWasModified;
            updatedAt.IsModified = updatedAtWasModified;

            if (exception is DbUpdateException updateException
                && IsTargetSlugConflict(updateException, drop))
            {
                return DropSlugWriteResult.SlugConflict;
            }

            throw;
        }
    }

    public async Task UpdateAsync(
        Drop drop,
        CancellationToken cancellationToken)
    {
        RequireTrackedDrop(drop);
        await dbContext.SaveChangesAsync(cancellationToken);
    }

    public async Task<Drop?> DeleteBySlugAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindBySlugAsync(slug, cancellationToken);
        if (drop is null)
        {
            return null;
        }

        dbContext.Drops.Remove(drop);
        await dbContext.SaveChangesAsync(cancellationToken);
        return drop;
    }

    private EntityEntry<Drop> RequireTrackedDrop(Drop drop)
    {
        var entry = dbContext.Entry(drop);
        if (entry.State is not (EntityState.Unchanged or EntityState.Modified))
        {
            throw new InvalidOperationException(
                "The Drop must be persisted and tracked by this store scope before updating.");
        }

        return entry;
    }

    private static bool IsTargetSlugConflict(DbUpdateException exception, Drop drop)
    {
        // SQLite exposes the constraint's columns in its error text, not as a
        // structured property. Do not turn other unique constraints, primary
        // keys, or errors from another pending Drop into this operation's result.
        return exception.InnerException is SqliteException { SqliteExtendedErrorCode: 2067 } sqlite
            && sqlite.Message.Contains("UNIQUE constraint failed: Drops.Slug'", StringComparison.Ordinal)
            && exception.Entries.Count == 1
            && ReferenceEquals(exception.Entries[0].Entity, drop);
    }
}
