using System.Text;
using Microsoft.Playwright;
using Xunit;
using static Microsoft.Playwright.Assertions;

namespace Teledrop.Tests;

public sealed partial class DropBrowserTests
{
    [Fact]
    public async Task MultipleFileDropClearsTheSelectionAndPreviewBeforeAcceptingASingleFile()
    {
        await page.GotoAsync("/");
        await page.Locator("#upload-file").SetInputFilesAsync(PreviewImage());
        await Expect(page.Locator("#upload-preview")).ToBeVisibleAsync();
        await using var multiple = await page.EvaluateHandleAsync("""
            () => {
                const files = new DataTransfer();
                files.items.add(new File(['first'], 'first.txt', { type: 'text/plain' }));
                files.items.add(new File(['second'], 'second.txt', { type: 'text/plain' }));
                return files;
            }
            """);

        await page.Locator("#upload-zone").DispatchEventAsync("drop", new { dataTransfer = multiple });

        await Expect(page.Locator("#upload-drop-error")).ToHaveTextAsync("파일은 한 번에 하나만 업로드할 수 있습니다.");
        await Expect(page.Locator("#upload-drop-error")).ToBeVisibleAsync();
        Assert.Equal(0, await page.Locator("#upload-file").EvaluateAsync<int>("input => input.files.length"));
        Assert.True(await page.Locator("#upload-file").EvaluateAsync<bool>("input => input.validity.valueMissing"));
        await Expect(page.Locator("#upload-preview")).ToBeHiddenAsync();
        Assert.Null(await page.Locator("#upload-preview").GetAttributeAsync("src"));
        await Expect(page.Locator("#upload-video")).ToBeHiddenAsync();
        await Expect(page.Locator("#upload-filename")).ToBeHiddenAsync();
        await Expect(page.Locator("#upload-prompt")).ToBeVisibleAsync();
        await using var single = await page.EvaluateHandleAsync("""
            () => {
                const files = new DataTransfer();
                files.items.add(new File(['accepted'], 'accepted.txt', { type: 'text/plain' }));
                return files;
            }
            """);

        await page.Locator("#upload-zone").DispatchEventAsync("drop", new { dataTransfer = single });

        await Expect(page.Locator("#upload-drop-error")).ToBeHiddenAsync();
        await Expect(page.Locator("#upload-filename")).ToHaveTextAsync("accepted.txt");
        Assert.True(await page.Locator("#upload-form").EvaluateAsync<bool>("form => form.checkValidity()"));
        await page.Locator("#upload-submit").ClickAsync();
        await page.WaitForURLAsync("**/drops/*");
        await Expect(page.Locator("#drop-heading")).ToHaveTextAsync("accepted.txt");
        Assert.Empty(errors);
    }

    [Fact]
    public async Task ChangingSelectedFileReplacesImageVideoAndGenericPreviews()
    {
        await page.GotoAsync("/");
        var input = page.Locator("#upload-file");
        var image = page.Locator("#upload-preview");
        var video = page.Locator("#upload-video");
        var icon = page.Locator("#upload-file-icon");

        await input.SetInputFilesAsync(PreviewImage());

        await Expect(image).ToBeVisibleAsync();
        await Expect(image).ToHaveJSPropertyAsync("naturalWidth", 2);
        await Expect(video).ToBeHiddenAsync();
        await Expect(icon).ToBeHiddenAsync();
        await Expect(page.Locator("#upload-filename")).ToHaveTextAsync("preview.svg");

        await input.SetInputFilesAsync(new FilePayload
        {
            Name = "selected.webm", MimeType = "video/webm",
            Buffer = await File.ReadAllBytesAsync(Path.Combine(AppContext.BaseDirectory, "Fixtures/preview.webm")),
        });

        await Expect(video).ToBeVisibleAsync();
        await Expect(video).ToHaveAttributeAsync("src", new System.Text.RegularExpressions.Regex("^blob:"));
        await Expect(image).ToBeHiddenAsync();
        Assert.Null(await image.GetAttributeAsync("src"));
        await Expect(icon).ToBeHiddenAsync();

        await input.SetInputFilesAsync(new FilePayload { Name = "note.txt", MimeType = "text/plain", Buffer = "note"u8.ToArray() });

        await Expect(icon).ToBeVisibleAsync();
        await Expect(video).ToBeHiddenAsync();
        Assert.Null(await video.GetAttributeAsync("src"));
        await Expect(image).ToBeHiddenAsync();
        await Expect(page.Locator("#upload-filename")).ToHaveTextAsync("note.txt");

        await input.SetInputFilesAsync(Array.Empty<FilePayload>());

        await Expect(icon).ToBeHiddenAsync();
        await Expect(page.Locator("#upload-icon")).ToBeVisibleAsync();
        await Expect(page.Locator("#upload-prompt")).ToBeVisibleAsync();
        await Expect(page.Locator("#upload-filename")).ToBeHiddenAsync();
        Assert.Empty(errors);
    }

    [Theory]
    [InlineData(404)]
    [InlineData(500)]
    public async Task FailedMetadataSavePreservesTheDraftAndAllowsRetry(int status)
    {
        await page.Locator("video").EvaluateAsync("video => window.videoBeforeFailure = video");
        await EditDescriptionAsync();
        await page.Locator("#DescriptionInput").FillAsync("Draft retained after failure");
        await page.RouteAsync("**/drops/video?handler=Metadata", route =>
            route.FulfillAsync(new() { Status = status, ContentType = "text/html", Body = "<h1>Server failure</h1>" }));

        await page.Locator("#drop-description-editor button[type=submit]").ClickAsync();

        await Expect(page.Locator("[data-operation-error=metadata]")).ToHaveTextAsync(status == 404
            ? "Drop을 찾을 수 없습니다. 페이지를 새로고침해 주세요."
            : "변경을 저장하지 못했습니다. 입력을 확인하고 다시 시도하세요.");
        await Expect(page.Locator("#DescriptionInput")).ToHaveValueAsync("Draft retained after failure");
        await Expect(page.Locator("#DescriptionInput")).ToBeEnabledAsync();
        await Expect(page.Locator("#drop-description-editor button[type=submit]")).ToBeEnabledAsync();
        await Expect(page.GetByText("Server failure", new() { Exact = true })).ToHaveCountAsync(0);
        Assert.True(await page.Locator("video").EvaluateAsync<bool>("video => video === window.videoBeforeFailure"));
        await IdleAsync();
        await page.UnrouteAsync("**/drops/video?handler=Metadata");

        await page.Locator("#drop-description-editor button[type=submit]").ClickAsync();

        await Expect(page.Locator("#drop-description")).ToHaveTextAsync("Draft retained after failure");
        await Expect(page.Locator("#DescriptionInput")).ToBeHiddenAsync();
        await page.ReloadAsync();
        await Expect(page.Locator("#drop-description")).ToHaveTextAsync("Draft retained after failure");
        Assert.Empty(errors);
    }

    [Fact]
    public async Task FailedListRefreshPreservesItsResultsAndTheOpenDescriptionDraft()
    {
        await SearchAsync("Watch");
        await EditDescriptionAsync();
        await page.Locator("#DescriptionInput").FillAsync("Unsaved description");
        await page.RouteAsync("**/*handler=DropList*", route => route.AbortAsync());

        await page.Locator("#drop-list-refresh").ClickAsync();

        await Expect(page.Locator("[data-list-error]")).ToBeVisibleAsync();
        await Expect(page.Locator("[data-list-error]")).ToHaveTextAsync("목록을 갱신하지 못했습니다. 새로고침으로 다시 시도하세요.");
        await Expect(page.Locator("#drop-list .td-drop-row")).ToHaveCountAsync(1);
        await Expect(page.Locator("#drop-search-input")).ToHaveValueAsync("Watch");
        await Expect(page.Locator("#DescriptionInput")).ToHaveValueAsync("Unsaved description");
        await IdleAsync();
        await page.UnrouteAsync("**/*handler=DropList*");

        await page.Locator("#drop-list-refresh").ClickAsync();

        await Expect(page.Locator("[data-list-error]")).ToBeHiddenAsync();
        await Expect(page.Locator("#drop-list-status")).ToContainTextAsync("검색 결과 1 개");
        await Expect(page.Locator("#DescriptionInput")).ToHaveValueAsync("Unsaved description");
        await Expect(page.Locator("#drop-search-input")).ToHaveValueAsync("Watch");
        Assert.Empty(errors);
    }

    [Fact]
    public async Task FailedSharingReadCanBeRetriedByRefreshingTheList()
    {
        await page.Locator("#drop-actions-toggle").ClickAsync();
        await page.Locator("#slug-open").ClickAsync();
        await page.Locator("#SlugInput").FillAsync("unsaved-url");
        await page.Locator("#url-dialog [data-dialog-close]").ClickAsync();
        await page.RouteAsync("**/drops/video?handler=SharedState", route => route.FulfillAsync(new() { Status = 500 }));

        await ChooseAccessAsync("public");

        await Expect(page.Locator("[data-operation-error=shared]")).ToBeVisibleAsync();
        await Expect(page.Locator("[data-operation-error=shared]")).ToContainTextAsync("목록 새로고침 후 다시 확인");
        await Expect(page.Locator("#access-toggle")).ToBeEnabledAsync();
        await Expect(page.Locator("#drop-access")).ToHaveAttributeAsync("data-access-level", "public");
        await IdleAsync();
        await page.UnrouteAsync("**/drops/video?handler=SharedState");

        await page.Locator("#drop-list-refresh").ClickAsync();

        await Expect(page.Locator("[data-operation-error=shared]")).ToBeHiddenAsync();
        await Expect(page.Locator("#drop-share-state")).ToContainTextAsync("누구나 열 수 있는");
        await page.Locator("#drop-actions-toggle").ClickAsync();
        await page.Locator("#slug-open").ClickAsync();
        await Expect(page.Locator("#SlugInput")).ToHaveValueAsync("unsaved-url");
        Assert.Empty(errors);
    }

    [Fact]
    public async Task FailedPublicUnlockKeepsTheFormAndCanBeRetried()
    {
        await SeedPdfAsync("unlock-retry", locked: true);
        await context.ClearCookiesAsync();
        await page.GotoAsync("/unlock-retry");
        await page.EvaluateAsync("() => window.documentBeforeFailure = document.body");
        await page.RouteAsync("**/unlock-retry?handler=Unlock", route =>
            route.FulfillAsync(new() { Status = 500, ContentType = "text/html", Body = "<h1>Server failure</h1>" }));
        await page.Locator("#DropPassword").FillAsync("secret");

        await page.Locator("[data-public-unlock] button[type=submit]").ClickAsync();

        await Expect(page.Locator("[data-public-error]")).ToHaveTextAsync("요청에 실패했습니다. 다시 시도하세요.");
        await Expect(page.Locator("[data-public-error]")).ToBeVisibleAsync();
        await Expect(page.Locator("#DropPassword")).ToHaveValueAsync("secret");
        await Expect(page.Locator("[data-public-unlock] button[type=submit]")).ToBeEnabledAsync();
        await Expect(page.Locator("[data-pdf-canvas]")).ToHaveCountAsync(0);
        Assert.True(await page.EvaluateAsync<bool>("() => document.body === window.documentBeforeFailure"));
        await IdleAsync();
        await page.UnrouteAsync("**/unlock-retry?handler=Unlock");

        await page.Locator("[data-public-unlock] button[type=submit]").ClickAsync();

        await Expect(page.Locator("[data-pdf-status]")).ToHaveTextAsync("1 / 2 페이지");
        await Expect(page.Locator("[data-public-unlock]")).ToHaveCountAsync(0);
        await Expect(page).ToHaveURLAsync(address + "/unlock-retry");
        Assert.Empty(errors);
    }

    [Fact]
    public async Task PdfLoadFailureExplainsTheProblemAndStillAllowsDownloading()
    {
        await HttpTestSupport.SeedDropAsync(factory, "failed-pdf", "not a PDF"u8.ToArray(), drop =>
        {
            drop.ContentType = "application/pdf";
            drop.FileName = "preview.pdf";
        });

        await page.GotoAsync("/drops/failed-pdf");

        await Expect(page.Locator("[data-pdf-status]")).ToHaveTextAsync("PDF를 표시하지 못했습니다. 다운로드 버튼으로 파일을 저장해주세요.");
        await Expect(page.Locator("[data-pdf-canvas]")).ToBeHiddenAsync();
        await Expect(page.Locator("[data-pdf-prev]")).ToBeDisabledAsync();
        await Expect(page.Locator("[data-pdf-next]")).ToBeDisabledAsync();
        var download = await page.RunAndWaitForDownloadAsync(() => page.Locator("#drop-download").ClickAsync());
        Assert.Equal("preview.pdf", download.SuggestedFilename);
        Assert.Null(await download.FailureAsync());
        Assert.Empty(errors);
    }

    [Fact]
    public async Task PdfPageRenderFailureReleasesTheControlsAndCanRetryTheSamePage()
    {
        await SeedPdfAsync("render-retry", locked: false);
        await page.GotoAsync("/drops/render-retry");
        await Expect(page.Locator("[data-pdf-status]")).ToHaveTextAsync("1 / 2 페이지");
        var canvas = page.Locator("[data-pdf-canvas]");
        // Fail the browser drawing surface, while keeping the real PDF loader and renderer.
        await canvas.EvaluateAsync("""
            canvas => {
                canvas.originalGetContext = canvas.getContext;
                canvas.getContext = () => { throw new Error('Injected canvas failure'); };
            }
            """);

        await page.Locator("[data-pdf-next]").ClickAsync();

        await Expect(page.Locator("[data-pdf-status]")).ToHaveTextAsync("페이지를 표시하지 못했습니다. 다운로드 버튼으로 파일을 저장해주세요.");
        await Expect(page.Locator("[data-pdf-prev]")).ToBeDisabledAsync();
        await Expect(page.Locator("[data-pdf-next]")).ToBeEnabledAsync();
        await Expect(page.Locator("[data-pdf-next]")).ToBeFocusedAsync();
        await canvas.EvaluateAsync("canvas => { canvas.getContext = canvas.originalGetContext; }");

        await page.Locator("[data-pdf-next]").ClickAsync();

        await Expect(page.Locator("[data-pdf-status]")).ToHaveTextAsync("2 / 2 페이지");
        await Expect(page.Locator("[data-pdf-prev]")).ToBeEnabledAsync();
        await Expect(page.Locator("[data-pdf-next]")).ToBeDisabledAsync();
        Assert.Empty(errors);
    }

    [Fact]
    public async Task RelativeDatesUseTheExpectedBoundaryAndLanguage()
    {
        var now = new DateTime(2026, 10, 18, 12, 0, 0, DateTimeKind.Utc);
        await page.Clock.SetFixedTimeAsync(now);
        var cases = new (int Seconds, string Korean, string English)[]
        {
            (-60, "몇 초 전", "A few seconds ago"),
            (44, "몇 초 전", "A few seconds ago"),
            (45, "1분 전", "1 minute ago"),
            (90, "2분 전", "2 minutes ago"),
            (2699, "45분 전", "45 minutes ago"),
            (2700, "1시간 전", "1 hour ago"),
            (5400, "2시간 전", "2 hours ago"),
            (79199, "22시간 전", "22 hours ago"),
            (79200, "어제", "yesterday"),
            (129600, "그저께", "2 days ago"),
            (2246399, "26일 전", "26 days ago"),
            (2246400, "지난달", "last month"),
            (3888000, "2개월 전", "2 months ago"),
            (27647999, "11개월 전", "11 months ago"),
            (27648000, "작년", "last year"),
            (63072000, "2년 전", "2 years ago"),
        };
        for (var index = 0; index < cases.Length; index++)
        {
            var createdAt = now.AddSeconds(-cases[index].Seconds);
            await HttpTestSupport.SeedDropAsync(factory, $"clock-case-{index:D2}", [1], drop => drop.CreatedAt = createdAt);
        }

        await page.GotoAsync("/?search=clock-case-&sort=name&direction=asc");

        var times = page.Locator("#drop-list time[data-relative-time]");
        await Expect(times).ToHaveTextAsync(cases.Select(item => item.Korean).ToArray());
        await ChooseLanguageAsync("en");
        await Expect(times).ToHaveTextAsync(cases.Select(item => item.English).ToArray());
        Assert.Empty(errors);
    }

    [Fact]
    public async Task BrowserFileSizesKeepBinaryUnitsAndGroupedNumbersAfterChangingLanguage()
    {
        var cases = new (long Bytes, string Expected)[]
        {
            (0, "0 B"), (1, "1 B"), (1023, "1,023 B"), (1024, "1 KB"), (1536, "1.5 KB"),
            (1048575, "1,024 KB"), (1048576, "1 MB"), (1073741824, "1 GB"),
            (1099511627776, "1 TB"), (1125899906842624, "1,024 TB"),
        };
        for (var index = 0; index < cases.Length; index++)
        {
            var bytes = cases[index].Bytes;
            await HttpTestSupport.SeedDropAsync(factory, $"size-case-{index:D2}", [1], drop => drop.FileSizeBytes = bytes);
        }

        await page.GotoAsync("/?search=size-case-&sort=name&direction=asc");

        var sizes = page.Locator("#drop-list [data-file-size]");
        await Expect(sizes).ToHaveTextAsync(cases.Select(item => item.Expected).ToArray());
        await ChooseLanguageAsync("en");
        await Expect(sizes).ToHaveTextAsync(cases.Select(item => item.Expected).ToArray());
        Assert.Empty(errors);
    }

    private static FilePayload PreviewImage() => new()
    {
        Name = "preview.svg", MimeType = "image/svg+xml",
        Buffer = Encoding.UTF8.GetBytes("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"2\" height=\"2\"><rect width=\"2\" height=\"2\" fill=\"red\"/></svg>"),
    };
}
