using System.Security.Cryptography;
using System.Text.RegularExpressions;

namespace Teledrop.Features.Drops;

public sealed class DropSlugGenerator(IDropSlugIndex dropSlugIndex)
{
    public const int MaximumSlugLength = 64;

    private const int CombinationAttempts = 12;
    private const int SuffixedAttempts = 12;
    private const int RandomSuffixByteCount = 4;

    private static readonly Regex CustomSlugPattern = new(
        "^[a-z0-9][a-z0-9-]{0,63}$",
        RegexOptions.CultureInvariant);

    private static readonly HashSet<string> ReservedSlugs = new(
        [
            "api",
            "css",
            "d",
            "drops",
            "error",
            "index",
            "js",
            "login",
            "logout",
            "static",
            "tickets",
            "u",
            "upload",
        ],
        StringComparer.Ordinal);

    private static readonly string[] Adjectives =
    [
        "able",
        "amber",
        "ancient",
        "apt",
        "arctic",
        "autumn",
        "awake",
        "azure",
        "balanced",
        "bashful",
        "bold",
        "brave",
        "bright",
        "brisk",
        "calm",
        "careful",
        "cheerful",
        "clear",
        "clever",
        "cloudy",
        "coastal",
        "coral",
        "cosmic",
        "crisp",
        "curious",
        "daring",
        "dawn",
        "deep",
        "delightful",
        "dusky",
        "eager",
        "early",
        "earthy",
        "easy",
        "emerald",
        "even",
        "fair",
        "faithful",
        "fancy",
        "fast",
        "fearless",
        "fern",
        "fine",
        "firm",
        "fleet",
        "floral",
        "foggy",
        "forest",
        "free",
        "fresh",
        "friendly",
        "frosty",
        "gentle",
        "glad",
        "golden",
        "grand",
        "green",
        "happy",
        "harbor",
        "hazy",
        "helpful",
        "hidden",
        "honest",
        "hushed",
        "icy",
        "indigo",
        "jolly",
        "joyful",
        "keen",
        "kind",
        "lively",
        "lucid",
        "lucky",
        "lunar",
        "mellow",
        "merry",
        "mighty",
        "misty",
        "modern",
        "modest",
        "morning",
        "nimble",
        "noble",
        "northern",
        "olive",
        "open",
        "patient",
        "peaceful",
        "peach",
        "plain",
        "playful",
        "pleasant",
        "plucky",
        "polar",
        "proud",
        "quick",
        "quiet",
        "radiant",
        "rapid",
        "ready",
        "red",
        "restful",
        "river",
        "rosy",
        "round",
        "royal",
        "sage",
        "sandy",
        "serene",
        "sharp",
        "shiny",
        "silver",
        "simple",
        "sleek",
        "smart",
        "soft",
        "solar",
        "sound",
        "southern",
        "spry",
        "steady",
        "still",
        "sunny",
        "swift",
        "tidy",
        "tranquil",
        "true",
        "vivid",
        "warm",
        "wise",
        "young",
    ];

    private static readonly string[] Nouns =
    [
        "acorn",
        "albatross",
        "apple",
        "badger",
        "bay",
        "bear",
        "beaver",
        "birch",
        "bison",
        "brook",
        "canyon",
        "cedar",
        "cherry",
        "cloud",
        "comet",
        "coral",
        "crane",
        "creek",
        "dawn",
        "deer",
        "dolphin",
        "dove",
        "dune",
        "eagle",
        "elm",
        "falcon",
        "fern",
        "field",
        "finch",
        "fjord",
        "flame",
        "forest",
        "fox",
        "frost",
        "garden",
        "glen",
        "grove",
        "gull",
        "harbor",
        "hare",
        "hawk",
        "hazel",
        "heron",
        "hill",
        "horizon",
        "island",
        "ivy",
        "jade",
        "jay",
        "lake",
        "lark",
        "leaf",
        "lily",
        "lynx",
        "maple",
        "marsh",
        "meadow",
        "meteor",
        "mist",
        "moon",
        "moss",
        "mountain",
        "oak",
        "ocean",
        "olive",
        "orchid",
        "oriole",
        "otter",
        "owl",
        "panda",
        "pebble",
        "pine",
        "planet",
        "pond",
        "poppy",
        "prairie",
        "quail",
        "rain",
        "raven",
        "reef",
        "ridge",
        "river",
        "robin",
        "rose",
        "sage",
        "salmon",
        "sand",
        "seal",
        "shadow",
        "shore",
        "sky",
        "snow",
        "sparrow",
        "spring",
        "spruce",
        "star",
        "stone",
        "storm",
        "stream",
        "summit",
        "sun",
        "swan",
        "thistle",
        "tiger",
        "timber",
        "trail",
        "tree",
        "tulip",
        "valley",
        "violet",
        "wave",
        "whale",
        "willow",
        "wind",
        "wolf",
        "wood",
        "wren",
        "yak",
        "zephyr",
    ];

    public async Task<string> GenerateUniqueSlugAsync(
        CancellationToken cancellationToken = default)
    {
        for (var attempt = 0; attempt < CombinationAttempts; attempt++)
        {
            var candidate = CreateWordCombination();
            if (!await SlugExistsAsync(candidate, cancellationToken))
            {
                return candidate;
            }
        }

        for (var attempt = 0; attempt < SuffixedAttempts; attempt++)
        {
            var suffix = Convert.ToHexStringLower(
                RandomNumberGenerator.GetBytes(RandomSuffixByteCount));
            var maximumBaseLength = MaximumSlugLength - suffix.Length - 1;
            var baseSlug = CreateWordCombination();
            if (baseSlug.Length > maximumBaseLength)
            {
                baseSlug = baseSlug[..maximumBaseLength].TrimEnd('-');
            }

            var candidate = $"{baseSlug}-{suffix}";
            if (!await SlugExistsAsync(candidate, cancellationToken))
            {
                return candidate;
            }
        }

        throw new InvalidOperationException(
            "A unique drop slug could not be generated.");
    }

    public static bool TryNormalizeCustomSlug(
        string? value,
        out string normalizedSlug,
        out DropSlugValidationError validationError)
    {
        normalizedSlug = value?.Trim().ToLowerInvariant() ?? string.Empty;

        if (!CustomSlugPattern.IsMatch(normalizedSlug))
        {
            validationError = DropSlugValidationError.InvalidFormat;
            return false;
        }

        if (ReservedSlugs.Contains(normalizedSlug))
        {
            validationError = DropSlugValidationError.Reserved;
            return false;
        }

        validationError = DropSlugValidationError.None;
        return true;
    }

    private async Task<bool> SlugExistsAsync(
        string slug,
        CancellationToken cancellationToken)
    {
        return await dropSlugIndex.ExistsAsync(
            slug,
            excludingDropId: null,
            cancellationToken);
    }

    private static string CreateWordCombination()
    {
        var adjective = Adjectives[
            RandomNumberGenerator.GetInt32(Adjectives.Length)];
        var noun = Nouns[
            RandomNumberGenerator.GetInt32(Nouns.Length)];
        return $"{adjective}-{noun}";
    }
}

public enum DropSlugValidationError
{
    None,
    InvalidFormat,
    Reserved,
}
