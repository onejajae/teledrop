namespace Teledrop.Features.Drops;

public static class DropAccessPolicy
{
    public static DropAccessDecision Evaluate(
        Drop drop,
        bool isOwner,
        bool hasValidDropPasswordGrant)
    {
        if (isOwner)
        {
            return DropAccessDecision.Allowed;
        }

        if (drop.IsPrivate)
        {
            return DropAccessDecision.OwnerAuthenticationRequired;
        }

        return drop.DropPasswordHash is not null
            && !hasValidDropPasswordGrant
                ? DropAccessDecision.DropPasswordRequired
                : DropAccessDecision.Allowed;
    }
}

public enum DropAccessDecision
{
    Allowed,
    OwnerAuthenticationRequired,
    DropPasswordRequired,
}
