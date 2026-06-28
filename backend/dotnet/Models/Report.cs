using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AI_RAG_Chatbot_for_Food_Recommendations.Models
{
    public class Report
    {
        [Key]
        public int Id { get; set; }

        public int UserId { get; set; }

        public int? ChatId { get; set; }

        [Required]
        [Column(TypeName = "TEXT")]
        public string MessageText { get; set; } = string.Empty;

        [MaxLength(50)]
        public string Reason { get; set; } = "other";

        [MaxLength(200)]
        public string ReasonText { get; set; } = "Lý do khác";

        [Column(TypeName = "TEXT")]
        public string? Details { get; set; }

        [Required]
        [MaxLength(20)]
        public string Status { get; set; } = "pending"; // 'pending', 'reviewed', 'resolved'

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        // Navigation properties
        [ForeignKey("UserId")]
        public User? User { get; set; }

        [ForeignKey("ChatId")]
        public Chat? Chat { get; set; }
    }
}
