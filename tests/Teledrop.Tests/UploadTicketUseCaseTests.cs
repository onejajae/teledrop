using Teledrop.Features.Drops;
using Teledrop.Features.UploadTickets;
using Xunit;

namespace Teledrop.Tests;

public sealed class UploadTicketUseCaseTests
{
    private static readonly DateTimeOffset Now =
        new(2026, 7, 27, 1, 2, 3, TimeSpan.Zero);

    [Fact]
    public async Task InvalidCodeRecordsAttemptAndTenthFailureRevokesTicket()
    {
        var dependencies = new UploadTicketDependencies();
        var useCases = dependencies.CreateGuestUploadUseCases();

        for (var attempt = 1;
             attempt < UploadTicket.MaximumFailedCodeAttempts;
             attempt++)
        {
            var result = await useCases.ValidateCodeAsync(
                dependencies.Ticket.Path,
                "aaaaaaaa",
                Now.UtcDateTime,
                CancellationToken.None);

            Assert.Equal(
                GuestTicketCodeStatus.InvalidCode,
                result.Status);
        }

        var finalResult = await useCases.ValidateCodeAsync(
            dependencies.Ticket.Path,
            "aaaaaaaa",
            Now.UtcDateTime,
            CancellationToken.None);

        Assert.Equal(
            GuestTicketCodeStatus.Unavailable,
            finalResult.Status);
        Assert.Equal(
            UploadTicket.MaximumFailedCodeAttempts,
            dependencies.Ticket.FailedCodeAttempts);
        Assert.Equal(Now.UtcDateTime, dependencies.Ticket.RevokedAtUtc);
    }

    [Fact]
    public async Task CorrectCodeStartsRetryWindowBeforeFileIsAccepted()
    {
        var dependencies = new UploadTicketDependencies();
        var useCases = dependencies.CreateGuestUploadUseCases();

        var result = await useCases.ValidateCodeAsync(
            dependencies.Ticket.Path.ToUpperInvariant(),
            "K7M2-9XPQ",
            Now.UtcDateTime,
            CancellationToken.None);

        Assert.Equal(GuestTicketCodeStatus.Authorized, result.Status);
        Assert.Equal(
            dependencies.Ticket.Id,
            result.Authorization?.UploadTicketId);
        Assert.Equal(
            Now.UtcDateTime,
            result.Authorization?.RequestStartedAtUtc);
        Assert.Equal(Now.UtcDateTime, dependencies.Ticket.FirstUsedAtUtc);
        Assert.Null(dependencies.Committer.CommittedDrop);
    }

    [Fact]
    public async Task AcceptedFileCreatesPrivateTicketLinkedDrop()
    {
        var dependencies = new UploadTicketDependencies();
        var useCases = dependencies.CreateGuestUploadUseCases();
        var authorization = new GuestUploadAuthorization(
            dependencies.Ticket.Id,
            Now.UtcDateTime);
        var storedFile = CreateStoredFile();

        var result = await useCases.AcceptAsync(
            authorization,
            storedFile,
            CancellationToken.None);

        Assert.Equal(
            GuestUploadCompletionStatus.Succeeded,
            result.Status);
        Assert.Equal(storedFile.FileName, result.FileName);
        Assert.Equal(storedFile.FileSizeBytes, result.FileSizeBytes);
        Assert.Null(
            typeof(GuestUploadCompletion).GetProperty("Slug"));

        var drop = Assert.IsType<Drop>(
            dependencies.Committer.CommittedDrop);
        Assert.True(drop.IsPrivate);
        Assert.Equal(dependencies.Ticket.Id, drop.UploadTicketId);
        Assert.Equal(storedFile.Location, drop.Location);
        Assert.Equal(Now.UtcDateTime, drop.CreatedAt);
        Assert.Empty(dependencies.FileCleanup.DeletedLocations);
    }

    [Fact]
    public async Task FailedAtomicCommitCleansStoredFile()
    {
        var dependencies = new UploadTicketDependencies();
        dependencies.Committer.ShouldCommit = false;
        var useCases = dependencies.CreateGuestUploadUseCases();
        var storedFile = CreateStoredFile();

        var result = await useCases.AcceptAsync(
            new GuestUploadAuthorization(
                dependencies.Ticket.Id,
                Now.UtcDateTime),
            storedFile,
            CancellationToken.None);

        Assert.Equal(
            GuestUploadCompletionStatus.Unavailable,
            result.Status);
        Assert.Equal(
            [storedFile.Location],
            dependencies.FileCleanup.DeletedLocations);
    }

    [Fact]
    public async Task IssueAndRevokePersistTicketTransitions()
    {
        var dependencies = new UploadTicketDependencies(ticket: null);
        var useCases = dependencies.CreateUploadTicketUseCases();

        var issued = await useCases.IssueAsync(CancellationToken.None);
        var revokeResult = await useCases.RevokeAsync(
            issued.Id,
            CancellationToken.None);

        Assert.Equal(UploadTicketCommandResult.Succeeded, revokeResult);
        Assert.Equal(Now.UtcDateTime, issued.CreatedAt);
        Assert.Equal(
            Now.UtcDateTime.Add(UploadTicket.InitialLifetime),
            issued.ExpiresAtUtc);
        Assert.Equal(
            UploadTicketCredentialGenerator.TicketPathLength,
            issued.Path.Length);
        Assert.Equal(
            UploadTicketCredentialGenerator.TicketCodeLength,
            issued.Code.Length);
        Assert.Equal(Now.UtcDateTime, issued.RevokedAtUtc);
        Assert.Equal(1, dependencies.Store.AddCount);
        Assert.Equal(1, dependencies.Store.UpdateCount);
    }

    private static StoredDropFile CreateStoredFile()
    {
        return new StoredDropFile(
            "stored-location",
            "guest.bin",
            "application/octet-stream",
            42,
            "file-hash");
    }

    private sealed class UploadTicketDependencies
    {
        internal UploadTicketDependencies(UploadTicket? ticket = default)
        {
            Ticket = ticket
                ?? UploadTicket.Issue(
                    Guid.NewGuid(),
                    "ab3k",
                    "k7m29xpq",
                    Now.UtcDateTime.AddHours(-1));
            Store = new FakeUploadTicketStore(Ticket);
        }

        internal UploadTicket Ticket { get; }

        internal FakeUploadTicketStore Store { get; }

        internal FakeGuestUploadCommitter Committer { get; } = new();

        internal FakeFileCleanup FileCleanup { get; } = new();

        internal GuestUploadUseCases CreateGuestUploadUseCases()
        {
            var dropSlugGenerator = new DropSlugGenerator(Store);
            var privateDropFactory = new PrivateDropFactory(
                dropSlugGenerator,
                new FixedTimeProvider(Now));
            return new GuestUploadUseCases(
                Store,
                Committer,
                privateDropFactory,
                FileCleanup,
                new FixedTimeProvider(Now));
        }

        internal UploadTicketUseCases CreateUploadTicketUseCases()
        {
            return new UploadTicketUseCases(
                Store,
                new UploadTicketCredentialGenerator(Store),
                new FixedTimeProvider(Now));
        }
    }

    private sealed class FakeUploadTicketStore(UploadTicket initialTicket)
        : IUploadTicketStore, IUploadTicketPathIndex, IDropSlugIndex
    {
        private UploadTicket? uploadTicket = initialTicket;

        internal int AddCount { get; private set; }

        internal int UpdateCount { get; private set; }

        public Task<UploadTicket?> FindByPathAsync(
            string path,
            CancellationToken cancellationToken)
        {
            return Task.FromResult(
                uploadTicket?.Path == path ? uploadTicket : null);
        }

        public Task<UploadTicket?> FindByIdAsync(
            Guid id,
            CancellationToken cancellationToken)
        {
            return Task.FromResult(
                uploadTicket?.Id == id ? uploadTicket : null);
        }

        public Task AddAsync(
            UploadTicket ticket,
            CancellationToken cancellationToken)
        {
            uploadTicket = ticket;
            AddCount++;
            return Task.CompletedTask;
        }

        public Task UpdateAsync(
            UploadTicket ticket,
            CancellationToken cancellationToken)
        {
            UpdateCount++;
            return Task.CompletedTask;
        }

        public Task<UploadTicketAttemptUpdate>
            EnsureFirstSuccessfulCodeAsync(
                Guid uploadTicketId,
                DateTime requestStartedAtUtc,
                CancellationToken cancellationToken)
        {
            var updated = uploadTicket?.Id == uploadTicketId
                && uploadTicket.RecordFirstSuccessfulCode(
                    requestStartedAtUtc);
            return Task.FromResult(
                new UploadTicketAttemptUpdate(updated, uploadTicket));
        }

        public Task<UploadTicketAttemptUpdate>
            TryRecordFailedCodeAttemptAsync(
                Guid uploadTicketId,
                DateTime requestStartedAtUtc,
                CancellationToken cancellationToken)
        {
            var updated = uploadTicket?.Id == uploadTicketId
                && uploadTicket.RecordFailedCodeAttempt(
                    requestStartedAtUtc);
            return Task.FromResult(
                new UploadTicketAttemptUpdate(updated, uploadTicket));
        }

        public Task<bool> ExistsAsync(
            string value,
            CancellationToken cancellationToken)
        {
            return Task.FromResult(
                uploadTicket?.Path == value
                || value == "existing-drop-slug");
        }

        Task<bool> IDropSlugIndex.ExistsAsync(
            string slug,
            Guid? excludingDropId,
            CancellationToken cancellationToken)
        {
            return Task.FromResult(slug == "existing-drop-slug");
        }
    }

    private sealed class FakeGuestUploadCommitter : IGuestUploadCommitter
    {
        internal bool ShouldCommit { get; set; } = true;

        internal Drop? CommittedDrop { get; private set; }

        public Task<bool> TryCommitAsync(
            Drop drop,
            Guid uploadTicketId,
            DateTime requestStartedAtUtc,
            DateTime consumedAtUtc,
            CancellationToken cancellationToken)
        {
            CommittedDrop = drop;
            return Task.FromResult(ShouldCommit);
        }
    }

    private sealed class FakeFileCleanup : IStoredDropFileCleanup
    {
        internal List<string> DeletedLocations { get; } = [];

        public void TryDelete(string location)
        {
            DeletedLocations.Add(location);
        }
    }

    private sealed class FixedTimeProvider(DateTimeOffset utcNow)
        : TimeProvider
    {
        public override DateTimeOffset GetUtcNow()
        {
            return utcNow;
        }
    }
}
