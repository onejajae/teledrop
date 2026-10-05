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
    DropSlugs dropSlugs,
    Teledrop.Localization.UiText ui)
    : PageModel
{
    public Drop? Drop { get; private set; }
    public string? PasswordErrorKey { get; private set; }
    public string? SlugErrorKey { get; private set; }

    public string FragmentPart { get; private set; } = string.Empty;
    public bool IsFragment => FragmentPart.Length > 0;
    private bool IsHtmx => Request.Headers["HX-Request"] == "true";

    public Task<IActionResult> OnGetFavoriteStateAsync(string slug, CancellationToken cancellationToken)
        => RenderStateAsync(slug, "favorite", cancellationToken);

    public Task<IActionResult> OnGetSharedStateAsync(string slug, CancellationToken cancellationToken)
        => RenderStateAsync(slug, "shared", cancellationToken);

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
            DescriptionInput,
            cancellationToken);
        if (result == DropCommandResult.NotFound)
        {
            return NotFound();
        }

        return await ChangedAsync(slug, "metadata", cancellationToken);
    }

    public async Task<IActionResult> OnPostAccessAsync(
        string slug,
        DropAccessLevel? access,
        CancellationToken cancellationToken)
    {
        if (access is not { } level || !Enum.IsDefined(level)) return BadRequest();
        var result = await dropUseCases.SetAccessAsync(
            slug, level, NewDropPassword, cancellationToken);
        if (result == SetDropAccessResult.NotFound)
        {
            return NotFound();
        }

        if (result == SetDropAccessResult.PasswordRequired)
        {
            ClearNewDropPassword();
            PasswordErrorKey = "Password.Required";
            ModelState.AddModelError(nameof(NewDropPassword), ui[PasswordErrorKey]);
            var drop = await FindDropAsync(slug, cancellationToken);
            if (drop is null)
            {
                return NotFound();
            }

            PopulatePage(drop);
            return IsHtmx ? Fragment("access", "invalid") : Page();
        }

        return await ChangedAsync(slug, "access", cancellationToken);
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
            SlugErrorKey = GetSlugValidationErrorKey(result.ValidationError);
            ModelState.AddModelError(nameof(SlugInput), ui[SlugErrorKey]);
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
            SlugErrorKey = "Url.Taken";
            ModelState.AddModelError(nameof(SlugInput), ui[SlugErrorKey]);
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

    private static string GetSlugValidationErrorKey(
        DropSlugValidationError validationError)
    {
        return validationError switch
        {
            DropSlugValidationError.InvalidFormat =>
                "Url.Format",
            DropSlugValidationError.Reserved =>
                "Url.Reserved",
            _ => "Url.Invalid",
        };
    }
}
