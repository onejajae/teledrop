using System.Globalization;
using System.Text.Encodings.Web;
using System.Text.Json;
using Microsoft.AspNetCore.Razor.TagHelpers;
using Teledrop.Localization;
using Xunit;

namespace Teledrop.Infrastructure.Tests;

public sealed class TranslationTagHelperTests
{
    [Theory]
    [InlineData("text", null)]
    [InlineData("aria-label", "aria-label")]
    [InlineData("title", "title")]
    [InlineData("placeholder", "placeholder")]
    [InlineData("tooltip", "data-tooltip")]
    [InlineData("alt", "alt")]
    [InlineData("summary", "data-list-summary")]
    public void TranslatesEverySupportedTargetAndRemovesAuthoringAttributes(string target, string? attribute)
    {
        var helper = new TranslationTagHelper(new UiText());
        switch (target)
        {
            case "text": helper.Text = "Password"; break;
            case "aria-label": helper.AriaLabel = "Password"; break;
            case "title": helper.Title = "Password"; break;
            case "placeholder": helper.Placeholder = "Password"; break;
            case "tooltip": helper.Tooltip = "Password"; break;
            case "alt": helper.Alt = "Password"; break;
            case "summary": helper.Summary = "Password"; break;
        }
        var (context, output) = CreateOutput(new("td-" + target, "Password"), new("td-args", "[]"));
        output.Content.SetHtmlContent("<strong>Preserved child</strong>");

        helper.Process(context, output);

        Assert.Equal("Password", output.Attributes["data-i18n-" + target].Value);
        Assert.False(output.Attributes.ContainsName("td-" + target));
        Assert.False(output.Attributes.ContainsName("td-args"));
        Assert.False(output.Attributes.ContainsName("data-i18n-args"));
        var translated = new UiText()["Password"];
        if (attribute is null) Assert.Equal(HtmlEncoder.Default.Encode(translated), output.Content.GetContent());
        else
        {
            Assert.Equal(translated, output.Attributes[attribute].Value);
            Assert.Equal("<strong>Preserved child</strong>", output.Content.GetContent());
        }
    }

    [Fact]
    public void UserArgumentsAreEncodedInVisibleTextAndSerializedForLaterLanguageChanges()
    {
        const string fileName = "<img src=x onerror=alert(1)> & \"quoted\"";
        var helper = new TranslationTagHelper(new UiText())
        {
            Text = "Delete.Question", AriaLabel = "Delete.Question", Args = [fileName],
        };
        var (context, output) = CreateOutput(new("td-text", "Delete.Question"),
            new("td-aria-label", "Delete.Question"), new("td-args", fileName));

        helper.Process(context, output);

        var expected = new UiText().Get("Delete.Question", fileName);
        Assert.Equal(HtmlEncoder.Default.Encode(expected), output.Content.GetContent());
        Assert.Equal(expected, output.Attributes["aria-label"].Value);
        var args = JsonSerializer.Deserialize<string[]>((string)output.Attributes["data-i18n-args"].Value);
        Assert.NotNull(args);
        Assert.Equal([fileName], args);
        using var writer = new StringWriter(CultureInfo.InvariantCulture);
        output.WriteTo(writer, HtmlEncoder.Default);
        Assert.DoesNotContain("<img", writer.ToString());
        Assert.Contains("&lt;img", writer.ToString());
        Assert.DoesNotContain(" td-", writer.ToString());
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    public void AbsentTranslationKeysPreserveExistingContent(string? key)
    {
        var helper = new TranslationTagHelper(new UiText()) { Text = key, Title = key };
        var (context, output) = CreateOutput(new("td-text", key), new("td-title", key));
        output.Content.SetContent("Existing message");

        helper.Process(context, output);

        Assert.Equal("Existing message", output.Content.GetContent());
        Assert.Empty(output.Attributes);
    }

    private static (TagHelperContext Context, TagHelperOutput Output) CreateOutput(params TagHelperAttribute[] attributes)
    {
        var context = new TagHelperContext(new(attributes), new Dictionary<object, object>(), "translation-test");
        var output = new TagHelperOutput("span", new(attributes),
            (_, _) => Task.FromResult<TagHelperContent>(new DefaultTagHelperContent()));
        return (context, output);
    }
}
