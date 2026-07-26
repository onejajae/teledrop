using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Teledrop.Data;

namespace Teledrop.Features.Drops;

public sealed class IndexModel(
    TeledropDbContext dbContext,
    IOptions<TeledropOptions> options,
    ILogger<IndexModel> logger)
    : PageModel
{
    public const int PageSize = 20;

    private const string DefaultSort = "created_at";
    private const string DefaultDirection = "desc";
    private const string LikeEscapeCharacter = "\\";

    private static readonly string[] FileSizeUnits =
        ["B", "KiB", "MiB", "GiB", "TiB"];

    public Drop? UploadedDrop { get; private set; }

    public bool DeleteSucceeded { get; private set; }

    public IReadOnlyList<Drop> Drops { get; private set; } = [];

    public string? Search { get; private set; }

    public string Sort { get; private set; } = DefaultSort;

    public string Direction { get; private set; } = DefaultDirection;

    public int CurrentPage { get; private set; } = 1;

    public int TotalPages { get; private set; } = 1;

    public int TotalDropCount { get; private set; }

    public async Task OnGetAsync(
        string? uploaded,
        bool deleted = false,
        string? search = null,
        string? sort = null,
        string? direction = null,
        int pageNumber = 1,
        CancellationToken cancellationToken = default)
    {
        DeleteSucceeded = deleted;
        Search = NormalizeSearch(search);
        Sort = NormalizeSort(sort);
        Direction = NormalizeDirection(direction);

        if (!string.IsNullOrWhiteSpace(uploaded))
        {
            UploadedDrop = await dbContext.Drops
                .AsNoTracking()
                .SingleOrDefaultAsync(
                    drop => drop.Slug == uploaded,
                    cancellationToken);
        }

        await LoadDropsAsync(pageNumber, cancellationToken);
    }

    public async Task<IActionResult> OnPostDeleteAsync(
        string slug,
        string? search = null,
        string? sort = null,
        string? direction = null,
        int pageNumber = 1,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(slug))
        {
            return BadRequest();
        }

        var drop = await dbContext.Drops.SingleOrDefaultAsync(
            candidate => candidate.Slug == slug,
            cancellationToken);
        if (drop is null)
        {
            return NotFound();
        }

        dbContext.Drops.Remove(drop);
        await dbContext.SaveChangesAsync(cancellationToken);

        try
        {
            var filePath = Path.GetFullPath(
                Path.Combine(options.Value.ShareDirectory, drop.Location));
            System.IO.File.Delete(filePath);
        }
        catch (Exception exception)
        {
            logger.LogWarning(
                exception,
                "Drop {DropId} was removed, but its file at location {Location} could not be deleted.",
                drop.Id,
                drop.Location);
        }

        return RedirectToList(
            search,
            sort,
            direction,
            pageNumber,
            deleted: true);
    }

    public async Task<IActionResult> OnPostFavoriteAsync(
        string slug,
        string? search = null,
        string? sort = null,
        string? direction = null,
        int pageNumber = 1,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(slug))
        {
            return BadRequest();
        }

        var drop = await dbContext.Drops.SingleOrDefaultAsync(
            candidate => candidate.Slug == slug,
            cancellationToken);
        if (drop is null)
        {
            return NotFound();
        }

        drop.IsFavorite = !drop.IsFavorite;
        await dbContext.SaveChangesAsync(cancellationToken);

        return RedirectToList(
            search,
            sort,
            direction,
            pageNumber);
    }

    public async Task<IActionResult> OnPostLogoutAsync()
    {
        await HttpContext.SignOutAsync(
            CookieAuthenticationDefaults.AuthenticationScheme);
        return RedirectToPage("/Login");
    }

    public static string FormatFileSize(long bytes)
    {
        if (bytes < 1024)
        {
            return $"{bytes:N0} {FileSizeUnits[0]}";
        }

        var size = (double)bytes;
        var unitIndex = 0;

        while (size >= 1024 && unitIndex < FileSizeUnits.Length - 1)
        {
            size /= 1024;
            unitIndex++;
        }

        return $"{size:0.#} {FileSizeUnits[unitIndex]}";
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

    private RedirectToPageResult RedirectToList(
        string? search,
        string? sort,
        string? direction,
        int pageNumber,
        bool deleted = false)
    {
        return RedirectToPage(
            "/Index",
            new
            {
                search = NormalizeSearch(search),
                sort = NormalizeSort(sort),
                direction = NormalizeDirection(direction),
                pageNumber = Math.Max(1, pageNumber),
                deleted = deleted ? true : (bool?)null,
            });
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
