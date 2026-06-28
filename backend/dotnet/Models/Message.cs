using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AI_RAG_Chatbot_for_Food_Recommendations.Models
{
    public class Message
    {
        [Key]
        public int Id { get; set; }

        public int ChatId { get; set; }

        [Required]
        public string Type { get; set; } = "user"; // 'user' or 'assistant'

        [Required]
        [Column(TypeName = "NVARCHAR(MAX)")]
        public string Text { get; set; } = string.Empty;

        [Column(TypeName = "NVARCHAR(MAX)")]
        public string? ResponseHtml { get; set; }

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        public bool? IsLiked { get; set; } // true = like, false = dislike, null = none

        // Navigation properties
        [ForeignKey("ChatId")]
        public Chat? Chat { get; set; }
    }
}
