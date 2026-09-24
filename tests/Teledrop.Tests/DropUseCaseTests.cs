using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Tests;

public sealed class DropUseCaseTests
{
    private static readonly DateTimeOffset Now =
        new(2026, 7, 27, 1, 2, 3, TimeSpan.Zero);

    [Fact]
    public async Task DeleteRemovesDatabaseRowBeforeStoredFile()
    {
        var operations = new List<string>();
        var dependencies = new DropDependencies(operations);
        await dependencies.Store.TryAddAsync(CreateDrop("delete-me"), default);
        var useCases = dependencies.CreateDropUseCases();

        var result = await useCases.DeleteAsync(
            "delete-me",
            CancellationToken.None);

        Assert.Equal(DropCommandResult.Succeeded, result);
        Assert.Equal(["database", "file"], operations);
        Assert.Null(await dependencies.Store.NewScope().FindBySlugAsync("delete-me", default));
    }

    [Fact]
    public async Task MetadataAndPasswordRulesAreAppliedInCore()
    {
        var dependencies = new DropDependencies();
        var drop = CreateDrop("edit-me");
        await dependencies.Store.TryAddAsync(drop, default);
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

        drop = (await dependencies.Store.NewScope().FindBySlugAsync("edit-me", default))!;
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

        internal DropUseCases CreateDropUseCases()
        {
            return new DropUseCases(
                Store,
                new FakePasswordHasher(),
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
