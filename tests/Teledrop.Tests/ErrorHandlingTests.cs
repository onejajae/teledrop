using System.Data.Common;
using System.Diagnostics;
using System.Net;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Teledrop.Pages;
using Xunit;
using static Teledrop.Tests.HttpTestSupport;

namespace Teledrop.Tests;

public sealed class ErrorHandlingTests
{
    private const string FaultSlug = "test-error-request";
    private const string PrivateFailureDetail = "test-only-database-failure-do-not-disclose";

    [Theory]
    [InlineData("en", "Could not process your request.")]
    [InlineData("ko", "요청을 처리하지 못했습니다.")]
    public async Task ProductionExceptionRendersAnUncachedLocalizedErrorWithTheRequestId(
        string language, string expectedHeading)
    {
        using var factory = new TeledropWebApplicationFactory();
        var interceptor = new FailingReadInterceptor();
        using var app = factory.WithWebHostBuilder(builder =>
        {
            builder.UseEnvironment("Production");
            builder.ConfigureServices(services => services.AddDbContext<TeledropDbContext>(
                options => options.AddInterceptors(interceptor)));
        });
        using var client = CreateClient(app, language: language);

        using var response = await client.GetAsync($"/{FaultSlug}");

        await AssertFailureResponseAsync(response, language, expectedHeading, interceptor.RequestId);
        Assert.Equal(1, interceptor.Failures);
    }

    [Fact]
    public async Task OwnerErrorPageDoesNotOpenTheDatabaseAgainDuringAnOutage()
    {
        const string language = "ko";
        const string expectedHeading = "요청을 처리하지 못했습니다.";
        using var factory = new TeledropWebApplicationFactory();
        var outage = new UnavailableDatabaseInterceptor();
        using var app = factory.WithWebHostBuilder(builder =>
        {
            builder.UseEnvironment("Production");
            builder.ConfigureServices(services => services.AddDbContext<TeledropDbContext>(
                options => options.AddInterceptors(outage)));
        });
        await SeedDropAsync(app, "outage-source", [1]);
        using var client = CreateClient(app, language: language);
        await LogInOwnerAsync(client);
        outage.IsUnavailable = true;

        using var response = await client.GetAsync("/outage-source");

        var html = await AssertFailureResponseAsync(response, language, expectedHeading, outage.RequestId);
        Assert.Equal(1, outage.FailedConnections);
        Assert.DoesNotContain("id=\"drop-list\"", html);
        Assert.DoesNotContain("outage-source.bin", html);
    }

    [Fact]
    public async Task FailedOwnerPostRendersTheErrorPageWithItsRequestId()
    {
        const string language = "ko";
        const string expectedHeading = "요청을 처리하지 못했습니다.";
        using var factory = new TeledropWebApplicationFactory();
        var failure = new FailingSaveInterceptor();
        using var app = factory.WithWebHostBuilder(builder =>
        {
            builder.UseEnvironment("Production");
            builder.ConfigureServices(services => services.AddDbContext<TeledropDbContext>(
                options => options.AddInterceptors(failure)));
        });
        await SeedDropAsync(app, "save-source", [1], drop => drop.Description = "Original description");
        using var client = CreateClient(app, language: language);
        await LogInOwnerAsync(client);
        var token = await GetAntiforgeryAsync(client, "/drops/save-source");
        failure.IsEnabled = true;
        using var form = new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["__RequestVerificationToken"] = token,
            ["DescriptionInput"] = "Must not be saved",
        });

        using var response = await client.PostAsync("/drops/save-source?handler=Metadata", form);

        var html = await AssertFailureResponseAsync(response, language, expectedHeading, failure.RequestId);
        Assert.Equal(1, failure.FailedSaves);
        Assert.DoesNotContain("id=\"drop-list\"", html);
        Assert.DoesNotContain("Must not be saved", html);
        await using var scope = app.Services.CreateAsyncScope();
        var saved = await scope.ServiceProvider.GetRequiredService<TeledropDbContext>()
            .Drops.AsNoTracking().SingleAsync();
        Assert.Equal("Original description", saved.Description);
        Assert.Null(saved.UpdatedAt);
    }

    [Fact]
    public void ErrorRequestIdFallsBackToTheHttpTraceWithoutAnActivity()
    {
        var originalActivity = Activity.Current;
        try
        {
            Activity.Current = null;
            var model = new ErrorModel
            {
                PageContext = new PageContext
                {
                    HttpContext = new DefaultHttpContext { TraceIdentifier = "fallback-http-request" },
                },
            };

            model.OnGet();

            Assert.Equal("fallback-http-request", model.RequestId);
            Assert.True(model.ShowRequestId);
        }
        finally
        {
            Activity.Current = originalActivity;
        }
    }

    private static async Task<string> AssertFailureResponseAsync(
        HttpResponseMessage response, string language, string expectedHeading, string? requestId)
    {
        Assert.Equal(HttpStatusCode.InternalServerError, response.StatusCode);
        Assert.False(string.IsNullOrEmpty(requestId));
        var html = WebUtility.HtmlDecode(await response.Content.ReadAsStringAsync());
        var heading = Regex.Match(html, "<h1\\b[^>]*>(.*?)</h1>", RegexOptions.Singleline);
        Assert.True(heading.Success);
        Assert.Equal(expectedHeading, heading.Groups[1].Value);
        Assert.Contains($"<html lang=\"{language}\"", html);
        Assert.Contains(language, response.Content.Headers.ContentLanguage);
        Assert.Contains($"<code>{requestId}</code>", html);
        Assert.DoesNotContain(PrivateFailureDetail, html);
        Assert.DoesNotContain(nameof(InvalidOperationException), html);
        Assert.True(response.Headers.CacheControl?.NoStore);
        Assert.True(response.Headers.CacheControl?.NoCache);
        Assert.Contains(response.Headers.Pragma, directive => directive.Name == "no-cache");
        Assert.Equal("nosniff", Assert.Single(response.Headers.GetValues("X-Content-Type-Options")));
        var policy = Assert.Single(response.Headers.GetValues("Content-Security-Policy"));
        Assert.Contains("default-src 'self'", policy);
        Assert.Contains("object-src 'none'", policy);
        Assert.Contains("frame-ancestors 'self'", policy);
        Assert.Contains("base-uri 'self'", policy);
        var nonce = Regex.Match(policy, "'nonce-([^']+)'");
        Assert.True(nonce.Success);
        Assert.Contains($"nonce=\"{nonce.Groups[1].Value}\"", html);
        return html;
    }

    private sealed class UnavailableDatabaseInterceptor : DbConnectionInterceptor
    {
        internal bool IsUnavailable { get; set; }
        internal int FailedConnections { get; private set; }
        internal string? RequestId { get; private set; }

        public override InterceptionResult ConnectionOpening(
            DbConnection connection, ConnectionEventData eventData, InterceptionResult result)
        {
            ThrowIfUnavailable();
            return result;
        }

        public override ValueTask<InterceptionResult> ConnectionOpeningAsync(
            DbConnection connection, ConnectionEventData eventData,
            InterceptionResult result, CancellationToken cancellationToken = default)
        {
            ThrowIfUnavailable();
            return ValueTask.FromResult(result);
        }

        private void ThrowIfUnavailable()
        {
            if (!IsUnavailable) return;
            FailedConnections++;
            RequestId ??= Activity.Current?.Id;
            throw new InvalidOperationException(PrivateFailureDetail);
        }
    }

    private sealed class FailingSaveInterceptor : SaveChangesInterceptor
    {
        internal bool IsEnabled { get; set; }
        internal int FailedSaves { get; private set; }
        internal string? RequestId { get; private set; }

        public override ValueTask<InterceptionResult<int>> SavingChangesAsync(
            DbContextEventData eventData, InterceptionResult<int> result,
            CancellationToken cancellationToken = default)
        {
            if (IsEnabled)
            {
                FailedSaves++;
                RequestId = Activity.Current?.Id;
                throw new InvalidOperationException(PrivateFailureDetail);
            }

            return ValueTask.FromResult(result);
        }
    }

    private sealed class FailingReadInterceptor : DbCommandInterceptor
    {
        internal int Failures { get; private set; }
        internal string? RequestId { get; private set; }

        public override ValueTask<InterceptionResult<DbDataReader>> ReaderExecutingAsync(
            DbCommand command, CommandEventData eventData,
            InterceptionResult<DbDataReader> result, CancellationToken cancellationToken = default)
        {
            if (command.Parameters.Cast<DbParameter>().Any(parameter => Equals(parameter.Value, FaultSlug)))
            {
                Failures++;
                RequestId = Activity.Current?.Id;
                throw new InvalidOperationException(PrivateFailureDetail);
            }

            return base.ReaderExecutingAsync(command, eventData, result, cancellationToken);
        }
    }
}
