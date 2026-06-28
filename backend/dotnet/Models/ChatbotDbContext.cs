using Microsoft.EntityFrameworkCore;

namespace AI_RAG_Chatbot_for_Food_Recommendations.Models
{
    public class ChatbotDbContext : DbContext
    {
        public ChatbotDbContext(DbContextOptions<ChatbotDbContext> options) : base(options)
        {
        }

        public DbSet<User> Users { get; set; }
        public DbSet<Chat> Chats { get; set; }
        public DbSet<Message> Messages { get; set; }
        public DbSet<Report> Reports { get; set; }
        public DbSet<PasswordReset> PasswordResets { get; set; }
        public DbSet<LoginHistory> LoginHistories { get; set; }
        public DbSet<ChatStatistics> ChatStatistics { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            // Configure unique constraint on User Email
            modelBuilder.Entity<User>()
                .HasIndex(u => u.Email)
                .IsUnique();

            // Configure one-to-one relationship for Statistics
            modelBuilder.Entity<User>()
                .HasOne(u => u.Statistics)
                .WithOne(s => s.User)
                .HasForeignKey<ChatStatistics>(s => s.UserId)
                .OnDelete(DeleteBehavior.Cascade);

            // Configure one-to-many relationship for Chats
            modelBuilder.Entity<Chat>()
                .HasOne(c => c.User)
                .WithMany(u => u.Chats)
                .HasForeignKey(c => c.UserId)
                .OnDelete(DeleteBehavior.Cascade);

            // Configure one-to-many relationship for Messages
            modelBuilder.Entity<Message>()
                .HasOne(m => m.Chat)
                .WithMany(c => c.Messages)
                .HasForeignKey(m => m.ChatId)
                .OnDelete(DeleteBehavior.Cascade);

            // Configure one-to-many relationship for Reports (User -> Reports)
            modelBuilder.Entity<Report>()
                .HasOne(r => r.User)
                .WithMany(u => u.Reports)
                .HasForeignKey(r => r.UserId)
                .OnDelete(DeleteBehavior.Restrict);

            // Configure relationship for Reports (Chat -> Reports)
            modelBuilder.Entity<Report>()
                .HasOne(r => r.Chat)
                .WithMany(c => c.Reports)
                .HasForeignKey(r => r.ChatId)
                .OnDelete(DeleteBehavior.SetNull);

            // Configure one-to-many relationship for Login History
            modelBuilder.Entity<LoginHistory>()
                .HasOne(l => l.User)
                .WithMany(u => u.LoginHistories)
                .HasForeignKey(l => l.UserId)
                .OnDelete(DeleteBehavior.Cascade);
        }
    }
}
