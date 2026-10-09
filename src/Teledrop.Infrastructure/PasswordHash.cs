using System.Security.Cryptography;
using System.Text;
using Geralt;

namespace Teledrop.Infrastructure;

public static class PasswordHash
{
    public static string Hash(string password)
    {
        var passwordBytes = Encoding.UTF8.GetBytes(password);
        try
        {
            Span<char> hash = stackalloc char[Argon2id.HashSize];
            Argon2id.ComputeHash(hash, passwordBytes, iterations: 3, memorySize: 64 * 1024 * 1024);
            return hash.ToString().TrimEnd('\0');
        }
        finally
        {
            CryptographicOperations.ZeroMemory(passwordBytes);
        }
    }

    public static bool Verify(string? encodedHash, string password)
    {
        if (string.IsNullOrEmpty(encodedHash)) return false;

        var passwordBytes = Encoding.UTF8.GetBytes(password);
        try
        {
            return Argon2id.VerifyHash(encodedHash, passwordBytes);
        }
        catch (FormatException)
        {
            return false;
        }
        catch (ArgumentOutOfRangeException)
        {
            return false;
        }
        finally
        {
            CryptographicOperations.ZeroMemory(passwordBytes);
        }
    }
}
