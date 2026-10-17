using Microsoft.Playwright;
using Xunit;
using static Microsoft.Playwright.Assertions;

namespace Teledrop.Tests;

public sealed partial class DropBrowserTests
{
    [Fact]
    public async Task PdfInitialSinglePageRenderShowsTheOnlyPageAndDisablesPagination()
    {
        const string slug = "single-page-control";
        const string fileName = "single-page.pdf";
        var bytes = await SeedInitialRenderPdfAsync(slug, fileName);

        await NavigateBeforeInitialPdfRenderAsync(slug);

        var canvas = page.Locator("[data-pdf-canvas]");
        await Expect(page.Locator("[data-pdf-status]")).ToHaveTextAsync("1 / 1 페이지");
        await Expect(canvas).ToBeVisibleAsync();
        await Expect(canvas).ToHaveAccessibleNameAsync("PDF 1 / 1 페이지");
        Assert.True(await canvas.EvaluateAsync<bool>("""
            canvas => {
                const pixels = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
                return pixels.some((value, index) => index % 4 !== 3 && value < 240);
            }
            """));
        await Expect(page.Locator("[data-pdf-prev]")).ToBeDisabledAsync();
        await Expect(page.Locator("[data-pdf-next]")).ToBeDisabledAsync();
        await Expect(page.Locator("#drop-download")).ToBeFocusedAsync();
        await AssertInitialPdfDownloadAsync(fileName, bytes);
        Assert.Empty(errors);
    }

    [Theory]
    [InlineData("single-page.pdf")]
    [InlineData("preview.pdf")]
    public async Task PdfInitialRenderFailureKeepsDownloadAvailableWithoutPagination(string fileName)
    {
        const string slug = "initial-render-failure";
        var bytes = await SeedInitialRenderPdfAsync(slug, fileName);
        // The real PDF.js loader succeeds. Only the first drawing attempt on
        // the preview's canvas fails, before any page has been displayed.
        await page.AddInitScriptAsync("""
            (() => {
                const getContext = HTMLCanvasElement.prototype.getContext;
                window.initialPdfRenderFailures = 0;
                HTMLCanvasElement.prototype.getContext = function (...args) {
                    if (this.matches('[data-pdf-canvas]') && args[0] === '2d'
                        && window.initialPdfRenderFailures === 0) {
                        window.initialPdfRenderFailures++;
                        throw new Error('Injected first-page canvas failure');
                    }
                    return getContext.apply(this, args);
                };
            })();
            """);

        await NavigateBeforeInitialPdfRenderAsync(slug);

        var status = page.Locator("[data-pdf-status]");
        var canvas = page.Locator("[data-pdf-canvas]");
        await Expect(status).ToHaveTextAsync("페이지를 표시하지 못했습니다. 다운로드 버튼으로 파일을 저장해주세요.");
        await Expect(status).ToBeVisibleAsync();
        Assert.Equal(1, await page.EvaluateAsync<int>("() => window.initialPdfRenderFailures"));
        await Expect(canvas).ToBeHiddenAsync();
        await Expect(canvas).ToHaveAttributeAsync("aria-label", $"{fileName} PDF 미리보기");
        await Expect(page.Locator("[data-pdf-prev]")).ToBeDisabledAsync();
        await Expect(page.Locator("[data-pdf-next]")).ToBeDisabledAsync();
        // An automatic preview failure must not steal focus from the available fallback.
        await Expect(page.Locator("#drop-download")).ToBeFocusedAsync();
        await AssertInitialPdfDownloadAsync(fileName, bytes);
        Assert.Empty(errors);
    }

    private async Task<byte[]> SeedInitialRenderPdfAsync(string slug, string fileName)
    {
        var bytes = await File.ReadAllBytesAsync(Path.Combine(AppContext.BaseDirectory, "Fixtures", fileName));
        await HttpTestSupport.SeedDropAsync(factory, slug, bytes, drop =>
        {
            drop.FileName = fileName;
            drop.ContentType = "application/pdf";
        });
        return bytes;
    }

    private async Task NavigateBeforeInitialPdfRenderAsync(string slug)
    {
        var requested = new TaskCompletionSource<int>(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        await page.RouteAsync($"**/d/{slug}?inline=true", async route =>
        {
            var response = await route.FetchAsync();
            requested.TrySetResult(response.Status);
            await release.Task;
            await route.FulfillAsync(new() { Response = response });
        });
        try
        {
            await page.GotoAsync($"/drops/{slug}", new() { WaitUntil = WaitUntilState.DOMContentLoaded });
            Assert.Equal(200, await requested.Task.WaitAsync(TimeSpan.FromSeconds(10)));
            await Expect(page.Locator("[data-pdf-status]")).ToHaveTextAsync("PDF 불러오는 중…");
            await page.Locator("#drop-download").FocusAsync();
            await Expect(page.Locator("#drop-download")).ToBeFocusedAsync();
        }
        finally
        {
            release.TrySetResult();
        }
    }

    private async Task AssertInitialPdfDownloadAsync(string fileName, byte[] expectedBytes)
    {
        var download = await page.RunAndWaitForDownloadAsync(() => page.Locator("#drop-download").ClickAsync());
        Assert.Equal(fileName, download.SuggestedFilename);
        Assert.Null(await download.FailureAsync());
        var path = await download.PathAsync();
        Assert.NotNull(path);
        Assert.Equal(expectedBytes, await File.ReadAllBytesAsync(path));
    }
}
