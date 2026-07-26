using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Teledrop.Data;

namespace Teledrop.Features.Drops;

[AllowAnonymous]
public sealed class DownloadModel(
    TeledropDbContext dbContext,
    DropUnlockCookie dropUnlockCookie,
    IOptions<TeledropOptions> options)
    : PageModel
{
    public async Task<IActionResult> OnGetAsync(
        string slug,
        bool inline = false,
        CancellationToken cancellationToken = default)
    {
        var drop = await dbContext.Drops
            .AsNoTracking()
            .SingleOrDefaultAsync(
                candidate => candidate.Slug == slug,
                cancellationToken);
        if (drop is null)
        {
            return User.Identity?.IsAuthenticated == true
                ? NotFound()
                : Challenge();
        }

        var isOwner = User.Identity?.IsAuthenticated == true;
        if (drop.IsPrivate && !isOwner)
        {
            return Challenge();
        }

        if (!isOwner
            && drop.DropPasswordHash is not null
            && !dropUnlockCookie.IsValid(Request, drop))
        {
            return Unauthorized();
        }

        var filePath = Path.GetFullPath(
            Path.Combine(options.Value.ShareDirectory, drop.Location));
        if (!System.IO.File.Exists(filePath))
        {
            return NotFound();
        }

        PhysicalFileResult result;
        if (inline)
        {
            Response.Headers.ContentDisposition = "inline";
            result = PhysicalFile(filePath, drop.ContentType);
        }
        else
        {
            result = PhysicalFile(
                filePath,
                drop.ContentType,
                drop.FileName);
        }

        result.EnableRangeProcessing = true;
        return result;
    }
}
