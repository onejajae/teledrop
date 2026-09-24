using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace Teledrop.Features.Drops;

[AllowAnonymous]
public sealed class PublicDropModel(DropAccess dropAccess) : PageModel
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
        var access = await dropAccess.ReadAsync(HttpContext, slug, cancellationToken);
        Drop = access.Drop;
        return access.Status switch
        {
            DropAccessStatus.Allowed => Display(),
            DropAccessStatus.OwnerAuthenticationRequired => Challenge(),
            DropAccessStatus.DropPasswordRequired => LockedPage(),
            DropAccessStatus.NotFound => NotFound(),
            _ => throw new InvalidOperationException("Unexpected Drop read result."),
        };
    }

    public async Task<IActionResult> OnPostUnlockAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var access = await dropAccess.UnlockAsync(HttpContext, slug, DropPassword, cancellationToken);
        switch (access.Status)
        {
            case DropAccessStatus.Allowed:
                return RedirectToPage("/PublicDrop", new { slug = access.Drop!.Slug });
            case DropAccessStatus.OwnerAuthenticationRequired:
                return Challenge();
            case DropAccessStatus.NotFound:
                return NotFound();
            case DropAccessStatus.InvalidDropPassword:
                DropPassword = string.Empty;
                ModelState.Remove(nameof(DropPassword));
                UnlockError = "드롭 비밀번호가 올바르지 않습니다.";
                return LockedPage();
            default:
                throw new InvalidOperationException("Unexpected Drop unlock result.");
        }
    }

    private IActionResult LockedPage()
    {
        IsLocked = true;
        Response.StatusCode = StatusCodes.Status401Unauthorized;
        return Display();
    }

    private IActionResult Display()
    {
        Response.Headers.CacheControl = "no-store";
        return Request.Headers["HX-Request"] == "true"
            ? Partial("_PublicDropContent", this)
            : Page();
    }
}
