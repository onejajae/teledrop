using System.Reflection;
using Teledrop.Features.Drops;

namespace Teledrop.Tests;

// Committed snapshots are shared; working copies belong to one store scope.
internal sealed class FakeDropStore : IDropCommandStore
{
    private static readonly PropertyInfo[] Properties = typeof(Drop).GetProperties();
    private readonly Dictionary<Guid, Drop> committed;
    private readonly Dictionary<Guid, TrackedDrop> tracked = [];
    private readonly List<string> operations;

    internal FakeDropStore(List<string>? operations = null)
        : this([], operations ?? [])
    {
    }

    private FakeDropStore(Dictionary<Guid, Drop> committed, List<string> operations)
    {
        this.committed = committed;
        this.operations = operations;
    }

    internal FakeDropStore NewScope() => new(committed, operations);

    public Task<Drop?> FindBySlugAsync(string slug, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        lock (committed)
        {
            return Task.FromResult(FindTrackedDrop(slug));
        }
    }

    public Task<DropSlugWriteResult> TryAddAsync(Drop drop, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        lock (committed)
        {
            if (tracked.ContainsKey(drop.Id) || committed.ContainsKey(drop.Id))
                throw new InvalidOperationException("Only a new Drop can be inserted.");

            var pending = StageChanges();
            pending.Add(drop.Id, Copy(drop));
            if (HasSlugConflict(pending, drop.Id))
                return Task.FromResult(DropSlugWriteResult.SlugConflict);

            tracked.Add(drop.Id, new TrackedDrop(drop, Copy(drop)));
            Commit(pending);
            return Task.FromResult(DropSlugWriteResult.Succeeded);
        }
    }

    public Task<DropSlugWriteResult> TryChangeSlugAsync(
        Drop drop, string newSlug, DateTime updatedAtUtc, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        lock (committed)
        {
            RequireTrackedDrop(drop);
            var previousSlug = drop.Slug;
            var previousUpdatedAt = drop.UpdatedAt;
            var succeeded = false;
            drop.Slug = newSlug;
            drop.UpdatedAt = updatedAtUtc;
            try
            {
                var pending = StageChanges();
                if (HasSlugConflict(pending, drop.Id))
                    return Task.FromResult(DropSlugWriteResult.SlugConflict);

                Commit(pending);
                succeeded = true;
                return Task.FromResult(DropSlugWriteResult.Succeeded);
            }
            finally
            {
                if (!succeeded)
                {
                    drop.Slug = previousSlug;
                    drop.UpdatedAt = previousUpdatedAt;
                }
            }
        }
    }

    public Task UpdateAsync(Drop drop, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        lock (committed)
        {
            RequireTrackedDrop(drop);
            var pending = StageChanges();
            HasSlugConflict(pending, targetId: null);
            Commit(pending);
            return Task.CompletedTask;
        }
    }

    public Task<Drop?> DeleteBySlugAsync(string slug, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        lock (committed)
        {
            var drop = FindTrackedDrop(slug);
            if (drop is null) return Task.FromResult<Drop?>(null);
            var pending = StageChanges();
            pending.Remove(drop.Id);
            HasSlugConflict(pending, targetId: null);
            tracked.Remove(drop.Id);
            Commit(pending);
            operations.Add("database");
            return Task.FromResult<Drop?>(drop);
        }
    }

    private Drop? FindTrackedDrop(string slug)
    {
        var saved = committed.Values.SingleOrDefault(drop => drop.Slug == slug);
        if (saved is null) return null;
        if (!tracked.TryGetValue(saved.Id, out var entry))
        {
            entry = new TrackedDrop(Copy(saved), Copy(saved));
            tracked.Add(saved.Id, entry);
        }
        return entry.Current;
    }

    private void RequireTrackedDrop(Drop drop)
    {
        if (!tracked.TryGetValue(drop.Id, out var entry)
            || !ReferenceEquals(entry.Current, drop))
        {
            throw new InvalidOperationException(
                "The Drop must be persisted and tracked by this store scope before updating.");
        }
    }

    private Dictionary<Guid, Drop> StageChanges()
    {
        var pending = new Dictionary<Guid, Drop>(committed);
        foreach (var (id, entry) in tracked)
        {
            // Merge only changed fields, as the SQLite adapter does. Nothing
            // reaches committed state until the whole write has been validated.
            var saved = Copy(committed[id]);
            foreach (var property in Properties)
            {
                var current = property.GetValue(entry.Current);
                if (!Equals(current, property.GetValue(entry.Original)))
                    property.SetValue(saved, current);
            }
            pending[id] = saved;
        }
        return pending;
    }

    private static bool HasSlugConflict(Dictionary<Guid, Drop> pending, Guid? targetId)
    {
        var conflicts = pending.Values.GroupBy(drop => drop.Slug, StringComparer.Ordinal)
            .Where(group => group.Count() > 1).ToArray();
        if (conflicts.Any(group => targetId is null || group.All(drop => drop.Id != targetId)))
            throw new InvalidOperationException("A different pending Drop has a Slug conflict.");
        return conflicts.Length > 0;
    }

    private void Commit(Dictionary<Guid, Drop> pending)
    {
        committed.Clear();
        foreach (var (id, drop) in pending) committed.Add(id, drop);
        foreach (var (id, entry) in tracked.ToArray())
            tracked[id] = new TrackedDrop(entry.Current, Copy(entry.Current));
    }

    private static Drop Copy(Drop drop) => new()
    {
        Id = drop.Id,
        Slug = drop.Slug,
        Title = drop.Title,
        Description = drop.Description,
        IsPrivate = drop.IsPrivate,
        DropPasswordHash = drop.DropPasswordHash,
        IsFavorite = drop.IsFavorite,
        FileName = drop.FileName,
        FileHash = drop.FileHash,
        FileSizeBytes = drop.FileSizeBytes,
        ContentType = drop.ContentType,
        Location = drop.Location,
        CreatedAt = drop.CreatedAt,
        UpdatedAt = drop.UpdatedAt,
    };

    private sealed record TrackedDrop(Drop Current, Drop Original);
}
