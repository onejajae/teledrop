using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Playwright;
using Teledrop.Data;
using Xunit;
using static Microsoft.Playwright.Assertions;

namespace Teledrop.Tests;

public sealed partial class DropBrowserTests
{
    [Theory]
    [InlineData("Access", 0)]
    [InlineData("Access", 500)]
    [InlineData("Slug", 0)]
    [InlineData("Slug", 500)]
    [InlineData("Delete", 0)]
    [InlineData("Delete", 500)]
    public async Task UncommittedManagementFailuresKeepTheirDraftsAndAllowAnExplicitRetry(string handler, int status)
    {
        var dialog = await OpenManagementDialogAsync(handler);
        var routePattern = $"**/drops/video?handler={handler}";
        await page.RouteAsync(routePattern, route => status == 0
            ? route.AbortAsync()
            : route.FulfillAsync(new() { Status = status, ContentType = "text/html", Body = "<h1>Rejected mutation</h1>" }));

        await page.Locator($"#{dialog} button[type=submit]").ClickAsync();

        await Expect(page.Locator($"#{dialog} [data-operation-error]")).ToBeVisibleAsync();
        await IdleAsync();
        await Expect(page).ToHaveURLAsync(address + "/drops/video");
        Assert.True(await page.Locator("#" + dialog).EvaluateAsync<bool>("dialog => dialog.matches(':modal')"));
        await Expect(page.Locator($"#{dialog} button[type=submit]")).ToBeEnabledAsync();
        await Expect(page.Locator("#drop-navigation-status")).ToBeHiddenAsync();
        if (handler == "Access")
        {
            await Expect(page.Locator("#NewDropPassword")).ToHaveValueAsync("retained-password");
            await Expect(page.Locator("#password-confirm")).ToHaveValueAsync("retained-password");
        }
        else if (handler == "Slug")
            await Expect(page.Locator("#SlugInput")).ToHaveValueAsync("renamed-after-retry");
        await using (var scope = factory.Services.CreateAsyncScope())
        {
            var drop = await scope.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops.SingleAsync(drop => drop.Slug == "video");
            Assert.True(drop.IsPrivate);
            Assert.Null(drop.DropPasswordHash);
        }
        await page.UnrouteAsync(routePattern);

        await page.Locator($"#{dialog} button[type=submit]").ClickAsync();

        if (handler == "Access")
        {
            await Expect(page.Locator("#password-dialog")).ToBeHiddenAsync();
            await Expect(page.Locator("#drop-access")).ToHaveAttributeAsync("data-access-level", "password");
        }
        else
            await page.WaitForURLAsync(handler == "Delete" ? "**/?deleted=True" : "**/drops/renamed-after-retry");
        Assert.Empty(errors);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task LostAccessResponseReadsTheCommittedVisibilityWithoutRepeatingTheMutation(bool password)
    {
        await page.Locator("video").EvaluateAsync("video => window.videoBeforeAccessRecovery = video");
        var committed = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var writes = 0;
        await page.RouteAsync("**/drops/video?handler=Access", async route =>
        {
            Interlocked.Increment(ref writes);
            var response = await route.FetchAsync();
            Assert.True(response.Ok);
            committed.TrySetResult();
            await route.AbortAsync();
        });

        if (password)
        {
            await OpenManagementDialogAsync("Access");
            await page.Locator("#password-form button[type=submit]").ClickAsync();
        }
        else await ChooseAccessAsync("public");
        await committed.Task.WaitAsync(TimeSpan.FromSeconds(10));

        await Expect(page.Locator("#drop-access")).ToHaveAttributeAsync("data-access-level", password ? "password" : "public");
        await Expect(page.Locator("#drop-share-state")).ToContainTextAsync(password ? "비밀번호를 아는 사람만" : "누구나 열 수 있는");
        await IdleAsync();
        Assert.Equal(1, writes);
        Assert.True(await page.Locator("video").EvaluateAsync<bool>("video => video === window.videoBeforeAccessRecovery"));
        if (password)
        {
            await Expect(page.Locator("#NewDropPassword")).ToHaveValueAsync("retained-password");
            await Expect(page.Locator("#password-confirm")).ToHaveValueAsync("retained-password");
            await Expect(page.Locator("#password-form button[type=submit]")).ToBeEnabledAsync();
        }
        else await Expect(page.Locator("#access-toggle")).ToBeFocusedAsync();
        Assert.Empty(errors);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task LostNavigationResponseFollowsTheOriginalDropEvenIfItsOldSlugIsReused(bool delete)
    {
        Guid originalId;
        await using (var scope = factory.Services.CreateAsyncScope())
            originalId = await scope.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops
                .Where(drop => drop.Slug == "video").Select(drop => drop.Id).SingleAsync();
        var handler = delete ? "Delete" : "Slug";
        var writes = 0;
        await page.RouteAsync($"**/drops/video?handler={handler}", async route =>
        {
            Interlocked.Increment(ref writes);
            var response = await route.FetchAsync();
            Assert.True(response.Ok);
            await HttpTestSupport.SeedDropAsync(factory, "video", [2], drop => drop.Description = "A different Drop reused the old Slug");
            await route.AbortAsync();
        });
        var dialog = await OpenManagementDialogAsync(handler);

        await page.Locator($"#{dialog} button[type=submit]").ClickAsync();

        await page.WaitForURLAsync(delete ? "**/?deleted=True" : "**/drops/renamed-after-retry");
        Assert.Equal(1, writes);
        await using var verification = factory.Services.CreateAsyncScope();
        var db = verification.ServiceProvider.GetRequiredService<TeledropDbContext>();
        var replacement = await db.Drops.SingleAsync(drop => drop.Slug == "video");
        Assert.NotEqual(originalId, replacement.Id);
        Assert.Equal("A different Drop reused the old Slug", replacement.Description);
        if (delete) Assert.False(await db.Drops.AnyAsync(drop => drop.Id == originalId));
        else Assert.Equal(originalId, (await db.Drops.SingleAsync(drop => drop.Slug == "renamed-after-retry")).Id);
        Assert.Empty(errors);
    }

    [Fact]
    public async Task FailedMutationStateReadCanBeRetriedWithoutSendingTheWriteAgain()
    {
        var writes = 0;
        await page.RouteAsync("**/drops/video?handler=Access", async route =>
        {
            Interlocked.Increment(ref writes);
            await route.FetchAsync();
            await route.AbortAsync();
        });
        await page.RouteAsync("**/*handler=RecoveryState*", route => route.AbortAsync());

        await ChooseAccessAsync("public");

        await Expect(page.Locator("[data-operation-error=access]").First).ToHaveAttributeAsync("data-i18n-text", "Operation.CheckFailed");
        await IdleAsync();
        await Expect(page.Locator("#access-toggle")).ToBeDisabledAsync();
        await page.UnrouteAsync("**/*handler=RecoveryState*");

        await page.Locator("#drop-list-refresh").ClickAsync();

        await Expect(page.Locator("#drop-access")).ToHaveAttributeAsync("data-access-level", "public");
        await Expect(page.Locator("[data-operation-error=access]").First).ToHaveAttributeAsync("data-i18n-text", "Operation.Uncertain");
        await IdleAsync();
        Assert.Equal(1, writes);
        Assert.Empty(errors);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task FailedRecoveryCannotReplayNavigationAgainstAReplacementDrop(bool delete)
    {
        var handler = delete ? "Delete" : "Slug";
        var writes = 0;
        await page.RouteAsync($"**/drops/video?handler={handler}", async route =>
        {
            if (Interlocked.Increment(ref writes) == 1)
            {
                await route.FetchAsync();
                await HttpTestSupport.SeedDropAsync(factory, "video", [2], drop => drop.Description = "Replacement must survive");
                await route.AbortAsync();
            }
            else await route.ContinueAsync();
        });
        await page.RouteAsync("**/*handler=RecoveryState*", route => route.AbortAsync());
        var dialog = await OpenManagementDialogAsync(handler);

        await page.Locator($"#{dialog} button[type=submit]").ClickAsync();

        await Expect(page.Locator($"#{dialog} [data-operation-error]")).ToHaveAttributeAsync("data-i18n-text", "Operation.CheckFailed");
        await Expect(page.Locator($"#{dialog} button[type=submit]")).ToBeDisabledAsync();
        await Expect(page.Locator("#access-toggle")).ToBeDisabledAsync();
        // Native submit events must be blocked too, not merely the visible button.
        Assert.False(await page.Locator($"#{dialog} form").EvaluateAsync<bool>(
            "form => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))"));
        await Expect(page).ToHaveURLAsync(address + "/drops/video");
        Assert.Equal(1, writes);
        await page.UnrouteAsync("**/*handler=RecoveryState*");
        await page.Locator($"#{dialog} [data-dialog-close]").First.ClickAsync();

        await page.Locator("#drop-list-refresh").ClickAsync();

        await page.WaitForURLAsync(delete ? "**/?deleted=True" : "**/drops/renamed-after-retry");
        Assert.Equal(1, writes);
        await using var scope = factory.Services.CreateAsyncScope();
        var replacement = await scope.ServiceProvider.GetRequiredService<TeledropDbContext>().Drops.SingleAsync(drop => drop.Slug == "video");
        Assert.Equal("Replacement must survive", replacement.Description);
        Assert.Equal(new byte[] { 2 }, await File.ReadAllBytesAsync(Path.Combine(factory.ShareDirectory, replacement.Location)));
        Assert.Empty(errors);
    }

    [Fact]
    public async Task QueuedNavigationWaitsUntilFailedRecoveryCanConfirmTheDrop()
    {
        var committed = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var renames = 0;
        await page.RouteAsync("**/drops/video?handler=Access", async route =>
        {
            await route.FetchAsync();
            committed.TrySetResult();
            await release.Task;
            await route.AbortAsync();
        });
        page.Request += (_, request) =>
        {
            if (request.Method == "POST" && request.Url.Contains("handler=Slug"))
                Interlocked.Increment(ref renames);
        };
        await page.RouteAsync("**/*handler=RecoveryState*", route => route.AbortAsync());
        try
        {
            await ChooseAccessAsync("public");
            await committed.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await OpenManagementDialogAsync("Slug");
            await page.Locator("#url-dialog button[type=submit]").ClickAsync();
            await Expect(page.Locator("#drop-navigation-status")).ToBeVisibleAsync();

            release.TrySetResult();

            await Expect(page.Locator("[data-operation-error=access]").First).ToHaveAttributeAsync("data-i18n-text", "Operation.CheckFailed");
            await Expect(page.Locator("#url-dialog button[type=submit]")).ToBeDisabledAsync();
            await Expect(page).ToHaveURLAsync(address + "/drops/video");
            Assert.Equal(0, Volatile.Read(ref renames));
            await page.UnrouteAsync("**/*handler=RecoveryState*");
            await page.Locator("#url-dialog [data-dialog-close]").ClickAsync();

            await page.Locator("#drop-list-refresh").ClickAsync();

            await page.WaitForURLAsync("**/drops/renamed-after-retry");
            Assert.Equal(1, Volatile.Read(ref renames));
            await Expect(page.Locator("#drop-access")).ToHaveAttributeAsync("data-access-level", "public");
            Assert.Empty(errors);
        }
        finally { release.TrySetResult(); }
    }

    private async Task<string> OpenManagementDialogAsync(string handler)
    {
        if (handler == "Access")
        {
            await ChooseAccessAsync("password");
            await page.Locator("#NewDropPassword").FillAsync("retained-password");
            await page.Locator("#password-confirm").FillAsync("retained-password");
            return "password-dialog";
        }
        await page.Locator("#drop-actions-toggle").ClickAsync();
        await page.Locator(handler == "Delete" ? "#delete-open" : "#slug-open").ClickAsync();
        if (handler == "Slug") await page.Locator("#SlugInput").FillAsync("renamed-after-retry");
        return handler == "Delete" ? "delete-dialog" : "url-dialog";
    }
}
