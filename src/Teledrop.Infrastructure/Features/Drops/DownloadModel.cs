using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.Net.Http.Headers;

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
            // 브라우저 뷰어에서 저장할 때도 원래 파일 이름을 쓰도록 inline에 이름을 함께 보낸다.
            var disposition = new ContentDispositionHeaderValue("inline");
            disposition.SetHttpFileName(drop.FileName);
            Response.Headers.ContentDisposition = disposition.ToString();
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
