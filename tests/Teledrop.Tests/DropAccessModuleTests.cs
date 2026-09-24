using System.Security.Claims;
using Isopoh.Cryptography.Argon2;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Teledrop.Data;
using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Tests;

public sealed class DropAccessModuleTests
{
    [Theory]
    [InlineData("missing", false, false, DropAccessStatus.OwnerAuthenticationRequired)]
    [InlineData("missing", false, true, DropAccessStatus.OwnerAuthenticationRequired)]
    [InlineData("missing", true, false, DropAccessStatus.NotFound)]
    [InlineData("missing", true, true, DropAccessStatus.NotFound)]
    [InlineData("private", false, false, DropAccessStatus.OwnerAuthenticationRequired)]
    [InlineData("private", false, true, DropAccessStatus.OwnerAuthenticationRequired)]
    [InlineData("locked", false, false, DropAccessStatus.DropPasswordRequired)]
    [InlineData("locked", false, true, DropAccessStatus.InvalidDropPassword)]
    public async Task DeniedResultsNeverExposeADropOrIssueAGrant(
        string slug, bool owner, bool unlock, DropAccessStatus expected)
    {
        using var factory = new TeledropWebApplicationFactory();
        await using var scope = factory.Services.CreateAsyncScope();
        if (slug != "missing")
        {
            var db = scope.ServiceProvider.GetRequiredService<TeledropDbContext>();
            db.Drops.Add(new Drop
            {
                Id = Guid.NewGuid(), Slug = slug, IsPrivate = slug == "private",
                DropPasswordHash = Argon2.Hash("secret"), Title = "Hidden title",
                FileName = "hidden.bin", FileHash = "hash", Location = "hidden-location",
                ContentType = "application/octet-stream",
            });
            await db.SaveChangesAsync();
        }
        var context = new DefaultHttpContext();
        if (owner)
            context.User = new ClaimsPrincipal(new ClaimsIdentity(
                [new Claim(ClaimTypes.Name, "Owner")], "test"));
        var access = scope.ServiceProvider.GetRequiredService<DropAccess>();

        var result = unlock
            ? await access.UnlockAsync(context, slug, "wrong", default)
            : await access.ReadAsync(context, slug, default);

        Assert.Equal(expected, result.Status);
        Assert.Null(result.Drop);
        Assert.False(context.Response.Headers.ContainsKey("Set-Cookie"));
    }
}
