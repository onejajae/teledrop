using Teledrop.Features.Api;
using Teledrop.Features.Drops;
using Teledrop.Infrastructure;
using Teledrop.Features.Auth;

if (args.FirstOrDefault() == "hash-password")
{
    Environment.ExitCode = HashPasswordCommand.Run(args.Skip(1).ToArray());
    return;
}

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddScoped<DropSlugs>();
builder.Services.AddScoped<DropUseCases>();
builder.Services.AddSingleton(TimeProvider.System);
builder.AddTeledropInfrastructure();

var app = builder.Build();
await app.InitializeTeledropStorageAsync();

app.UseTeledropSecurityHeaders();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();

app.MapApiUpload();
app.MapStaticAssets()
   .AllowAnonymous();
app.MapRazorPages()
   .WithStaticAssets();

app.Run();

public partial class Program;
