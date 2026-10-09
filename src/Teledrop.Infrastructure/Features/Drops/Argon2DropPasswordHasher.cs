using Teledrop.Infrastructure;

namespace Teledrop.Features.Drops;

public sealed class Argon2DropPasswordHasher : IDropPasswordHasher
{
    public string Hash(string dropPassword)
    {
        return PasswordHash.Hash(dropPassword);
    }
}
