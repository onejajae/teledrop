using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace Teledrop.Features.Drops;

public sealed class IndexModel : PageModel
{
    public const int PageSize = DropList.PageSize;

    private static readonly string[] FileSizeUnits =
        ["B", "KB", "MB", "GB", "TB"];

    public bool DeleteSucceeded { get; private set; }

    public IActionResult OnGetDropList(string? currentSlug)
    {
        Response.Headers.CacheControl = "no-store";
        return new ViewComponentResult
        {
            ViewComponentName = "DropList",
            Arguments = new { currentSlug },
        };
    }

    public void OnGet(bool deleted = false)
    {
        DeleteSucceeded = deleted;
    }

    public IActionResult OnPost() => NotFound();

    public async Task<IActionResult> OnPostLogoutAsync()
    {
        await HttpContext.SignOutAsync(
            CookieAuthenticationDefaults.AuthenticationScheme);
        return RedirectToPage("/Login");
    }

    public static string FormatFileSize(long bytes)
    {
        if (bytes < 1024)
        {
            return $"{bytes:N0} {FileSizeUnits[0]}";
        }

        var size = (double)bytes;
        var unitIndex = 0;

        while (size >= 1024 && unitIndex < FileSizeUnits.Length - 1)
        {
            size /= 1024;
            unitIndex++;
        }

        return $"{size:0.##} {FileSizeUnits[unitIndex]}";
    }
}
