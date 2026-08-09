using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using Teledrop.Data;

namespace Teledrop.Features.Drops;

[Authorize]
public sealed class DropDetailModel(
    TeledropDbContext dbContext,
    DropUseCases dropUseCases)
    : PageModel
{
    public Drop? Drop { get; private set; }

    [BindProperty]
    public string? TitleInput { get; set; }

    [BindProperty]
    public string? DescriptionInput { get; set; }

    [BindProperty]
    public string? NewDropPassword { get; set; }

    [BindProperty]
    public string? SlugInput { get; set; }

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
        var result = await dropUseCases.UpdateMetadataAsync(
            slug,
            TitleInput,
            DescriptionInput,
            cancellationToken);
        if (result == DropCommandResult.NotFound)
        {
            return NotFound();
        }

        return RedirectToCurrentDrop(slug);
    }

    public async Task<IActionResult> OnPostVisibilityAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var result = await dropUseCases.ToggleVisibilityAsync(
            slug,
            cancellationToken);
        if (result == DropCommandResult.NotFound)
        {
            return NotFound();
        }

        return RedirectToCurrentDrop(slug);
    }

    public async Task<IActionResult> OnPostPasswordAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var result = await dropUseCases.SetPasswordAsync(
            slug,
            NewDropPassword ?? string.Empty,
            cancellationToken);
        if (result == SetDropPasswordResult.NotFound)
        {
            return NotFound();
        }

        if (result == SetDropPasswordResult.PasswordRequired)
        {
            ClearNewDropPassword();
            ModelState.AddModelError(
                nameof(NewDropPassword),
                "새 드롭 비밀번호를 입력하세요.");
            var drop = await FindDropAsync(slug, cancellationToken);
            if (drop is null)
            {
                return NotFound();
            }

            PopulatePage(drop);
            return Page();
        }

        return RedirectToCurrentDrop(slug);
    }

    public async Task<IActionResult> OnPostClearPasswordAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var result = await dropUseCases.ClearPasswordAsync(
            slug,
            cancellationToken);
        if (result == DropCommandResult.NotFound)
        {
            return NotFound();
        }

        return RedirectToCurrentDrop(slug);
    }

    public async Task<IActionResult> OnPostSlugAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var result = await dropUseCases.ChangeSlugAsync(
            slug,
            SlugInput,
            cancellationToken);
        if (result.Status == ChangeDropSlugStatus.NotFound)
        {
            return NotFound();
        }

        if (result.Status == ChangeDropSlugStatus.Invalid)
        {
            ModelState.Remove(nameof(SlugInput));
            SlugInput = result.NormalizedSlug;
            ModelState.AddModelError(
                nameof(SlugInput),
                GetSlugValidationErrorMessage(result.ValidationError));
            var drop = await FindDropAsync(slug, cancellationToken);
            if (drop is null)
            {
                return NotFound();
            }

            PopulatePage(drop, preserveSlugInput: true);
            return Page();
        }

        if (result.Status == ChangeDropSlugStatus.AlreadyExists)
        {
            ModelState.Remove(nameof(SlugInput));
            SlugInput = result.NormalizedSlug;
            ModelState.AddModelError(
                nameof(SlugInput),
                "이미 사용 중인 slug입니다.");
            var drop = await FindDropAsync(slug, cancellationToken);
            if (drop is null)
            {
                return NotFound();
            }

            PopulatePage(drop, preserveSlugInput: true);
            return Page();
        }

        return RedirectToCurrentDrop(result.NormalizedSlug);
    }

    public async Task<IActionResult> OnPostFavoriteAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var result = await dropUseCases.ToggleFavoriteAsync(
            slug,
            cancellationToken);
        if (result == DropCommandResult.NotFound)
        {
            return NotFound();
        }

        return RedirectToCurrentDrop(slug);
    }

    public async Task<IActionResult> OnPostDeleteAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var result = await dropUseCases.DeleteAsync(
            slug,
            cancellationToken);
        if (result == DropCommandResult.NotFound)
        {
            return NotFound();
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

    private static string GetSlugValidationErrorMessage(
        DropSlugValidationError validationError)
    {
        return validationError switch
        {
            DropSlugValidationError.InvalidFormat =>
                "slug는 영문 소문자 또는 숫자로 시작하고, 영문 소문자·숫자·하이픈만 사용해 64자 이하여야 합니다.",
            DropSlugValidationError.Reserved =>
                "이 slug는 teledrop 경로에 예약되어 있습니다.",
            _ => "slug가 올바르지 않습니다.",
        };
    }
}
