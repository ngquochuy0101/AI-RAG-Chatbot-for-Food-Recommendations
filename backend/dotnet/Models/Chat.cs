using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AI_RAG_Chatbot_for_Food_Recommendations.Models
{
    public class Chat
    {
        [Key]
        public int Id { get; set; }

        public int UserId { get; set; }

        [MaxLength(255)]
        public string Title { get; set; } = "Cuộc trò chuyện";

        public bool IsPinned { get; set; } = false;

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

        // Navigation properties
        [ForeignKey("UserId")]
        public User? User { get; set; }

        public ICollection<Message> Messages { get; set; } = new List<Message>();
        public ICollection<Report> Reports { get; set; } = new List<Report>();
    }
}
