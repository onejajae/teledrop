using System.ComponentModel.DataAnnotations;
using System.Security.Claims;
using Isopoh.Cryptography.Argon2;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.Extensions.Options;

namespace Teledrop.Features.Auth;

[AllowAnonymous]
public sealed class LoginModel(IOptionsMonitor<TeledropOptions> optionsMonitor)
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

    public string? ErrorMessage { get; private set; }

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
            ErrorMessage = "소유자 이름과 비밀번호를 입력하세요.";
            ClearPassword();
            return Page();
        }

        var options = optionsMonitor.CurrentValue;
        var passwordMatches = Argon2.Verify(options.WebPassword, Password);
        var usernameMatches = string.Equals(
            Username,
            options.WebUsername,
            StringComparison.Ordinal);

        if (!usernameMatches || !passwordMatches)
        {
            ErrorMessage = "소유자 이름 또는 비밀번호가 올바르지 않습니다.";
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
