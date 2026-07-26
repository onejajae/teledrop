using Microsoft.EntityFrameworkCore;
using Teledrop.Data;

namespace Teledrop.Features.Drops;

public sealed class EfDropStore(TeledropDbContext dbContext)
    : IDropCommandStore, IDropSlugIndex
{
    public async Task<Drop?> FindBySlugAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        return await dbContext.Drops.SingleOrDefaultAsync(
            drop => drop.Slug == slug,
            cancellationToken);
    }

    public async Task AddAsync(
        Drop drop,
        CancellationToken cancellationToken)
    {
        dbContext.Drops.Add(drop);
        await dbContext.SaveChangesAsync(cancellationToken);
    }

    public async Task UpdateAsync(
        Drop drop,
        CancellationToken cancellationToken)
    {
        _ = drop;
        await dbContext.SaveChangesAsync(cancellationToken);
    }

    public async Task<Drop?> DeleteBySlugAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        var drop = await FindBySlugAsync(slug, cancellationToken);
        if (drop is null)
        {
            return null;
        }

        dbContext.Drops.Remove(drop);
        await dbContext.SaveChangesAsync(cancellationToken);
        return drop;
    }

    public async Task<bool> ExistsAsync(
        string slug,
        Guid? excludingDropId,
        CancellationToken cancellationToken)
    {
        return await dbContext.Drops
            .AsNoTracking()
            .AnyAsync(
                drop => drop.Slug == slug
                    && (excludingDropId == null
                        || drop.Id != excludingDropId),
                cancellationToken);
    }
}
