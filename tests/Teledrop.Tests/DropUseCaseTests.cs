using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Tests;

public sealed class DropUseCaseTests
{
    private static readonly DateTimeOffset Now =
        new(2026, 7, 27, 1, 2, 3, TimeSpan.Zero);

    [Fact]
    public async Task CreatePrivateDropPersistsPrivateDropWithStoredFile()
    {
        var dependencies = new DropDependencies();
        var useCase = dependencies.CreatePrivateDrop();
        var storedFile = CreateStoredFile();

        var drop = await useCase.ExecuteAsync(
            storedFile,
            "title",
            "description",
            CancellationToken.None);

        Assert.True(drop.IsPrivate);
        Assert.Equal(storedFile.Location, drop.Location);
        Assert.Equal(storedFile.FileHash, drop.FileHash);
        Assert.Equal("title", drop.Title);
        Assert.Equal("description", drop.Description);
        Assert.Equal(Now.UtcDateTime, drop.CreatedAt);
        Assert.Same(drop, Assert.Single(dependencies.Store.Drops));
        Assert.Empty(dependencies.FileCleanup.DeletedLocations);
    }

    [Fact]
    public async Task CreatePrivateDropCleansFileWhenPersistenceFails()
    {
        var dependencies = new DropDependencies
        {
            Store = { ThrowOnAdd = true },
        };
        var useCase = dependencies.CreatePrivateDrop();
        var storedFile = CreateStoredFile();

        await Assert.ThrowsAsync<InvalidOperationException>(
            () => useCase.ExecuteAsync(
                storedFile,
                title: null,
                description: null,
                CancellationToken.None));

        Assert.Equal(
            [storedFile.Location],
            dependencies.FileCleanup.DeletedLocations);
    }

    [Fact]
    public async Task DeleteRemovesDatabaseRowBeforeStoredFile()
    {
        var operations = new List<string>();
        var dependencies = new DropDependencies(operations);
        dependencies.Store.Drops.Add(CreateDrop("delete-me"));
        var useCases = dependencies.CreateDropUseCases();

        var result = await useCases.DeleteAsync(
            "delete-me",
            CancellationToken.None);

        Assert.Equal(DropCommandResult.Succeeded, result);
        Assert.Equal(["database", "file"], operations);
        Assert.Empty(dependencies.Store.Drops);
    }

    [Fact]
    public async Task MetadataAndPasswordRulesAreAppliedInCore()
    {
        var dependencies = new DropDependencies();
        var drop = CreateDrop("edit-me");
        dependencies.Store.Drops.Add(drop);
        var useCases = dependencies.CreateDropUseCases();

        var metadataResult = await useCases.UpdateMetadataAsync(
            drop.Slug,
            "  title  ",
            "   ",
            CancellationToken.None);
        var emptyPasswordResult = await useCases.SetPasswordAsync(
            drop.Slug,
            string.Empty,
            CancellationToken.None);
        var passwordResult = await useCases.SetPasswordAsync(
            drop.Slug,
            "secret",
            CancellationToken.None);

        Assert.Equal(DropCommandResult.Succeeded, metadataResult);
        Assert.Equal("title", drop.Title);
        Assert.Null(drop.Description);
        Assert.Equal(
            SetDropPasswordResult.PasswordRequired,
            emptyPasswordResult);
        Assert.Equal(SetDropPasswordResult.Succeeded, passwordResult);
        Assert.Equal("hashed:secret", drop.DropPasswordHash);
        Assert.Equal(Now.UtcDateTime, drop.UpdatedAt);
    }

    [Fact]
    public async Task ChangeSlugNormalizesAndRejectsReservedOrExistingValues()
    {
        var dependencies = new DropDependencies();
        var drop = CreateDrop("original");
        dependencies.Store.Drops.Add(drop);
        dependencies.Store.Drops.Add(CreateDrop("already-used"));
        var useCases = dependencies.CreateDropUseCases();

        var reserved = await useCases.ChangeSlugAsync(
            drop.Slug,
            " API ",
            CancellationToken.None);
        var existing = await useCases.ChangeSlugAsync(
            drop.Slug,
            " Already-Used ",
            CancellationToken.None);
        var changed = await useCases.ChangeSlugAsync(
            drop.Slug,
            " New-Slug ",
            CancellationToken.None);

        Assert.Equal(ChangeDropSlugStatus.Invalid, reserved.Status);
        Assert.Equal(DropSlugValidationError.Reserved, reserved.ValidationError);
        Assert.Equal(ChangeDropSlugStatus.AlreadyExists, existing.Status);
        Assert.Equal(ChangeDropSlugStatus.Succeeded, changed.Status);
        Assert.Equal("new-slug", drop.Slug);
    }

    private static StoredDropFile CreateStoredFile()
    {
        return new StoredDropFile(
            "stored-location",
            "sample.bin",
            "application/octet-stream",
            42,
            "file-hash");
    }

    private static Drop CreateDrop(string slug)
    {
        return new Drop
        {
            Id = Guid.NewGuid(),
            Slug = slug,
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

        internal CreatePrivateDrop CreatePrivateDrop()
        {
            var factory = new PrivateDropFactory(
                new DropSlugGenerator(Store),
                new FixedTimeProvider(Now));
            return new CreatePrivateDrop(factory, Store, FileCleanup);
        }

        internal DropUseCases CreateDropUseCases()
        {
            return new DropUseCases(
                Store,
                Store,
                new FakePasswordHasher(),
                FileCleanup,
                new FixedTimeProvider(Now));
        }
    }

    private sealed class FakeDropStore(List<string> operations)
        : IDropCommandStore, IDropSlugIndex
    {
        internal List<Drop> Drops { get; } = [];

        internal bool ThrowOnAdd { get; set; }

        public Task<Drop?> FindBySlugAsync(
            string slug,
            CancellationToken cancellationToken)
        {
            return Task.FromResult(
                Drops.SingleOrDefault(drop => drop.Slug == slug));
        }

        public Task AddAsync(
            Drop drop,
            CancellationToken cancellationToken)
        {
            if (ThrowOnAdd)
            {
                throw new InvalidOperationException("Persistence failed.");
            }

            Drops.Add(drop);
            return Task.CompletedTask;
        }

        public Task UpdateAsync(
            Drop drop,
            CancellationToken cancellationToken)
        {
            return Task.CompletedTask;
        }

        public Task<Drop?> DeleteBySlugAsync(
            string slug,
            CancellationToken cancellationToken)
        {
            var drop = Drops.SingleOrDefault(candidate => candidate.Slug == slug);
            if (drop is not null)
            {
                Drops.Remove(drop);
                operations.Add("database");
            }

            return Task.FromResult(drop);
        }

        public Task<bool> ExistsAsync(
            string slug,
            Guid? excludingDropId,
            CancellationToken cancellationToken)
        {
            return Task.FromResult(
                Drops.Any(drop =>
                    drop.Slug == slug
                    && drop.Id != excludingDropId));
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

    private sealed class FakePasswordHasher : IDropPasswordHasher
    {
        public string Hash(string dropPassword)
        {
            return $"hashed:{dropPassword}";
        }
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
