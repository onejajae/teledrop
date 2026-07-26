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
    public Drop? UploadedDrop { get; private set; }

    public bool DeleteSucceeded { get; private set; }

    public async Task OnGetAsync(
        string? uploaded,
        bool deleted = false,
        CancellationToken cancellationToken = default)
    {
        DeleteSucceeded = deleted;

        if (string.IsNullOrWhiteSpace(uploaded))
        {
            return;
        }

        UploadedDrop = await dbContext.Drops
            .AsNoTracking()
            .SingleOrDefaultAsync(
                drop => drop.Slug == uploaded,
                cancellationToken);
    }

    public async Task<IActionResult> OnPostDeleteAsync(
        string slug,
        CancellationToken cancellationToken)
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

        return RedirectToPage("/Index", new { deleted = true });
    }

    public async Task<IActionResult> OnPostLogoutAsync()
    {
        await HttpContext.SignOutAsync(
            CookieAuthenticationDefaults.AuthenticationScheme);
        return RedirectToPage("/Login");
    }
}
