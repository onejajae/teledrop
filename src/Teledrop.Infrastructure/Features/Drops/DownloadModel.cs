using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace Teledrop.Features.Drops;

[AllowAnonymous]
public sealed class DownloadModel(
    DropAccess dropAccess,
    DropFileStore fileStore)
    : PageModel
{
    public async Task<IActionResult> OnGetAsync(
        string slug,
        bool inline = false,
        CancellationToken cancellationToken = default)
    {
        var access = await dropAccess.ReadAsync(HttpContext, slug, cancellationToken);
        switch (access.Status)
        {
            case DropAccessStatus.OwnerAuthenticationRequired:
                return Challenge();
            case DropAccessStatus.DropPasswordRequired:
                return Unauthorized();
            case DropAccessStatus.NotFound:
                return NotFound();
            case DropAccessStatus.Allowed:
                break;
            default:
                throw new InvalidOperationException("Unexpected Drop read result.");
        }

        var drop = access.Drop!;
        var filePath = fileStore.FindFilePath(drop.Location);
        if (filePath is null)
        {
            return NotFound();
        }

        PhysicalFileResult result;
        if (inline && DropPreviewPolicy.Evaluate(drop.ContentType).AllowInline)
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
