using Teledrop.Features.Drops;
using Teledrop.Testing;
using Xunit;

namespace Teledrop.Core.Tests;

public sealed class DropUseCaseTests
{
    private static readonly DateTimeOffset Now =
        new(2026, 7, 27, 1, 2, 3, TimeSpan.Zero);

    [Fact]
    public async Task DeleteRemovesDatabaseRowBeforeStoredFile()
    {
        const string location = "opaque-stored-file-id";
        var operations = new List<string>();
        var dependencies = new DropDependencies(operations);
        var drop = CreateDrop("delete-me");
        drop.Location = location;
        await dependencies.Store.TryAddAsync(drop, default);
        var useCases = dependencies.CreateDropUseCases();

        var result = await useCases.DeleteAsync(
            "delete-me",
            CancellationToken.None);

        Assert.Equal(DropCommandResult.Succeeded, result);
        Assert.Equal(["database", "file"], operations);
        Assert.Equal([location], dependencies.FileCleanup.DeletedLocations);
        Assert.Null(await dependencies.Store.NewScope().FindBySlugAsync("delete-me", default));
    }

    [Theory]
    [InlineData(null, null)]
    [InlineData("", null)]
    [InlineData(" \t\r\n ", null)]
    [InlineData("  description\nsecond line  ", "description\nsecond line")]
    public async Task MetadataNormalizesOptionalTextAndUpdatesItsTimestamp(
        string? description, string? expected)
    {
        var dependencies = new DropDependencies();
        var drop = CreateDrop("edit-me", DropAccessLevel.Password);
        drop.Description = "Original description";
        drop.UpdatedAt = Now.AddDays(-1).UtcDateTime;
        await dependencies.Store.TryAddAsync(drop, default);
        var useCases = dependencies.CreateDropUseCases();

        var result = await useCases.UpdateMetadataAsync(drop.Slug, description, default);

        drop = (await dependencies.Store.NewScope().FindBySlugAsync("edit-me", default))!;
        Assert.Equal(DropCommandResult.Succeeded, result);
        Assert.Equal(expected, drop.Description);
        Assert.Equal(Now.UtcDateTime, drop.UpdatedAt);
        Assert.Equal(DropAccessLevel.Password, drop.AccessLevel);
        Assert.Equal("hashed:old", drop.DropPasswordHash);
    }

    [Theory]
    [InlineData(DropAccessLevel.Private, null)]
    [InlineData(DropAccessLevel.Private, "")]
    [InlineData(DropAccessLevel.Public, null)]
    [InlineData(DropAccessLevel.Public, "")]
    [InlineData(DropAccessLevel.Password, null)]
    [InlineData(DropAccessLevel.Password, "")]
    public async Task MissingNewPasswordPreservesEveryAccessStateWithoutSideEffects(
        DropAccessLevel from, string? password)
    {
        var dependencies = new DropDependencies();
        var drop = CreateDrop("access", from);
        var originalHash = drop.DropPasswordHash;
        var originalTime = Now.AddDays(-1).UtcDateTime;
        drop.Description = "Original description";
        drop.UpdatedAt = originalTime;
        await dependencies.Store.TryAddAsync(drop, default);
        drop.Description = "Pending description";
        var useCases = dependencies.CreateDropUseCases();

        var result = await useCases.SetAccessAsync("access", DropAccessLevel.Password, password, default);

        Assert.Equal(SetDropAccessResult.PasswordRequired, result);
        Assert.Equal(from, drop.AccessLevel);
        Assert.Equal(originalHash, drop.DropPasswordHash);
        Assert.Equal(originalTime, drop.UpdatedAt);
        Assert.Equal("Pending description", drop.Description);
        var stored = (await dependencies.Store.NewScope().FindBySlugAsync("access", default))!;
        Assert.Equal(from, stored.AccessLevel);
        Assert.Equal(originalHash, stored.DropPasswordHash);
        Assert.Equal(originalTime, stored.UpdatedAt);
        Assert.Equal("Original description", stored.Description);
        Assert.Empty(dependencies.PasswordHasher.Inputs);
        Assert.Empty(dependencies.FileCleanup.DeletedLocations);
    }

    [Theory]
    [InlineData(DropAccessLevel.Private, DropAccessLevel.Private, false, true, null)]
    [InlineData(DropAccessLevel.Private, DropAccessLevel.Public, true, false, null)]
    [InlineData(DropAccessLevel.Private, DropAccessLevel.Password, true, false, "hashed:secret")]
    [InlineData(DropAccessLevel.Public, DropAccessLevel.Private, true, true, null)]
    [InlineData(DropAccessLevel.Public, DropAccessLevel.Public, false, false, null)]
    [InlineData(DropAccessLevel.Public, DropAccessLevel.Password, true, false, "hashed:secret")]
    [InlineData(DropAccessLevel.Password, DropAccessLevel.Private, true, true, null)]
    [InlineData(DropAccessLevel.Password, DropAccessLevel.Public, true, false, null)]
    [InlineData(DropAccessLevel.Password, DropAccessLevel.Password, true, false, "hashed:secret")]
    public async Task AccessTransitionsCommitCompleteStatesAndLeaveNoOpsUntouched(
        DropAccessLevel from, DropAccessLevel to, bool changed, bool isPrivate, string? hash)
    {
        var dependencies = new DropDependencies();
        var drop = CreateDrop("access", from);
        var originalTime = Now.AddDays(-1).UtcDateTime;
        drop.UpdatedAt = originalTime;
        drop.Description = "Original description";
        await dependencies.Store.TryAddAsync(drop, default);
        drop.Description = "Pending description";
        var useCases = dependencies.CreateDropUseCases();

        var result = await useCases.SetAccessAsync("access", to, "secret", default);

        var stored = (await dependencies.Store.NewScope().FindBySlugAsync("access", default))!;
        Assert.Equal(SetDropAccessResult.Succeeded, result);
        Assert.Equal(to, stored.AccessLevel);
        Assert.Equal(isPrivate, stored.IsPrivate);
        Assert.Equal(hash, stored.DropPasswordHash);
        Assert.Equal(changed ? Now.UtcDateTime : originalTime, stored.UpdatedAt);
        Assert.Equal(changed ? "Pending description" : "Original description", stored.Description);
        Assert.Equal(to, drop.AccessLevel);
        Assert.Equal(hash, drop.DropPasswordHash);
        Assert.Equal(changed ? Now.UtcDateTime : originalTime, drop.UpdatedAt);
        Assert.Equal("Pending description", drop.Description);
        if (to == DropAccessLevel.Password)
            Assert.Equal(["secret"], dependencies.PasswordHasher.Inputs);
        else
            Assert.Empty(dependencies.PasswordHasher.Inputs);
        Assert.Empty(dependencies.FileCleanup.DeletedLocations);
    }

    [Fact]
    public async Task PasswordChangePassesTheExactSubmittedTextToTheHasher()
    {
        const string password = "  드롭 비밀번호 🔑\t ";
        var dependencies = new DropDependencies();
        var drop = CreateDrop("access", DropAccessLevel.Password);
        await dependencies.Store.TryAddAsync(drop, default);

        var result = await dependencies.CreateDropUseCases()
            .SetAccessAsync(drop.Slug, DropAccessLevel.Password, password, default);

        Assert.Equal(SetDropAccessResult.Succeeded, result);
        Assert.Equal([password], dependencies.PasswordHasher.Inputs);
        var stored = (await dependencies.Store.NewScope().FindBySlugAsync(drop.Slug, default))!;
        Assert.Equal(DropAccessLevel.Password, stored.AccessLevel);
        Assert.Equal($"hashed:{password}", stored.DropPasswordHash);
        Assert.Equal(Now.UtcDateTime, stored.UpdatedAt);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("missing")]
    public async Task MissingDropsDoNotCommitOtherChangesOrDeleteFiles(string slug)
    {
        var dependencies = new DropDependencies();
        var existing = CreateDrop("existing");
        await dependencies.Store.TryAddAsync(existing, default);
        existing.Description = "Pending change";
        var useCases = dependencies.CreateDropUseCases();

        Assert.Equal(DropCommandResult.NotFound,
            await useCases.UpdateMetadataAsync(slug, "New description", default));
        Assert.Equal(DropCommandResult.NotFound,
            await useCases.SetFavoriteAsync(slug, true, default));
        Assert.Equal(SetDropAccessResult.NotFound,
            await useCases.SetAccessAsync(slug, DropAccessLevel.Password, "secret", default));
        Assert.Equal(DropCommandResult.NotFound,
            await useCases.DeleteAsync(slug, default));

        var saved = (await dependencies.Store.NewScope().FindBySlugAsync("existing", default))!;
        Assert.Null(saved.Description);
        Assert.False(saved.IsFavorite);
        Assert.Equal(DropAccessLevel.Private, saved.AccessLevel);
        Assert.Null(saved.UpdatedAt);
        Assert.Equal("Pending change", existing.Description);
        Assert.Empty(dependencies.PasswordHasher.Inputs);
        Assert.Empty(dependencies.FileCleanup.DeletedLocations);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task FailedOrCanceledDeletionKeepsTheStoredFile(bool cancelDuringDelete)
    {
        var dependencies = new DropDependencies();
        await dependencies.Store.TryAddAsync(CreateDrop("keep-me"), default);
        using var cancellation = new CancellationTokenSource();
        Exception failure = cancelDuringDelete
            ? new OperationCanceledException(cancellation.Token)
            : new IOException("Database write failed.");
        var store = new FailingDeleteStore(dependencies.Store, failure, cancellation, cancelDuringDelete);
        var useCases = new DropUseCases(store, dependencies.PasswordHasher,
            dependencies.FileCleanup, new FixedTimeProvider(Now));

        var thrown = await Record.ExceptionAsync(
            () => useCases.DeleteAsync("keep-me", cancellation.Token));

        Assert.Same(failure, thrown);
        Assert.Equal("keep-me", store.RequestedSlug);
        Assert.Equal(cancellation.Token, store.RequestedCancellationToken);
        Assert.Equal(cancelDuringDelete, cancellation.IsCancellationRequested);
        Assert.NotNull(await dependencies.Store.NewScope().FindBySlugAsync("keep-me", default));
        Assert.Empty(dependencies.FileCleanup.DeletedLocations);
    }

    [Fact]
    public async Task AlreadyCanceledDeletionKeepsTheDatabaseRowAndStoredFile()
    {
        var dependencies = new DropDependencies();
        await dependencies.Store.TryAddAsync(CreateDrop("keep-me"), default);
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            dependencies.CreateDropUseCases().DeleteAsync("keep-me", cancellation.Token));

        Assert.NotNull(await dependencies.Store.NewScope().FindBySlugAsync("keep-me", default));
        Assert.Empty(dependencies.FileCleanup.DeletedLocations);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task UnchangedFavoriteDoesNotCommitOtherPendingChanges(bool isFavorite)
    {
        var dependencies = new DropDependencies();
        var drop = CreateDrop("favorite");
        drop.IsFavorite = isFavorite;
        drop.UpdatedAt = Now.AddDays(-1).UtcDateTime;
        await dependencies.Store.TryAddAsync(drop, default);
        drop.Description = "Pending description";

        var result = await dependencies.CreateDropUseCases()
            .SetFavoriteAsync(drop.Slug, isFavorite, default);

        var saved = (await dependencies.Store.NewScope().FindBySlugAsync(drop.Slug, default))!;
        Assert.Equal(DropCommandResult.Succeeded, result);
        Assert.Equal(isFavorite, saved.IsFavorite);
        Assert.Equal(Now.AddDays(-1).UtcDateTime, saved.UpdatedAt);
        Assert.Null(saved.Description);
        Assert.Equal("Pending description", drop.Description);
    }

    [Theory]
    [InlineData(false, true)]
    [InlineData(true, false)]
    public async Task FavoriteChangesPersistWithoutChangingTheContentTimestamp(
        bool initial, bool desired)
    {
        var dependencies = new DropDependencies();
        var drop = CreateDrop("favorite");
        drop.IsFavorite = initial;
        drop.UpdatedAt = Now.AddDays(-1).UtcDateTime;
        await dependencies.Store.TryAddAsync(drop, default);

        var result = await dependencies.CreateDropUseCases()
            .SetFavoriteAsync(drop.Slug, desired, default);

        var saved = (await dependencies.Store.NewScope().FindBySlugAsync(drop.Slug, default))!;
        Assert.Equal(DropCommandResult.Succeeded, result);
        Assert.Equal(desired, saved.IsFavorite);
        Assert.Equal(Now.AddDays(-1).UtcDateTime, saved.UpdatedAt);
    }

    [Fact]
    public async Task InvalidAccessLevelDoesNotChangeOrCommitTheDrop()
    {
        var dependencies = new DropDependencies();
        var drop = CreateDrop("access");
        await dependencies.Store.TryAddAsync(drop, default);
        drop.Description = "Pending description";

        var error = await Assert.ThrowsAsync<ArgumentOutOfRangeException>(() =>
            dependencies.CreateDropUseCases().SetAccessAsync(drop.Slug,
                (DropAccessLevel)99, "secret", default));

        Assert.Equal("level", error.ParamName);
        var saved = (await dependencies.Store.NewScope().FindBySlugAsync(drop.Slug, default))!;
        Assert.Equal(DropAccessLevel.Private, saved.AccessLevel);
        Assert.Null(saved.DropPasswordHash);
        Assert.Null(saved.UpdatedAt);
        Assert.Null(saved.Description);
        Assert.Equal(DropAccessLevel.Private, drop.AccessLevel);
        Assert.Null(drop.DropPasswordHash);
        Assert.Null(drop.UpdatedAt);
        Assert.Equal("Pending description", drop.Description);
        Assert.Empty(dependencies.PasswordHasher.Inputs);
        Assert.Empty(dependencies.FileCleanup.DeletedLocations);
    }

    private static Drop CreateDrop(string slug, DropAccessLevel level = DropAccessLevel.Private)
    {
        return new Drop
        {
            Id = Guid.NewGuid(),
            Slug = slug,
            IsPrivate = level == DropAccessLevel.Private,
            DropPasswordHash = level == DropAccessLevel.Password ? "hashed:old" : null,
            FileName = "sample.bin",
            FileHash = "file-hash",
            ContentType = "application/octet-stream",
            Location = $"{slug}-location",
            CreatedAt = Now.UtcDateTime,
        };
    }

    private sealed class DropDependencies
    {
        private readonly List<string> operations;

        internal DropDependencies(List<string>? operations = null)
        {
            this.operations = operations ?? [];
            Store = new FakeDropStore(this.operations);
            FileCleanup = new FakeFileCleanup(this.operations);
        }

        internal FakeDropStore Store { get; }

        internal FakeFileCleanup FileCleanup { get; }

        internal RecordingPasswordHasher PasswordHasher { get; } = new();

        internal DropUseCases CreateDropUseCases()
        {
            return new DropUseCases(
                Store,
                PasswordHasher,
                FileCleanup,
                new FixedTimeProvider(Now));
        }
    }

    private sealed class FakeFileCleanup(List<string> operations)
        : IStoredDropFileCleanup
    {
        internal List<string> DeletedLocations { get; } = [];

        public void TryDelete(string location)
        {
            DeletedLocations.Add(location);
            operations.Add("file");
        }
    }

    private sealed class RecordingPasswordHasher : IDropPasswordHasher
    {
        internal List<string> Inputs { get; } = [];

        public string Hash(string dropPassword)
        {
            Inputs.Add(dropPassword);
            return $"hashed:{dropPassword}";
        }
    }

    private sealed class FailingDeleteStore(
        FakeDropStore inner, Exception failure,
        CancellationTokenSource cancellation, bool cancelDuringDelete)
        : IDropCommandStore
    {
        internal string? RequestedSlug { get; private set; }
        internal CancellationToken RequestedCancellationToken { get; private set; }

        public Task<Drop?> DeleteBySlugAsync(string slug, CancellationToken cancellationToken)
        {
            RequestedSlug = slug;
            RequestedCancellationToken = cancellationToken;
            if (cancelDuringDelete) cancellation.Cancel();
            return Task.FromException<Drop?>(failure);
        }

        public Task<Drop?> FindBySlugAsync(string slug, CancellationToken cancellationToken)
            => inner.FindBySlugAsync(slug, cancellationToken);
        public Task<DropSlugWriteResult> TryAddAsync(Drop drop, CancellationToken cancellationToken)
            => inner.TryAddAsync(drop, cancellationToken);
        public Task<DropSlugWriteResult> TryChangeSlugAsync(
            Drop drop, string newSlug, DateTime updatedAtUtc, CancellationToken cancellationToken)
            => inner.TryChangeSlugAsync(drop, newSlug, updatedAtUtc, cancellationToken);
        public Task UpdateAsync(Drop drop, CancellationToken cancellationToken)
            => inner.UpdateAsync(drop, cancellationToken);
        public Task UpdateAccessAsync(Drop drop, CancellationToken cancellationToken)
            => inner.UpdateAccessAsync(drop, cancellationToken);
    }

    private sealed class FixedTimeProvider(DateTimeOffset utcNow)
        : TimeProvider
    {
        public override DateTimeOffset GetUtcNow()
        {
            return utcNow;
        }
    }
}
