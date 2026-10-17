using System.Globalization;
using Teledrop.Features.Drops;
using Teledrop.Localization;
using Xunit;

namespace Teledrop.Infrastructure.Tests;

public sealed class LocalizationFormattingTests
{
    [Theory]
    [InlineData(0L, "0 B")]
    [InlineData(1023L, "1,023 B")]
    [InlineData(1024L, "1 KB")]
    [InlineData(1536L, "1.5 KB")]
    [InlineData(1048575L, "1024 KB")]
    [InlineData(1125899906842624L, "1024 TB")]
    public void FileSizesPreserveTheBinaryThresholdRoundingAndLargestUnit(long bytes, string expected)
    {
        using var scope = new CultureScope("en-US");

        Assert.Equal(expected, IndexModel.FormatFileSize(bytes));
    }

    [Theory]
    [InlineData("en-US", "en", "Sign in", "Page 3 of 12")]
    [InlineData("ko-KR", "ko", "로그인", "3 / 12 페이지")]
    [InlineData("fr-FR", "en", "Sign in", "Page 3 of 12")]
    public void ResourceSelectionAndMissingKeysHaveStableFallbacks(
        string culture, string language, string login, string page)
    {
        using var scope = new CultureScope(culture);
        var ui = new UiText();

        Assert.Equal(language, UiText.Language);
        Assert.Equal(login, ui["Login"]);
        Assert.Equal(page, ui.Get("Pdf.Page", 3, 12));
        Assert.Equal("Unknown.Resource.Key", ui["Unknown.Resource.Key"]);
    }

    [Fact]
    public void FormattedArgumentsUseTheCurrentCultureWithoutChangingTheResourceLanguage()
    {
        using var scope = new CultureScope("de-DE", "en-US");

        Assert.Equal("en", UiText.Language);
        Assert.Equal("1,5 KB", IndexModel.FormatFileSize(1536));
        Assert.Equal("12,5%", new UiText().Get("Upload.Percent", 12.5m));
    }

    private sealed class CultureScope : IDisposable
    {
        private readonly CultureInfo previousCulture = CultureInfo.CurrentCulture;
        private readonly CultureInfo previousUiCulture = CultureInfo.CurrentUICulture;

        internal CultureScope(string culture, string? uiCulture = null)
        {
            CultureInfo.CurrentCulture = CultureInfo.GetCultureInfo(culture);
            CultureInfo.CurrentUICulture = CultureInfo.GetCultureInfo(uiCulture ?? culture);
        }

        public void Dispose()
        {
            CultureInfo.CurrentCulture = previousCulture;
            CultureInfo.CurrentUICulture = previousUiCulture;
        }
    }
}
