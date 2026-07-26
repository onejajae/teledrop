using System.Security.Cryptography;
using Microsoft.EntityFrameworkCore;
using Teledrop.Data;

namespace Teledrop.Features.UploadTickets;

public sealed class UploadTicketCredentialGenerator(
    TeledropDbContext dbContext)
{
    public const int TicketPathLength = 4;
    public const int TicketCodeLength = 8;
    public const string Alphabet = "abcdefghjkmnpqrstuvwxyz23456789";

    private const int PathGenerationAttempts = 12;

    public async Task<string> GenerateUniqueTicketPathAsync(
        CancellationToken cancellationToken = default)
    {
        for (var attempt = 0; attempt < PathGenerationAttempts; attempt++)
        {
            var candidate = CreateRandomValue(TicketPathLength);
            var exists = await dbContext.UploadTickets
                .AsNoTracking()
                .AnyAsync(
                    ticket => ticket.Path == candidate,
                    cancellationToken);
            if (!exists)
            {
                return candidate;
            }
        }

        throw new InvalidOperationException(
            "A unique Ticket Path could not be generated.");
    }

    public string GenerateTicketCode()
    {
        return CreateRandomValue(TicketCodeLength);
    }

    public static bool TryNormalizeTicketPath(
        string? value,
        out string normalizedPath)
    {
        return TryNormalize(
            value,
            TicketPathLength,
            out normalizedPath);
    }

    public static bool TryNormalizeTicketCode(
        string? value,
        out string normalizedCode)
    {
        return TryNormalize(
            value,
            TicketCodeLength,
            out normalizedCode);
    }

    public static string FormatTicketCode(string code)
    {
        return string.Concat(
            code.AsSpan(0, 4),
            "-",
            code.AsSpan(4, 4))
            .ToUpperInvariant();
    }

    private static string CreateRandomValue(int length)
    {
        return string.Create(
            length,
            Alphabet,
            static (characters, alphabet) =>
            {
                for (var index = 0; index < characters.Length; index++)
                {
                    characters[index] = alphabet[
                        RandomNumberGenerator.GetInt32(31)];
                }
            });
    }

    private static bool TryNormalize(
        string? value,
        int expectedLength,
        out string normalizedValue)
    {
        normalizedValue = value?
            .Replace("-", string.Empty, StringComparison.Ordinal)
            .ToLowerInvariant()
            ?? string.Empty;

        return normalizedValue.Length == expectedLength
            && normalizedValue.All(Alphabet.Contains);
    }
}
