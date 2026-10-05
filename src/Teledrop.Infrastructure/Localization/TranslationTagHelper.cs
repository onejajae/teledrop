using System.Text.Json;
using Microsoft.AspNetCore.Razor.TagHelpers;

namespace Teledrop.Localization;

[HtmlTargetElement(Attributes = "td-text")]
[HtmlTargetElement(Attributes = "td-aria-label")]
[HtmlTargetElement(Attributes = "td-title")]
[HtmlTargetElement(Attributes = "td-placeholder")]
[HtmlTargetElement(Attributes = "td-tooltip")]
[HtmlTargetElement(Attributes = "td-alt")]
[HtmlTargetElement(Attributes = "td-summary")]
public sealed class TranslationTagHelper(UiText text) : TagHelper
{
    public override int Order => 1000;
    [HtmlAttributeName("td-text")] public string? Text { get; set; }
    [HtmlAttributeName("td-aria-label")] public string? AriaLabel { get; set; }
    [HtmlAttributeName("td-title")] public string? Title { get; set; }
    [HtmlAttributeName("td-placeholder")] public string? Placeholder { get; set; }
    [HtmlAttributeName("td-tooltip")] public string? Tooltip { get; set; }
    [HtmlAttributeName("td-alt")] public string? Alt { get; set; }
    [HtmlAttributeName("td-summary")] public string? Summary { get; set; }
    [HtmlAttributeName("td-args")] public object?[] Args { get; set; } = [];

    public override void Process(TagHelperContext context, TagHelperOutput output)
    {
        foreach (var (target, key) in new[] { ("text", Text), ("aria-label", AriaLabel), ("title", Title),
            ("placeholder", Placeholder), ("tooltip", Tooltip), ("alt", Alt), ("summary", Summary) })
        {
            output.Attributes.RemoveAll("td-" + target);
            if (string.IsNullOrEmpty(key)) continue;
            output.Attributes.SetAttribute("data-i18n-" + target, key);
            var translated = text.Get(key, Args);
            if (target == "text") output.Content.SetContent(translated);
            else output.Attributes.SetAttribute(target switch { "tooltip" => "data-tooltip", "summary" => "data-list-summary", _ => target }, translated);
        }
        output.Attributes.RemoveAll("td-args");
        if (Args.Length > 0) output.Attributes.SetAttribute("data-i18n-args", JsonSerializer.Serialize(Args));
    }
}
