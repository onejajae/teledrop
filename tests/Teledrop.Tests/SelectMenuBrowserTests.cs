using Microsoft.Playwright;
using Xunit;
using static Microsoft.Playwright.Assertions;

namespace Teledrop.Tests;

public sealed partial class DropBrowserTests
{
    [Fact]
    public async Task SortMenuChoosesFieldAndOrderWithKeyboardAndPointer()
    {
        var button = page.Locator("#drop-sort-toggle");
        var menu = page.Locator("#drop-sort-menu");
        await Expect(button).ToHaveAccessibleNameAsync("정렬 기준 날짜 내림차순");
        await button.FocusAsync();
        await page.Keyboard.PressAsync("Enter");
        await Expect(menu).ToBeVisibleAsync();
        // 선택형 메뉴는 현재 정렬 기준에서 연다.
        await Expect(page.Locator("#drop-sort-created_at")).ToBeFocusedAsync();
        await Expect(page.Locator("#drop-sort-created_at")).ToHaveAttributeAsync("aria-checked", "true");
        await Expect(page.Locator("#drop-sort-desc")).ToHaveAttributeAsync("aria-checked", "true");
        // 현재 값(버튼)도 다른 항목(링크)처럼 메뉴 폭을 다 채워 강조가 오른쪽 끝까지 닿는다.
        var current = (await page.Locator("#drop-sort-created_at").BoundingBoxAsync())!;
        var other = (await page.Locator("#drop-sort-name").BoundingBoxAsync())!;
        Assert.Equal(other.Width, current.Width);
        await page.Keyboard.PressAsync("ArrowDown");
        await Expect(page.Locator("#drop-sort-name")).ToBeFocusedAsync();
        await page.Keyboard.PressAsync("Escape");
        await Expect(menu).ToBeHiddenAsync();
        await Expect(button).ToBeFocusedAsync();
        await Expect(page.Locator("#drop-list")).ToHaveAttributeAsync("data-list-state", new System.Text.RegularExpressions.Regex("\"sort\":\"created_at\""));
        await button.ClickAsync();
        await page.Keyboard.PressAsync("Tab");
        await Expect(button).ToHaveAttributeAsync("aria-expanded", "false");

        await button.FocusAsync();
        await page.Keyboard.PressAsync("Enter");
        await page.Keyboard.PressAsync("ArrowDown");
        await page.Keyboard.PressAsync("Enter");
        await Expect(page.Locator("#drop-list")).ToHaveAttributeAsync("data-list-state", new System.Text.RegularExpressions.Regex("\"sort\":\"name\""));
        await IdleAsync();
        await Expect(button).ToBeFocusedAsync();
        await Expect(button).ToHaveAccessibleNameAsync("정렬 기준 이름 내림차순");

        await button.ClickAsync();
        await page.Locator("#drop-sort-asc").ClickAsync();
        await Expect(page.Locator("#drop-list")).ToHaveAttributeAsync("data-list-state", new System.Text.RegularExpressions.Regex("\"direction\":\"asc\""));
        await IdleAsync();
        await Expect(button).ToHaveAccessibleNameAsync("정렬 기준 이름 오름차순");
        await button.ClickAsync();
        await Expect(page.Locator("#drop-sort-name")).ToHaveAttributeAsync("aria-checked", "true");
        await Expect(page.Locator("#drop-sort-asc")).ToHaveAttributeAsync("aria-checked", "true");
        Assert.Empty(errors);
    }

    [Fact]
    public async Task SortMenuFitsNarrowScreensAndOnlyOneMenuOpensAtATime()
    {
        await page.SetViewportSizeAsync(320, 800);
        foreach (var language in new[] { "ko", "en" })
        {
            await ChooseLanguageAsync(language);
            await Expect(page.Locator("#drop-sort-toggle")).ToHaveAccessibleNameAsync(language == "ko" ? "정렬 기준 날짜 내림차순" : "Sort by Date Descending");
            foreach (var theme in new[] { "light", "dark" })
            {
                await page.EvaluateAsync("t => document.documentElement.dataset.theme = 'teledrop-' + t", theme);
                await page.WaitForTimeoutAsync(180);
                await page.Locator("#language-toggle").ClickAsync();
                await Expect(page.Locator("#language-options")).ToBeVisibleAsync();
                await page.Locator("#drop-sort-toggle").ClickAsync();
                await Expect(page.Locator("#language-options")).ToBeHiddenAsync();
                await Expect(page.Locator("#drop-sort-menu")).ToBeVisibleAsync();
                var bounds = (await page.Locator("#drop-sort-menu").BoundingBoxAsync())!;
                Assert.True(bounds.X >= 0 && bounds.X + bounds.Width <= 320, $"{bounds.X} + {bounds.Width}");
                Assert.True(await page.EvaluateAsync<bool>("() => document.documentElement.scrollWidth <= innerWidth"));
                if (Environment.GetEnvironmentVariable("TELEDROP_CAPTURE_UI") == "1")
                    await page.ScreenshotAsync(new() { Path = Path.Combine(Path.GetTempPath(), $"teledrop-sort-{language}-{theme}.png"), FullPage = true });
                await page.Keyboard.PressAsync("Escape");
                await Expect(page.Locator("#drop-sort-menu")).ToBeHiddenAsync();
                await page.Locator("#drop-sort-toggle").ClickAsync();
                await page.Locator("#theme-toggle").ClickAsync();
                await Expect(page.Locator("#drop-sort-menu")).ToBeHiddenAsync();
            }
        }
        Assert.Empty(errors);
    }

    [Fact]
    public async Task SortingStillWorksWithoutJavaScript()
    {
        await using var plain = await browser.NewContextAsync(new() { BaseURL = address, JavaScriptEnabled = false, Locale = "ko-KR" });
        var target = await plain.NewPageAsync();
        await LoginAsync(target);
        await Expect(target.Locator("#drop-sort-toggle")).ToBeHiddenAsync();
        await target.Locator("#drop-sort-name").ClickAsync();
        await Expect(target.Locator("#drop-list")).ToHaveAttributeAsync("data-list-state", new System.Text.RegularExpressions.Regex("\"sort\":\"name\""));
        await target.Locator("#drop-sort-asc").ClickAsync();
        await Expect(target.Locator("#drop-list")).ToHaveAttributeAsync("data-list-state", new System.Text.RegularExpressions.Regex("\"sort\":\"name\",\"direction\":\"asc\""));
    }
}
