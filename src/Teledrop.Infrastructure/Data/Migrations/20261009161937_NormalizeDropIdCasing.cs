using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Teledrop.Data.Migrations
{
    /// <inheritdoc />
    public partial class NormalizeDropIdCasing : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Microsoft.Data.Sqlite binds Guid keys as uppercase text. Imported
            // lowercase IDs can be read by Slug, but UPDATE/DELETE by Id miss them.
            migrationBuilder.Sql("""
                UPDATE "Drops"
                SET "Id" = upper("Id")
                WHERE "Id" <> upper("Id");
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            // Downgrades retain canonical casing; the logical GUIDs are unchanged.
        }
    }
}
