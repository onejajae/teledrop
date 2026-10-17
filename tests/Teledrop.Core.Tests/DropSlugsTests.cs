using Teledrop.Features.Drops;
using Teledrop.Testing;
using Xunit;

namespace Teledrop.Core.Tests;

public sealed class DropSlugsTests
{
    private static readonly DateTimeOffset Now = new(2026, 9, 24, 12, 0, 0, TimeSpan.Zero);
    private static readonly StoredDropFile File = new(
        "stored-location", "sample.bin", "application/octet-stream", 42, "file-hash");

    [Theory]
    [InlineData(0)]
    [InlineData(12)]
    [InlineData(23)]
    public async Task CreationRetriesCollisionsWithoutReplacingTheDropOrCleaningItsFile(int collisions)
    {
        var cleanup = new RecordingCleanup();
        var store = new ScriptedStore { Collisions = collisions };
        store.BeforeAdd = () => Assert.Empty(cleanup.Deleted);
        var slugs = new DropSlugs(store, cleanup, new AdvancingTimeProvider());
        using var cancellation = new CancellationTokenSource();

        var drop = await slugs.CreatePrivateAsync(File, "description", cancellation.Token);

        Assert.Equal(collisions + 1, store.Attempts.Count);
        Assert.All(store.Attempts, attempt =>
        {
            Assert.Equal(drop.Id, attempt.Id);
            Assert.Equal(Now.UtcDateTime, attempt.CreatedAt);
            Assert.Equal(File.Location, attempt.Location);
            Assert.Equal(cancellation.Token, attempt.CancellationToken);
        });
        AssertCandidateShapes(store.Attempts);
        Assert.True(drop.IsPrivate);
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
            () => slugs.CreatePrivateAsync(File, null, default));

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
            () => slugs.CreatePrivateAsync(File, null, default));

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
            () => slugs.CreatePrivateAsync(File, null, cancellation.Token));

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

        var drop = await slugs.CreatePrivateAsync(File, null, cancellation.Token);

        Assert.True(cancellation.IsCancellationRequested);
        Assert.NotNull(await store.Inner.NewScope().FindBySlugAsync(drop.Slug, default));
        Assert.Empty(cleanup.Deleted);
    }

    [Fact]
    public async Task CancellationWhileCreationIsWaitingForStorageCleansTheFileOnce()
    {
        using var cancellation = new CancellationTokenSource();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var cleanup = new RecordingCleanup();
        var store = new ScriptedStore
        {
            BeforeCommit = token =>
            {
                entered.SetResult();
                return release.Task.WaitAsync(token);
            },
        };
        var slugs = new DropSlugs(store, cleanup, new AdvancingTimeProvider());
        var creation = slugs.CreatePrivateAsync(File, "description", cancellation.Token);

        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            var attempt = Assert.Single(store.Attempts);
            Assert.Equal(cancellation.Token, attempt.CancellationToken);
            Assert.Empty(cleanup.Deleted);
            cancellation.Cancel();

            var error = await Assert.ThrowsAnyAsync<OperationCanceledException>(
                () => creation.WaitAsync(TimeSpan.FromSeconds(5)));

            Assert.Equal(cancellation.Token, error.CancellationToken);
            Assert.Single(store.Attempts);
            Assert.Equal([File.Location], cleanup.Deleted);
            Assert.Null(await store.Inner.NewScope().FindBySlugAsync(attempt.Slug, default));
        }
        finally
        {
            release.TrySetResult();
            await Record.ExceptionAsync(() => creation);
        }
    }

    [Theory]
    [InlineData(null, "", DropSlugValidationError.InvalidFormat)]
    [InlineData("   ", "", DropSlugValidationError.InvalidFormat)]
    [InlineData("한글", "한글", DropSlugValidationError.InvalidFormat)]
    [InlineData("two words", "two words", DropSlugValidationError.InvalidFormat)]
    [InlineData("INVALID!", "invalid!", DropSlugValidationError.InvalidFormat)]
    [InlineData("-name", "-name", DropSlugValidationError.InvalidFormat)]
    public async Task InvalidCustomSlugsDoNotChangeTheDrop(
        string? requested, string normalized, DropSlugValidationError error)
    {
        var store = new FakeDropStore();
        var drop = CreateDrop("source");
        var originalTime = Now.AddDays(-1).UtcDateTime;
        drop.UpdatedAt = originalTime;
        await store.TryAddAsync(drop, default);
        drop.Description = "Pending description";
        var cleanup = new RecordingCleanup();
        var slugs = new DropSlugs(store, cleanup, new AdvancingTimeProvider());

        var result = await slugs.ChangeAsync("source", requested, default);

        Assert.Equal(ChangeDropSlugStatus.Invalid, result.Status);
        Assert.Equal(normalized, result.NormalizedSlug);
        Assert.Equal(error, result.ValidationError);
        Assert.Equal("source", drop.Slug);
        Assert.Equal(originalTime, drop.UpdatedAt);
        Assert.Equal("Pending description", drop.Description);
        var stored = (await store.NewScope().FindBySlugAsync("source", default))!;
        Assert.Equal(drop.Id, stored.Id);
        Assert.Equal(originalTime, stored.UpdatedAt);
        Assert.Null(stored.Description);
        Assert.Empty(cleanup.Deleted);
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
        drop.Description = "Pending";
        var slugs = new DropSlugs(store, new RecordingCleanup(), new AdvancingTimeProvider());

        var result = await slugs.ChangeAsync("source", " SOURCE ", default);

        Assert.Equal(ChangeDropSlugStatus.Succeeded, result.Status);
        var saved = (await store.NewScope().FindBySlugAsync("source", default))!;
        Assert.Equal(Now.AddDays(-1).UtcDateTime, saved.UpdatedAt);
        Assert.Null(saved.Description);
        Assert.Equal("Pending", drop.Description);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task RenameStorageFailureOrCancellationPropagatesWithoutCleanupOrCommit(
        bool cancelDuringWrite)
    {
        using var cancellation = new CancellationTokenSource();
        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var failure = new IOException("Rename storage failed.");
        var cleanup = new RecordingCleanup();
        var store = new ScriptedStore
        {
            BeforeRename = token =>
            {
                entered.SetResult();
                return release.Task.WaitAsync(token);
            },
        };
        var drop = CreateDrop("source");
        var originalTime = Now.AddDays(-1).UtcDateTime;
        drop.UpdatedAt = originalTime;
        await store.Inner.TryAddAsync(drop, default);
        drop.Description = "Pending description";
        var slugs = new DropSlugs(store, cleanup, new AdvancingTimeProvider());
        var rename = slugs.ChangeAsync("source", " New-Slug ", cancellation.Token);

        try
        {
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(5));
            Assert.Equal([cancellation.Token], store.FindTokens);
            var attempt = Assert.Single(store.Renames);
            Assert.Equal(cancellation.Token, attempt.CancellationToken);
            Assert.Equal("source", attempt.OriginalSlug);
            Assert.Equal(originalTime, attempt.OriginalUpdatedAt);
            Assert.Equal("new-slug", attempt.RequestedSlug);
            Assert.Equal(Now.UtcDateTime, attempt.RequestedUpdatedAt);
            if (cancelDuringWrite) cancellation.Cancel();
            else release.SetException(failure);

            var error = await Record.ExceptionAsync(() => rename.WaitAsync(TimeSpan.FromSeconds(5)));

            if (cancelDuringWrite)
                Assert.Equal(cancellation.Token,
                    Assert.IsAssignableFrom<OperationCanceledException>(error).CancellationToken);
            else
                Assert.Same(failure, error);
            Assert.Empty(cleanup.Deleted);
            Assert.Equal("source", drop.Slug);
            Assert.Equal(originalTime, drop.UpdatedAt);
            Assert.Equal("Pending description", drop.Description);
            var saved = (await store.Inner.NewScope().FindBySlugAsync("source", default))!;
            Assert.Equal(drop.Id, saved.Id);
            Assert.Equal(originalTime, saved.UpdatedAt);
            Assert.Null(saved.Description);
            Assert.Null(await store.Inner.NewScope().FindBySlugAsync("new-slug", default));
        }
        finally
        {
            release.TrySetResult();
            await Record.ExceptionAsync(() => rename);
        }
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("missing")]
    public async Task MissingDropReturnsNotFoundBeforeValidatingTheRequestedSlug(string currentSlug)
    {
        var slugs = new DropSlugs(new FakeDropStore(), new RecordingCleanup(), new AdvancingTimeProvider());

        var result = await slugs.ChangeAsync(currentSlug, "!", default);

        Assert.Equal(ChangeDropSlugStatus.NotFound, result.Status);
    }

    [Theory]
    [InlineData(1, ChangeDropSlugStatus.Succeeded)]
    [InlineData(64, ChangeDropSlugStatus.Succeeded)]
    [InlineData(65, ChangeDropSlugStatus.Invalid)]
    public async Task CustomSlugLengthBoundaryIsAppliedAfterNormalization(
        int length, ChangeDropSlugStatus expected)
    {
        var store = new FakeDropStore();
        var drop = CreateDrop("source");
        await store.TryAddAsync(drop, default);
        var slugs = new DropSlugs(store, new RecordingCleanup(), new AdvancingTimeProvider());
        var normalized = new string('a', length);

        var result = await slugs.ChangeAsync("source", $"  {normalized.ToUpperInvariant()}  ", default);

        Assert.Equal(expected, result.Status);
        Assert.Equal(normalized, result.NormalizedSlug);
        var saved = await store.NewScope().FindBySlugAsync(
            expected == ChangeDropSlugStatus.Succeeded ? normalized : "source", default);
        Assert.NotNull(saved);
        Assert.Equal(drop.Id, saved.Id);
        Assert.Equal(expected == ChangeDropSlugStatus.Succeeded ? Now.UtcDateTime : (DateTime?)null,
            saved.UpdatedAt);
        if (expected == ChangeDropSlugStatus.Succeeded)
        {
            Assert.Null(await store.NewScope().FindBySlugAsync("source", default));
            Assert.Equal(DropSlugValidationError.None, result.ValidationError);
        }
        else
        {
            Assert.Null(await store.NewScope().FindBySlugAsync(normalized, default));
            Assert.Equal(DropSlugValidationError.InvalidFormat, result.ValidationError);
        }
    }

    [Theory]
    [InlineData("api")]
    [InlineData("css")]
    [InlineData("d")]
    [InlineData("drops")]
    [InlineData("error")]
    [InlineData("index")]
    [InlineData("js")]
    [InlineData("login")]
    [InlineData("logout")]
    [InlineData("static")]
    [InlineData("upload")]
    public async Task ReservedRoutesCannotReplaceADropSlug(string reserved)
    {
        var store = new FakeDropStore();
        var drop = CreateDrop("source");
        await store.TryAddAsync(drop, default);
        var slugs = new DropSlugs(store, new RecordingCleanup(), new AdvancingTimeProvider());

        var result = await slugs.ChangeAsync("source", $" {reserved.ToUpperInvariant()} ", default);

        Assert.Equal(ChangeDropSlugStatus.Invalid, result.Status);
        Assert.Equal(DropSlugValidationError.Reserved, result.ValidationError);
        Assert.Equal(reserved, result.NormalizedSlug);
        Assert.Equal("source", drop.Slug);
        Assert.Null(drop.UpdatedAt);
        Assert.Equal(drop.Id, (await store.NewScope().FindBySlugAsync("source", default))!.Id);
        Assert.Null(await store.NewScope().FindBySlugAsync(reserved, default));
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

    private sealed record Attempt(
        Guid Id, string Slug, DateTime CreatedAt, string Location, CancellationToken CancellationToken);

    private sealed record RenameAttempt(
        string OriginalSlug, DateTime? OriginalUpdatedAt,
        string RequestedSlug, DateTime RequestedUpdatedAt, CancellationToken CancellationToken);

    private sealed class ScriptedStore : IDropCommandStore
    {
        internal FakeDropStore Inner { get; } = new();
        internal List<Attempt> Attempts { get; } = [];
        internal List<CancellationToken> FindTokens { get; } = [];
        internal List<RenameAttempt> Renames { get; } = [];
        internal int Collisions { get; init; }
        internal Exception? Failure { get; init; }
        internal Action? BeforeAdd { get; set; }
        internal Action? AfterCommit { get; init; }
        internal Func<CancellationToken, Task>? BeforeCommit { get; init; }
        internal Func<CancellationToken, Task>? BeforeRename { get; init; }

        public async Task<DropSlugWriteResult> TryAddAsync(Drop drop, CancellationToken cancellationToken)
        {
            Attempts.Add(new Attempt(drop.Id, drop.Slug, drop.CreatedAt, drop.Location, cancellationToken));
            BeforeAdd?.Invoke();
            if (Attempts.Count <= Collisions) return DropSlugWriteResult.SlugConflict;
            if (Failure is not null) throw Failure;
            if (BeforeCommit is not null) await BeforeCommit(cancellationToken);
            var result = await Inner.TryAddAsync(drop, cancellationToken);
            if (result == DropSlugWriteResult.Succeeded) AfterCommit?.Invoke();
            return result;
        }

        public Task<Drop?> FindBySlugAsync(string slug, CancellationToken cancellationToken)
        {
            FindTokens.Add(cancellationToken);
            return Inner.FindBySlugAsync(slug, cancellationToken);
        }

        public async Task<DropSlugWriteResult> TryChangeSlugAsync(
            Drop drop, string newSlug, DateTime updatedAtUtc, CancellationToken cancellationToken)
        {
            Renames.Add(new RenameAttempt(drop.Slug, drop.UpdatedAt, newSlug, updatedAtUtc, cancellationToken));
            if (BeforeRename is not null) await BeforeRename(cancellationToken);
            return await Inner.TryChangeSlugAsync(drop, newSlug, updatedAtUtc, cancellationToken);
        }
        public Task UpdateAsync(Drop drop, CancellationToken cancellationToken)
            => Inner.UpdateAsync(drop, cancellationToken);
        public Task UpdateAccessAsync(Drop drop, CancellationToken cancellationToken)
            => Inner.UpdateAccessAsync(drop, cancellationToken);
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
