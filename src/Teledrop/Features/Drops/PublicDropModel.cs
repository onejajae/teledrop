using Isopoh.Cryptography.Argon2;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using Teledrop.Data;

namespace Teledrop.Features.Drops;

[AllowAnonymous]
public sealed class PublicDropModel(
    TeledropDbContext dbContext,
    DropUnlockCookie dropUnlockCookie)
    : PageModel
{
    public Drop? Drop { get; private set; }

    public bool IsLocked { get; private set; }

    public string? UnlockError { get; private set; }

    [BindProperty]
    public string DropPassword { get; set; } = string.Empty;

    public async Task<IActionResult> OnGetAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return MissingDropResult();
        }

        var accessDecision = EvaluateAccess(drop);
        if (accessDecision
            == DropAccessDecision.OwnerAuthenticationRequired)
        {
            return Challenge();
        }

        if (accessDecision == DropAccessDecision.DropPasswordRequired)
        {
            return LockedPage();
        }

        Drop = drop;
        return Page();
    }

    public async Task<IActionResult> OnPostUnlockAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null)
        {
            return MissingDropResult();
        }

        var accessDecision = DropAccessPolicy.Evaluate(
            drop,
            IsOwner(),
            hasValidDropPasswordGrant:
                drop.DropPasswordHash is null);
        if (accessDecision
            == DropAccessDecision.OwnerAuthenticationRequired)
        {
            return Challenge();
        }

        if (accessDecision == DropAccessDecision.Allowed)
        {
            return RedirectToPublicDrop(drop.Slug);
        }

        if (string.IsNullOrEmpty(DropPassword)
            || !Argon2.Verify(drop.DropPasswordHash, DropPassword))
        {
            DropPassword = string.Empty;
            ModelState.Remove(nameof(DropPassword));
            UnlockError = "드롭 비밀번호가 올바르지 않습니다.";
            return LockedPage();
        }

        dropUnlockCookie.Append(Response, drop);
        return RedirectToPublicDrop(drop.Slug);
    }

    private async Task<Drop?> FindDropAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(slug))
        {
            return null;
        }

        return await dbContext.Drops
            .AsNoTracking()
            .SingleOrDefaultAsync(
                candidate => candidate.Slug == slug,
                cancellationToken);
    }

    private IActionResult MissingDropResult()
    {
        return IsOwner() ? NotFound() : Challenge();
    }

    private PageResult LockedPage()
    {
        Drop = null;
        IsLocked = true;
        Response.StatusCode = StatusCodes.Status401Unauthorized;
        return Page();
    }

    private RedirectToPageResult RedirectToPublicDrop(string slug)
    {
        return RedirectToPage("/PublicDrop", new { slug });
    }

    private bool IsOwner()
    {
        return User.Identity?.IsAuthenticated == true;
    }

    private DropAccessDecision EvaluateAccess(Drop drop)
    {
        return DropAccessPolicy.Evaluate(
            drop,
            IsOwner(),
            drop.DropPasswordHash is null
                || dropUnlockCookie.IsValid(Request, drop));
    }
}
