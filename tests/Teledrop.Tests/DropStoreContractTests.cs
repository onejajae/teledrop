using Microsoft.EntityFrameworkCore;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Tests;

public sealed class DropStoreContractTests
{
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task ChangesArePersistedOnlyWhenTheScopeCommits(bool sqlite)
    {
        using var fixture = new StoreFixture(sqlite);
        await SeedAsync(fixture);
        using var scope = fixture.CreateScope();
        var drop = (await scope.Store.FindBySlugAsync("source", default))!;
        await scope.Store.UpdateAsync(drop, default); // Unchanged is valid.
        drop.FileName = "Updated";

        Assert.Equal("Original", (await ReadAsync(fixture))!.FileName);
        await scope.Store.UpdateAsync(drop, default);
        Assert.Equal("Updated", (await ReadAsync(fixture))!.FileName);

        drop.FileName = "Unsaved";
        Assert.Equal("Updated", (await ReadAsync(fixture))!.FileName);
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, false)]
    [InlineData(true, true)]
    public async Task UpdateRejectsUntrackedOrOtherScopeObjects(bool sqlite, bool otherScope)
    {
        using var fixture = new StoreFixture(sqlite);
        await SeedAsync(fixture);
        using var scope = fixture.CreateScope();
        var drop = otherScope ? (await ReadAsync(fixture))! : CreateDrop();
        drop.FileName = "Must not persist";

        await Assert.ThrowsAsync<InvalidOperationException>(
            () => scope.Store.UpdateAsync(drop, default));
        await Assert.ThrowsAsync<InvalidOperationException>(
            () => scope.Store.UpdateAccessAsync(drop, default));
        await Assert.ThrowsAsync<InvalidOperationException>(
            () => scope.Store.TryChangeSlugAsync(drop, "rejected", DateTime.UtcNow, default));
        Assert.Equal("Original", (await ReadAsync(fixture))!.FileName);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task DeletedObjectsCannotBeUpdated(bool sqlite)
    {
        using var fixture = new StoreFixture(sqlite);
        await SeedAsync(fixture);
        using var scope = fixture.CreateScope();
        var drop = (await scope.Store.FindBySlugAsync("source", default))!;

        await scope.Store.DeleteBySlugAsync("source", default);

        await Assert.ThrowsAsync<InvalidOperationException>(
            () => scope.Store.UpdateAsync(drop, default));
        await Assert.ThrowsAsync<InvalidOperationException>(
            () => scope.Store.UpdateAccessAsync(drop, default));
        await Assert.ThrowsAsync<InvalidOperationException>(
            () => scope.Store.TryChangeSlugAsync(drop, "rejected", DateTime.UtcNow, default));
        Assert.Null(await ReadAsync(fixture));
    }

    [Theory]
    [InlineData(EntityState.Added)]
    [InlineData(EntityState.Deleted)]
    public async Task UpdateRejectsPendingInsertionsAndDeletions(EntityState state)
    {
        using var fixture = new StoreFixture(sqlite: true);
        await SeedAsync(fixture);
        using var scope = fixture.CreateScope();
        var drop = (await scope.Store.FindBySlugAsync("source", default))!;
        scope.Database!.Entry(drop).State = state;

        await Assert.ThrowsAsync<InvalidOperationException>(
            () => scope.Store.UpdateAsync(drop, default));
        await Assert.ThrowsAsync<InvalidOperationException>(
            () => scope.Store.UpdateAccessAsync(drop, default));
        await Assert.ThrowsAsync<InvalidOperationException>(
            () => scope.Store.TryChangeSlugAsync(drop, "rejected", DateTime.UtcNow, default));
        Assert.Equal("Original", (await ReadAsync(fixture))!.FileName);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task DifferentFieldsCanBeCommittedWithoutOverwritingEachOther(bool sqlite)
    {
        using var fixture = new StoreFixture(sqlite);
        await SeedAsync(fixture);
        using var first = fixture.CreateScope();
        using var second = fixture.CreateScope();
        var metadata = (await first.Store.FindBySlugAsync("source", default))!;
        var visibility = (await second.Store.FindBySlugAsync("source", default))!;
        metadata.FileName = "Updated";
        visibility.IsPrivate = false;

        await first.Store.UpdateAsync(metadata, default);
        await second.Store.UpdateAsync(visibility, default);

        var saved = (await ReadAsync(fixture))!;
        Assert.Equal("Updated", saved.FileName);
        Assert.False(saved.IsPrivate);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task ConflictingInsertIsUntrackedAndRetryCommitsTheScopesPendingChanges(bool sqlite)
    {
        using var fixture = new StoreFixture(sqlite);
        await SeedAsync(fixture);
        using var scope = fixture.CreateScope();
        var existing = (await scope.Store.FindBySlugAsync("source", default))!;
        existing.FileName = "Pending";
        var candidate = CreateDrop("source");

        Assert.Equal(DropSlugWriteResult.SlugConflict, await scope.Store.TryAddAsync(candidate, default));
        Assert.Equal("Original", (await ReadAsync(fixture))!.FileName);
        Assert.Equal("Pending", existing.FileName);
        await Assert.ThrowsAsync<InvalidOperationException>(() => scope.Store.UpdateAsync(candidate, default));

        candidate.Slug = "available";
        Assert.Equal(DropSlugWriteResult.Succeeded, await scope.Store.TryAddAsync(candidate, default));
        Assert.Equal(candidate.Id, (await ReadAsync(fixture, "available"))!.Id);
        Assert.Equal("Pending", (await ReadAsync(fixture))!.FileName);
        candidate.FileName = "Saved after retry";
        await scope.Store.UpdateAsync(candidate, default);
        Assert.Equal("Saved after retry", (await ReadAsync(fixture, "available"))!.FileName);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task FailedInsertDoesNotReappearInALaterCommit(bool sqlite)
    {
        using var fixture = new StoreFixture(sqlite);
        await SeedAsync(fixture);
        using var scope = fixture.CreateScope();
        var rejected = CreateDrop("source");
        Assert.Equal(DropSlugWriteResult.SlugConflict, await scope.Store.TryAddAsync(rejected, default));
        rejected.Slug = "must-not-appear";

        Assert.Equal(DropSlugWriteResult.Succeeded, await scope.Store.TryAddAsync(CreateDrop("other"), default));

        Assert.Null(await ReadAsync(fixture, "must-not-appear"));
        Assert.NotNull(await ReadAsync(fixture, "other"));
        Assert.NotEqual(rejected.Id, (await ReadAsync(fixture))!.Id);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task RenameConflictPreservesPendingFieldsAndCommitsNoneOfThem(bool sqlite)
    {
        using var fixture = new StoreFixture(sqlite);
        await SeedAsync(fixture, "source", "taken", "other");
        using var scope = fixture.CreateScope();
        var drop = (await scope.Store.FindBySlugAsync("source", default))!;
        var other = (await scope.Store.FindBySlugAsync("other", default))!;
        var pendingTime = new DateTime(2026, 9, 24, 12, 0, 0, DateTimeKind.Utc);
        drop.FileName = "Pending title";
        drop.UpdatedAt = pendingTime;
        other.Description = "Pending description";

        var result = await scope.Store.TryChangeSlugAsync(drop, "taken", pendingTime.AddHours(1), default);

        Assert.Equal(DropSlugWriteResult.SlugConflict, result);
        Assert.Same(drop, await scope.Store.FindBySlugAsync("source", default));
        Assert.Equal("source", drop.Slug);
        Assert.Equal(pendingTime, drop.UpdatedAt);
        Assert.Equal("Pending title", drop.FileName);
        Assert.Equal("Pending description", other.Description);
        Assert.Equal("Original", (await ReadAsync(fixture))!.FileName);
        Assert.Null((await ReadAsync(fixture))!.UpdatedAt);
        Assert.Null((await ReadAsync(fixture, "other"))!.Description);

        // A later ordinary write must retain the pending changes without
        // submitting the rejected Slug or its timestamp again.
        await scope.Store.UpdateAsync(other, default);
        var saved = (await ReadAsync(fixture))!;
        Assert.Equal("Pending title", saved.FileName);
        Assert.Equal(pendingTime, saved.UpdatedAt);
        Assert.Equal("Pending description", (await ReadAsync(fixture, "other"))!.Description);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task RejectedRenameDoesNotMarkTimeForALaterOverwrite(bool sqlite)
    {
        using var fixture = new StoreFixture(sqlite);
        await SeedAsync(fixture, "source", "taken");
        using var first = fixture.CreateScope();
        var drop = (await first.Store.FindBySlugAsync("source", default))!;
        Assert.Equal(DropSlugWriteResult.SlugConflict,
            await first.Store.TryChangeSlugAsync(drop, "taken", DateTime.UtcNow, default));
        var otherTime = new DateTime(2026, 9, 24, 14, 0, 0, DateTimeKind.Utc);
        using (var second = fixture.CreateScope())
        {
            var other = (await second.Store.FindBySlugAsync("source", default))!;
            other.UpdatedAt = otherTime;
            await second.Store.UpdateAsync(other, default);
        }

        drop.FileName = "Only title changed";
        await first.Store.UpdateAsync(drop, default);

        Assert.Equal(otherTime, (await ReadAsync(fixture))!.UpdatedAt);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task RenameCommitsPendingChangesAndPreservesOtherScopesFields(bool sqlite)
    {
        using var fixture = new StoreFixture(sqlite);
        await SeedAsync(fixture, "source", "other");
        using var first = fixture.CreateScope();
        var drop = (await first.Store.FindBySlugAsync("source", default))!;
        var pending = (await first.Store.FindBySlugAsync("other", default))!;
        pending.Description = "Pending";
        using (var second = fixture.CreateScope())
        {
            var other = (await second.Store.FindBySlugAsync("source", default))!;
            other.FileName = "Written elsewhere";
            await second.Store.UpdateAsync(other, default);
        }
        var updatedAt = new DateTime(2026, 9, 24, 14, 0, 0, DateTimeKind.Utc);

        Assert.Equal(DropSlugWriteResult.Succeeded,
            await first.Store.TryChangeSlugAsync(drop, "renamed", updatedAt, default));

        Assert.Same(drop, await first.Store.FindBySlugAsync("renamed", default));
        Assert.Equal("renamed", drop.Slug);
        Assert.Equal(updatedAt, drop.UpdatedAt);
        Assert.Null(await ReadAsync(fixture));
        Assert.Equal("Written elsewhere", (await ReadAsync(fixture, "renamed"))!.FileName);
        Assert.Equal("Pending", (await ReadAsync(fixture, "other"))!.Description);
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, false)]
    [InlineData(true, true)]
    public async Task CompetingScopesCanCommitTheSameSlugOnlyOnce(bool sqlite, bool insert)
    {
        using var fixture = new StoreFixture(sqlite);
        await SeedAsync(fixture, "first", "second");
        using var first = fixture.CreateScope();
        using var second = fixture.CreateScope();
        // Both callers choose their candidate before either writes. Deliberate
        // interleaving tests the race without depending on thread scheduling.
        var firstDrop = insert ? CreateDrop("shared") : (await first.Store.FindBySlugAsync("first", default))!;
        var secondDrop = insert ? CreateDrop("shared") : (await second.Store.FindBySlugAsync("second", default))!;
        var time = DateTime.UtcNow;

        var winner = insert ? await first.Store.TryAddAsync(firstDrop, default)
            : await first.Store.TryChangeSlugAsync(firstDrop, "shared", time, default);
        var loser = insert ? await second.Store.TryAddAsync(secondDrop, default)
            : await second.Store.TryChangeSlugAsync(secondDrop, "shared", time, default);

        Assert.Equal(DropSlugWriteResult.Succeeded, winner);
        Assert.Equal(DropSlugWriteResult.SlugConflict, loser);
        Assert.Equal(firstDrop.Id, (await ReadAsync(fixture, "shared"))!.Id);
        if (!insert)
        {
            Assert.Equal("second", secondDrop.Slug);
            Assert.Null(secondDrop.UpdatedAt);
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task DuplicateIdentityIsNotASlugConflictAndDoesNotPoisonTheScope(bool sqlite)
    {
        using var fixture = new StoreFixture(sqlite);
        await SeedAsync(fixture);
        var id = (await ReadAsync(fixture))!.Id;
        using var scope = fixture.CreateScope();
        var candidate = CreateDrop("available");
        candidate.Id = id;

        await Assert.ThrowsAnyAsync<Exception>(() => scope.Store.TryAddAsync(candidate, default));
        await Assert.ThrowsAsync<InvalidOperationException>(() => scope.Store.UpdateAsync(candidate, default));

        Assert.Null(await ReadAsync(fixture, "available"));
        Assert.Equal(DropSlugWriteResult.Succeeded, await scope.Store.TryAddAsync(CreateDrop("available"), default));
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, false)]
    [InlineData(true, true)]
    public async Task AnotherPendingDropsConflictIsNotReportedAsTheTargetsConflict(bool sqlite, bool insert)
    {
        using var fixture = new StoreFixture(sqlite);
        await SeedAsync(fixture, "source", "other", "taken");
        using var scope = fixture.CreateScope();
        var other = (await scope.Store.FindBySlugAsync("other", default))!;
        other.Slug = "taken";
        var target = insert ? CreateDrop("available") : (await scope.Store.FindBySlugAsync("source", default))!;

        await Assert.ThrowsAnyAsync<Exception>(() => insert
            ? scope.Store.TryAddAsync(target, default)
            : scope.Store.TryChangeSlugAsync(target, "available", DateTime.UtcNow, default));

        Assert.Null(await ReadAsync(fixture, "available"));
        Assert.NotNull(await ReadAsync(fixture, "other"));
        Assert.Equal("taken", other.Slug); // The unrelated pending edit remains.
        if (!insert)
        {
            Assert.Equal("source", target.Slug);
            Assert.Null(target.UpdatedAt);
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task DifferentUniqueConstraintIsNotTranslatedIntoASlugConflict(bool insert)
    {
        using var fixture = new StoreFixture(sqlite: true);
        await SeedAsync(fixture);
        using var scope = fixture.CreateScope();
        var different = CreateDrop("other");
        different.FileName = "Other";
        await scope.Store.TryAddAsync(different, default);
        await scope.Database!.Database.ExecuteSqlRawAsync("CREATE UNIQUE INDEX Test_UniqueFileName ON Drops (FileName)");
        var drop = insert ? CreateDrop("available") : (await scope.Store.FindBySlugAsync("source", default))!;
        if (!insert) drop.FileName = "Other";

        await Assert.ThrowsAsync<DbUpdateException>(() => insert
            ? scope.Store.TryAddAsync(drop, default)
            : scope.Store.TryChangeSlugAsync(drop, "available", DateTime.UtcNow, default));

        Assert.Null(await ReadAsync(fixture, "available"));
        if (insert)
        {
            drop.FileName = "New title";
            Assert.Equal(DropSlugWriteResult.Succeeded, await scope.Store.TryAddAsync(drop, default));
        }
        else
        {
            Assert.Equal("source", drop.Slug);
            Assert.Null(drop.UpdatedAt);
            Assert.Equal("Other", drop.FileName);
            drop.FileName = "New title";
            await scope.Store.UpdateAsync(drop, default);
            Assert.Null((await ReadAsync(fixture))!.UpdatedAt);
        }
    }

    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, false)]
    [InlineData(true, true)]
    public async Task CompetingAccessChangesPersistTheLastCompleteState(bool sqlite, bool privateFirst)
    {
        using var fixture = new StoreFixture(sqlite);
        using (var seed = fixture.CreateScope())
        {
            var drop = CreateDrop();
            drop.IsPrivate = false;
            await seed.Store.TryAddAsync(drop, default);
        }

        using var first = fixture.CreateScope();
        using var second = fixture.CreateScope();
        // Both requests read public before either saves. Re-reading through the
        // use case returns each scope's tracked copy, fixing the race order.
        var firstDrop = (await first.Store.FindBySlugAsync("source", default))!;
        await second.Store.FindBySlugAsync("source", default);
        firstDrop.Description = "Preserve this description";
        firstDrop.IsFavorite = true;
        var firstLevel = privateFirst ? DropAccessLevel.Private : DropAccessLevel.Password;
        var lastLevel = privateFirst ? DropAccessLevel.Password : DropAccessLevel.Private;

        Assert.Equal(SetDropAccessResult.Succeeded,
            await CreateUseCases(first.Store).SetAccessAsync("source", firstLevel, "secret", default));
        var afterFirst = (await ReadAsync(fixture))!;
        Assert.Equal(firstLevel, afterFirst.AccessLevel);
        Assert.Equal(privateFirst ? null : "hashed:secret", afterFirst.DropPasswordHash);

        Assert.Equal(SetDropAccessResult.Succeeded,
            await CreateUseCases(second.Store).SetAccessAsync("source", lastLevel, "secret", default));
        var saved = (await ReadAsync(fixture))!;
        Assert.Equal(lastLevel, saved.AccessLevel);
        Assert.Equal(!privateFirst, saved.IsPrivate);
        Assert.Equal(privateFirst ? "hashed:secret" : null, saved.DropPasswordHash);
        Assert.Equal("Preserve this description", saved.Description);
        Assert.True(saved.IsFavorite);
    }

    private static DropUseCases CreateUseCases(IDropCommandStore store)
        => new(store, new TestPasswordHasher(), new UnusedFileCleanup(), TimeProvider.System);

    private sealed class TestPasswordHasher : IDropPasswordHasher
    {
        public string Hash(string dropPassword) => $"hashed:{dropPassword}";
    }

    private sealed class UnusedFileCleanup : IStoredDropFileCleanup
    {
        public void TryDelete(string location) => throw new NotSupportedException();
    }

    private static async Task SeedAsync(StoreFixture fixture, params string[] slugs)
    {
        using var scope = fixture.CreateScope();
        foreach (var slug in slugs.Length == 0 ? ["source"] : slugs)
            Assert.Equal(DropSlugWriteResult.Succeeded, await scope.Store.TryAddAsync(CreateDrop(slug), default));
    }

    private static async Task<Drop?> ReadAsync(StoreFixture fixture, string slug = "source")
    {
        using var scope = fixture.CreateScope();
        return await scope.Store.FindBySlugAsync(slug, default);
    }

    private static Drop CreateDrop(string slug = "source") => new()
    {
        Id = Guid.NewGuid(), Slug = slug,
        FileName = "Original", FileHash = "hash", ContentType = "application/octet-stream",
        Location = "source-location",
    };

    private sealed class StoreFixture : IDisposable
    {
        private readonly FakeDropStore fake = new();
        private readonly string? directory;
        private readonly DbContextOptions<TeledropDbContext>? options;

        internal StoreFixture(bool sqlite)
        {
            if (!sqlite) return;
            directory = Path.Combine(Path.GetTempPath(), $"teledrop-store-tests-{Guid.NewGuid():N}");
            Directory.CreateDirectory(directory);
            options = new DbContextOptionsBuilder<TeledropDbContext>()
                .UseSqlite($"Data Source={Path.Combine(directory, "database.db")};Pooling=False")
                .Options;
            using var database = new TeledropDbContext(options);
            database.Database.Migrate();
        }

        internal StoreScope CreateScope()
        {
            if (options is null) return new StoreScope(fake.NewScope());
            var database = new TeledropDbContext(options);
            return new StoreScope(new EfDropStore(database), database);
        }

        public void Dispose()
        {
            if (directory is not null) Directory.Delete(directory, recursive: true);
        }
    }

    private sealed class StoreScope(IDropCommandStore store, TeledropDbContext? database = null)
        : IDisposable
    {
        internal IDropCommandStore Store { get; } = store;
        internal TeledropDbContext? Database { get; } = database;
        public void Dispose() => Database?.Dispose();
    }
}
