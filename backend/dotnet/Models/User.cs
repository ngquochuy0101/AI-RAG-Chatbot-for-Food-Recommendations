using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AI_RAG_Chatbot_for_Food_Recommendations.Models
{
    public class User
    {
        [Key]
        public int Id { get; set; }

        [Required]
        [MaxLength(100)]
        public string Name { get; set; } = string.Empty;

        [Required]
        [MaxLength(100)]
        public string Email { get; set; } = string.Empty;

        [Required]
        [MaxLength(255)]
        public string Password { get; set; } = string.Empty;

        public bool IsAdmin { get; set; } = false;

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        public DateTime? LastLogin { get; set; }

        // Navigation properties
        public ICollection<Chat> Chats { get; set; } = new List<Chat>();
        public ICollection<Report> Reports { get; set; } = new List<Report>();
        public ICollection<LoginHistory> LoginHistories { get; set; } = new List<LoginHistory>();
        public ChatStatistics? Statistics { get; set; }
    }
}
