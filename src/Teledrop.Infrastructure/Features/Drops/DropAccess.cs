using Isopoh.Cryptography.Argon2;
using Microsoft.EntityFrameworkCore;
using Teledrop.Data;

namespace Teledrop.Features.Drops;

public sealed class DropAccess(
    TeledropDbContext dbContext,
    DropUnlockCookie unlockCookie)
{
    public async Task<DropAccessResult> ReadAsync(
        HttpContext context,
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null) return MissingDrop(context);

        var decision = Evaluate(context, drop);
        if (decision == DropAccessDecision.DropPasswordRequired
            && unlockCookie.IsValid(context.Request, drop))
        {
            decision = Evaluate(context, drop, hasValidGrant: true);
        }

        return FromDecision(drop, decision);
    }

    public async Task<DropAccessResult> UnlockAsync(
        HttpContext context,
        string slug,
        string? dropPassword,
        CancellationToken cancellationToken)
    {
        var drop = await FindDropAsync(slug, cancellationToken);
        if (drop is null) return MissingDrop(context);

        // A submitted password is checked even if the request already has a
        // valid grant. Owner and public Drops without a password need no grant.
        var decision = Evaluate(context, drop);
        if (decision != DropAccessDecision.DropPasswordRequired)
            return FromDecision(drop, decision);

        if (string.IsNullOrEmpty(dropPassword)
            || !Argon2.Verify(drop.DropPasswordHash, dropPassword))
        {
            return DropAccessResult.InvalidDropPassword;
        }

        unlockCookie.Append(context.Response, drop);
        return DropAccessResult.Allowed(drop);
    }

    private Task<Drop?> FindDropAsync(string slug, CancellationToken cancellationToken)
    {
        return string.IsNullOrWhiteSpace(slug)
            ? Task.FromResult<Drop?>(null)
            : dbContext.Drops.AsNoTracking().SingleOrDefaultAsync(
                drop => drop.Slug == slug, cancellationToken);
    }

    private static DropAccessResult MissingDrop(HttpContext context)
        => context.User.Identity?.IsAuthenticated == true
            ? DropAccessResult.NotFound
            : DropAccessResult.OwnerAuthenticationRequired;

    private static DropAccessDecision Evaluate(HttpContext context, Drop drop, bool hasValidGrant = false)
        => DropAccessPolicy.Evaluate(
            drop,
            context.User.Identity?.IsAuthenticated == true,
            hasValidGrant);

    private static DropAccessResult FromDecision(Drop drop, DropAccessDecision decision)
        => decision switch
        {
            DropAccessDecision.Allowed => DropAccessResult.Allowed(drop),
            DropAccessDecision.OwnerAuthenticationRequired => DropAccessResult.OwnerAuthenticationRequired,
            DropAccessDecision.DropPasswordRequired => DropAccessResult.DropPasswordRequired,
            _ => throw new InvalidOperationException("Unknown Drop access decision."),
        };
}

// Only an allowed result carries a Drop. Denied callers cannot accidentally
// render metadata while choosing their page, redirect, or download response.
public sealed class DropAccessResult
{
    private DropAccessResult(DropAccessStatus status, Drop? drop = null)
    {
        Status = status;
        Drop = drop;
    }

    public DropAccessStatus Status { get; }
    public Drop? Drop { get; }

    internal static DropAccessResult Allowed(Drop drop) => new(DropAccessStatus.Allowed, drop);
    internal static DropAccessResult OwnerAuthenticationRequired { get; } = new(DropAccessStatus.OwnerAuthenticationRequired);
    internal static DropAccessResult DropPasswordRequired { get; } = new(DropAccessStatus.DropPasswordRequired);
    internal static DropAccessResult InvalidDropPassword { get; } = new(DropAccessStatus.InvalidDropPassword);
    internal static DropAccessResult NotFound { get; } = new(DropAccessStatus.NotFound);
}

public enum DropAccessStatus
{
    Allowed,
    OwnerAuthenticationRequired,
    DropPasswordRequired,
    InvalidDropPassword,
    NotFound,
}
