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

public sealed class DropBrowserTests : IAsyncLifetime
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
        context = await browser.NewContextAsync(new() { BaseURL = address });
        page = await context.NewPageAsync();
        page.SetDefaultTimeout(10000);
        page.PageError += (_, error) => errors.Enqueue(error);
        await LoginAsync(page);
        await page.GotoAsync("/drops/video");
        Assert.True(await page.EvaluateAsync<bool>("() => typeof htmx !== 'undefined'"));
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
        await target.Locator("button[type=submit]").ClickAsync();
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
                Id = Guid.NewGuid(), Slug = slug, Title = i == 0 ? "Watch" : $"Drop {i:D2}",
                Description = "Original description", IsPrivate = true, FileName = slug + ".webm",
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
        await page.Locator("#favorite-button").ClickAsync();
        await IdleAsync();
        await Expect(page.Locator("#favorite-button")).ToHaveAttributeAsync("aria-pressed", "true");
        await Expect(page.Locator("[data-list-favorite]:visible")).ToHaveCountAsync(1);
        await Expect(page).ToHaveURLAsync(address + "/drops/video");
        Assert.True(await page.Locator("video").EvaluateAsync<bool>("v => v === window.originalVideo && !v.paused"));

        await page.Locator("#metadata-open").ClickAsync();
        await page.Locator("#TitleInput").FillAsync("Renamed");
        await page.Locator("#DescriptionInput").FillAsync("Updated description");
        await page.Locator("#metadata-dialog button[type=submit]").ClickAsync();
        await Expect(page.Locator("#metadata-dialog")).Not.ToBeVisibleAsync();
        await Expect(page.Locator("#drop-heading")).ToHaveTextAsync("Renamed");
        await Expect(page.Locator("#drop-description")).ToHaveTextAsync("Updated description");
        await Expect(page.GetByText("검색 결과가 없습니다.", new() { Exact = true })).ToBeVisibleAsync();
        Assert.True(await page.Locator("video").EvaluateAsync<bool>("v => v === window.originalVideo && !v.paused"));

        await page.Locator("#password-open").ClickAsync();
        await page.Locator("#password-form").EvaluateAsync("f => { f.noValidate = true; f.requestSubmit(); }");
        await Expect(page.GetByText("새 드롭 비밀번호를 입력하세요.", new() { Exact = true })).ToBeVisibleAsync();
        Assert.True(await page.Locator("#password-dialog").EvaluateAsync<bool>("d => d.matches(':modal')"));
        await page.Locator("#NewDropPassword").FillAsync("drop-secret");
        await page.Locator("#password-confirm").FillAsync("drop-secret");
        await page.Locator("#password-form button[type=submit]").ClickAsync();
        await Expect(page.Locator("#password-dialog")).Not.ToBeVisibleAsync();
        await page.Locator("#password-open").ClickAsync();
        await Expect(page.Locator("#NewDropPassword")).ToHaveValueAsync("");
        await page.GetByRole(AriaRole.Button, new() { Name = "비밀번호 해제", Exact = true }).ClickAsync();
        await Expect(page.Locator("#password-dialog")).Not.ToBeVisibleAsync();
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
            await page.Locator("#favorite-button").ClickAsync();
            await stored.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await Expect(page.Locator("#favorite-button")).ToHaveAttributeAsync("aria-pressed", "true");
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
        await page.Locator("#favorite-button").ClickAsync();
        await Expect(page.Locator("#favorite-recovery")).ToBeVisibleAsync();
        await page.UnrouteAsync("**/drops/video?handler=Favorite");
        await page.UnrouteAsync("**/drops/video?handler=FavoriteState");
        await page.Locator("[data-favorite-retry]").ClickAsync();
        await IdleAsync();
        await Expect(page.Locator("#drop-favorite")).ToHaveAttributeAsync("data-favorite-value", "true");
        await Expect(page.Locator("#favorite-recovery")).Not.ToBeVisibleAsync();
    }

    [Fact]
    public async Task ConcurrentVisibilityAndPasswordResponsesDoNotOverwriteEachOther()
    {
        var stored = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await page.RouteAsync("**/drops/video?handler=Visibility", async route =>
        {
            var response = await route.FetchAsync();
            stored.SetResult();
            await release.Task;
            await route.FulfillAsync(new() { Response = response });
        });
        try
        {
            await page.Locator("#visibility-button").ClickAsync();
            await stored.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await page.Locator("#password-open").ClickAsync();
            await page.Locator("#NewDropPassword").FillAsync("secret");
            await page.Locator("#password-confirm").FillAsync("secret");
            await page.Locator("#password-form button[type=submit]").ClickAsync();
            await Expect(page.Locator("#password-dialog")).Not.ToBeVisibleAsync();
        }
        finally { release.TrySetResult(); }
        await IdleAsync();
        await Expect(page.Locator("#visibility-button")).ToHaveAttributeAsync("aria-label", "나만 보기로 변경");
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
            await page.Locator("#favorite-button").ClickAsync();
            await stored.Task.WaitAsync(TimeSpan.FromSeconds(10));
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
        await page.Locator("#slug-open").ClickAsync();
        await page.Locator("#SlugInput").FillAsync("unsaved-slug");
        await page.Locator("#url-dialog [data-dialog-close]").ClickAsync();
        try
        {
            await page.Locator("#favorite-button").ClickAsync();
            await captured.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await page.Locator("#visibility-button").ClickAsync();
            await Expect(page.Locator("#visibility-button")).ToHaveAttributeAsync("aria-label", "나만 보기로 변경");
        }
        finally { release.TrySetResult(); }
        await IdleAsync();
        await Expect(page.Locator("#drop-share-state")).ToContainTextAsync("누구나 열 수 있는");
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
            await page.Locator("#favorite-button").ClickAsync();
            await stored.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await page.GetByRole(AriaRole.Combobox, new() { Name = "정렬 기준" }).SelectOptionAsync("title");
            await Expect(page.Locator("#drop-list")).ToHaveAttributeAsync("data-list-state", new System.Text.RegularExpressions.Regex("title"));
            await SearchAsync("Watch");
        }
        finally { release.TrySetResult(); }
        await IdleAsync();
        await Expect(page.Locator("#drop-list .td-drop-row")).ToHaveCountAsync(1);
        await Expect(page.GetByRole(AriaRole.Searchbox)).ToHaveValueAsync("Watch");
        await Expect(page.GetByRole(AriaRole.Combobox, new() { Name = "정렬 기준" })).ToHaveValueAsync("title");
        await Expect(page.Locator("[data-list-favorite]:visible")).ToHaveCountAsync(1);
        await Expect(page).ToHaveURLAsync(address + "/drops/video");
        Assert.Empty(errors);
    }

    [Fact]
    public async Task SlugValidationErrorReleasesNavigationBarrier()
    {
        await page.Locator("#slug-open").ClickAsync();
        await page.Locator("#SlugInput").FillAsync("invalid!");
        await page.Locator("#url-dialog button[type=submit]").ClickAsync();
        await Expect(page.Locator("#url-dialog .field-validation-error")).ToBeVisibleAsync();
        Assert.True(await page.Locator("#url-dialog").EvaluateAsync<bool>("d => d.matches(':modal')"));
        await page.Locator("#url-dialog [data-dialog-close]").ClickAsync();
        await page.Locator("#favorite-button").ClickAsync();
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
    public async Task ParameterizedPdfRendersAndChangesPages()
    {
        await SeedPdfAsync("pdf", locked: false);
        await page.GotoAsync("/drops/pdf");
        var canvas = page.Locator("[data-pdf-canvas]");
        var status = page.Locator("[data-pdf-status]");
        await Expect(canvas).ToBeVisibleAsync();
        await Expect(status).ToHaveTextAsync("1 / 2 페이지");
        await Expect(page.Locator("[data-pdf-prev]")).ToBeDisabledAsync();
        var firstPage = await canvas.EvaluateAsync<string>("c => c.toDataURL()");

        await page.Locator("[data-pdf-next]").ClickAsync();

        await Expect(status).ToHaveTextAsync("2 / 2 페이지");
        Assert.NotEqual(firstPage, await canvas.EvaluateAsync<string>("c => c.toDataURL()"));
        await Expect(page.Locator("[data-pdf-next]")).ToBeDisabledAsync();
        await page.Locator("[data-pdf-prev]").ClickAsync();
        await Expect(status).ToHaveTextAsync("1 / 2 페이지");
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
        await page.Locator("#favorite-button").ClickAsync();
        await page.WaitForURLAsync("**/login");
    }
}
