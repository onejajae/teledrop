using Microsoft.EntityFrameworkCore;
using Teledrop.Data;
using Xunit;

namespace Teledrop.Infrastructure.Tests;

[CollectionDefinition(nameof(DesignTimeDatabaseEnvironment), DisableParallelization = true)]
public sealed class DesignTimeDatabaseEnvironment
{
}

[Collection(nameof(DesignTimeDatabaseEnvironment))]
public sealed class TeledropDbContextFactoryTests
{
    [Theory]
    [InlineData(null, "Data Source=share/database.db")]
    [InlineData("Data Source=design-time-override.db;Pooling=False",
        "Data Source=design-time-override.db;Pooling=False")]
    public void DesignTimeContextUsesTheEnvironmentOrDefaultConnection(
        string? configured, string expected)
    {
        const string variable = "ConnectionStrings__DefaultConnection";
        var original = Environment.GetEnvironmentVariable(variable);
        try
        {
            Environment.SetEnvironmentVariable(variable, configured);

            using var context = new TeledropDbContextFactory().CreateDbContext([]);

            Assert.Equal("Microsoft.EntityFrameworkCore.Sqlite", context.Database.ProviderName);
            Assert.Equal(expected, context.Database.GetConnectionString());
            Assert.Equal(System.Data.ConnectionState.Closed,
                context.Database.GetDbConnection().State);
        }
        finally
        {
            Environment.SetEnvironmentVariable(variable, original);
        }
    }
}
