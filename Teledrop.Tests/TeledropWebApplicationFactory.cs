using Isopoh.Cryptography.Argon2;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;

namespace Teledrop.Tests;

internal sealed class TeledropWebApplicationFactory : WebApplicationFactory<Program>
{
    internal const string WebUsername = "admin";
    internal const string WebPassword = "password";

    private static readonly string InitialPasswordHash = Argon2.Hash(WebPassword);
    private static readonly string ChangedPasswordHash = Argon2.Hash("changed-password");

    private readonly MutableConfigurationSource configurationSource;
    private readonly string temporaryDirectory;

    internal string ShareDirectory { get; }

    internal TeledropWebApplicationFactory()
    {
        temporaryDirectory = Path.Combine(
            Path.GetTempPath(),
            $"teledrop-tests-{Guid.NewGuid():N}");

        ShareDirectory = Path.Combine(temporaryDirectory, "share");
        var databasePath = Path.Combine(temporaryDirectory, "database.db");

        Directory.CreateDirectory(temporaryDirectory);

        configurationSource = new MutableConfigurationSource(
            new Dictionary<string, string?>
            {
                ["WEB_USERNAME"] = WebUsername,
                ["WEB_PASSWORD"] = InitialPasswordHash,
                ["SHARE_DIRECTORY"] = ShareDirectory,
                ["ConnectionStrings:DefaultConnection"] = $"Data Source={databasePath}",
            });
    }

    internal void ChangeWebPassword()
    {
        configurationSource.Provider.SetValue(
            "WEB_PASSWORD",
            ChangedPasswordHash);
    }

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseSetting("hostBuilder:reloadConfigOnChange", "false");
        builder.UseEnvironment("Testing");
        builder.ConfigureAppConfiguration((_, configurationBuilder) =>
        {
            configurationBuilder.Add(configurationSource);
        });
    }

    protected override IEnumerable<System.Reflection.Assembly> GetTestAssemblies()
    {
        return [typeof(TeledropWebApplicationFactory).Assembly];
    }

    protected override void Dispose(bool disposing)
    {
        base.Dispose(disposing);

        if (disposing && Directory.Exists(temporaryDirectory))
        {
            Directory.Delete(temporaryDirectory, recursive: true);
        }
    }

    private sealed class MutableConfigurationSource(
        IReadOnlyDictionary<string, string?> initialValues)
        : IConfigurationSource
    {
        internal MutableConfigurationProvider Provider { get; } = new(initialValues);

        public IConfigurationProvider Build(IConfigurationBuilder builder)
        {
            return Provider;
        }
    }

    private sealed class MutableConfigurationProvider(
        IReadOnlyDictionary<string, string?> initialValues)
        : ConfigurationProvider
    {
        public override void Load()
        {
            Data = new Dictionary<string, string?>(
                initialValues,
                StringComparer.OrdinalIgnoreCase);
        }

        internal void SetValue(string key, string value)
        {
            Set(key, value);
            OnReload();
        }
    }
}
