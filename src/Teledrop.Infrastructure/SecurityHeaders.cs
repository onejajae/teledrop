using System.Security.Cryptography;

namespace Teledrop.Infrastructure
{
    public static class SecurityHeadersExtensions
    {
        public static IApplicationBuilder UseTeledropSecurityHeaders(
            this IApplicationBuilder app)
        {
            return app.Use(async (context, next) =>
            {
                var scriptNonce = Convert.ToBase64String(
                    RandomNumberGenerator.GetBytes(32));
                context.Items[SecurityHeaders.ContentSecurityPolicyNonceItemKey] = scriptNonce;

                context.Response.OnStarting(() =>
                {
                    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
                    context.Response.Headers["Content-Security-Policy"] =
                        "default-src 'self'; "
                        + $"script-src 'self' 'nonce-{scriptNonce}'; "
                        + "style-src 'self' 'unsafe-inline'; "
                        + "img-src 'self' blob:; "
                        + "media-src 'self' blob:; "
                        + "object-src 'none'; "
                        + "frame-ancestors 'self'; "
                        + "base-uri 'self'";
                    return Task.CompletedTask;
                });

                await next();
            });
        }
    }
}

internal static class SecurityHeaders
{
    internal const string ContentSecurityPolicyNonceItemKey = "ContentSecurityPolicyNonce";
}
