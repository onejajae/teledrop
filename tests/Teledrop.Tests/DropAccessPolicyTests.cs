using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Tests;

public sealed class DropAccessPolicyTests
{
    [Fact]
    public void OwnerCanAccessEveryDropWithoutPasswordGrant()
    {
        var drop = CreateDrop(isPrivate: true, hasPassword: true);

        var decision = DropAccessPolicy.Evaluate(
            drop,
            isOwner: true,
            hasValidDropPasswordGrant: false);

        Assert.Equal(DropAccessDecision.Allowed, decision);
    }

    [Fact]
    public void PrivateDropRequiresOwnerAuthentication()
    {
        var drop = CreateDrop(isPrivate: true, hasPassword: false);

        var decision = DropAccessPolicy.Evaluate(
            drop,
            isOwner: false,
            hasValidDropPasswordGrant: false);

        Assert.Equal(
            DropAccessDecision.OwnerAuthenticationRequired,
            decision);
    }

    [Fact]
    public void PublicDropWithoutPasswordAllowsAnonymousAccess()
    {
        var drop = CreateDrop(isPrivate: false, hasPassword: false);

        var decision = DropAccessPolicy.Evaluate(
            drop,
            isOwner: false,
            hasValidDropPasswordGrant: false);

        Assert.Equal(DropAccessDecision.Allowed, decision);
    }

    [Fact]
    public void PasswordProtectedPublicDropRequiresValidGrant()
    {
        var drop = CreateDrop(isPrivate: false, hasPassword: true);

        var locked = DropAccessPolicy.Evaluate(
            drop,
            isOwner: false,
            hasValidDropPasswordGrant: false);
        var unlocked = DropAccessPolicy.Evaluate(
            drop,
            isOwner: false,
            hasValidDropPasswordGrant: true);

        Assert.Equal(DropAccessDecision.DropPasswordRequired, locked);
        Assert.Equal(DropAccessDecision.Allowed, unlocked);
    }

    private static Drop CreateDrop(bool isPrivate, bool hasPassword)
    {
        return new Drop
        {
            Id = Guid.NewGuid(),
            Slug = "policy-drop",
            IsPrivate = isPrivate,
            DropPasswordHash = hasPassword ? "encoded-hash" : null,
            FileName = "sample.bin",
            FileHash = "hash",
            ContentType = "application/octet-stream",
            Location = "location",
        };
    }
}
