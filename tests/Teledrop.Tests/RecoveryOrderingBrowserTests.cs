using Microsoft.Playwright;
using Xunit;
using static Microsoft.Playwright.Assertions;

namespace Teledrop.Tests;

public sealed partial class DropBrowserTests
{
    [Fact]
    public async Task IdentityRecoveryWaitsForQueuedFavoriteReadWithoutLeavingControlsLocked()
    {
        await page.Locator("video").EvaluateAsync("""
            async video => {
                window.videoBeforeQueuedRecovery = video;
                video.muted = true;
                video.loop = true;
                await video.play();
            }
            """);
        await page.EvaluateAsync("""
            () => {
                window.recoveryRequestOrder = [];
                for (const phase of ['config', 'before', 'finally']) {
                    document.addEventListener(`htmx:${phase}:request`, event => {
                        const ctx = event.detail.ctx;
                        const read = ctx.request.headers['X-Drop-Read'];
                        const write = ctx.sourceElement.closest?.('form[data-drop-action]')?.dataset.dropAction;
                        if (read || write) window.recoveryRequestOrder.push(`${phase}:${read ? 'read-' + read : 'write-' + write}`);
                    });
                }
            }
            """);

        var sharedCaptured = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var releaseShared = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var favoriteCaptured = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var releaseFavorite = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var recoveryCaptured = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var releaseRecovery = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var sharedReads = 0;
        var recoveryReads = 0;
        var favoriteWrites = 0;
        var accessWrites = 0;
        await page.RouteAsync("**/drops/video?handler=SharedState", async route =>
        {
            var order = Interlocked.Increment(ref sharedReads);
            var response = await route.FetchAsync();
            if (order == 1)
            {
                sharedCaptured.TrySetResult();
                await releaseShared.Task;
            }
            await route.FulfillAsync(new() { Response = response });
        });
        await page.RouteAsync("**/drops/video?handler=FavoriteState", async route =>
        {
            var response = await route.FetchAsync();
            favoriteCaptured.TrySetResult();
            await releaseFavorite.Task;
            await route.FulfillAsync(new() { Response = response });
        });
        await page.RouteAsync("**/*handler=RecoveryState*", async route =>
        {
            Interlocked.Increment(ref recoveryReads);
            var response = await route.FetchAsync();
            recoveryCaptured.TrySetResult();
            await releaseRecovery.Task;
            await route.FulfillAsync(new() { Response = response });
        });
        await page.RouteAsync("**/drops/video?handler=Favorite", route =>
        {
            Interlocked.Increment(ref favoriteWrites);
            return route.AbortAsync();
        });
        await page.RouteAsync("**/drops/video?handler=Access", route =>
        {
            Interlocked.Increment(ref accessWrites);
            return route.AbortAsync();
        });

        try
        {
            // A successful metadata save starts the shared read that occupies the queue.
            await EditDescriptionAsync();
            await page.Locator("#DescriptionInput").FillAsync("Saved before recovery");
            await page.Locator("#drop-description-editor button[type=submit]").ClickAsync();
            await sharedCaptured.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await Expect(page.Locator("#drop-description")).ToHaveTextAsync("Saved before recovery");
            await EditDescriptionAsync();
            await page.Locator("#DescriptionInput").FillAsync("Unsaved draft during queued recovery");

            await ClickFavoriteAsync();
            await page.WaitForFunctionAsync("""
                () => window.recoveryRequestOrder.includes('finally:write-favorite')
                    && window.recoveryRequestOrder.includes('config:read-favorite')
                """);
            Assert.DoesNotContain("before:read-favorite",
                await page.EvaluateAsync<string[]>("() => window.recoveryRequestOrder"));

            await ChooseAccessAsync("public");
            await page.WaitForFunctionAsync("() => window.recoveryRequestOrder.includes('finally:write-access')");
            await Expect(page.Locator("[data-operation-error=access]").First)
                .ToHaveAttributeAsync("data-i18n-text", "Operation.Checking");
            await Expect(page.Locator("#access-toggle")).ToBeDisabledAsync();

            releaseShared.TrySetResult();
            await favoriteCaptured.Task.WaitAsync(TimeSpan.FromSeconds(10));
            var pendingOrder = await page.EvaluateAsync<string[]>("() => window.recoveryRequestOrder");
            Assert.Contains("finally:read-shared", pendingOrder);
            Assert.Contains("before:read-favorite", pendingOrder);
            Assert.DoesNotContain("before:read-recovery", pendingOrder);
            Assert.True(Array.IndexOf(pendingOrder, "finally:read-shared")
                < Array.IndexOf(pendingOrder, "before:read-favorite"));

            releaseFavorite.TrySetResult();
            await recoveryCaptured.Task.WaitAsync(TimeSpan.FromSeconds(10));
            var recoveryOrder = await page.EvaluateAsync<string[]>("() => window.recoveryRequestOrder");
            Assert.Contains("finally:read-favorite", recoveryOrder);
            Assert.Contains("before:read-recovery", recoveryOrder);
            Assert.True(Array.IndexOf(recoveryOrder, "finally:read-favorite")
                < Array.IndexOf(recoveryOrder, "before:read-recovery"));

            releaseRecovery.TrySetResult();
            await page.WaitForFunctionAsync("""
                () => window.recoveryRequestOrder.includes('finally:read-recovery')
                    && window.recoveryRequestOrder.filter(event => event === 'finally:read-shared').length >= 2
                """);

            await Expect(page.Locator("[data-operation-error=access]").First)
                .ToHaveAttributeAsync("data-i18n-text", "Operation.Uncertain");
            await Expect(page.Locator("#drop-access")).ToHaveAttributeAsync("data-access-level", "private");
            await Expect(page.Locator("#drop-favorite")).ToHaveAttributeAsync("data-favorite-value", "false");
            await Expect(page.Locator("#access-toggle")).ToBeEnabledAsync();
            await Expect(page.Locator("#favorite-button")).ToBeEnabledAsync();
            await Expect(page.Locator("#DescriptionInput")).ToBeEnabledAsync();
            await Expect(page.Locator("#DescriptionInput")).ToHaveValueAsync("Unsaved draft during queued recovery");
            await Expect(page.Locator("#drop-description-editor button[type=submit]")).ToBeEnabledAsync();
            await Expect(page.Locator("#drop-detail [data-drop-action][aria-busy=true]")).ToHaveCountAsync(0);
            Assert.True(await page.Locator("video").EvaluateAsync<bool>(
                "video => video === window.videoBeforeQueuedRecovery && !video.paused"));
            Assert.Equal(1, Volatile.Read(ref favoriteWrites));
            Assert.Equal(1, Volatile.Read(ref accessWrites));
            Assert.Equal(1, Volatile.Read(ref recoveryReads));
            Assert.Empty(errors);
        }
        finally
        {
            releaseShared.TrySetResult();
            releaseFavorite.TrySetResult();
            releaseRecovery.TrySetResult();
        }
    }
}
