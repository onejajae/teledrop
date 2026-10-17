using Microsoft.Playwright;
using Xunit;
using static Microsoft.Playwright.Assertions;

namespace Teledrop.Tests;

public sealed partial class DropBrowserTests
{
    [Fact]
    public async Task OlderSearchResponseCannotReplaceTheNewerResultsOrMoveFocus()
    {
        await ObserveOrderedListResponsesAsync(keepFirstResponseAfterAbort: true);
        var captured = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var requests = 0;
        await page.RouteAsync("**/*handler=DropList*", async route =>
        {
            var order = Interlocked.Increment(ref requests);
            var response = await route.FetchAsync();
            if (order == 1)
            {
                captured.TrySetResult();
                await release.Task;
            }
            await FulfillOrderedListAsync(route, response, order == 1 ? "older" : "newer");
        });
        try
        {
            await page.Locator("#drop-search-toggle").ClickAsync();
            await page.Locator("#drop-search-input").FillAsync("Original");
            await page.Locator("#drop-search-submit").ClickAsync();
            await captured.Task.WaitAsync(TimeSpan.FromSeconds(10));

            await page.Locator("#drop-search-input").FillAsync("Watch");
            await page.Locator("#drop-search-submit").ClickAsync();
            await WaitForOrderedListAsync("newer");
            await Expect(page.Locator("#drop-list .td-drop-row")).ToHaveCountAsync(1);
            await Expect(page.Locator("#drop-list [data-drop-slug=video]")).ToBeVisibleAsync();
            await page.Locator("#theme-toggle").FocusAsync();

            release.TrySetResult();
            await WaitForOrderedListAsync("older");

            await Expect(page.Locator("#drop-search-input")).ToHaveValueAsync("Watch");
            await Expect(page.Locator("#drop-list .td-drop-row")).ToHaveCountAsync(1);
            await Expect(page.Locator("#drop-list [data-drop-slug=video]")).ToBeVisibleAsync();
            await Expect(page.Locator("#drop-list-status")).ToHaveTextAsync("검색 결과 1 개, 1 / 1 페이지");
            await Expect(page.Locator("[data-list-error]")).ToBeHiddenAsync();
            await Expect(page.Locator("#theme-toggle")).ToBeFocusedAsync();
            Assert.DoesNotContain("swap:older", await page.EvaluateAsync<string[]>("() => window.orderedListEvents"));
            Assert.True(await page.Locator("video").EvaluateAsync<bool>("video => video === window.orderingVideo"));
            await Expect(page).ToHaveURLAsync(address + "/drops/video");
            await IdleAsync();
            Assert.Empty(errors);
        }
        finally { release.TrySetResult(); }
    }

    [Fact]
    public async Task ListReadFromBeforeAMutationCannotUndoItsOptimisticState()
    {
        await SearchAsync("Watch");
        await ObserveOrderedListResponsesAsync(keepFirstResponseAfterAbort: false);
        await page.Locator("#drop-list").EvaluateAsync("list => window.listBeforeMutation = list");
        var listCaptured = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var releaseList = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var mutationStored = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var releaseMutation = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var reads = 0;
        await page.RouteAsync("**/*handler=DropList*", async route =>
        {
            var order = Interlocked.Increment(ref reads);
            var response = await route.FetchAsync();
            if (order == 1)
            {
                listCaptured.TrySetResult();
                await releaseList.Task;
            }
            await FulfillOrderedListAsync(route, response, order == 1 ? "before-mutation" : "after-mutation");
        });
        await page.RouteAsync("**/drops/video?handler=Favorite", async route =>
        {
            var response = await route.FetchAsync();
            mutationStored.TrySetResult();
            await releaseMutation.Task;
            await route.FulfillAsync(new() { Response = response });
        });
        try
        {
            await page.Locator("#drop-list-refresh").ClickAsync();
            await listCaptured.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await ClickFavoriteAsync();
            await mutationStored.Task.WaitAsync(TimeSpan.FromSeconds(10));
            await Expect(page.Locator("[data-list-favorite]:visible")).ToHaveCountAsync(1);
            await page.Locator("#theme-toggle").FocusAsync();

            releaseList.TrySetResult();
            await WaitForOrderedListAsync("before-mutation");

            Assert.True(await page.Locator("#drop-list").EvaluateAsync<bool>("list => list === window.listBeforeMutation"));
            await Expect(page.Locator("[data-list-favorite]:visible")).ToHaveCountAsync(1);
            await Expect(page.Locator("#favorite-button")).ToBeDisabledAsync();
            await Expect(page.Locator("#drop-search-input")).ToHaveValueAsync("Watch");
            await Expect(page.Locator("#theme-toggle")).ToBeFocusedAsync();
            Assert.DoesNotContain("swap:before-mutation", await page.EvaluateAsync<string[]>("() => window.orderedListEvents"));

            releaseMutation.TrySetResult();
            await WaitForOrderedListAsync("after-mutation");
            await IdleAsync();

            await Expect(page.Locator("#drop-favorite")).ToHaveAttributeAsync("data-favorite-value", "true");
            await Expect(page.Locator("[data-list-favorite]:visible")).ToHaveCountAsync(1);
            await Expect(page.Locator("#favorite-button")).ToBeEnabledAsync();
            await Expect(page.Locator("#drop-list-status")).ToHaveTextAsync("검색 결과 1 개, 1 / 1 페이지");
            await Expect(page.Locator("#theme-toggle")).ToBeFocusedAsync();
            Assert.True(await page.Locator("video").EvaluateAsync<bool>("video => video === window.orderingVideo"));
            Assert.Empty(errors);
        }
        finally
        {
            releaseList.TrySetResult();
            releaseMutation.TrySetResult();
        }
    }

    private async Task ObserveOrderedListResponsesAsync(bool keepFirstResponseAfterAbort)
    {
        await page.EvaluateAsync("""
            keepFirstResponseAfterAbort => {
                window.orderedListEvents = [];
                window.orderingVideo = document.querySelector('video');
                let first = true;
                document.addEventListener('htmx:before:request', event => {
                    const ctx = event.detail.ctx;
                    if (!first || !ctx.sourceElement.closest?.('#drop-list')) return;
                    first = false;
                    if (keepFirstResponseAfterAbort) {
                        // Model delivery that already won the transport cancellation race.
                        // The response still comes from the real application via route.fetch.
                        const fetch = ctx.fetch;
                        ctx.fetch = (url, options) => fetch(url, { ...options, signal: undefined });
                    }
                });
                for (const [event, prefix] of [['htmx:after:swap', 'swap'], ['htmx:finally:request', 'complete']]) {
                    document.addEventListener(event, event => {
                        const name = event.detail.ctx.response?.headers.get('X-Test-List-Response');
                        if (name) window.orderedListEvents.push(`${prefix}:${name}`);
                    });
                }
            }
            """, keepFirstResponseAfterAbort);
    }

    private Task WaitForOrderedListAsync(string name) => page.WaitForFunctionAsync(
        "name => window.orderedListEvents.includes('complete:' + name)", name);

    private static Task FulfillOrderedListAsync(IRoute route, IAPIResponse response, string name)
    {
        var headers = new Dictionary<string, string>(response.Headers)
        {
            ["X-Test-List-Response"] = name,
        };
        return route.FulfillAsync(new() { Response = response, Headers = headers });
    }
}
