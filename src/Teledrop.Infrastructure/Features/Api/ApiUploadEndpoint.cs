using System.Security.Cryptography;
using System.Text;
using Microsoft.Extensions.Options;
using Microsoft.Net.Http.Headers;
using Teledrop.Features.Drops;

namespace Teledrop.Features.Api;

public static class ApiUploadEndpoint
{
    private const string ApiKeyHeaderName = "X-API-Key";

    public static RouteHandlerBuilder MapApiUpload(this IEndpointRouteBuilder endpoints)
        => endpoints.MapPost("/api/upload", HandleAsync).AllowAnonymous().DisableAntiforgery();

    private static async Task<IResult> HandleAsync(
        HttpContext httpContext, DropUploadReceiver uploads, IOptions<TeledropOptions> options)
    {
        if (!HasValidApiKey(httpContext.Request, options.Value))
        {
            httpContext.Response.Headers[HeaderNames.WWWAuthenticate] = "ApiKey";
            return Results.Unauthorized();
        }
        try
        {
            var drop = await uploads.ReceiveApiAsync(httpContext.Request, httpContext.RequestAborted);
            return Results.Ok(new ApiUploadResponse(drop.Slug, $"/{drop.Slug}", drop.FileName, drop.FileSizeBytes));
        }
        catch (DropUploadTooLargeException)
        {
            return Results.StatusCode(StatusCodes.Status413PayloadTooLarge);
        }
        catch (InvalidUploadException)
        {
            return Results.BadRequest();
        }
    }

    private static bool HasValidApiKey(
        HttpRequest request,
        TeledropOptions options)
    {
        if (string.IsNullOrWhiteSpace(options.ApiKey)
            || !request.Headers.TryGetValue(
                ApiKeyHeaderName,
                out var providedApiKeys)
            || providedApiKeys.Count != 1)
        {
            return false;
        }

        return ApiKeysMatch(
            options.ApiKey,
            providedApiKeys[0] ?? string.Empty);
    }

    private static bool ApiKeysMatch(
        string expectedApiKey,
        string providedApiKey)
    {
        var expectedHash = SHA256.HashData(
            Encoding.UTF8.GetBytes(expectedApiKey));
        var providedHash = SHA256.HashData(
            Encoding.UTF8.GetBytes(providedApiKey));

        return CryptographicOperations.FixedTimeEquals(
            expectedHash,
            providedHash);
    }

    private sealed record ApiUploadResponse(
        string Slug,
        string Url,
        string FileName,
        long SizeBytes);

}
