namespace Teledrop.Features.Drops;

public interface IDropCommandStore
{
    /// <summary>
    /// Returns a Drop tracked for the lifetime of this store scope.
    /// Changing the returned object does not persist it until a write commits.
    /// </summary>
    Task<Drop?> FindBySlugAsync(
        string slug,
        CancellationToken cancellationToken);

    /// <summary>
    /// Inserts a new Drop and commits pending changes in this scope.
    /// A SlugConflict leaves the Drop unpersisted and untracked, so the same
    /// object can be retried with another Slug. Other failures propagate.
    /// </summary>
    Task<DropSlugWriteResult> TryAddAsync(
        Drop drop,
        CancellationToken cancellationToken);

    /// <summary>
    /// Changes a persisted Drop tracked by this scope and commits pending changes.
    /// The caller must not apply the new Slug or UpdatedAt before this call.
    /// On failure, restores those fields and their tracking state to the values
    /// at entry, preserving all other pending changes. Only the target Drop's
    /// Slug uniqueness violation returns SlugConflict; other failures propagate.
    /// </summary>
    /// <exception cref="InvalidOperationException">
    /// The Drop is untracked, belongs to another scope, or is pending insertion
    /// or deletion.
    /// </exception>
    Task<DropSlugWriteResult> TryChangeSlugAsync(
        Drop drop,
        string newSlug,
        DateTime updatedAtUtc,
        CancellationToken cancellationToken);

    /// <summary>
    /// Commits pending changes in this scope. The Drop must already be persisted
    /// and tracked by this scope (for example, returned by FindBySlugAsync).
    /// Only changed fields are written, preserving other scopes' field changes.
    /// </summary>
    /// <exception cref="InvalidOperationException">
    /// The Drop is untracked, belongs to another scope, or is pending insertion
    /// or deletion.
    /// </exception>
    Task UpdateAsync(
        Drop drop,
        CancellationToken cancellationToken);

    Task<Drop?> DeleteBySlugAsync(
        string slug,
        CancellationToken cancellationToken);
}

public enum DropSlugWriteResult
{
    Succeeded,
    SlugConflict,
}

public interface IStoredDropFileCleanup
{
    void TryDelete(string location);
}

public interface IDropPasswordHasher
{
    string Hash(string dropPassword);
}
