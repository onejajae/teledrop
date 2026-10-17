using Teledrop.Features.Drops;
using Xunit;

namespace Teledrop.Core.Tests;

public sealed class DropAccessPolicyTests
{
    [Theory]
    [InlineData(DropAccessLevel.Private, true, false, DropAccessDecision.Allowed)]
    [InlineData(DropAccessLevel.Private, true, true, DropAccessDecision.Allowed)]
    [InlineData(DropAccessLevel.Public, true, false, DropAccessDecision.Allowed)]
    [InlineData(DropAccessLevel.Public, true, true, DropAccessDecision.Allowed)]
    [InlineData(DropAccessLevel.Password, true, false, DropAccessDecision.Allowed)]
    [InlineData(DropAccessLevel.Password, true, true, DropAccessDecision.Allowed)]
    [InlineData(DropAccessLevel.Private, false, false, DropAccessDecision.OwnerAuthenticationRequired)]
    [InlineData(DropAccessLevel.Private, false, true, DropAccessDecision.OwnerAuthenticationRequired)]
    [InlineData(DropAccessLevel.Public, false, false, DropAccessDecision.Allowed)]
    [InlineData(DropAccessLevel.Public, false, true, DropAccessDecision.Allowed)]
    [InlineData(DropAccessLevel.Password, false, false, DropAccessDecision.DropPasswordRequired)]
    [InlineData(DropAccessLevel.Password, false, true, DropAccessDecision.Allowed)]
    public void AccessDependsOnOwnerVisibilityAndPasswordGrant(
        DropAccessLevel level, bool owner, bool hasGrant, DropAccessDecision expected)
    {
        var drop = CreateDrop(level);

        var decision = DropAccessPolicy.Evaluate(drop, owner, hasGrant);

        Assert.Equal(expected, decision);
    }

    private static Drop CreateDrop(DropAccessLevel level)
    {
        return new Drop
        {
            Id = Guid.NewGuid(),
            Slug = "policy-drop",
            IsPrivate = level == DropAccessLevel.Private,
            DropPasswordHash = level == DropAccessLevel.Password ? "encoded-hash" : null,
            FileName = "sample.bin",
            FileHash = "hash",
            ContentType = "application/octet-stream",
            Location = "location",
        };
    }
}
