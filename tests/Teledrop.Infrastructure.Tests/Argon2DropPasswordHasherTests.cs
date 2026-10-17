using Isopoh.Cryptography.Argon2;
using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Infrastructure.Tests;

public sealed class Argon2DropPasswordHasherTests
{
    [Fact]
    public void HashesPreserveTheExactPasswordAndUseFreshSalts()
    {
        var hasher = new Argon2DropPasswordHasher();
        const string password = "  드롭 비밀번호 🔑  ";

        var first = hasher.Hash(password);
        var second = hasher.Hash(password);

        Assert.NotEqual(first, second);
        foreach (var encoded in new[] { first, second })
        {
            Assert.True(Argon2.Verify(encoded, password));
            Assert.False(Argon2.Verify(encoded, password.Trim()));
            Assert.False(Argon2.Verify(encoded, "wrong-password"));
        }
    }
}
