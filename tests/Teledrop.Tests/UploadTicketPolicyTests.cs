using Teledrop.Features.UploadTickets;
using Xunit;

namespace Teledrop.Tests;

public sealed class UploadTicketPolicyTests
{
    private static readonly DateTime IssuedAtUtc =
        new(2026, 7, 27, 0, 0, 0, DateTimeKind.Utc);

    [Fact]
    public void IssueCreatesTwentyFourHourTicket()
    {
        var ticket = UploadTicket.Issue(
            Guid.NewGuid(),
            "ab3k",
            "k7m29xpq",
            IssuedAtUtc);

        Assert.Equal(IssuedAtUtc, ticket.CreatedAt);
        Assert.Equal(
            IssuedAtUtc.Add(UploadTicket.InitialLifetime),
            ticket.ExpiresAtUtc);
        Assert.True(ticket.CanAcceptUpload(IssuedAtUtc));
        Assert.False(ticket.CanAcceptUpload(ticket.ExpiresAtUtc));
    }

    [Fact]
    public void FirstSuccessfulCodeStartsThirtyMinuteRetryWindowOnce()
    {
        var ticket = CreateTicket();
        var firstUse = IssuedAtUtc.AddHours(1);

        Assert.True(ticket.RecordFirstSuccessfulCode(firstUse));
        Assert.True(ticket.RecordFirstSuccessfulCode(firstUse.AddMinutes(5)));
        Assert.Equal(firstUse, ticket.FirstUsedAtUtc);
        Assert.True(ticket.CanAcceptUpload(
            firstUse.Add(UploadTicket.RetryWindow).AddTicks(-1)));
        Assert.False(ticket.CanAcceptUpload(
            firstUse.Add(UploadTicket.RetryWindow)));
    }

    [Fact]
    public void TenthFailedCodeAttemptRevokesTicket()
    {
        var ticket = CreateTicket();

        for (var attempt = 1;
             attempt <= UploadTicket.MaximumFailedCodeAttempts;
             attempt++)
        {
            Assert.True(ticket.RecordFailedCodeAttempt(
                IssuedAtUtc.AddMinutes(attempt)));
        }

        Assert.Equal(
            UploadTicket.MaximumFailedCodeAttempts,
            ticket.FailedCodeAttempts);
        Assert.NotNull(ticket.RevokedAtUtc);
        Assert.False(ticket.CanAcceptUpload(IssuedAtUtc.AddMinutes(11)));
        Assert.False(ticket.RecordFailedCodeAttempt(
            IssuedAtUtc.AddMinutes(11)));
        Assert.Equal(
            UploadTicket.MaximumFailedCodeAttempts,
            ticket.FailedCodeAttempts);
    }

    [Fact]
    public void ConsumedAndRevokedTicketsCannotTransitionAgain()
    {
        var consumedTicket = CreateTicket();
        var dropId = Guid.NewGuid();

        Assert.True(consumedTicket.TryConsume(
            dropId,
            IssuedAtUtc,
            IssuedAtUtc.AddMinutes(1)));
        Assert.Equal(dropId, consumedTicket.CreatedDropId);
        Assert.False(consumedTicket.TryConsume(
            Guid.NewGuid(),
            IssuedAtUtc,
            IssuedAtUtc.AddMinutes(2)));

        var revokedTicket = CreateTicket();
        Assert.True(revokedTicket.Revoke(IssuedAtUtc.AddMinutes(1)));
        Assert.False(revokedTicket.Revoke(IssuedAtUtc.AddMinutes(2)));
        Assert.False(revokedTicket.RecordFirstSuccessfulCode(
            IssuedAtUtc.AddMinutes(2)));
    }

    private static UploadTicket CreateTicket()
    {
        return UploadTicket.Issue(
            Guid.NewGuid(),
            "ab3k",
            "k7m29xpq",
            IssuedAtUtc);
    }
}
