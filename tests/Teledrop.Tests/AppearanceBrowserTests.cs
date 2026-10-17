using Microsoft.Playwright;
using Teledrop.Localization;
using Xunit;
using static Microsoft.Playwright.Assertions;

namespace Teledrop.Tests;

public sealed partial class DropBrowserTests
{
    [Theory]
    [InlineData(ColorScheme.Light, "light", "dark", "Theme.Dark", "Theme.Light")]
    [InlineData(ColorScheme.Dark, "dark", "light", "Theme.Light", "Theme.Dark")]
    public async Task ThemeFollowsTheSystemUntilTheOwnerChoosesAndKeepsThatChoice(
        ColorScheme system, string initial, string chosen, string initialLabel, string chosenLabel)
    {
        await page.EmulateMediaAsync(new() { ColorScheme = system });
        await page.EvaluateAsync("() => localStorage.removeItem('teledrop-theme')");
        await page.ReloadAsync();
        var root = page.Locator("html");
        var button = page.Locator("#theme-toggle");
        await Expect(root).ToHaveAttributeAsync("data-theme", "teledrop-" + initial);
        await Expect(button).ToHaveAccessibleNameAsync(UiText.Catalogs["ko"][initialLabel]);

        await button.ClickAsync();

        await Expect(root).ToHaveAttributeAsync("data-theme", "teledrop-" + chosen);
        await Expect(button).ToHaveAccessibleNameAsync(UiText.Catalogs["ko"][chosenLabel]);
        Assert.Equal(chosen, await page.EvaluateAsync<string>("() => localStorage.getItem('teledrop-theme')"));
        // The stored choice takes priority even though the OS still prefers the original theme.
        await page.ReloadAsync();
        await Expect(root).ToHaveAttributeAsync("data-theme", "teledrop-" + chosen);
        await Expect(button).ToHaveAccessibleNameAsync(UiText.Catalogs["ko"][chosenLabel]);
        Assert.Empty(errors);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task ShareLinkCanBeCopiedOrSelectedWhenClipboardAccessIsDenied(bool denied)
    {
        await ConfigureClipboardAsync(denied);
        await page.Locator("#drop-actions-toggle").ClickAsync();
        await page.Locator("#slug-open").ClickAsync();
        var input = page.Locator("#share-link");
        var button = page.Locator("#copy-share-link");
        await Expect(input).ToHaveValueAsync(address + "/video");

        await button.ClickAsync();

        await Expect(button).ToHaveTextAsync(UiText.Catalogs["ko"][denied ? "Copy.Selected" : "Copy.Done"]);
        if (denied)
            Assert.True(await input.EvaluateAsync<bool>(
                "input => document.activeElement === input && input.selectionStart === 0 && input.selectionEnd === input.value.length"));
        else
            Assert.Equal(address + "/video", await page.EvaluateAsync<string>("() => navigator.clipboard.readText()"));
        Assert.Empty(errors);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task HashCopyFeedbackRestoresItsLabelAfterSuccessOrSelectionFallback(bool denied)
    {
        var drop = await HttpTestSupport.SeedDropAsync(factory, "hash-feedback", "hash feedback"u8.ToArray());
        await page.GotoAsync("/drops/hash-feedback");
        await ConfigureClipboardAsync(denied);
        await page.Clock.InstallAsync();
        var hash = page.Locator("[data-file-hash]");
        await Expect(hash).ToBeHiddenAsync();
        await page.Locator(".td-file-card > summary").ClickAsync();
        await Expect(hash).ToHaveTextAsync(drop.FileHash);
        var button = page.Locator("[data-copy-hash]");

        await button.ClickAsync();

        await Expect(button).ToHaveAccessibleNameAsync(UiText.Catalogs["ko"][denied ? "Hash.Selected" : "Copy.Done"]);
        Assert.Equal(drop.FileHash, await page.EvaluateAsync<string>(denied
            ? "() => getSelection().toString()"
            : "() => navigator.clipboard.readText()"));
        await page.Clock.FastForwardAsync(2000);
        await Expect(button).ToHaveAccessibleNameAsync(UiText.Catalogs["ko"]["Hash.Copy"]);
        await Expect(button).ToHaveAttributeAsync("data-tooltip", UiText.Catalogs["ko"]["Hash.Copy"]);
        Assert.Empty(errors);
    }

    private async Task ConfigureClipboardAsync(bool denied)
    {
        if (denied)
            await page.EvaluateAsync("""
                () => Object.defineProperty(navigator.clipboard, 'writeText', {
                    value: async () => { throw new DOMException('Clipboard denied for test', 'NotAllowedError'); }
                })
                """);
        else
            await context.GrantPermissionsAsync(["clipboard-read", "clipboard-write"]);
    }
}
