using Microsoft.Playwright;
using Xunit;
using static Microsoft.Playwright.Assertions;

namespace Teledrop.Tests;

public sealed partial class DropBrowserTests
{
    [Theory]
    [InlineData(400)]
    [InlineData(200)]
    public async Task UnsuccessfulLanguageResponsesPreserveTheChoiceAndDraftUntilRetry(int status)
    {
        await ObserveLanguageRequestsAsync();
        await EditDescriptionAsync();
        await page.Locator("#DescriptionInput").FillAsync("Unchanged language draft");
        await page.RouteAsync("**/settings/language", route => route.FulfillAsync(new()
        {
            Status = status, ContentType = "text/html", Body = "<h1>Language request failed</h1>",
        }));

        await page.Locator("#language-toggle").ClickAsync();
        await page.Locator("#language-en").ClickAsync();

        await Expect(page.Locator("#language-error")).ToBeVisibleAsync();
        await Expect(page.Locator("#language-error")).ToHaveTextAsync("언어 설정을 저장하지 못했습니다. 다시 선택해 주세요.");
        await ExpectLanguageChoiceAsync("ko");
        await Expect(page.Locator("#DescriptionInput")).ToHaveValueAsync("Unchanged language draft");
        await Expect(page.GetByText("Language request failed", new() { Exact = true })).ToHaveCountAsync(0);
        Assert.True(await page.Locator("video").EvaluateAsync<bool>("video => video === window.languageVideo"));
        Assert.Equal(["en"], await page.EvaluateAsync<string[]>("() => window.languageRequests"));
        await page.UnrouteAsync("**/settings/language");

        await ChooseLanguageAsync("en");

        await ExpectLanguageChoiceAsync("en");
        await Expect(page.Locator("#language-error")).ToBeHiddenAsync();
        await Expect(page.Locator("#DescriptionInput")).ToHaveValueAsync("Unchanged language draft");
        await Expect(page.Locator("#drop-description-editor button[type=submit]")).ToHaveTextAsync("Save");
        Assert.True(await page.Locator("video").EvaluateAsync<bool>("video => video === window.languageVideo"));
        Assert.Equal(["en", "en"], await page.EvaluateAsync<string[]>("() => window.languageRequests"));
        Assert.Empty(errors);
    }

    [Fact]
    public async Task LanguageTimeoutRejectsDuplicateChoicesAndIgnoresALateSavedResponse()
    {
        await ObserveLanguageRequestsAsync();
        await EditDescriptionAsync();
        await page.Locator("#DescriptionInput").FillAsync("Draft survives the timeout");
        await page.Clock.InstallAsync();
        var captured = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var delivered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var requests = 0;
        await page.RouteAsync("**/settings/language", async route =>
        {
            var order = Interlocked.Increment(ref requests);
            var response = await route.FetchAsync();
            if (order == 1)
            {
                captured.TrySetResult();
                await release.Task;
            }
            try
            {
                await route.FulfillAsync(new() { Response = response });
                if (order == 1) delivered.TrySetResult();
            }
            catch (Exception exception)
            {
                if (order == 1) delivered.TrySetException(exception);
                throw;
            }
        });
        try
        {
            await page.Locator("#language-toggle").ClickAsync();
            await page.Locator("#language-en").ClickAsync();
            await captured.Task.WaitAsync(TimeSpan.FromSeconds(10));
            var button = page.Locator("#language-toggle");
            await Expect(button).ToHaveAttributeAsync("aria-busy", "true");
            await Expect(button).ToHaveAttributeAsync("aria-disabled", "true");
            await Expect(page.Locator("html")).ToHaveAttributeAsync("lang", "ko");
            await Expect(page.Locator("#language-ko")).ToHaveAttributeAsync("aria-checked", "true");

            // Pointer activation cannot reopen the busy picker, and a queued option
            // activation must not issue another save while the first is pending.
            await button.ClickAsync(new() { Force = true });
            await Expect(button).ToHaveAttributeAsync("aria-expanded", "false");
            await page.Locator("#language-ko").DispatchEventAsync("click");
            Assert.Equal(["en"], await page.EvaluateAsync<string[]>("() => window.languageRequests"));

            await page.Clock.FastForwardAsync(10000);

            await Expect(page.Locator("#language-error")).ToBeVisibleAsync();
            await ExpectLanguageChoiceAsync("ko");
            await Expect(page.Locator("#DescriptionInput")).ToHaveValueAsync("Draft survives the timeout");
            Assert.Contains("AbortError:en", await page.EvaluateAsync<string[]>("() => window.languageCompletions"));

            // Choosing the current language is a real retry that pins the preference.
            // Its response arrives before the first request's saved English response.
            await ChooseLanguageAsync("ko");
            await ExpectLanguageChoiceAsync("ko");
            await Expect(page.Locator("#language-error")).ToBeHiddenAsync();
            Assert.Equal(["en", "ko"], await page.EvaluateAsync<string[]>("() => window.languageRequests"));

            release.TrySetResult();
            await delivered.Task.WaitAsync(TimeSpan.FromSeconds(10));

            await ExpectLanguageChoiceAsync("ko");
            await Expect(page.Locator("#language-error")).ToBeHiddenAsync();
            await Expect(page.Locator("#DescriptionInput")).ToHaveValueAsync("Draft survives the timeout");
            Assert.True(await page.Locator("video").EvaluateAsync<bool>("video => video === window.languageVideo"));
            Assert.Equal(["AbortError:en", "204:ko"],
                await page.EvaluateAsync<string[]>("() => window.languageCompletions"));
            Assert.Equal(2, Volatile.Read(ref requests));
            await page.ReloadAsync();
            await ExpectLanguageChoiceAsync("ko");
            Assert.Empty(errors);
        }
        finally { release.TrySetResult(); }
    }

    private async Task ExpectLanguageChoiceAsync(string language)
    {
        await Expect(page.Locator("html")).ToHaveAttributeAsync("lang", language);
        await Expect(page.Locator("#language-native")).ToHaveValueAsync(language);
        await Expect(page.Locator("#language-ko")).ToHaveAttributeAsync("aria-checked", language == "ko" ? "true" : "false");
        await Expect(page.Locator("#language-en")).ToHaveAttributeAsync("aria-checked", language == "en" ? "true" : "false");
        await Expect(page.Locator("#language-toggle")).Not.ToHaveAttributeAsync("aria-busy", "true");
        await Expect(page.Locator("#language-toggle")).Not.ToHaveAttributeAsync("aria-disabled", "true");
    }

    private async Task ObserveLanguageRequestsAsync()
    {
        await page.EvaluateAsync("""
            () => {
                window.languageRequests = [];
                window.languageCompletions = [];
                window.languageVideo = document.querySelector('video');
                const fetch = window.fetch.bind(window);
                window.fetch = (input, options) => {
                    const url = new URL(typeof input === 'string' ? input : input.url, document.baseURI);
                    if (url.pathname !== '/settings/language') return fetch(input, options);
                    const language = options.body.get('language');
                    window.languageRequests.push(language);
                    return fetch(input, options).then(response => {
                        window.languageCompletions.push(`${response.status}:${language}`);
                        return response;
                    }, error => {
                        window.languageCompletions.push(`${error.name}:${language}`);
                        throw error;
                    });
                };
            }
            """);
    }
}
