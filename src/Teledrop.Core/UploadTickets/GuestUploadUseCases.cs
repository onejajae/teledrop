using System.Security.Cryptography;
using System.Text;
using Teledrop.Features.Drops;

namespace Teledrop.Features.UploadTickets;

public sealed class GuestUploadUseCases(
    IUploadTicketStore uploadTicketStore,
    IGuestUploadCommitter guestUploadCommitter,
    PrivateDropFactory privateDropFactory,
    IStoredDropFileCleanup fileCleanup,
    TimeProvider timeProvider)
{
    public async Task<UploadTicketAvailability> GetAvailabilityAsync(
        string? path,
        DateTime utcNow,
        CancellationToken cancellationToken)
    {
        var uploadTicket = await FindByPathAsync(path, cancellationToken);
        if (uploadTicket is null)
        {
            return UploadTicketAvailability.Missing;
        }

        return uploadTicket.CanAcceptUpload(utcNow)
            ? UploadTicketAvailability.Available
            : UploadTicketAvailability.Unavailable;
    }

    public async Task<GuestTicketCodeResult> ValidateCodeAsync(
        string? path,
        string providedCode,
        DateTime requestStartedAtUtc,
        CancellationToken cancellationToken)
    {
        var uploadTicket = await FindByPathAsync(path, cancellationToken);
        if (uploadTicket is null)
        {
            return GuestTicketCodeResult.Missing();
        }

        if (!uploadTicket.CanAcceptUpload(requestStartedAtUtc))
        {
            return GuestTicketCodeResult.Unavailable();
        }

        if (!TicketCodesMatch(uploadTicket.Code, providedCode))
        {
            var attempt = await uploadTicketStore
                .TryRecordFailedCodeAttemptAsync(
                    uploadTicket.Id,
                    requestStartedAtUtc,
                    cancellationToken);

            return attempt.Updated
                && attempt.UploadTicket?.CanAcceptUpload(
                    requestStartedAtUtc) == true
                    ? GuestTicketCodeResult.InvalidCode()
                    : GuestTicketCodeResult.Unavailable();
        }

        var firstUse = await uploadTicketStore
            .EnsureFirstSuccessfulCodeAsync(
                uploadTicket.Id,
                requestStartedAtUtc,
                cancellationToken);
        if (firstUse.UploadTicket?.CanAcceptUpload(
                requestStartedAtUtc) != true)
        {
            return GuestTicketCodeResult.Unavailable();
        }

        return GuestTicketCodeResult.Authorized(
            new GuestUploadAuthorization(
                uploadTicket.Id,
                requestStartedAtUtc));
    }

    public async Task<GuestUploadCompletion> AcceptAsync(
        GuestUploadAuthorization authorization,
        StoredDropFile storedFile,
        CancellationToken cancellationToken)
    {
        try
        {
            var drop = await privateDropFactory.CreateAsync(
                storedFile,
                title: null,
                description: null,
                uploadTicketId: authorization.UploadTicketId,
                cancellationToken: cancellationToken);
            var committed = await guestUploadCommitter.TryCommitAsync(
                drop,
                authorization.UploadTicketId,
                authorization.RequestStartedAtUtc,
                timeProvider.GetUtcNow().UtcDateTime,
                cancellationToken);
            if (!committed)
            {
                fileCleanup.TryDelete(storedFile.Location);
                return GuestUploadCompletion.Unavailable();
            }

            return GuestUploadCompletion.Succeeded(
                storedFile.FileName,
                storedFile.FileSizeBytes);
        }
        catch
        {
            fileCleanup.TryDelete(storedFile.Location);
            throw;
        }
    }

    private async Task<UploadTicket?> FindByPathAsync(
        string? path,
        CancellationToken cancellationToken)
    {
        if (!UploadTicketCredentialGenerator.TryNormalizeTicketPath(
                path,
                out var normalizedPath))
        {
            return null;
        }

        return await uploadTicketStore.FindByPathAsync(
            normalizedPath,
            cancellationToken);
    }

    private static bool TicketCodesMatch(
        string expectedCode,
        string providedCode)
    {
        Span<byte> expectedBytes =
            stackalloc byte[UploadTicketCredentialGenerator.TicketCodeLength];
        Span<byte> providedBytes =
            stackalloc byte[UploadTicketCredentialGenerator.TicketCodeLength];

        Encoding.ASCII.GetBytes(expectedCode, expectedBytes);
        var isValid = UploadTicketCredentialGenerator.TryNormalizeTicketCode(
            providedCode,
            out var normalizedCode);
        if (isValid)
        {
            Encoding.ASCII.GetBytes(normalizedCode, providedBytes);
        }

        var matches = CryptographicOperations.FixedTimeEquals(
            expectedBytes,
            providedBytes);
        return isValid & matches;
    }
}

public enum UploadTicketAvailability
{
    Available,
    Missing,
    Unavailable,
}

public sealed record GuestUploadAuthorization(
    Guid UploadTicketId,
    DateTime RequestStartedAtUtc);

public sealed record GuestTicketCodeResult(
    GuestTicketCodeStatus Status,
    GuestUploadAuthorization? Authorization)
{
    public static GuestTicketCodeResult Authorized(
        GuestUploadAuthorization authorization)
    {
        return new(GuestTicketCodeStatus.Authorized, authorization);
    }

    public static GuestTicketCodeResult Missing()
    {
        return new(GuestTicketCodeStatus.Missing, null);
    }

    public static GuestTicketCodeResult InvalidCode()
    {
        return new(GuestTicketCodeStatus.InvalidCode, null);
    }

    public static GuestTicketCodeResult Unavailable()
    {
        return new(GuestTicketCodeStatus.Unavailable, null);
    }
}

public enum GuestTicketCodeStatus
{
    Authorized,
    Missing,
    InvalidCode,
    Unavailable,
}

public sealed record GuestUploadCompletion(
    GuestUploadCompletionStatus Status,
    string? FileName,
    long FileSizeBytes)
{
    public static GuestUploadCompletion Succeeded(
        string fileName,
        long fileSizeBytes)
    {
        return new(
            GuestUploadCompletionStatus.Succeeded,
            fileName,
            fileSizeBytes);
    }

    public static GuestUploadCompletion Unavailable()
    {
        return new(
            GuestUploadCompletionStatus.Unavailable,
            FileName: null,
            FileSizeBytes: 0);
    }
}

public enum GuestUploadCompletionStatus
{
    Succeeded,
    Unavailable,
}
