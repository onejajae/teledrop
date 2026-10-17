using System.Collections;
using System.Globalization;
using System.Resources;
using System.Text.RegularExpressions;
using Teledrop.Localization;
using Xunit;

namespace Teledrop.Infrastructure.Tests;

public sealed class LocalizationResourceTests
{
    [Fact]
    public void CatalogsContainTheSameKeysAndPlaceholders()
    {
        var resources = new ResourceManager("Teledrop.Localization.UiStrings", typeof(UiText).Assembly);
        Dictionary<string, string> Read(CultureInfo culture) => resources.GetResourceSet(culture, true, false)!
            .Cast<DictionaryEntry>().ToDictionary(entry => (string)entry.Key, entry => (string)entry.Value!);
        var english = Read(CultureInfo.InvariantCulture);
        var korean = Read(CultureInfo.GetCultureInfo("ko"));
        Assert.Equal(english.Keys.Order(), korean.Keys.Order());
        foreach (var key in english.Keys)
        {
            Assert.False(string.IsNullOrWhiteSpace(korean[key]));
            Assert.Equal(Regex.Matches(english[key], @"\{\d+\}").Select(m => m.Value).Order(),
                Regex.Matches(korean[key], @"\{\d+\}").Select(m => m.Value).Order());
        }
        Assert.Equal("Sign in", UiText.Catalogs["en"]["Login"]);
        Assert.Equal("로그인", UiText.Catalogs["ko"]["Login"]);
    }
}
