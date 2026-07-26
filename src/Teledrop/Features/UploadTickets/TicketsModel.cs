using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using Teledrop.Data;

namespace Teledrop.Features.UploadTickets;

public sealed class TicketsModel(
    TeledropDbContext dbContext,
    UploadTicketUseCases uploadTicketUseCases,
    TimeProvider timeProvider)
    : PageModel
{
    public IReadOnlyList<UploadTicket> UploadTickets { get; private set; } = [];

    public UploadTicket? IssuedUploadTicket { get; private set; }

    public string? IssuedUploadTicketUrl { get; private set; }

    public DateTime UtcNow { get; private set; }

    public async Task OnGetAsync(
        CancellationToken cancellationToken = default)
    {
        SetNoStore();
        await LoadUploadTicketsAsync(cancellationToken);
    }

    public async Task<IActionResult> OnPostIssueAsync(
        CancellationToken cancellationToken = default)
    {
        SetNoStore();

        var uploadTicket = await uploadTicketUseCases.IssueAsync(
            cancellationToken);

        IssuedUploadTicket = uploadTicket;
        IssuedUploadTicketUrl = Url.Page(
                "/GuestUpload",
                pageHandler: null,
                values: new { path = uploadTicket.Path },
                protocol: Request.Scheme)
            ?? $"{Request.Scheme}://{Request.Host}/u/{uploadTicket.Path}";

        await LoadUploadTicketsAsync(cancellationToken);
        return Page();
    }

    public async Task<IActionResult> OnPostRevokeAsync(
        Guid id,
        CancellationToken cancellationToken = default)
    {
        SetNoStore();

        var result = await uploadTicketUseCases.RevokeAsync(
            id,
            cancellationToken);
        if (result == UploadTicketCommandResult.NotFound)
        {
            return NotFound();
        }

        return RedirectToPage("/Tickets");
    }

    public string GetStatusLabel(UploadTicket uploadTicket)
    {
        if (uploadTicket.RevokedAtUtc is not null)
        {
            return "폐기됨";
        }

        if (uploadTicket.ConsumedAtUtc is not null)
        {
            return "소진됨";
        }

        return uploadTicket.CanAcceptUpload(UtcNow)
            ? "살아있음"
            : "만료됨";
    }

    public bool CanRevoke(UploadTicket uploadTicket)
    {
        return uploadTicket.CanAcceptUpload(UtcNow);
    }

    private async Task LoadUploadTicketsAsync(
        CancellationToken cancellationToken)
    {
        UtcNow = timeProvider.GetUtcNow().UtcDateTime;
        UploadTickets = await dbContext.UploadTickets
            .AsNoTracking()
            .OrderByDescending(ticket => ticket.CreatedAt)
            .ThenByDescending(ticket => ticket.Id)
            .ToListAsync(cancellationToken);
    }

    private void SetNoStore()
    {
        Response.Headers.CacheControl = "no-store";
    }
}
