using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Infrastructure.Tests;

public sealed class DropListTests
{
    [Theory]
    [InlineData("%")]
    [InlineData("_")]
    [InlineData("\\")]
    [InlineData("\\%_")]
    public async Task SearchTreatsLikeMetacharactersAsLiteralText(string literal)
    {
        using var fixture = new ListFixture();
        fixture.Database.AddRange(
            CreateDrop(1, "filename", $"before{literal}after"),
            CreateDrop(2, "description", "other", description: $"before{literal}after"),
            CreateDrop(3, "wildcard", "beforeXafter", description: "before-anything-after"),
            CreateDrop(4, "unrelated", "unrelated"));
        await fixture.Database.SaveChangesAsync();
        var list = new DropList(fixture.Database);

        await list.LoadAsync($"  {literal}  ", "name", "asc", 1, default);

        Assert.Equal(literal, list.Search);
        Assert.Equal(["description", "filename"], list.Drops.Select(drop => drop.Slug).Order());
        Assert.Equal(2, list.TotalDropCount);
    }

    [Theory]
    [InlineData("created_at", "asc", "beta,alpha,charlie")]
    [InlineData("created_at", "desc", "charlie,alpha,beta")]
    [InlineData("name", "asc", "alpha,beta,charlie")]
    [InlineData("name", "desc", "charlie,beta,alpha")]
    [InlineData("size", "asc", "beta,charlie,alpha")]
    [InlineData("size", "desc", "alpha,charlie,beta")]
    public async Task EachSortDirectionReturnsTheCompleteExpectedOrder(string sort, string direction, string expected)
    {
        using var fixture = new ListFixture();
        await SeedDistinctSortValuesAsync(fixture);
        var list = new DropList(fixture.Database);

        await list.LoadAsync(null, sort, direction, 1, default);

        Assert.Equal(expected.Split(','), list.Drops.Select(drop => drop.Slug));
        Assert.Equal(sort, list.Sort);
        Assert.Equal(direction, list.Direction);
        Assert.Equal(3, list.TotalDropCount);
        Assert.Equal(1, list.TotalPages);
    }

    [Theory]
    [InlineData("created_at", "asc")]
    [InlineData("created_at", "desc")]
    [InlineData("name", "asc")]
    [InlineData("name", "desc")]
    [InlineData("size", "asc")]
    [InlineData("size", "desc")]
    public async Task TiedSortValuesUseAscendingIdsAcrossPageBoundaries(string sort, string direction)
    {
        using var fixture = new ListFixture();
        // Insertion order is deliberately opposite to the stable secondary order.
        fixture.Database.AddRange(Enumerable.Range(1, 23).Reverse()
            .Select(index => CreateDrop(index, $"drop-{index:D2}", "same-name")));
        await fixture.Database.SaveChangesAsync();
        var list = new DropList(fixture.Database);

        await list.LoadAsync(null, sort, direction, 1, default);
        var first = list.Drops.Select(drop => drop.Slug).ToArray();
        await list.LoadAsync(null, sort, direction, 2, default);

        Assert.Equal(Enumerable.Range(1, 20).Select(index => $"drop-{index:D2}"), first);
        Assert.Equal(["drop-21", "drop-22", "drop-23"], list.Drops.Select(drop => drop.Slug));
    }

    [Theory]
    [InlineData(int.MinValue, 1, 1, 20)]
    [InlineData(int.MaxValue, 2, 21, 3)]
    public async Task OutOfRangePagesAreClampedWithoutLosingFiles(int requestedPage, int page, int first, int count)
    {
        using var fixture = new ListFixture();
        fixture.Database.AddRange(Enumerable.Range(1, 23)
            .Select(index => CreateDrop(index, $"drop-{index:D2}", $"file-{index:D2}")));
        await fixture.Database.SaveChangesAsync();
        var list = new DropList(fixture.Database);

        await list.LoadAsync(null, "name", "asc", requestedPage, default);

        Assert.Equal(page, list.CurrentPage);
        Assert.Equal(2, list.TotalPages);
        Assert.Equal(23, list.TotalDropCount);
        Assert.Equal(Enumerable.Range(first, count).Select(index => $"drop-{index:D2}"),
            list.Drops.Select(drop => drop.Slug));
    }

    [Theory]
    [InlineData(null, null, null)]
    [InlineData(" \t ", "unknown", "backwards")]
    public async Task EmptySearchAndInvalidSortUseTheDefaultOrder(string? search, string? sort, string? direction)
    {
        using var fixture = new ListFixture();
        await SeedDistinctSortValuesAsync(fixture);
        var list = new DropList(fixture.Database);

        await list.LoadAsync(search, sort, direction, 1, default);

        Assert.Null(list.Search);
        Assert.Equal("created_at", list.Sort);
        Assert.Equal("desc", list.Direction);
        Assert.Equal(["charlie", "alpha", "beta"], list.Drops.Select(drop => drop.Slug));
    }

    [Fact]
    public async Task EmptySearchResultsResetPageAndCountWithoutReturningOtherFiles()
    {
        using var fixture = new ListFixture();
        await SeedDistinctSortValuesAsync(fixture);
        var list = new DropList(fixture.Database);

        await list.LoadAsync("no-match", "size", "asc", int.MaxValue, default);

        Assert.Empty(list.Drops);
        Assert.Equal(0, list.TotalDropCount);
        Assert.Equal(1, list.TotalPages);
        Assert.Equal(1, list.CurrentPage);
        Assert.Equal("no-match", list.Search);
    }

    private static async Task SeedDistinctSortValuesAsync(ListFixture fixture)
    {
        fixture.Database.AddRange(
            CreateDrop(3, "alpha", "alpha", bytes: 300, day: 2),
            CreateDrop(2, "beta", "beta", bytes: 100, day: 1),
            CreateDrop(1, "charlie", "charlie", bytes: 200, day: 3));
        await fixture.Database.SaveChangesAsync();
    }

    private static Drop CreateDrop(int id, string slug, string fileName, string? description = null,
        long bytes = 1, int day = 1) => new()
    {
        Id = Guid.Parse($"00000000-0000-0000-0000-{id:D12}"),
        Slug = slug, FileName = fileName, Description = description,
        FileSizeBytes = bytes, CreatedAt = new DateTime(2026, 1, day, 0, 0, 0, DateTimeKind.Utc),
        FileHash = "hash", ContentType = "application/octet-stream", Location = slug,
    };

    private sealed class ListFixture : IDisposable
    {
        private readonly SqliteConnection connection = new("Data Source=:memory:");
        internal TeledropDbContext Database { get; }

        internal ListFixture()
        {
            connection.Open();
            Database = new(new DbContextOptionsBuilder<TeledropDbContext>().UseSqlite(connection).Options);
            Database.Database.EnsureCreated();
        }

        public void Dispose()
        {
            Database.Dispose();
            connection.Dispose();
        }
    }
}
