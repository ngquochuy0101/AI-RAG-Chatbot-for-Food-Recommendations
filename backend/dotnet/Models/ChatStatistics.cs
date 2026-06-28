using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace AI_RAG_Chatbot_for_Food_Recommendations.Models
{
    public class ChatStatistics
    {
        [Key]
        public int Id { get; set; }

        public int UserId { get; set; }

        public int TotalChats { get; set; } = 0;

        public int TotalMessages { get; set; } = 0;

        public DateTime LastActivity { get; set; } = DateTime.UtcNow;

        // Navigation properties
        [ForeignKey("UserId")]
        public User? User { get; set; }
    }
}
