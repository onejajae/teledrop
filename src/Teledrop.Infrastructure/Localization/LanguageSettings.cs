using Microsoft.AspNetCore.Localization;
using Microsoft.Net.Http.Headers;

namespace Teledrop.Localization;

public static class LanguageSettings
{
    public static IServiceCollection AddTeledropLanguages(this IServiceCollection services)
    {
        services.AddSingleton<UiText>();
        services.Configure<RequestLocalizationOptions>(options =>
        {
            options.SetDefaultCulture("en").AddSupportedCultures("en", "ko").AddSupportedUICultures("en", "ko");
            options.RequestCultureProviders = [new CookieRequestCultureProvider(), new BrowserLanguageProvider()];
            options.ApplyCurrentCultureToResponseHeaders = true;
        });
        return services;
    }

    private sealed class BrowserLanguageProvider : RequestCultureProvider
    {
        public override Task<ProviderCultureResult?> DetermineProviderCultureResult(HttpContext httpContext)
        {
            // Examine all browser preferences, including ones beyond the framework's default first three.
            if (StringWithQualityHeaderValue.TryParseList(httpContext.Request.Headers.AcceptLanguage.Select(value => value ?? string.Empty).ToArray(), out var values))
            {
                foreach (var value in values.Where(value => (value.Quality ?? 1) > 0).OrderByDescending(value => value.Quality ?? 1))
                {
                    var language = value.Value.ToString().Split('-')[0].ToLowerInvariant();
                    if (language is "ko" or "en") return Task.FromResult<ProviderCultureResult?>(new(language));
                }
            }
            return Task.FromResult<ProviderCultureResult?>(null);
        }
    }
}
