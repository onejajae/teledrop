using Microsoft.EntityFrameworkCore;
using Teledrop.Data;

namespace Teledrop.Features.Drops;

public sealed class DropList(TeledropDbContext dbContext)
{
    public const int PageSize = 20;
    private const string DefaultSort = "created_at";
    private const string DefaultDirection = "desc";
    private const string LikeEscapeCharacter = "\\";

    public string? CurrentSlug { get; set; }

    public IReadOnlyList<Drop> Drops { get; private set; } = [];

    public string? Search { get; private set; }

    public string Sort { get; private set; } = DefaultSort;

    public string Direction { get; private set; } = DefaultDirection;

    public int CurrentPage { get; private set; } = 1;

    public int TotalPages { get; private set; } = 1;

    public int TotalDropCount { get; private set; }

    public async Task LoadAsync(string? search, string? sort, string? direction,
        int pageNumber, CancellationToken cancellationToken)
    {
        Search = NormalizeSearch(search);
        Sort = NormalizeSort(sort);
        Direction = NormalizeDirection(direction);
        await LoadDropsAsync(pageNumber, cancellationToken);
    }

    private async Task LoadDropsAsync(
        int pageNumber,
        CancellationToken cancellationToken)
    {
        IQueryable<Drop> dropsQuery = dbContext.Drops.AsNoTracking();

        if (Search is not null)
        {
            var likePattern = CreateLikePattern(Search);
            dropsQuery = dropsQuery.Where(
                drop =>
                    EF.Functions.Like(
                        drop.Title ?? string.Empty,
                        likePattern,
                        LikeEscapeCharacter)
                    || EF.Functions.Like(
                        drop.FileName,
                        likePattern,
                        LikeEscapeCharacter));
        }

        TotalDropCount = await dropsQuery.CountAsync(cancellationToken);
        TotalPages = Math.Max(
            1,
            (TotalDropCount + PageSize - 1) / PageSize);
        CurrentPage = Math.Clamp(pageNumber, 1, TotalPages);

        var orderedDrops = (Sort, Direction) switch
        {
            ("created_at", "asc") => dropsQuery
                .OrderBy(drop => drop.CreatedAt)
                .ThenBy(drop => drop.Id),
            ("title", "asc") => dropsQuery
                .OrderBy(drop => drop.Title ?? drop.FileName)
                .ThenBy(drop => drop.Id),
            ("title", "desc") => dropsQuery
                .OrderByDescending(drop => drop.Title ?? drop.FileName)
                .ThenBy(drop => drop.Id),
            ("size", "asc") => dropsQuery
                .OrderBy(drop => drop.FileSizeBytes)
                .ThenBy(drop => drop.Id),
            ("size", "desc") => dropsQuery
                .OrderByDescending(drop => drop.FileSizeBytes)
                .ThenBy(drop => drop.Id),
            _ => dropsQuery
                .OrderByDescending(drop => drop.CreatedAt)
                .ThenBy(drop => drop.Id),
        };

        Drops = await orderedDrops
            .Skip((CurrentPage - 1) * PageSize)
            .Take(PageSize)
            .ToListAsync(cancellationToken);
    }

    private static string? NormalizeSearch(string? search)
    {
        return string.IsNullOrWhiteSpace(search)
            ? null
            : search.Trim();
    }

    private static string NormalizeSort(string? sort)
    {
        return sort is "created_at" or "title" or "size"
            ? sort
            : DefaultSort;
    }

    private static string NormalizeDirection(string? direction)
    {
        return direction is "asc" or "desc"
            ? direction
            : DefaultDirection;
    }

    private static string CreateLikePattern(string search)
    {
        var escapedSearch = search
            .Replace("\\", "\\\\", StringComparison.Ordinal)
            .Replace("%", "\\%", StringComparison.Ordinal)
            .Replace("_", "\\_", StringComparison.Ordinal);

        return $"%{escapedSearch}%";
    }
}
