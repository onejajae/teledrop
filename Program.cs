using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Teledrop;
using Teledrop.Data;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddRazorPages();
builder.Services.Configure<TeledropOptions>(builder.Configuration);

var connectionString = builder.Configuration.GetConnectionString(
        TeledropDbContext.ConnectionStringName)
    ?? TeledropDbContext.DefaultConnectionString;

builder.Services.AddDbContext<TeledropDbContext>(options =>
    options.UseSqlite(connectionString));

var app = builder.Build();

var teledropOptions = app.Services.GetRequiredService<IOptions<TeledropOptions>>().Value;
Directory.CreateDirectory(teledropOptions.ShareDirectory);

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

app.UseAuthorization();

app.MapStaticAssets();
app.MapRazorPages()
   .WithStaticAssets();

app.Run();
