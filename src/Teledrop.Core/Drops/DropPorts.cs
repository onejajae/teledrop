namespace Teledrop.Features.Drops;

public interface IDropCommandStore
{
    Task<Drop?> FindBySlugAsync(
        string slug,
        CancellationToken cancellationToken);

    Task AddAsync(
        Drop drop,
        CancellationToken cancellationToken);

    Task UpdateAsync(
        Drop drop,
        CancellationToken cancellationToken);

    Task<Drop?> DeleteBySlugAsync(
        string slug,
        CancellationToken cancellationToken);
}

public interface IDropSlugIndex
{
    Task<bool> ExistsAsync(
        string slug,
        Guid? excludingDropId,
        CancellationToken cancellationToken);
}

public interface IStoredDropFileCleanup
{
    void TryDelete(string location);
}

public interface IDropPasswordHasher
{
    string Hash(string dropPassword);
}
