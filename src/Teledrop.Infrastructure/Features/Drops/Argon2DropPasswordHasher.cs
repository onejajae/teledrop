using Isopoh.Cryptography.Argon2;

namespace Teledrop.Features.Drops;

public sealed class Argon2DropPasswordHasher : IDropPasswordHasher
{
    public string Hash(string dropPassword)
    {
        return Argon2.Hash(dropPassword);
    }
}
