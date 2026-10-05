using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Localization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace Teledrop.Localization;

[AllowAnonymous]
public sealed class LanguageModel(TimeProvider timeProvider) : PageModel
{
    public IActionResult OnGet() => NotFound();

    public IActionResult OnPost(string language, string? returnUrl)
    {
        if (language is not ("ko" or "en")) return BadRequest();
        Response.Cookies.Append(CookieRequestCultureProvider.DefaultCookieName,
            CookieRequestCultureProvider.MakeCookieValue(new RequestCulture(language)), new CookieOptions
            {
                Expires = timeProvider.GetUtcNow().AddYears(1), HttpOnly = true,
                Secure = Request.IsHttps, SameSite = SameSiteMode.Lax, IsEssential = true,
                Path = Request.PathBase.HasValue ? Request.PathBase.Value : "/",
            });
        Response.Headers.CacheControl = "no-store";
        if (Request.Headers["X-Requested-With"] == "XMLHttpRequest") return new NoContentResult();
        return LocalRedirect(Url.IsLocalUrl(returnUrl) ? returnUrl! : Url.Page("/Index")!);
    }
}
