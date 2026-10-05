using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace Teledrop.Features.Drops;

// CSRF is validated by the receiver before file streaming, without Request.Form buffering.
[IgnoreAntiforgeryToken]
public sealed class UploadModel(DropUploadReceiver uploads) : PageModel
{
    public IActionResult OnGet() => RedirectToPage("/Index");

    public async Task<IActionResult> OnPostAsync()
    {
        try
        {
            var drop = await uploads.ReceiveWebAsync(HttpContext, HttpContext.RequestAborted);
            if (string.Equals(Request.Headers["HX-Request"], "true", StringComparison.OrdinalIgnoreCase))
            {
                Response.Headers["HX-Redirect"] = Url.Page("/DropDetail", new { slug = drop.Slug });
                return new StatusCodeResult(StatusCodes.Status204NoContent);
            }
            return RedirectToPage("/DropDetail", new { slug = drop.Slug });
        }
        catch (DropUploadTooLargeException)
        {
            return StatusCode(StatusCodes.Status413PayloadTooLarge);
        }
        catch (InvalidUploadException)
        {
            return BadRequest();
        }
    }
}
