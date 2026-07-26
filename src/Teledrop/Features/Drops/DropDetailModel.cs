using Isopoh.Cryptography.Argon2;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Teledrop.Data;

namespace Teledrop.Features.Drops;

[Authorize]
public sealed class DropDetailModel(
    TeledropDbContext dbContext,
    IOptions<TeledropOptions> options,
    ILogger<DropDetailModel> logger)
    : PageModel
{
    public Drop? Drop { get; private set; }

    [BindProperty]
    public string? TitleInput { get; set; }

    [BindProperty]
    public string? DescriptionInput { get; set; }

    [BindProperty]
    public string NewDropPassword { get; set; } = string.Empty;

    [BindProperty]
    public string SlugInput { get; set; } = string.Empty;

    public async Task<IActionResult> OnGetAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return NotFound();
        }

        PopulatePage(drop);
        return Page();
    }

    public async Task<IActionResult> OnPostMetadataAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return NotFound();
        }

        drop.Title = NormalizeOptionalText(TitleInput);
        drop.Description = NormalizeOptionalText(DescriptionInput);
        drop.UpdatedAt = DateTime.UtcNow;
        await dbContext.SaveChangesAsync(cancellationToken);

        return RedirectToCurrentDrop(drop.Slug);
    }

    public async Task<IActionResult> OnPostVisibilityAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return NotFound();
        }

        drop.IsPrivate = !drop.IsPrivate;
        drop.UpdatedAt = DateTime.UtcNow;
        await dbContext.SaveChangesAsync(cancellationToken);

        return RedirectToCurrentDrop(drop.Slug);
    }

    public async Task<IActionResult> OnPostPasswordAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return NotFound();
        }

        if (string.IsNullOrEmpty(NewDropPassword))
        {
            ClearNewDropPassword();
            ModelState.AddModelError(
                nameof(NewDropPassword),
                "새 드롭 비밀번호를 입력하세요.");
            PopulatePage(drop);
            return Page();
        }

        drop.DropPasswordHash = Argon2.Hash(NewDropPassword);
        drop.UpdatedAt = DateTime.UtcNow;
        await dbContext.SaveChangesAsync(cancellationToken);

        return RedirectToCurrentDrop(drop.Slug);
    }

    public async Task<IActionResult> OnPostClearPasswordAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return NotFound();
        }

        drop.DropPasswordHash = null;
        drop.UpdatedAt = DateTime.UtcNow;
        await dbContext.SaveChangesAsync(cancellationToken);

        return RedirectToCurrentDrop(drop.Slug);
    }

    public async Task<IActionResult> OnPostSlugAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return NotFound();
        }

        if (!DropSlugGenerator.TryNormalizeCustomSlug(
                SlugInput,
                out var normalizedSlug,
                out var errorMessage))
        {
            ModelState.Remove(nameof(SlugInput));
            SlugInput = normalizedSlug;
            ModelState.AddModelError(nameof(SlugInput), errorMessage);
            PopulatePage(drop, preserveSlugInput: true);
            return Page();
        }

        var slugAlreadyExists = await dbContext.Drops
            .AsNoTracking()
            .AnyAsync(
                candidate =>
                    candidate.Id != drop.Id
                    && candidate.Slug == normalizedSlug,
                cancellationToken);
        if (slugAlreadyExists)
        {
            ModelState.Remove(nameof(SlugInput));
            SlugInput = normalizedSlug;
            ModelState.AddModelError(
                nameof(SlugInput),
                "이미 사용 중인 slug입니다.");
            PopulatePage(drop, preserveSlugInput: true);
            return Page();
        }

        if (!string.Equals(
                drop.Slug,
                normalizedSlug,
                StringComparison.Ordinal))
        {
            drop.Slug = normalizedSlug;
            drop.UpdatedAt = DateTime.UtcNow;
            await dbContext.SaveChangesAsync(cancellationToken);
        }

        return RedirectToCurrentDrop(drop.Slug);
    }

    public async Task<IActionResult> OnPostFavoriteAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return NotFound();
        }

        drop.IsFavorite = !drop.IsFavorite;
        await dbContext.SaveChangesAsync(cancellationToken);

        return RedirectToCurrentDrop(drop.Slug);
    }

    public async Task<IActionResult> OnPostDeleteAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
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

        return RedirectToPage("/Index", new { deleted = true });
    }

    private async Task<Drop?> FindDropAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(slug))
        {
            return null;
        }

        return await dbContext.Drops.SingleOrDefaultAsync(
            candidate => candidate.Slug == slug,
            cancellationToken);
    }

    private void PopulatePage(Drop drop, bool preserveSlugInput = false)
    {
        Drop = drop;
        TitleInput = drop.Title;
        DescriptionInput = drop.Description;

        if (!preserveSlugInput)
        {
            SlugInput = drop.Slug;
        }
    }

    private void ClearNewDropPassword()
    {
        NewDropPassword = string.Empty;
        ModelState.Remove(nameof(NewDropPassword));
    }

    private RedirectToPageResult RedirectToCurrentDrop(string slug)
    {
        return RedirectToPage("/DropDetail", new { slug });
    }

    private static string? NormalizeOptionalText(string? value)
    {
        var normalized = value?.Trim();
        return string.IsNullOrEmpty(normalized) ? null : normalized;
    }
}
