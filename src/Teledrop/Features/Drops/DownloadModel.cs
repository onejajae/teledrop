using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Microsoft.Net.Http.Headers;
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

        var accessDecision = DropAccessPolicy.Evaluate(
            drop,
            User.Identity?.IsAuthenticated == true,
            drop.DropPasswordHash is null
                || dropUnlockCookie.IsValid(Request, drop));
        if (accessDecision
            == DropAccessDecision.OwnerAuthenticationRequired)
        {
            return Challenge();
        }

        if (accessDecision == DropAccessDecision.DropPasswordRequired)
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
        if (inline && IsSafeInlineContentType(drop.ContentType))
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

    private static bool IsSafeInlineContentType(string contentType)
    {
        if (!MediaTypeHeaderValue.TryParse(
                contentType,
                out var parsedContentType)
            || parsedContentType is null)
        {
            return false;
        }

        var mediaType = parsedContentType.MediaType.Value;
        if (string.IsNullOrEmpty(mediaType))
        {
            return false;
        }

        return (mediaType.StartsWith(
                    "image/",
                    StringComparison.OrdinalIgnoreCase)
                && !string.Equals(
                    mediaType,
                    "image/svg+xml",
                    StringComparison.OrdinalIgnoreCase))
            || mediaType.StartsWith(
                "video/",
                StringComparison.OrdinalIgnoreCase)
            || mediaType.StartsWith(
                "audio/",
                StringComparison.OrdinalIgnoreCase)
            || string.Equals(
                mediaType,
                "application/pdf",
                StringComparison.OrdinalIgnoreCase)
            || string.Equals(
                mediaType,
                "text/plain",
                StringComparison.OrdinalIgnoreCase);
    }
}
