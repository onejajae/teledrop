using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Teledrop.Data;

namespace Teledrop.Features.Drops;

public sealed class DownloadModel(
    TeledropDbContext dbContext,
    IOptions<TeledropOptions> options)
    : PageModel
{
    public async Task<IActionResult> OnGetAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await dbContext.Drops
            .AsNoTracking()
            .SingleOrDefaultAsync(
                candidate => candidate.Slug == slug,
                cancellationToken);
        if (drop is null)
        {
            return NotFound();
        }

        var filePath = Path.GetFullPath(
            Path.Combine(options.Value.ShareDirectory, drop.Location));
        if (!System.IO.File.Exists(filePath))
        {
            return NotFound();
        }

        var result = PhysicalFile(
            filePath,
            drop.ContentType,
            drop.FileName);
        result.EnableRangeProcessing = true;
        return result;
    }
}
