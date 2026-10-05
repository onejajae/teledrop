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
    public async Task MetadataIsNormalizedInCore()
    {
        var dependencies = new DropDependencies();
        var drop = CreateDrop("edit-me");
        await dependencies.Store.TryAddAsync(drop, default);
        var useCases = dependencies.CreateDropUseCases();

        var result = await useCases.UpdateMetadataAsync(drop.Slug, "  description  ", default);

        drop = (await dependencies.Store.NewScope().FindBySlugAsync("edit-me", default))!;
        Assert.Equal(DropCommandResult.Succeeded, result);
        Assert.Equal("description", drop.Description);
        Assert.Equal(Now.UtcDateTime, drop.UpdatedAt);
    }

    [Fact]
    public async Task PasswordLevelRequiresANewPassword()
    {
        var dependencies = new DropDependencies();
        await dependencies.Store.TryAddAsync(CreateDrop("edit-me"), default);
        var useCases = dependencies.CreateDropUseCases();

        var empty = await useCases.SetAccessAsync("edit-me", DropAccessLevel.Password, "", default);
        var missing = await useCases.SetAccessAsync("edit-me", DropAccessLevel.Password, null, default);
        var stored = (await dependencies.Store.NewScope().FindBySlugAsync("edit-me", default))!;

        Assert.Equal(SetDropAccessResult.PasswordRequired, empty);
        Assert.Equal(SetDropAccessResult.PasswordRequired, missing);
        Assert.Equal(DropAccessLevel.Private, stored.AccessLevel);
        Assert.Null(stored.UpdatedAt);
    }

    [Theory]
    [InlineData(DropAccessLevel.Private, DropAccessLevel.Private, false, true, null)]
    [InlineData(DropAccessLevel.Private, DropAccessLevel.Password, true, false, "hashed:secret")]
    [InlineData(DropAccessLevel.Password, DropAccessLevel.Private, true, true, null)]
    [InlineData(DropAccessLevel.Password, DropAccessLevel.Public, true, false, null)]
    [InlineData(DropAccessLevel.Password, DropAccessLevel.Password, true, false, "hashed:secret")]
    [InlineData(DropAccessLevel.Public, DropAccessLevel.Private, true, true, null)]
    [InlineData(DropAccessLevel.Public, DropAccessLevel.Public, false, false, null)]
    public async Task AccessLevelSetsVisibilityAndPasswordTogether(
        DropAccessLevel from, DropAccessLevel to, bool touched, bool isPrivate, string? hash)
    {
        var dependencies = new DropDependencies();
        var drop = CreateDrop("access");
        drop.IsPrivate = from == DropAccessLevel.Private;
        drop.DropPasswordHash = from == DropAccessLevel.Password ? "hashed:old" : null;
        await dependencies.Store.TryAddAsync(drop, default);
        var useCases = dependencies.CreateDropUseCases();

        var result = await useCases.SetAccessAsync("access", to, "secret", default);

        var stored = (await dependencies.Store.NewScope().FindBySlugAsync("access", default))!;
        Assert.Equal(SetDropAccessResult.Succeeded, result);
        Assert.Equal(to, stored.AccessLevel);
        Assert.Equal(isPrivate, stored.IsPrivate);
        Assert.Equal(hash, stored.DropPasswordHash);
        Assert.Equal(touched ? Now.UtcDateTime : (DateTime?)null, stored.UpdatedAt);
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
