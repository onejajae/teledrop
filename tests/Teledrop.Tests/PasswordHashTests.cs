using Isopoh.Cryptography.Argon2;
using Teledrop.Infrastructure;
using Xunit;

namespace Teledrop.Tests;

public sealed class PasswordHashTests
{
    [Theory]
    [InlineData(1)]
    [InlineData(4)]
    public void VerifiesExistingHashesWithoutChangingTheirParameters(int parallelism)
    {
        const string password = "기존 비밀번호 $ with spaces";
        var hash = Argon2.Hash(password, timeCost: 3, memoryCost: 65536, parallelism: parallelism);

        Assert.True(PasswordHash.Verify(hash, password));
        Assert.False(PasswordHash.Verify(hash, "wrong-password"));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("$argon2id$invalid")]
    [InlineData("$argon2id$v=19$m=65536,t=3,p=4$invalid$invalid")]
    public void RejectsMalformedHashes(string? hash)
    {
        Assert.False(PasswordHash.Verify(hash, "password"));
    }
}
