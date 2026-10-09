using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Tests;

public sealed class DropIdMigrationTests
{
    private const string InitialMigration = "20260725230618_InitialCreate";

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task ImportedPasswordProtectedDropsCanBeUpdatedAndDeleted(bool delete)
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<TeledropDbContext>().UseSqlite(connection).Options;
        var imported = CreateDrop("imported");
        imported.Id = Guid.Parse("aabbccdd-1122-3344-5566-778899aabbcc");
        var native = CreateDrop("native");
        await using (var before = new TeledropDbContext(options))
        {
            await before.GetService<IMigrator>().MigrateAsync(InitialMigration);
            before.Drops.AddRange(imported, native);
            await before.SaveChangesAsync();
            await before.Database.ExecuteSqlInterpolatedAsync(
                $"UPDATE Drops SET Id = {imported.Id.ToString("D")} WHERE Slug = {imported.Slug}");
        }

        await using var after = new TeledropDbContext(options);
        await after.Database.MigrateAsync();
        var store = new EfDropStore(after);
        var drop = (await store.FindBySlugAsync(imported.Slug, default))!;
        Assert.Equal(imported.Id, drop.Id);
        Assert.Equal(imported.Slug, drop.Slug);
        Assert.Equal(imported.Location, drop.Location);
        Assert.Equal(imported.FileName, drop.FileName);
        Assert.Equal(imported.FileHash, drop.FileHash);
        Assert.Equal(imported.DropPasswordHash, drop.DropPasswordHash);
        Assert.Equal(DropAccessLevel.Password, drop.AccessLevel);
        Assert.Null(drop.UpdatedAt);
        Assert.Equal(native.Id, (await store.FindBySlugAsync(native.Slug, default))!.Id);

        if (delete)
        {
            Assert.NotNull(await store.DeleteBySlugAsync(imported.Slug, default));
            Assert.Null(await store.FindBySlugAsync(imported.Slug, default));
        }
        else
        {
            drop.DropPasswordHash = null;
            await store.UpdateAccessAsync(drop, default);
            after.ChangeTracker.Clear();
            var saved = (await store.FindBySlugAsync(imported.Slug, default))!;
            Assert.Equal(DropAccessLevel.Public, saved.AccessLevel);
        }
        Assert.NotNull(await store.FindBySlugAsync(native.Slug, default));
    }

    [Fact]
    public async Task CaseOnlyDuplicateIdsAbortMigrationWithoutDiscardingEitherDrop()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        var options = new DbContextOptionsBuilder<TeledropDbContext>().UseSqlite(connection).Options;
        await using var database = new TeledropDbContext(options);
        await database.GetService<IMigrator>().MigrateAsync(InitialMigration);
        var native = CreateDrop("native");
        native.Id = Guid.Parse("aabbccdd-1122-3344-5566-778899aabbcc");
        database.Drops.Add(native);
        await database.SaveChangesAsync();
        await database.Database.ExecuteSqlRawAsync("""
            INSERT INTO Drops (Id, Slug, IsPrivate, DropPasswordHash, IsFavorite,
                FileName, FileHash, FileSizeBytes, ContentType, Location, CreatedAt)
            SELECT lower(Id), 'imported', IsPrivate, DropPasswordHash, IsFavorite,
                FileName, FileHash, FileSizeBytes, ContentType, Location, CreatedAt
            FROM Drops WHERE Slug = 'native';
            """);

        var error = await Assert.ThrowsAsync<SqliteException>(() => database.Database.MigrateAsync());

        Assert.Equal(19, error.SqliteErrorCode);
        Assert.Equal(2, await database.Drops.CountAsync());
        Assert.Equal(InitialMigration, Assert.Single(await database.Database.GetAppliedMigrationsAsync()));
    }

    private static Drop CreateDrop(string slug) => new()
    {
        Id = Guid.NewGuid(), Slug = slug, IsPrivate = false,
        DropPasswordHash = "existing-password-hash", FileName = "existing.txt",
        FileHash = "existing-file-hash", ContentType = "text/plain", Location = slug + "-location",
    };
}
