using System.Collections;
using System.Globalization;
using System.Resources;
using Microsoft.Extensions.Localization;

[assembly: RootNamespace("Teledrop")]
[assembly: NeutralResourcesLanguage("en")]

namespace Teledrop.Localization;

public sealed class UiText
{
    private static readonly ResourceManager Resources = new("Teledrop.Localization.UiStrings", typeof(UiText).Assembly);
    public static string Language => CultureInfo.CurrentUICulture.TwoLetterISOLanguageName == "ko" ? "ko" : "en";
    public string this[string key] => Get(key);

    public string Get(string key, params object?[] args)
        => string.Format(CultureInfo.CurrentCulture,
            Resources.GetString(key, CultureInfo.GetCultureInfo(Language)) ?? key, args);

    public static IReadOnlyDictionary<string, Dictionary<string, string>> Catalogs { get; } = BuildCatalogs();

    private static Dictionary<string, Dictionary<string, string>> BuildCatalogs()
    {
        var keys = Resources.GetResourceSet(CultureInfo.InvariantCulture, true, true)!
            .Cast<DictionaryEntry>().Select(entry => (string)entry.Key).ToArray();
        return new[] { "ko", "en" }.ToDictionary(language => language,
            language => keys.ToDictionary(key => key,
                key => Resources.GetString(key, CultureInfo.GetCultureInfo(language))!));
    }
}
