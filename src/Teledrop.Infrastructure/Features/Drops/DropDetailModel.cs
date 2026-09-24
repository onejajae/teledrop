using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using Teledrop.Data;

namespace Teledrop.Features.Drops;

[Authorize]
public sealed class DropDetailModel(
    TeledropDbContext dbContext,
    DropUseCases dropUseCases,
    DropSlugs dropSlugs)
    : PageModel
{
    public Drop? Drop { get; private set; }

    public string FragmentPart { get; private set; } = string.Empty;
    public bool IsFragment => FragmentPart.Length > 0;
    private bool IsHtmx => Request.Headers["HX-Request"] == "true";

    public Task<IActionResult> OnGetFavoriteStateAsync(string slug, CancellationToken cancellationToken)
        => RenderStateAsync(slug, "favorite", cancellationToken);

    public Task<IActionResult> OnGetSharedStateAsync(string slug, CancellationToken cancellationToken)
        => RenderStateAsync(slug, "shared", cancellationToken);

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

        return await ChangedAsync(slug, "metadata", cancellationToken);
    }

    public async Task<IActionResult> OnPostVisibilityAsync(
        string slug,
        bool? isPrivate,
        CancellationToken cancellationToken)
    {
        if (isPrivate is null) return BadRequest();
        var result = await dropUseCases.SetVisibilityAsync(
            slug, isPrivate.Value, cancellationToken);
        if (result == DropCommandResult.NotFound)
        {
            return NotFound();
        }

        return await ChangedAsync(slug, "visibility", cancellationToken);
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
            return IsHtmx ? Fragment("password", "invalid") : Page();
        }

        return await ChangedAsync(slug, "password", cancellationToken);
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

        return await ChangedAsync(slug, "password", cancellationToken);
    }

    public async Task<IActionResult> OnPostSlugAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var result = await dropSlugs.ChangeAsync(
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
            return IsHtmx ? Fragment("slug", "invalid") : Page();
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
            return IsHtmx ? Fragment("slug", "invalid") : Page();
        }

        return Navigate("/DropDetail", new { slug = result.NormalizedSlug });
    }

    public async Task<IActionResult> OnPostFavoriteAsync(
        string slug,
        bool? isFavorite,
        CancellationToken cancellationToken)
    {
        if (isFavorite is null) return BadRequest();
        var result = await dropUseCases.SetFavoriteAsync(
            slug, isFavorite.Value, cancellationToken);
        if (result == DropCommandResult.NotFound)
        {
            return NotFound();
        }

        return await ChangedAsync(slug, "favorite", cancellationToken);
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

        return Navigate("/Index", new { deleted = true });
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

    private async Task<IActionResult> ChangedAsync(
        string slug, string part, CancellationToken cancellationToken)
    {
        if (!IsHtmx) return RedirectToPage("/DropDetail", new { slug });
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null) return NotFound();
        ClearNewDropPassword();
        PopulatePage(drop);
        return Fragment(part, "changed");
    }

    private async Task<IActionResult> RenderStateAsync(
        string slug, string part, CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null) return NotFound();
        PopulatePage(drop);
        return Fragment(part, "read");
    }

    private PartialViewResult Fragment(string part, string outcome)
    {
        FragmentPart = part;
        Response.Headers.CacheControl = "no-store";
        Response.Headers["X-Drop-Outcome"] = outcome;
        return Partial("DropDetails/_Change", this);
    }

    private IActionResult Navigate(string page, object values)
    {
        if (!IsHtmx) return RedirectToPage(page, values);
        Response.Headers["HX-Redirect"] = Url.Page(page, values);
        return new StatusCodeResult(StatusCodes.Status204NoContent);
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
