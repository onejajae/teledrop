using System.Collections.Concurrent;
using Isopoh.Cryptography.Argon2;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Playwright;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;
using static Microsoft.Playwright.Assertions;

namespace Teledrop.Tests;

public sealed partial class DropBrowserTests : IAsyncLifetime
{
    private readonly TeledropWebApplicationFactory factory = new();
    private IPlaywright playwright = null!;
    private IBrowser browser = null!;
    private IBrowserContext context = null!;
    private IPage page = null!;
    private string address = null!;
    private readonly ConcurrentQueue<string> errors = new();

    public async Task InitializeAsync()
    {
        factory.UseKestrel(0);
        using var client = factory.CreateClient();
        address = client.BaseAddress!.ToString().TrimEnd('/');
        await SeedAsync();
        playwright = await Playwright.CreateAsync();
        browser = await playwright.Chromium.LaunchAsync(new() { Headless = true });
        context = await browser.NewContextAsync(new() { BaseURL = address, Locale = "ko-KR" });
        page = await context.NewPageAsync();
        page.SetDefaultTimeout(10000);
        page.PageError += (_, error) => errors.Enqueue(error);
        await LoginAsync(page);
        await page.GotoAsync("/drops/video");
        Assert.Equal("4.0.0", await page.EvaluateAsync<string>("() => htmx.version"));
    }

    public async Task DisposeAsync()
    {
        if (context is not null) await context.DisposeAsync();
        if (browser is not null) await browser.DisposeAsync();
        playwright?.Dispose();
        factory.Dispose();
    }

    private async Task LoginAsync(IPage target)
    {
        await target.GotoAsync("/login");
        await target.Locator("#Username").FillAsync(TeledropWebApplicationFactory.WebUsername);
        await target.Locator("#Password").FillAsync(TeledropWebApplicationFactory.WebPassword);
        await target.Locator(".td-login button[type=submit]").ClickAsync();
        await target.WaitForURLAsync(address + "/");
    }

    private async Task SeedAsync()
    {
        var bytes = await File.ReadAllBytesAsync(Path.Combine(AppContext.BaseDirectory, "Fixtures/preview.webm"));
        await using var scope = factory.Services.CreateAsyncScope();
        var db = scope.ServiceProvider.GetRequiredService<TeledropDbContext>();
        for (var i = 0; i < 23; i++)
        {
            var slug = i == 0 ? "video" : $"drop-{i:D2}";
            var location = Guid.NewGuid().ToString("N");
            await File.WriteAllBytesAsync(Path.Combine(factory.ShareDirectory, location), bytes);
            db.Drops.Add(new Drop
            {
                Id = Guid.NewGuid(), Slug = slug,
                Description = i == 0 ? "Watch" : "Original description", IsPrivate = true, FileName = slug + ".webm",
                FileHash = new string('a', 64), FileSizeBytes = bytes.Length, ContentType = "video/webm",
                Location = location, CreatedAt = DateTime.UtcNow.AddMinutes(-i),
            });
        }
        await db.SaveChangesAsync();
    }

    private async Task SearchAsync(string search)
    {
        if (!await page.Locator("#drop-search").EvaluateAsync<bool>("el => el.open"))
            await page.Locator("[data-toggle-search]").ClickAsync();
        await page.GetByRole(AriaRole.Searchbox).FillAsync(search);
        var response = page.WaitForResponseAsync(r => r.Request.Headers.ContainsKey("hx-request") && r.Url.Contains("handler=DropList"));
        await page.Locator(".td-search-row button[type=submit]").ClickAsync();
        await response;
        await Expect(page.Locator("#drop-list")).ToHaveAttributeAsync("data-list-state", new System.Text.RegularExpressions.Regex("\\\"search\\\":\\\"" + search));
    }

    private async Task EditDescriptionAsync()
    {
        await page.Locator("#drop-actions-toggle").ClickAsync();
        await page.Locator("#metadata-open").ClickAsync();
    }

    private async Task ClickFavoriteAsync()
    {
        await page.Locator("#drop-actions-toggle").ClickAsync();
        await page.Locator("#favorite-button").ClickAsync();
    }

    private async Task ChooseAccessAsync(string level)
    {
        await page.Locator("#access-toggle").ClickAsync();
        await page.Locator($"#access-{level}").ClickAsync();
    }

    private async Task IdleAsync()
    {
        await Expect(page.Locator("[data-drop-action][aria-busy=true]")).ToHaveCountAsync(0);
        await Expect(page.Locator(".htmx-request")).ToHaveCountAsync(0);
    }

    [Fact]
    public async Task ChangesPreserveMediaAndListStateAndDialogsCanRetry()
    {
        await page.Locator("video").EvaluateAsync("async video => { window.originalVideo = video; video.muted = true; video.loop = true; await video.play(); }");
        await SearchAsync("Watch");
        await ClickFavoriteAsync();
        await IdleAsync();
        await Expect(page.Locator("#favorite-button")).ToHaveTextAsync("즐겨찾기 해제");
        await Expect(page.Locator("[data-list-favorite]:visible")).ToHaveCountAsync(1);
        await Expect(page).ToHaveURLAsync(address + "/drops/video");
        Assert.True(await page.Locator("video").EvaluateAsync<bool>("v => v === window.originalVideo && !v.paused"));

        await EditDescriptionAsync();
        await Expect(page.Locator("#DescriptionInput")).ToBeFocusedAsync();
        await page.Locator("#DescriptionInput").FillAsync("Updated description");
        await page.Locator("#drop-description-editor button[type=submit]").ClickAsync();
        await Expect(page.Locator("#DescriptionInput")).Not.ToBeVisibleAsync();
        await Expect(page.Locator("#drop-actions-toggle")).ToBeFocusedAsync();
        await Expect(page.Locator("#drop-heading")).ToHaveTextAsync("video.webm");
        await Expect(page.Locator("#drop-description")).ToHaveTextAsync("Updated description");
        await Expect(page.GetByText("검색 결과가 없습니다.", new() { Exact = true })).ToBeVisibleAsync();
        Assert.True(await page.Locator("video").EvaluateAsync<bool>("v => v === window.originalVideo && !v.paused"));

        // 공개 범위는 버튼 하나에 현재 상태를 보여 주고 메뉴에서 바꾼다.
        var access = page.Locator("#access-toggle");
        await Expect(access).ToHaveAccessibleNameAsync("공개 범위 나만 보기");
        await ChooseAccessAsync("password");
        await Expect(page.Locator("#password-title")).ToHaveTextAsync("비밀번호로 공개");
        await Expect(page.Locator("#NewDropPassword")).ToBeFocusedAsync();
        await page.Locator("#password-form").EvaluateAsync("f => { f.noValidate = true; f.requestSubmit(); }");
        await Expect(page.GetByText("새 드롭 비밀번호를 입력하세요.", new() { Exact = true })).ToBeVisibleAsync();
        Assert.True(await page.Locator("#password-dialog").EvaluateAsync<bool>("d => d.matches(':modal')"));
        await page.Locator("#NewDropPassword").FillAsync("drop-secret");
        await page.Locator("#password-confirm").FillAsync("drop-secret");
        await page.Locator("#password-form button[type=submit]").ClickAsync();
        await Expect(page.Locator("#password-dialog")).Not.ToBeVisibleAsync();
        await Expect(access).ToBeFocusedAsync();
        await Expect(access).ToHaveAccessibleNameAsync("공개 범위 비밀번호 공개");
        await Expect(page.Locator("#drop-share-state")).ToContainTextAsync("비밀번호를 아는 사람만");
        await access.ClickAsync();
        await Expect(page.Locator("#access-password")).ToHaveAttributeAsync("aria-checked", "true");
        await page.Locator("#password-change").ClickAsync();
        await Expect(page.Locator("#password-title")).ToHaveTextAsync("비밀번호 변경");
        await Expect(page.Locator("#NewDropPassword")).ToHaveValueAsync("");
        await page.Locator("#password-dialog [data-dialog-close]").ClickAsync();
        await ChooseAccessAsync("public");
        await Expect(page.Locator("#drop-share-state")).ToContainTextAsync("누구나 열 수 있는");
        await Expect(page.Locator("#password-change")).ToHaveCountAsync(0);
        // 다시 비밀번호를 걸었다가 나만 보기로 바꾸면 비밀번호가 함께 지워진다.
        await ChooseAccessAsync("password");
        await page.Locator("#NewDropPassword").FillAsync("drop-secret");
        await page.Locator("#password-confirm").FillAsync("drop-secret");
        await page.Locator("#password-form button[type=submit]").ClickAsync();
        await Expect(page.Locator("#password-dialog")).Not.ToBeVisibleAsync();
        await ChooseAccessAsync("private");
        await Expect(access).ToHaveAccessibleNameAsync("공개 범위 나만 보기");
        await Expect(page.Locator("#drop-share-state")).ToContainTextAsync("소유자만");
        await Expect(page.Locator("#password-change")).ToHaveCountAsync(0);
        Assert.Empty(errors);
    }

    [Fact]
    public async Task FavoriteIsOptimisticAndLostResponseIsReconciled()
    {
        var stored = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var reads = 0;
        page.Request += (_, request) => { if (request.Url.Contains("handler=FavoriteState")) Interlocked.Increment(ref reads); };
        await page.RouteAsync("**/drops/video?handler=Favorite", async route =>
        {
            await route.FetchAsync();
            stored.SetResult();
            await release.Task;
            await route.AbortAsync("failed");
        });
        try
        {
            await ClickFavoriteAsync();
            await stored.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await Expect(page.Locator("#favorite-button")).ToHaveTextAsync("즐겨찾기 해제");
            await Expect(page.Locator("#favorite-button")).ToBeDisabledAsync();
            await Expect(page.Locator("[data-list-favorite]:visible")).ToHaveCountAsync(1);
        }
        finally { release.TrySetResult(); }
        await IdleAsync();
        await Expect(page.Locator("#drop-favorite")).ToHaveAttributeAsync("data-favorite-value", "true");
        await Expect(page.Locator("#favorite-recovery")).Not.ToBeVisibleAsync();
        Assert.Equal(1, reads);
        Assert.Empty(errors);
    }

    [Fact]
    public async Task FailedFavoriteReadOffersExplicitRetryOfOriginalState()
    {
        await page.RouteAsync("**/drops/video?handler=Favorite", route => route.AbortAsync());
        await page.RouteAsync("**/drops/video?handler=FavoriteState", route => route.AbortAsync());
        await ClickFavoriteAsync();
        await Expect(page.Locator("#favorite-recovery")).ToBeVisibleAsync();
        await page.UnrouteAsync("**/drops/video?handler=Favorite");
        await page.UnrouteAsync("**/drops/video?handler=FavoriteState");
        await page.Locator("[data-favorite-retry]").ClickAsync();
        await IdleAsync();
        await Expect(page.Locator("#drop-favorite")).ToHaveAttributeAsync("data-favorite-value", "true");
        await Expect(page.Locator("#favorite-recovery")).Not.ToBeVisibleAsync();
    }

    [Fact]
    public async Task AccessChangesWaitForEachOther()
    {
        var stored = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await page.RouteAsync("**/drops/video?handler=Access", async route =>
        {
            var response = await route.FetchAsync();
            if (stored.TrySetResult()) await release.Task;
            await route.FulfillAsync(new() { Response = response });
        });
        try
        {
            await ChooseAccessAsync("public");
            await stored.Task.WaitAsync(TimeSpan.FromSeconds(10));
            // 공개 범위 응답이 메뉴와 비밀번호 대화상자를 새로 그리므로, 변경이 끝나기 전에는 열 수 없다.
            await Expect(page.Locator("#access-toggle")).ToBeDisabledAsync();
        }
        finally { release.TrySetResult(); }
        await IdleAsync();
        await Expect(page.Locator("#access-toggle")).ToHaveAccessibleNameAsync("공개 범위 링크 공개");
        await ChooseAccessAsync("password");
        await Expect(page.Locator("#password-title")).ToHaveTextAsync("비밀번호로 공개");
        await page.Locator("#NewDropPassword").FillAsync("secret");
        await page.Locator("#password-confirm").FillAsync("secret");
        await page.Locator("#password-form button[type=submit]").ClickAsync();
        await Expect(page.Locator("#password-dialog")).Not.ToBeVisibleAsync();
        await IdleAsync();
        await Expect(page.Locator("#access-toggle")).ToHaveAccessibleNameAsync("공개 범위 비밀번호 공개");
        await Expect(page.Locator("#drop-share-state")).ToContainTextAsync("비밀번호를 아는 사람만");
        Assert.Empty(errors);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task NavigationWaitsForExistingSave(bool delete)
    {
        var stored = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var navigationSent = false;
        page.Request += (_, r) => { if (r.Method == "POST" && (r.Url.Contains("handler=Slug") || r.Url.Contains("handler=Delete"))) navigationSent = true; };
        await page.RouteAsync("**/drops/video?handler=Favorite", async route =>
        {
            var response = await route.FetchAsync(); stored.SetResult(); await release.Task;
            await route.FulfillAsync(new() { Response = response });
        });
        try
        {
            await ClickFavoriteAsync();
            await stored.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await page.Locator("#drop-actions-toggle").ClickAsync();
            await page.Locator(delete ? "#delete-open" : "#slug-open").ClickAsync();
            if (!delete) await page.Locator("#SlugInput").FillAsync("renamed-video");
            await page.Locator(delete ? "#delete-dialog button[type=submit]" : "#url-dialog button[type=submit]").ClickAsync();
            await Expect(page.Locator("#drop-navigation-status")).ToBeVisibleAsync();
            Assert.False(navigationSent);
        }
        finally { release.TrySetResult(); }
        await page.WaitForURLAsync(delete ? "**/?deleted=True" : "**/drops/renamed-video");
        Assert.True(navigationSent);
        Assert.Empty(errors);
    }

    [Fact]
    public async Task StaleSharedReadIsDiscardedAndOtherDialogDraftIsPreserved()
    {
        var captured = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var count = 0;
        await page.RouteAsync("**/drops/video?handler=SharedState", async route =>
        {
            var response = await route.FetchAsync();
            if (Interlocked.Increment(ref count) == 1)
            {
                captured.SetResult(); await release.Task;
            }
            await route.FulfillAsync(new() { Response = response });
        });
        await page.Locator("#drop-actions-toggle").ClickAsync();
        await page.Locator("#slug-open").ClickAsync();
        await page.Locator("#SlugInput").FillAsync("unsaved-slug");
        await page.Locator("#url-dialog [data-dialog-close]").ClickAsync();
        try
        {
            await ClickFavoriteAsync();
            await captured.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await ChooseAccessAsync("public");
            await Expect(page.Locator("#drop-access")).ToHaveAttributeAsync("data-access-level", "public");
        }
        finally { release.TrySetResult(); }
        await IdleAsync();
        await Expect(page.Locator("#drop-share-state")).ToContainTextAsync("누구나 열 수 있는");
        await page.Locator("#drop-actions-toggle").ClickAsync();
        await page.Locator("#slug-open").ClickAsync();
        await Expect(page.Locator("#SlugInput")).ToHaveValueAsync("unsaved-slug");
        Assert.True(count >= 2);
        Assert.Empty(errors);
    }

    [Fact]
    public async Task NewListConditionsWinWhileMutationIsInFlight()
    {
        var stored = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await page.RouteAsync("**/drops/video?handler=Favorite", async route =>
        {
            var response = await route.FetchAsync(); stored.SetResult(); await release.Task;
            await route.FulfillAsync(new() { Response = response });
        });
        try
        {
            await ClickFavoriteAsync();
            await stored.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await page.Locator("#drop-sort-toggle").ClickAsync();
            await page.Locator("#drop-sort-name").ClickAsync();
            await Expect(page.Locator("#drop-list")).ToHaveAttributeAsync("data-list-state", new System.Text.RegularExpressions.Regex("\"sort\":\"name\""));
            await SearchAsync("Watch");
        }
        finally { release.TrySetResult(); }
        await IdleAsync();
        await Expect(page.Locator("#drop-list .td-drop-row")).ToHaveCountAsync(1);
        await Expect(page.GetByRole(AriaRole.Searchbox)).ToHaveValueAsync("Watch");
        await Expect(page.Locator("#drop-sort-current")).ToHaveTextAsync("이름");
        await Expect(page.Locator("[data-list-favorite]:visible")).ToHaveCountAsync(1);
        await Expect(page).ToHaveURLAsync(address + "/drops/video");
        Assert.Empty(errors);
    }

    [Fact]
    public async Task SlugValidationErrorReleasesNavigationBarrier()
    {
        await page.Locator("#drop-actions-toggle").ClickAsync();
        await page.Locator("#slug-open").ClickAsync();
        await page.Locator("#SlugInput").FillAsync("invalid!");
        await page.Locator("#url-dialog button[type=submit]").ClickAsync();
        await Expect(page.Locator("#url-dialog .field-validation-error")).ToBeVisibleAsync();
        Assert.True(await page.Locator("#url-dialog").EvaluateAsync<bool>("d => d.matches(':modal')"));
        await page.Locator("#url-dialog [data-dialog-close]").ClickAsync();
        await ClickFavoriteAsync();
        await IdleAsync();
        await Expect(page.Locator("#drop-favorite")).ToHaveAttributeAsync("data-favorite-value", "true");
        Assert.Empty(errors);
    }

    [Fact]
    public async Task PublicUnlockRendersErrorsAndThenPreviewWithoutNavigation()
    {
        await using (var scope = factory.Services.CreateAsyncScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<TeledropDbContext>();
            var drop = await db.Drops.SingleAsync(d => d.Slug == "video");
            drop.IsPrivate = false; drop.DropPasswordHash = Argon2.Hash("secret");
            await db.SaveChangesAsync();
        }
        await context.ClearCookiesAsync();
        await page.GotoAsync("/video");
        await page.Locator("#DropPassword").FillAsync("wrong");
        await page.Locator("[data-public-unlock] button[type=submit]").ClickAsync();
        await Expect(page.GetByText("드롭 비밀번호가 올바르지 않습니다.", new() { Exact = true })).ToBeVisibleAsync();
        await Expect(page.Locator("#DropPassword")).ToHaveValueAsync("");
        await Expect(page.Locator("video")).ToHaveCountAsync(0);
        await page.EvaluateAsync("() => { window.unlockDocument = document.body; }");
        await page.Locator("#DropPassword").FillAsync("secret");
        await page.Locator("[data-public-unlock] button[type=submit]").ClickAsync();
        await Expect(page.Locator("video")).ToBeVisibleAsync();
        Assert.True(await page.EvaluateAsync<bool>("() => window.unlockDocument === document.body"));
        await Expect(page).ToHaveURLAsync(address + "/video");
        Assert.Empty(errors);
    }

    [Fact]
    public async Task KeyboardListAndActionsKeepFocusAndAnnounceResults()
    {
        await Expect(page.Locator("#drop-sort-toggle")).ToHaveAccessibleNameAsync("정렬 기준 날짜 내림차순");
        await page.Locator("[data-toggle-search]").ClickAsync();
        await Expect(page.Locator("#drop-search > summary")).ToBeHiddenAsync();
        await page.Locator("[data-toggle-search]").FocusAsync();
        await page.Keyboard.PressAsync("Enter");
        await Expect(page.Locator("[data-toggle-search]")).ToHaveAttributeAsync("aria-expanded", "false");
        await Expect(page.Locator("[data-toggle-search]")).ToBeFocusedAsync();
        await page.Keyboard.PressAsync("Enter");
        await page.Locator("#drop-search-input").FillAsync("Watch");
        await page.Locator("#drop-search-submit").FocusAsync();
        await page.Keyboard.PressAsync("Enter");
        await Expect(page.Locator("#drop-list-status")).ToContainTextAsync("검색 결과 1 개");
        await Expect(page.Locator("#drop-search-submit")).ToBeFocusedAsync();
        await page.Locator("#drop-search-input").FillAsync("");
        await page.Locator("#drop-search-submit").FocusAsync();
        await page.Keyboard.PressAsync("Enter");
        await Expect(page.Locator("#drop-list-status")).ToContainTextAsync("업로드 23 개");
        await Expect(page.Locator("#drop-search-toggle")).ToBeFocusedAsync();
        // 공개 범위 메뉴는 현재 값에서 열리고, 고른 뒤에는 메뉴 버튼으로 돌아온다.
        await page.Locator("#access-toggle").FocusAsync();
        await page.Keyboard.PressAsync("Enter");
        await Expect(page.Locator("#access-private")).ToBeFocusedAsync();
        await page.Keyboard.PressAsync("ArrowDown");
        await page.Keyboard.PressAsync("Enter");
        await Expect(page.Locator("#drop-access")).ToHaveAttributeAsync("data-access-level", "public");
        await IdleAsync();
        await Expect(page.Locator("#access-toggle")).ToBeFocusedAsync();
        // 즐겨찾기는 ⋯ 메뉴의 체크 항목이며, 고른 뒤에는 메뉴 버튼으로 돌아온다.
        await page.Locator("#drop-actions-toggle").FocusAsync();
        await page.Keyboard.PressAsync("Enter");
        await Expect(page.Locator("#favorite-button")).ToBeFocusedAsync();
        await page.Keyboard.PressAsync("Enter");
        await Expect(page.Locator("#favorite-button")).ToHaveTextAsync("즐겨찾기 해제");
        await IdleAsync();
        await Expect(page.Locator("#drop-actions-toggle")).ToBeFocusedAsync();
        Assert.Empty(errors);
    }

    [Fact]
    public async Task ListPaginationAndDelayedRefreshRespectKeyboardPosition()
    {
        await page.GotoAsync("/");
        await page.Locator("#drop-list-next").FocusAsync();
        await page.Keyboard.PressAsync("Enter");
        await Expect(page.Locator("#drop-list-status")).ToContainTextAsync("2 / 2 페이지");
        await Expect(page.Locator("#drop-list-heading")).ToBeFocusedAsync();
        await page.Locator("#drop-list-prev").ClickAsync();
        await Expect(page.Locator("#drop-list-status")).ToContainTextAsync("1 / 2 페이지");
        await page.Locator("#drop-sort-toggle").FocusAsync();
        await page.Keyboard.PressAsync("Enter");
        await page.Keyboard.PressAsync("ArrowDown");
        await page.Keyboard.PressAsync("Enter");
        await IdleAsync();
        await Expect(page.Locator("#drop-sort-toggle")).ToBeFocusedAsync();
        var pending = new TaskCompletionSource<IRoute>();
        var release = new TaskCompletionSource();
        await page.RouteAsync("**/*handler=DropList*", async route => {
            pending.TrySetResult(route);
            await release.Task;
            await route.ContinueAsync();
        });
        await page.Locator("#drop-list-refresh").ClickAsync();
        await pending.Task.WaitAsync(TimeSpan.FromSeconds(10));
        await page.Locator("#theme-toggle").FocusAsync();
        release.SetResult();
        await IdleAsync();
        await Expect(page.Locator("#theme-toggle")).ToBeFocusedAsync();
        Assert.Empty(errors);
    }

    [Fact]
    public async Task ThemesMeetContrastAndTooltipRemainsHoverable()
    {
        await page.GotoAsync("/");
        await page.SetViewportSizeAsync(320, 800);
        foreach (var theme in new[] { "light", "dark" })
        {
            await page.EvaluateAsync("theme => document.documentElement.dataset.theme = 'teledrop-' + theme", theme);
            // Wait for the theme color transition before measuring its final colors.
            await page.WaitForTimeoutAsync(200);
            var ratios = await page.EvaluateAsync<double[]>("""
                () => {
                    const luminance = color => {
                        const c = color.match(/[\d.]+/g).slice(0, 3).map(v => Number(v) / 255)
                            .map(v => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
                        return c[0] * .2126 + c[1] * .7152 + c[2] * .0722;
                    };
                    const ratio = (a, b) => {
                        const [low, high] = [luminance(a), luminance(b)].sort((a,b) => a-b);
                        return (high + .05) / (low + .05);
                    };
                    const prompt = getComputedStyle(document.querySelector('#upload-prompt'));
                    const zone = getComputedStyle(document.querySelector('#upload-zone'));
                    const sort = getComputedStyle(document.querySelector('#drop-sort-toggle'));
                    const surface = getComputedStyle(document.querySelector('#drop-list'));
                    return [ratio(prompt.color, zone.backgroundColor), ratio(sort.color, surface.backgroundColor)];
                }
                """);
            Assert.True(ratios[0] >= 4.5, $"{theme} text contrast {ratios[0]}");
            Assert.True(ratios[1] >= 4.5, $"{theme} sort text contrast {ratios[1]}");
            Assert.True(await page.EvaluateAsync<bool>("() => document.documentElement.scrollWidth <= innerWidth"));
        }
        var button = page.Locator("#drop-search-toggle");
        await button.HoverAsync();
        var bounds = (await button.BoundingBoxAsync())!;
        await page.Mouse.MoveAsync(bounds.X + bounds.Width / 2, bounds.Y - 8);
        Assert.Equal("visible", await button.EvaluateAsync<string>("e => getComputedStyle(e, '::after').visibility"));
        await page.Keyboard.PressAsync("Escape");
        Assert.Equal("hidden", await button.EvaluateAsync<string>("e => getComputedStyle(e, '::after').visibility"));
    }

    [Fact]
    public async Task ActionMenuWorksWithKeyboardAndReturnsFocus()
    {
        var toggle = page.Locator("#drop-actions-toggle");
        var menu = page.Locator("#drop-actions");
        await Expect(toggle).ToHaveAccessibleNameAsync("더보기");
        await Expect(menu).ToBeHiddenAsync();
        await toggle.FocusAsync();
        await page.Keyboard.PressAsync("Enter");
        await Expect(toggle).ToHaveAttributeAsync("aria-expanded", "true");
        await Expect(page.Locator("#favorite-button")).ToBeFocusedAsync();
        await page.Keyboard.PressAsync("ArrowDown");
        await Expect(page.Locator("#metadata-open")).ToBeFocusedAsync();
        await page.Keyboard.PressAsync("ArrowDown");
        await Expect(page.Locator("#slug-open")).ToBeFocusedAsync();
        await page.Keyboard.PressAsync("ArrowDown");
        await Expect(page.Locator("#delete-open")).ToBeFocusedAsync();
        await page.Keyboard.PressAsync("ArrowDown");
        await Expect(page.Locator("#favorite-button")).ToBeFocusedAsync();
        await page.Keyboard.PressAsync("Escape");
        await Expect(menu).ToBeHiddenAsync();
        await Expect(toggle).ToBeFocusedAsync();
        await Expect(toggle).ToHaveAttributeAsync("aria-expanded", "false");

        // 메뉴에서 연 대화상자를 닫으면 숨은 항목 대신 메뉴 버튼으로 돌아간다.
        await page.Keyboard.PressAsync("ArrowUp");
        await Expect(page.Locator("#delete-open")).ToBeFocusedAsync();
        await page.Keyboard.PressAsync("Enter");
        await Expect(page.Locator("#delete-dialog")).ToBeVisibleAsync();
        await Expect(menu).ToBeHiddenAsync();
        await page.Keyboard.PressAsync("Escape");
        await Expect(page.Locator("#delete-dialog")).Not.ToBeVisibleAsync();
        await Expect(toggle).ToBeFocusedAsync();

        await toggle.ClickAsync();
        await Expect(menu).ToBeVisibleAsync();
        await page.Mouse.ClickAsync(5, 5);
        await Expect(menu).ToBeHiddenAsync();

        // 좁은 화면에서도 공개 범위 메뉴가 화면 안에 들어온다.
        await page.SetViewportSizeAsync(320, 800);
        await page.Locator("#access-toggle").ClickAsync();
        var bounds = (await page.Locator("#access-menu").BoundingBoxAsync())!;
        Assert.True(bounds.X >= 0 && bounds.X + bounds.Width <= 320, $"{bounds.X} + {bounds.Width}");
        Assert.Empty(errors);
    }

    [Fact]
    public async Task ValidationExplainsTheErrorAndTooltipCanBeDismissed()
    {
        await page.Locator("#access-toggle").FocusAsync();
        await page.Keyboard.PressAsync("Enter");
        await page.Keyboard.PressAsync("End");
        await Expect(page.Locator("#access-password")).ToBeFocusedAsync();
        await page.Keyboard.PressAsync("Enter");
        await page.Locator("#password-form").EvaluateAsync("f => { f.noValidate = true; f.requestSubmit(); }");
        var input = page.Locator("#NewDropPassword");
        await Expect(input).ToBeFocusedAsync();
        await Expect(input).ToHaveAttributeAsync("aria-invalid", "true");
        await Expect(input).ToHaveAccessibleDescriptionAsync("새 드롭 비밀번호를 입력하세요.");
        await page.Keyboard.PressAsync("Escape");
        // 메뉴에서 연 대화상자를 닫으면 공개 범위 버튼으로 돌아온다.
        await Expect(page.Locator("#access-toggle")).ToBeFocusedAsync();
        var actions = page.Locator("#drop-actions-toggle");
        await actions.FocusAsync();
        await page.Keyboard.PressAsync("Escape");
        await Expect(actions).ToHaveAttributeAsync("data-tooltip-dismissed", "");
        await Expect(actions).ToBeFocusedAsync();
        Assert.Equal("hidden", await actions.EvaluateAsync<string>("e => getComputedStyle(e, '::after').visibility"));
        Assert.Empty(errors);
    }

    [Fact]
    public async Task DescriptionEditsInPlace()
    {
        await page.GotoAsync("/drops/drop-01");
        var input = page.Locator("#DescriptionInput");
        var actions = page.Locator("#drop-actions-toggle");
        await Expect(input).ToBeHiddenAsync();

        // 설명 글자를 눌러도 편집이 열리지 않는다. 편집은 ⋯ 메뉴에서만 연다.
        await page.Locator("#drop-description").ClickAsync();
        await Expect(input).ToBeHiddenAsync();
        await EditDescriptionAsync();
        await Expect(input).ToBeFocusedAsync();
        await input.FillAsync("Discarded");
        await page.Keyboard.PressAsync("Escape");
        await Expect(input).ToBeHiddenAsync();
        await Expect(page.Locator("#drop-description")).ToHaveTextAsync("Original description");
        await Expect(actions).ToBeFocusedAsync();

        await EditDescriptionAsync();
        await input.FillAsync("Saved with keyboard");
        await page.Keyboard.PressAsync("Control+Enter");
        await Expect(page.Locator("#drop-description")).ToHaveTextAsync("Saved with keyboard");
        await Expect(actions).ToBeFocusedAsync();

        // 설명을 비우면 설명 자리가 사라지고, 메뉴 항목은 "설명 추가"가 된다.
        await EditDescriptionAsync();
        await input.FillAsync("");
        await page.Locator("#drop-description-editor button[type=submit]").ClickAsync();
        await Expect(page.Locator("#drop-description")).ToHaveCountAsync(0);
        await Expect(page.Locator("#drop-description-editor")).ToBeHiddenAsync();
        await Expect(page.Locator("#metadata-open")).ToHaveTextAsync("설명 추가");
        await EditDescriptionAsync();
        await Expect(input).ToBeFocusedAsync();
        await Expect(input).ToHaveAttributeAsync("placeholder", "설명");
        await page.Locator("[data-description-cancel]").ClickAsync();
        await Expect(page.Locator("#drop-description-editor")).ToBeHiddenAsync();
        Assert.Empty(errors);
    }

    [Fact]
    public async Task DescriptionSavesWithoutJavaScript()
    {
        await using var plain = await browser.NewContextAsync(new() { BaseURL = address, JavaScriptEnabled = false, Locale = "ko-KR" });
        var target = await plain.NewPageAsync();
        await LoginAsync(target);
        await target.GotoAsync("/drops/drop-02");
        var input = target.Locator("#DescriptionInput");
        await Expect(input).ToBeVisibleAsync();
        await input.FillAsync("No script description");
        await target.Locator("#drop-description-editor button[type=submit]").ClickAsync();
        await Expect(target.Locator("#DescriptionInput")).ToHaveValueAsync("No script description");
    }

    [Fact]
    public async Task ActiveSearchStaysOpenUntilCleared()
    {
        await SearchAsync("Watch");
        var panel = page.Locator("#drop-search");
        await page.Locator("[data-toggle-search]").ClickAsync();
        Assert.True(await panel.EvaluateAsync<bool>("el => el.open"));
        await Expect(page.GetByRole(AriaRole.Searchbox)).ToBeFocusedAsync();

        var response = page.WaitForResponseAsync(r => r.Request.Headers.ContainsKey("hx-request") && r.Url.Contains("handler=DropList"));
        await page.Locator("#drop-search-clear").ClickAsync();
        await response;

        await Expect(page.Locator("#drop-list")).ToHaveAttributeAsync("data-list-state", new System.Text.RegularExpressions.Regex("\\\"search\\\":null"));
        await Expect(page.Locator("#drop-search-clear")).ToHaveCountAsync(0);
        Assert.False(await panel.EvaluateAsync<bool>("el => el.open"));
        Assert.Empty(errors);
    }

    [Fact]
    public async Task ParameterizedPdfRendersAndChangesPages()
    {
        await SeedPdfAsync("pdf", locked: false);
        await page.GotoAsync("/drops/pdf");
        var canvas = page.Locator("[data-pdf-canvas]");
        var status = page.Locator("[data-pdf-status]");
        await Expect(canvas).ToBeVisibleAsync();
        await Expect(status).ToHaveTextAsync("1 / 2 페이지");
        await Expect(page.Locator("[data-pdf-prev]")).ToBeDisabledAsync();
        var open = page.Locator("[data-pdf-open]");
        await Expect(open).ToHaveAttributeAsync("href", "/d/pdf?inline=true");
        await Expect(open).ToHaveAttributeAsync("target", "_blank");
        await Expect(open).ToHaveAccessibleNameAsync("새 탭에서 PDF 열기");
        var firstPage = await canvas.EvaluateAsync<string>("c => c.toDataURL()");

        await page.Locator("[data-pdf-next]").ClickAsync();

        await Expect(status).ToHaveTextAsync("2 / 2 페이지");
        await Expect(page.Locator("[data-pdf-prev]")).ToBeFocusedAsync();
        Assert.NotEqual(firstPage, await canvas.EvaluateAsync<string>("c => c.toDataURL()"));
        await Expect(page.Locator("[data-pdf-next]")).ToBeDisabledAsync();
        await page.Locator("[data-pdf-prev]").ClickAsync();
        await Expect(status).ToHaveTextAsync("1 / 2 페이지");
        Assert.Empty(errors);
    }

    [Fact]
    public async Task FileDetailsShowAndCopyTheSha256Hash()
    {
        await SeedPdfAsync("hash-pdf", locked: false);
        var bytes = await File.ReadAllBytesAsync(Path.Combine(AppContext.BaseDirectory, "Fixtures/preview.pdf"));
        var expected = Convert.ToHexStringLower(System.Security.Cryptography.SHA256.HashData(bytes));
        await context.GrantPermissionsAsync(["clipboard-read", "clipboard-write"]);
        await page.GotoAsync("/drops/hash-pdf");
        var hash = page.Locator("[data-file-hash]");
        await Expect(hash).ToBeHiddenAsync();

        await page.Locator(".td-file-card > summary").ClickAsync();

        await Expect(hash).ToHaveTextAsync(expected);
        await page.Locator("[data-copy-hash]").ClickAsync();
        await Expect(page.Locator("[data-copy-hash]")).ToHaveAccessibleNameAsync("복사됨");
        Assert.Equal(expected, await page.EvaluateAsync<string>("() => navigator.clipboard.readText()"));
        Assert.Empty(errors);
    }

    [Fact]
    public async Task LockedPdfInitializesAfterUnlockWithoutReplacingTheDocument()
    {
        await SeedPdfAsync("locked-pdf", locked: true);
        await context.ClearCookiesAsync();
        await page.GotoAsync("/locked-pdf");
        await Expect(page.Locator("[data-pdf-canvas]")).ToHaveCountAsync(0);
        await page.EvaluateAsync("() => { window.pdfDocumentBeforeUnlock = document.body; }");
        await page.Locator("#DropPassword").FillAsync("secret");

        await page.Locator("[data-public-unlock] button[type=submit]").ClickAsync();

        await Expect(page.Locator("[data-pdf-canvas]")).ToBeVisibleAsync();
        await Expect(page.Locator("[data-pdf-status]")).ToHaveTextAsync("1 / 2 페이지");
        Assert.True(await page.EvaluateAsync<bool>("() => document.body === window.pdfDocumentBeforeUnlock"));
        await Expect(page).ToHaveURLAsync(address + "/locked-pdf");
        Assert.Empty(errors);
    }

    private async Task SeedPdfAsync(string slug, bool locked)
    {
        var bytes = await File.ReadAllBytesAsync(Path.Combine(AppContext.BaseDirectory, "Fixtures/preview.pdf"));
        await HttpTestSupport.SeedDropAsync(factory, slug, bytes, drop =>
        {
            drop.FileName = "preview.pdf";
            drop.ContentType = "APPLICATION/PDF; charset=binary";
            drop.IsPrivate = !locked;
            drop.DropPasswordHash = locked ? Argon2.Hash("secret") : null;
        });
    }

    [Fact]
    public async Task UploadOpensItsNewDetailAndExpiredSessionNavigatesToLogin()
    {
        await page.GotoAsync("/");
        await page.Locator("#upload-file").SetInputFilesAsync(new FilePayload
        {
            Name = "uploaded.txt", MimeType = "text/plain", Buffer = "browser upload"u8.ToArray(),
        });
        await page.Locator("#upload-submit").ClickAsync();
        await page.WaitForURLAsync("**/drops/*");
        await Expect(page.GetByText("uploaded.txt", new() { Exact = true }).First).ToBeVisibleAsync();
        factory.ChangeWebPassword();
        await ClickFavoriteAsync();
        await page.WaitForURLAsync("**/login");
    }

    [Theory]
    [InlineData(413)]
    [InlineData(0)]
    public async Task UploadCanRetryAfterRejectionOrNetworkFailure(int failureStatus)
    {
        await page.GotoAsync("/");
        var firstRequest = true;
        await page.RouteAsync("**/upload", async route =>
        {
            if (!firstRequest) { await route.ContinueAsync(); return; }
            firstRequest = false;
            if (failureStatus == 0) await route.AbortAsync("failed");
            else await route.FulfillAsync(new() { Status = failureStatus });
        });
        await page.Locator("#upload-file").SetInputFilesAsync(new FilePayload
        {
            Name = "retry.txt", MimeType = "text/plain", Buffer = "retry upload"u8.ToArray(),
        });
        await page.Locator("#upload-submit").ClickAsync();
        await Expect(page.Locator("#upload-progress-label")).ToHaveTextAsync(
            failureStatus == 413 ? "파일이 최대 크기를 초과했습니다." : "업로드에 실패했습니다.");
        await Expect(page.Locator("#upload-submit")).ToBeEnabledAsync();
        await Expect(page.Locator("#upload-submit")).ToBeFocusedAsync();
        await Expect(page.Locator("#upload-progress")).ToHaveAccessibleNameAsync("파일 업로드 진행률");
        await page.Locator("#upload-submit").ClickAsync();
        await page.WaitForURLAsync("**/drops/*");
        await Expect(page.GetByText("retry.txt", new() { Exact = true }).First).ToBeVisibleAsync();
        Assert.Empty(errors);
    }
}
