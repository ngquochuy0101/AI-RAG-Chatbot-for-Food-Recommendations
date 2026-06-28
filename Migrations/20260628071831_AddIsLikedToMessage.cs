using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace AI_RAG_Chatbot_for_Food_Recommendations.Migrations
{
    /// <inheritdoc />
    public partial class AddIsLikedToMessage : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<bool>(
                name: "IsLiked",
                table: "Messages",
                type: "bit",
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "IsLiked",
                table: "Messages");
        }
    }
}
