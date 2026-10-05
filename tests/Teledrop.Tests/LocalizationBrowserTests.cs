using Microsoft.Playwright;
using Xunit;
using static Microsoft.Playwright.Assertions;

namespace Teledrop.Tests;

public sealed partial class DropBrowserTests
{
    private async Task ChooseLanguageAsync(string language)
    {
        await page.Locator("#language-toggle").ClickAsync();
        await page.Locator($"#language-{language}").ClickAsync();
        await Expect(page.Locator("html")).ToHaveAttributeAsync("lang", language);
        await Expect(page.Locator("#language-toggle")).Not.ToHaveAttributeAsync("aria-busy", "true");
    }

    [Fact]
    public async Task LanguageSwitchPreservesMediaDraftsListAndUpdatesLateResponses()
    {
        await page.Locator("video").EvaluateAsync("async video => { window.originalVideo = video; video.muted = true; video.loop = true; await video.play(); }");
        await SearchAsync("Watch");
        await EditDescriptionAsync();
        await page.Locator("#DescriptionInput").FillAsync("Unchanged description 내용");
        var pending = new TaskCompletionSource();
        var release = new TaskCompletionSource();
        await page.RouteAsync("**/*handler=DropList*", async route => {
            var response = await route.FetchAsync(); // Capture a Korean response before switching.
            pending.TrySetResult();
            await release.Task;
            await route.FulfillAsync(new() { Response = response });
        });
        await page.Locator("#drop-list-refresh").ClickAsync();
        await pending.Task.WaitAsync(TimeSpan.FromSeconds(10));
        await ChooseLanguageAsync("en");
        release.SetResult();
        await IdleAsync();
        await Expect(page.Locator("#drop-list-heading")).ToHaveTextAsync("My uploads");
        await Expect(page.Locator("#drop-search-input")).ToHaveValueAsync("Watch");
        await Expect(page.Locator("#drop-list-status")).ToHaveTextAsync("Search results: 1. Page 1 of 1.");
        Assert.True(await page.Locator("video").EvaluateAsync<bool>("v => v === window.originalVideo && !v.paused"));
        // 언어를 바꿔도 편집 중인 설명은 그대로 남고, 편집 영역의 문구만 바뀐다.
        await Expect(page.Locator("#DescriptionInput")).ToHaveValueAsync("Unchanged description 내용");
        await Expect(page.Locator("#drop-description-editor button[type=submit]")).ToHaveTextAsync("Save");
        await page.Locator("[data-description-cancel]").ClickAsync();
        await Expect(page.Locator("#drop-description")).ToHaveTextAsync("Watch");
        await page.UnrouteAsync("**/*handler=DropList*");
        var mutationPending = new TaskCompletionSource();
        var mutationRelease = new TaskCompletionSource();
        await page.RouteAsync("**/*handler=Access*", async route => {
            var response = await route.FetchAsync(); // English mutation response will arrive after switching back.
            mutationPending.TrySetResult();
            await mutationRelease.Task;
            await route.FulfillAsync(new() { Response = response });
        });
        await ChooseAccessAsync("public");
        await mutationPending.Task.WaitAsync(TimeSpan.FromSeconds(10));
        await ChooseLanguageAsync("ko");
        mutationRelease.SetResult();
        await IdleAsync();
        await Expect(page.Locator("#access-toggle")).ToHaveAccessibleNameAsync("공개 범위 링크 공개");
        Assert.Empty(errors);
    }

    [Fact]
    public async Task LanguageSwitchKeepsUploadAndTranslatesExistingErrors()
    {
        await page.GotoAsync("/");
        await page.Locator("#upload-file").SetInputFilesAsync(new FilePayload { Name = "원본.txt", MimeType = "text/plain", Buffer = "sample"u8.ToArray() });
        await page.Locator("#upload-file").EvaluateAsync("e => window.originalInput = e");
        await ChooseLanguageAsync("en");
        Assert.True(await page.Locator("#upload-file").EvaluateAsync<bool>("e => e === window.originalInput && e.files[0].name === '원본.txt'"));
        await Expect(page.Locator("#upload-filename")).ToHaveTextAsync("원본.txt");
        var pending = new TaskCompletionSource();
        var release = new TaskCompletionSource();
        await page.RouteAsync("**/upload", async route => {
            pending.TrySetResult();
            await release.Task;
            await route.FulfillAsync(new() { Status = 413 });
        });
        await page.Locator("#upload-submit").ClickAsync();
        await pending.Task.WaitAsync(TimeSpan.FromSeconds(10));
        await ChooseLanguageAsync("ko");
        await Expect(page.Locator("#upload-progress-title")).ToHaveTextAsync("업로드 중...");
        release.SetResult();
        await Expect(page.Locator("#upload-progress-label")).ToHaveTextAsync("파일이 최대 크기를 초과했습니다.");
        await ChooseLanguageAsync("en");
        await Expect(page.Locator("#upload-progress-label")).ToHaveTextAsync("The file exceeds the maximum size.");
        Assert.True(await page.Locator("#upload-file").EvaluateAsync<bool>("e => e.files.length === 1"));
        Assert.Empty(errors);
    }

    [Fact]
    public async Task LanguageSwitchKeepsPdfPageAndCanvas()
    {
        await SeedPdfAsync("localized-pdf", locked: false);
        await page.GotoAsync("/drops/localized-pdf");
        await Expect(page.Locator("[data-pdf-status]")).ToHaveTextAsync("1 / 2 페이지");
        await page.Locator("[data-pdf-next]").ClickAsync();
        await Expect(page.Locator("[data-pdf-status]")).ToHaveTextAsync("2 / 2 페이지");
        var image = await page.Locator("[data-pdf-canvas]").EvaluateAsync<string>("e => { window.originalCanvas = e; return e.toDataURL(); }");
        await ChooseLanguageAsync("en");
        await Expect(page.Locator("[data-pdf-status]")).ToHaveTextAsync("Page 2 of 2");
        Assert.Equal(image, await page.Locator("[data-pdf-canvas]").EvaluateAsync<string>("e => e.toDataURL()"));
        Assert.True(await page.Locator("[data-pdf-canvas]").EvaluateAsync<bool>("e => e === window.originalCanvas"));
        Assert.Empty(errors);
    }

    [Fact]
    public async Task LanguagePickerKeyboardFailureRetryAndLoginPersistence()
    {
        await context.ClearCookiesAsync();
        await page.GotoAsync("/login");
        await page.Locator("#Username").FillAsync("draft");
        await page.Locator("#Password").FillAsync("secret draft");
        var button = page.Locator("#language-toggle");
        await button.FocusAsync();
        await page.Keyboard.PressAsync("Enter");
        await Expect(page.Locator("#language-ko")).ToBeFocusedAsync();
        await Expect(page.Locator("#language-ko")).ToHaveAttributeAsync("aria-checked", "true");
        await page.Keyboard.PressAsync("End");
        await Expect(page.Locator("#language-en")).ToBeFocusedAsync();
        await page.Keyboard.PressAsync("Escape");
        await Expect(button).ToBeFocusedAsync();
        await Expect(page.Locator("html")).ToHaveAttributeAsync("lang", "ko");
        await button.ClickAsync();
        await page.Keyboard.PressAsync("Tab");
        await Expect(page.Locator("#theme-toggle")).ToBeFocusedAsync();
        await Expect(button).ToHaveAttributeAsync("aria-expanded", "false");
        await page.RouteAsync("**/settings/language", r => r.AbortAsync());
        await button.FocusAsync();
        await page.Keyboard.PressAsync("Enter");
        await page.Keyboard.PressAsync("End");
        await page.Keyboard.PressAsync("Enter");
        await Expect(page.Locator("#language-error")).ToBeVisibleAsync();
        await Expect(page.Locator("html")).ToHaveAttributeAsync("lang", "ko");
        await page.UnrouteAsync("**/settings/language");
        await ChooseLanguageAsync("en");
        await Expect(page.Locator("#Username")).ToHaveValueAsync("draft");
        await Expect(page.Locator("#Password")).ToHaveValueAsync("secret draft");
        await Expect(page).ToHaveTitleAsync("Sign in - teledrop");
        await page.Locator("#Username").FillAsync(TeledropWebApplicationFactory.WebUsername);
        await page.Locator("#Password").FillAsync(TeledropWebApplicationFactory.WebPassword);
        await page.Locator(".td-login button[type=submit]").ClickAsync();
        await page.WaitForURLAsync(address + "/");
        await Expect(page.Locator("html")).ToHaveAttributeAsync("lang", "en");
        await page.GetByRole(AriaRole.Button, new() { Name = "Sign out", Exact = true }).ClickAsync();
        await page.WaitForURLAsync("**/login");
        await Expect(page.Locator("html")).ToHaveAttributeAsync("lang", "en");
        Assert.Empty(errors);
    }

    [Fact]
    public async Task LanguageValidationAndNarrowLayoutsStayAccessible()
    {
        await ChooseLanguageAsync("ko"); // Selecting the detected language also pins the preference.
        Assert.Contains(await context.CookiesAsync(), cookie => cookie.Name == ".AspNetCore.Culture");
        await ChooseAccessAsync("password");
        await page.Locator("#password-form").EvaluateAsync("f => { f.noValidate = true; f.requestSubmit(); }");
        await Expect(page.Locator("#NewDropPassword")).ToHaveAccessibleDescriptionAsync("새 드롭 비밀번호를 입력하세요.");
        await page.Keyboard.PressAsync("Escape");
        await ChooseLanguageAsync("en");
        await ChooseAccessAsync("password");
        await Expect(page.Locator("#NewDropPassword")).ToHaveAccessibleDescriptionAsync("Enter a new file password.");
        await page.Locator("#NewDropPassword").FillAsync("first");
        await page.Locator("#password-confirm").FillAsync("second");
        Assert.Equal("The passwords do not match.", await page.Locator("#password-confirm").EvaluateAsync<string>("e => e.validationMessage"));
        await page.Locator("#password-dialog [data-dialog-close]").ClickAsync();
        await page.SetViewportSizeAsync(320, 800);
        foreach (var lang in new[] { "en", "ko" })
        {
            await ChooseLanguageAsync(lang);
            foreach (var theme in new[] { "light", "dark" })
            {
                await page.EvaluateAsync("t => document.documentElement.dataset.theme = 'teledrop-' + t", theme);
                await page.WaitForTimeoutAsync(180);
                Assert.True(await page.EvaluateAsync<bool>("() => document.documentElement.scrollWidth <= innerWidth"));
                var github = (await page.Locator(".td-topbar a[target=_blank]").BoundingBoxAsync())!;
                var language = (await page.Locator("#language-toggle").BoundingBoxAsync())!;
                var brightness = (await page.Locator("#theme-toggle").BoundingBoxAsync())!;
                Assert.True(github.X + github.Width <= language.X && language.X + language.Width <= brightness.X);
                await page.Locator("#language-toggle").ClickAsync();
                await Expect(page.Locator("#language-options").GetByRole(AriaRole.Menuitemradio)).ToHaveCountAsync(2);
                if (Environment.GetEnvironmentVariable("TELEDROP_CAPTURE_UI") == "1")
                    await page.ScreenshotAsync(new() { Path = Path.Combine(Path.GetTempPath(), $"teledrop-language-{lang}-{theme}.png"), FullPage = true });
                await page.Keyboard.PressAsync("Escape");
            }
        }
        Assert.Empty(errors);
    }

    [Fact]
    public async Task OtherTabsKeepTheirLanguageUntilFullNavigation()
    {
        var other = await context.NewPageAsync();
        await other.GotoAsync("/drops/video");
        await ChooseLanguageAsync("en");
        await Expect(other.Locator("html")).ToHaveAttributeAsync("lang", "ko");
        await other.Locator("#drop-list-refresh").ClickAsync();
        await Expect(other.Locator("#drop-list-status")).ToContainTextAsync("업로드 23 개");
        await Expect(other.Locator("#drop-list-heading")).ToHaveTextAsync("내 업로드");
        await other.ReloadAsync();
        await Expect(other.Locator("html")).ToHaveAttributeAsync("lang", "en");
        await Expect(other.Locator("#drop-list-heading")).ToHaveTextAsync("My uploads");
        await other.CloseAsync();
        Assert.Empty(errors);
    }

    [Fact]
    public async Task LanguageSelectionWorksWithoutJavaScript()
    {
        await using var plain = await browser.NewContextAsync(new() { BaseURL = address, JavaScriptEnabled = false, Locale = "ko-KR" });
        var target = await plain.NewPageAsync();
        await target.GotoAsync("/login?ReturnUrl=%2Fdrops%2Fvideo");
        await target.Locator("#language-native").SelectOptionAsync("en");
        await target.Locator("#language-form button[type=submit]").ClickAsync();
        await Expect(target.Locator("html")).ToHaveAttributeAsync("lang", "en");
        await Expect(target).ToHaveURLAsync(address + "/login?ReturnUrl=%2Fdrops%2Fvideo");
        await Expect(target.GetByLabel("Username", new() { Exact = true })).ToBeVisibleAsync();
    }
}
