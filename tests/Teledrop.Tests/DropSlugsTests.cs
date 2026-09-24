using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Tests;

public sealed class DropSlugsTests
{
    private static readonly DateTimeOffset Now = new(2026, 9, 24, 12, 0, 0, TimeSpan.Zero);
    private static readonly StoredDropFile File = new(
        "stored-location", "sample.bin", "application/octet-stream", 42, "file-hash");

    [Theory]
    [InlineData(0)]
    [InlineData(2)]
    [InlineData(12)]
    [InlineData(23)]
    public async Task CreationRetriesCollisionsWithoutReplacingTheDropOrCleaningItsFile(int collisions)
    {
        var cleanup = new RecordingCleanup();
        var store = new ScriptedStore { Collisions = collisions };
        store.BeforeAdd = () => Assert.Empty(cleanup.Deleted);
        var slugs = new DropSlugs(store, cleanup, new AdvancingTimeProvider());

        var drop = await slugs.CreatePrivateAsync(File, " title ", "description", default);

        Assert.Equal(collisions + 1, store.Attempts.Count);
        Assert.All(store.Attempts, attempt =>
        {
            Assert.Equal(drop.Id, attempt.Id);
            Assert.Equal(Now.UtcDateTime, attempt.CreatedAt);
            Assert.Equal(File.Location, attempt.Location);
        });
        AssertCandidateShapes(store.Attempts);
        Assert.True(drop.IsPrivate);
        Assert.Equal(" title ", drop.Title);
        Assert.Equal("description", drop.Description);
        Assert.Equal(File.FileName, drop.FileName);
        Assert.Equal(File.FileHash, drop.FileHash);
        Assert.Equal(File.FileSizeBytes, drop.FileSizeBytes);
        Assert.Equal(File.ContentType, drop.ContentType);
        var saved = await store.Inner.NewScope().FindBySlugAsync(drop.Slug, default);
        Assert.NotNull(saved);
        Assert.Equal(drop.Id, saved.Id);
        Assert.Equal(File.Location, saved.Location);
        Assert.Empty(cleanup.Deleted);
    }

    [Fact]
    public async Task ExhaustionStopsAfterTwentyFourCandidatesAndCleansOnce()
    {
        var cleanup = new RecordingCleanup();
        var store = new ScriptedStore { Collisions = 24 };
        store.BeforeAdd = () => Assert.Empty(cleanup.Deleted);
        var slugs = new DropSlugs(store, cleanup, new AdvancingTimeProvider());

        await Assert.ThrowsAsync<InvalidOperationException>(
            () => slugs.CreatePrivateAsync(File, null, null, default));

        Assert.Equal(24, store.Attempts.Count);
        AssertCandidateShapes(store.Attempts);
        Assert.Equal([File.Location], cleanup.Deleted);
        foreach (var attempt in store.Attempts)
            Assert.Null(await store.Inner.NewScope().FindBySlugAsync(attempt.Slug, default));
    }

    [Fact]
    public async Task OtherStorageFailuresStopRetriesAndKeepTheirOriginalException()
    {
        var failure = new IOException("Storage failure.");
        var cleanup = new RecordingCleanup();
        var store = new ScriptedStore { Collisions = 2, Failure = failure };
        var slugs = new DropSlugs(store, cleanup, new AdvancingTimeProvider());

        var thrown = await Assert.ThrowsAsync<IOException>(
            () => slugs.CreatePrivateAsync(File, null, null, default));

        Assert.Same(failure, thrown);
        Assert.Equal(3, store.Attempts.Count);
        Assert.Equal([File.Location], cleanup.Deleted);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task CancellationBeforeOrBetweenAttemptsCleansOnce(bool beforeFirstAttempt)
    {
        using var cancellation = new CancellationTokenSource();
        var cleanup = new RecordingCleanup();
        var store = new ScriptedStore { Collisions = 24, BeforeAdd = cancellation.Cancel };
        if (beforeFirstAttempt) cancellation.Cancel();
        var slugs = new DropSlugs(store, cleanup, new AdvancingTimeProvider());

        await Assert.ThrowsAnyAsync<OperationCanceledException>(
            () => slugs.CreatePrivateAsync(File, null, null, cancellation.Token));

        Assert.Equal(beforeFirstAttempt ? 0 : 1, store.Attempts.Count);
        Assert.Equal([File.Location], cleanup.Deleted);
    }

    [Fact]
    public async Task CancellationAfterSuccessfulCommitDoesNotDeleteTheStoredFile()
    {
        using var cancellation = new CancellationTokenSource();
        var cleanup = new RecordingCleanup();
        var store = new ScriptedStore { AfterCommit = cancellation.Cancel };
        var slugs = new DropSlugs(store, cleanup, new AdvancingTimeProvider());

        var drop = await slugs.CreatePrivateAsync(File, null, null, cancellation.Token);

        Assert.True(cancellation.IsCancellationRequested);
        Assert.NotNull(await store.Inner.NewScope().FindBySlugAsync(drop.Slug, default));
        Assert.Empty(cleanup.Deleted);
    }

    [Theory]
    [InlineData(null, "", DropSlugValidationError.InvalidFormat)]
    [InlineData("INVALID!", "invalid!", DropSlugValidationError.InvalidFormat)]
    [InlineData(" API ", "api", DropSlugValidationError.Reserved)]
    [InlineData("-name", "-name", DropSlugValidationError.InvalidFormat)]
    public async Task InvalidCustomSlugsDoNotChangeTheDrop(
        string? requested, string normalized, DropSlugValidationError error)
    {
        var store = new FakeDropStore();
        var drop = CreateDrop("source");
        await store.TryAddAsync(drop, default);
        var slugs = new DropSlugs(store, new RecordingCleanup(), new AdvancingTimeProvider());

        var result = await slugs.ChangeAsync("source", requested, default);

        Assert.Equal(ChangeDropSlugStatus.Invalid, result.Status);
        Assert.Equal(normalized, result.NormalizedSlug);
        Assert.Equal(error, result.ValidationError);
        Assert.Equal("source", drop.Slug);
        Assert.Null(drop.UpdatedAt);
    }

    [Fact]
    public async Task CustomConflictKeepsTheOldSlugAndCanBeRetriedInTheSameScope()
    {
        var store = new FakeDropStore();
        var drop = CreateDrop("source");
        await store.TryAddAsync(drop, default);
        await store.TryAddAsync(CreateDrop("taken"), default);
        var slugs = new DropSlugs(store, new RecordingCleanup(), new AdvancingTimeProvider());

        var conflict = await slugs.ChangeAsync("source", " TAKEN ", default);
        Assert.Equal(ChangeDropSlugStatus.AlreadyExists, conflict.Status);
        Assert.Equal("taken", conflict.NormalizedSlug);
        Assert.Equal("source", drop.Slug);
        Assert.Null(drop.UpdatedAt);

        var changed = await slugs.ChangeAsync("source", " New-Slug ", default);
        Assert.Equal(ChangeDropSlugStatus.Succeeded, changed.Status);
        Assert.Equal("new-slug", changed.NormalizedSlug);
        Assert.Null(await store.NewScope().FindBySlugAsync("source", default));
        Assert.Equal(drop.Id, (await store.NewScope().FindBySlugAsync("new-slug", default))!.Id);
    }

    [Fact]
    public async Task SameNormalizedSlugDoesNotTouchTimeOrCommitOtherPendingChanges()
    {
        var store = new FakeDropStore();
        var drop = CreateDrop("source");
        drop.UpdatedAt = Now.AddDays(-1).UtcDateTime;
        await store.TryAddAsync(drop, default);
        drop.Title = "Pending";
        var slugs = new DropSlugs(store, new RecordingCleanup(), new AdvancingTimeProvider());

        var result = await slugs.ChangeAsync("source", " SOURCE ", default);

        Assert.Equal(ChangeDropSlugStatus.Succeeded, result.Status);
        var saved = (await store.NewScope().FindBySlugAsync("source", default))!;
        Assert.Equal(Now.AddDays(-1).UtcDateTime, saved.UpdatedAt);
        Assert.Null(saved.Title);
        Assert.Equal("Pending", drop.Title);
    }

    [Theory]
    [InlineData("")]
    [InlineData("missing")]
    public async Task MissingDropReturnsNotFoundBeforeValidatingTheRequestedSlug(string currentSlug)
    {
        var slugs = new DropSlugs(new FakeDropStore(), new RecordingCleanup(), new AdvancingTimeProvider());

        var result = await slugs.ChangeAsync(currentSlug, "!", default);

        Assert.Equal(ChangeDropSlugStatus.NotFound, result.Status);
    }

    private static void AssertCandidateShapes(IReadOnlyList<Attempt> attempts)
    {
        for (var index = 0; index < attempts.Count; index++)
        {
            Assert.Matches(index < 12 ? "^[a-z]+-[a-z]+$" : "^[a-z]+-[a-z]+-[0-9a-f]{8}$", attempts[index].Slug);
            Assert.InRange(attempts[index].Slug.Length, 1, 64);
        }
    }

    private static Drop CreateDrop(string slug) => new()
    {
        Id = Guid.NewGuid(), Slug = slug, FileName = File.FileName,
        ContentType = File.ContentType, FileHash = File.FileHash, Location = File.Location,
    };

    private sealed record Attempt(Guid Id, string Slug, DateTime CreatedAt, string Location);

    private sealed class ScriptedStore : IDropCommandStore
    {
        internal FakeDropStore Inner { get; } = new();
        internal List<Attempt> Attempts { get; } = [];
        internal int Collisions { get; init; }
        internal Exception? Failure { get; init; }
        internal Action? BeforeAdd { get; set; }
        internal Action? AfterCommit { get; init; }

        public async Task<DropSlugWriteResult> TryAddAsync(Drop drop, CancellationToken cancellationToken)
        {
            Attempts.Add(new Attempt(drop.Id, drop.Slug, drop.CreatedAt, drop.Location));
            BeforeAdd?.Invoke();
            if (Attempts.Count <= Collisions) return DropSlugWriteResult.SlugConflict;
            if (Failure is not null) throw Failure;
            var result = await Inner.TryAddAsync(drop, cancellationToken);
            if (result == DropSlugWriteResult.Succeeded) AfterCommit?.Invoke();
            return result;
        }

        public Task<Drop?> FindBySlugAsync(string slug, CancellationToken cancellationToken)
            => Inner.FindBySlugAsync(slug, cancellationToken);
        public Task<DropSlugWriteResult> TryChangeSlugAsync(
            Drop drop, string newSlug, DateTime updatedAtUtc, CancellationToken cancellationToken)
            => Inner.TryChangeSlugAsync(drop, newSlug, updatedAtUtc, cancellationToken);
        public Task UpdateAsync(Drop drop, CancellationToken cancellationToken)
            => Inner.UpdateAsync(drop, cancellationToken);
        public Task<Drop?> DeleteBySlugAsync(string slug, CancellationToken cancellationToken)
            => Inner.DeleteBySlugAsync(slug, cancellationToken);
    }

    private sealed class RecordingCleanup : IStoredDropFileCleanup
    {
        internal List<string> Deleted { get; } = [];
        public void TryDelete(string location) => Deleted.Add(location);
    }

    private sealed class AdvancingTimeProvider : TimeProvider
    {
        private DateTimeOffset now = Now;
        public override DateTimeOffset GetUtcNow()
        {
            var result = now;
            now = now.AddSeconds(1);
            return result;
        }
    }
}
