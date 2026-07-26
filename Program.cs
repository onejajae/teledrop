using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authorization;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Teledrop;
using Teledrop.Data;
using Teledrop.Features.Auth;

var builder = WebApplication.CreateBuilder(args);

builder.WebHost.ConfigureKestrel((context, options) =>
{
    options.Limits.MaxRequestBodySize = context.Configuration.GetValue(
        "MAX_UPLOAD_BYTES",
        TeledropOptions.DefaultMaxUploadBytes);
});

builder.Services.AddRazorPages();
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
    });

builder.Services.AddAuthorization(options =>
{
    options.FallbackPolicy = new AuthorizationPolicyBuilder()
        .RequireAuthenticatedUser()
        .Build();
});

builder.Services.AddDbContext<TeledropDbContext>((serviceProvider, options) =>
{
    var configuration = serviceProvider.GetRequiredService<IConfiguration>();
    options.UseSqlite(GetDatabaseConnectionString(configuration));
});

var app = builder.Build();

var teledropOptions = app.Services.GetRequiredService<IOptions<TeledropOptions>>().Value;
Directory.CreateDirectory(teledropOptions.ShareDirectory);

var connectionString = GetDatabaseConnectionString(app.Configuration);
var databasePath = new SqliteConnectionStringBuilder(connectionString).DataSource;
var databaseDirectory = Path.GetDirectoryName(databasePath);
if (!string.IsNullOrWhiteSpace(databaseDirectory))
{
    Directory.CreateDirectory(databaseDirectory);
}

using (var scope = app.Services.CreateScope())
{
    var dbContext = scope.ServiceProvider.GetRequiredService<TeledropDbContext>();
    dbContext.Database.Migrate();
}

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}

app.UseHttpsRedirection();

app.UseRouting();

app.UseAuthentication();
app.UseAuthorization();

app.MapStaticAssets()
   .AllowAnonymous();
app.MapRazorPages()
   .WithStaticAssets();

app.Run();

static string GetDatabaseConnectionString(IConfiguration configuration)
{
    return configuration.GetConnectionString(TeledropDbContext.ConnectionStringName)
        ?? TeledropDbContext.DefaultConnectionString;
}

public partial class Program;
