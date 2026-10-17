using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Options;
using Xunit;

namespace Teledrop.Tests;

public sealed class StartupValidationTests
{
    [Theory]
    [InlineData("WEB_USERNAME", "", "WEB_USERNAME must be set to the owner login name.")]
    [InlineData("WEB_USERNAME", "   ", "WEB_USERNAME must be set to the owner login name.")]
    [InlineData("WEB_PASSWORD", "", "WEB_PASSWORD must be set to an argon2id encoded hash string.")]
    [InlineData("WEB_PASSWORD", "plaintext-password", "WEB_PASSWORD must be set to an argon2id encoded hash string.")]
    [InlineData("MAX_UPLOAD_BYTES", "0", "MAX_UPLOAD_BYTES must be greater than zero.")]
    [InlineData("MAX_UPLOAD_BYTES", "-1", "MAX_UPLOAD_BYTES must be greater than zero.")]
    public void InvalidConfigurationPreventsStartupBeforeCreatingStorage(
        string key, string value, string expectedFailure)
    {
        using var factory = new TeledropWebApplicationFactory();
        using var app = factory.WithWebHostBuilder(builder => builder.ConfigureAppConfiguration(
            (_, configuration) => configuration.AddInMemoryCollection(
                new Dictionary<string, string?> { [key] = value })));

        var error = Assert.Throws<OptionsValidationException>(() =>
        {
            using var client = app.CreateClient();
        });

        Assert.Contains(expectedFailure, error.Failures);
        Assert.False(Directory.Exists(factory.ShareDirectory));
        Assert.False(File.Exists(factory.DatabasePath));
    }
}
