using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Teledrop.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddUploadTickets : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<Guid>(
                name: "UploadTicketId",
                table: "Drops",
                type: "TEXT",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "UploadTickets",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "TEXT", nullable: false),
                    Path = table.Column<string>(type: "TEXT", nullable: false),
                    Code = table.Column<string>(type: "TEXT", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "TEXT", nullable: false),
                    ExpiresAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false),
                    FirstUsedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true),
                    ConsumedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true),
                    RevokedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true),
                    FailedCodeAttempts = table.Column<int>(type: "INTEGER", nullable: false),
                    CreatedDropId = table.Column<Guid>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_UploadTickets", x => x.Id);
                });

            migrationBuilder.CreateIndex(
                name: "IX_Drops_UploadTicketId",
                table: "Drops",
                column: "UploadTicketId");

            migrationBuilder.CreateIndex(
                name: "IX_UploadTickets_Path",
                table: "UploadTickets",
                column: "Path",
                unique: true);

            migrationBuilder.AddForeignKey(
                name: "FK_Drops_UploadTickets_UploadTicketId",
                table: "Drops",
                column: "UploadTicketId",
                principalTable: "UploadTickets",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Drops_UploadTickets_UploadTicketId",
                table: "Drops");

            migrationBuilder.DropTable(
                name: "UploadTickets");

            migrationBuilder.DropIndex(
                name: "IX_Drops_UploadTicketId",
                table: "Drops");

            migrationBuilder.DropColumn(
                name: "UploadTicketId",
                table: "Drops");
        }
    }
}
