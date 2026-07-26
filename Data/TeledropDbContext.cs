using Microsoft.EntityFrameworkCore;
using Teledrop.Features.Drops;
using Teledrop.Features.UploadTickets;

namespace Teledrop.Data;

public sealed class TeledropDbContext(DbContextOptions<TeledropDbContext> options)
    : DbContext(options)
{
    internal const string ConnectionStringName = "DefaultConnection";
    internal const string DefaultConnectionString = "Data Source=share/database.db";

    public DbSet<Drop> Drops => Set<Drop>();

    public DbSet<UploadTicket> UploadTickets => Set<UploadTicket>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<Drop>()
            .HasIndex(drop => drop.Slug)
            .IsUnique();

        modelBuilder.Entity<Drop>()
            .HasOne<UploadTicket>()
            .WithMany()
            .HasForeignKey(drop => drop.UploadTicketId)
            .OnDelete(DeleteBehavior.SetNull);

        modelBuilder.Entity<UploadTicket>()
            .HasIndex(ticket => ticket.Path)
            .IsUnique();
    }
}
