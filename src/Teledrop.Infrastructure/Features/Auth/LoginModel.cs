using System.ComponentModel.DataAnnotations;
using System.Security.Claims;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.Extensions.Options;
using Teledrop.Infrastructure;

namespace Teledrop.Features.Auth;

[AllowAnonymous]
public sealed class LoginModel(IOptionsMonitor<TeledropOptions> optionsMonitor, Teledrop.Localization.UiText ui)
    : PageModel
{
    [BindProperty]
    [Required]
    public string Username { get; set; } = string.Empty;

    [BindProperty]
    [Required]
    [DataType(DataType.Password)]
    public string Password { get; set; } = string.Empty;

    [BindProperty(SupportsGet = true)]
    public string? ReturnUrl { get; set; }

    public string? ErrorKey { get; private set; }
    public string? ErrorMessage => ErrorKey is null ? null : ui[ErrorKey];

    public IActionResult OnGet()
    {
        return User.Identity?.IsAuthenticated == true
            ? LocalRedirect(GetReturnLocation())
            : Page();
    }

    public async Task<IActionResult> OnPostAsync()
    {
        if (!ModelState.IsValid)
        {
            ErrorKey = "Login.Required";
            ClearPassword();
            return Page();
        }

        var options = optionsMonitor.CurrentValue;
        var passwordMatches = PasswordHash.Verify(options.WebPassword, Password);
        var usernameMatches = string.Equals(
            Username,
            options.WebUsername,
            StringComparison.Ordinal);

        if (!usernameMatches || !passwordMatches)
        {
            ErrorKey = "Login.Invalid";
            ClearPassword();
            return Page();
        }

        var claims = new[]
        {
            new Claim(ClaimTypes.Name, options.WebUsername),
            new Claim(
                OwnerSession.PasswordFingerprintClaimType,
                OwnerSession.CreatePasswordFingerprint(options.WebPassword)),
        };
        var identity = new ClaimsIdentity(
            claims,
            CookieAuthenticationDefaults.AuthenticationScheme);
        var principal = new ClaimsPrincipal(identity);
        var properties = new AuthenticationProperties
        {
            IsPersistent = true,
        };

        await HttpContext.SignInAsync(
            CookieAuthenticationDefaults.AuthenticationScheme,
            principal,
            properties);

        return LocalRedirect(GetReturnLocation());
    }

    private string GetReturnLocation()
    {
        return Url.IsLocalUrl(ReturnUrl) ? ReturnUrl : "/";
    }

    private void ClearPassword()
    {
        Password = string.Empty;
        ModelState.Remove(nameof(Password));
    }
}
