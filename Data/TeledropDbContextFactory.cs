using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace Teledrop.Data;

public sealed class TeledropDbContextFactory
    : IDesignTimeDbContextFactory<TeledropDbContext>
{
    public TeledropDbContext CreateDbContext(string[] args)
    {
        var connectionString = Environment.GetEnvironmentVariable(
                "ConnectionStrings__DefaultConnection")
            ?? TeledropDbContext.DefaultConnectionString;
        var options = new DbContextOptionsBuilder<TeledropDbContext>()
            .UseSqlite(connectionString)
            .Options;

        return new TeledropDbContext(options);
    }
}
