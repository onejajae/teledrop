using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authorization;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Teledrop.Data;
using Teledrop.Features.Auth;
using Teledrop.Features.Drops;

namespace Teledrop.Infrastructure;

public static class TeledropInfrastructure
{
    public static WebApplicationBuilder AddTeledropInfrastructure(
        this WebApplicationBuilder builder)
    {
        builder.WebHost.ConfigureKestrel((context, options) =>
        {
            options.Limits.MaxRequestBodySize = context.Configuration.GetValue(
                "MAX_UPLOAD_BYTES",
                TeledropOptions.DefaultMaxUploadBytes);
        });

        builder.Services.AddRazorPages();
        builder.Services.AddDataProtection();
        builder.Services.AddSingleton<DropUnlockCookie>();
        builder.Services.AddScoped<DropAccess>();
        builder.Services.AddScoped<EfDropStore>();
        builder.Services.AddScoped<IDropCommandStore>(
            services => services.GetRequiredService<EfDropStore>());
        builder.Services.AddScoped<IDropPasswordHasher, Argon2DropPasswordHasher>();
        builder.Services.AddScoped<DropFileStore>();
        builder.Services.AddScoped<IStoredDropFileCleanup>(
            services => services.GetRequiredService<DropFileStore>());
        builder.Services.AddScoped<DropUploadReceiver>();
        builder.Services
            .AddOptions<TeledropOptions>()
            .Bind(builder.Configuration)
            .Validate(
                options => !string.IsNullOrWhiteSpace(options.WebUsername),
                "WEB_USERNAME must be set to the owner login name.")
            .Validate(
                options => !string.IsNullOrWhiteSpace(options.WebPassword)
                    && options.WebPassword.StartsWith("$argon2id$", StringComparison.Ordinal),
                "WEB_PASSWORD must be set to an argon2id encoded hash string.")
            .Validate(
                options => options.MaxUploadBytes > 0,
                "MAX_UPLOAD_BYTES must be greater than zero.")
            .ValidateOnStart();

        builder.Services
            .AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
            .AddCookie(options =>
            {
                options.LoginPath = "/login";
                options.ExpireTimeSpan = TimeSpan.FromDays(30);
                options.SlidingExpiration = true;
                options.Events.OnValidatePrincipal = OwnerSession.ValidatePrincipalAsync;
                options.Events.OnRedirectToLogin = context =>
                {
                    if (context.Request.Headers["HX-Request"] == "true")
                    {
                        context.Response.Headers["HX-Redirect"] = "/login";
                    }
                    else
                    {
                        context.Response.Redirect(context.RedirectUri);
                    }

                    return Task.CompletedTask;
                };
            });

        builder.Services.AddAuthorization(options =>
        {
            options.FallbackPolicy = new AuthorizationPolicyBuilder()
                .RequireAuthenticatedUser()
                .Build();
        });

        builder.Services.AddDbContext<TeledropDbContext>((services, options) =>
        {
            var configuration = services.GetRequiredService<IConfiguration>();
            options.UseSqlite(GetDatabaseConnectionString(configuration));
        });

        return builder;
    }

    public static async Task InitializeTeledropStorageAsync(
        this WebApplication app,
        CancellationToken cancellationToken = default)
    {
        var options = app.Services.GetRequiredService<IOptions<TeledropOptions>>().Value;
        Directory.CreateDirectory(options.ShareDirectory);

        var connectionString = GetDatabaseConnectionString(app.Configuration);
        var databasePath = new SqliteConnectionStringBuilder(connectionString).DataSource;
        var databaseDirectory = Path.GetDirectoryName(databasePath);
        if (!string.IsNullOrWhiteSpace(databaseDirectory))
        {
            Directory.CreateDirectory(databaseDirectory);
        }

        await using var scope = app.Services.CreateAsyncScope();
        var dbContext = scope.ServiceProvider.GetRequiredService<TeledropDbContext>();
        await dbContext.Database.MigrateAsync(cancellationToken);
    }

    private static string GetDatabaseConnectionString(IConfiguration configuration)
    {
        return configuration.GetConnectionString(TeledropDbContext.ConnectionStringName)
            ?? TeledropDbContext.DefaultConnectionString;
    }
}
