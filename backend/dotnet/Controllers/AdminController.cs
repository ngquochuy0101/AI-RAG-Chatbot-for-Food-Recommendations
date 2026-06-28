using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using AI_RAG_Chatbot_for_Food_Recommendations.Models;
using System.Linq;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Security.Claims;

namespace AI_RAG_Chatbot_for_Food_Recommendations.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    [Authorize] // Ensure the user is logged in
    public class AdminController : ControllerBase
    {
        private readonly ChatbotDbContext _context;
        public AdminController(ChatbotDbContext context)
        {
            _context = context;
        }

        [AllowAnonymous]
        [HttpGet("seed-data")]
        public async Task<IActionResult> SeedData()
        {
            var random = new System.Random();
            var users = new List<User>();
            
            // Create 10 dummy users
            for (int i = 0; i < 10; i++)
            {
                users.Add(new User
                {
                    Name = $"Dummy User {i}",
                    Email = $"dummy{i}@example.com",
                    Password = "hashedpassword123",
                    CreatedAt = System.DateTime.UtcNow.AddDays(-random.Next(1, 60))
                });
            }
            _context.Users.AddRange(users);
            await _context.SaveChangesAsync();

            var chats = new List<Chat>();
            // Create chats for these users
            foreach (var user in users)
            {
                int numChats = random.Next(2, 6);
                for (int c = 0; c < numChats; c++)
                {
                    chats.Add(new Chat
                    {
                        UserId = user.Id,
                        Title = $"Đoạn chat ngẫu nhiên {c}",
                        CreatedAt = user.CreatedAt.AddDays(random.Next(0, 5)),
                        UpdatedAt = System.DateTime.UtcNow
                    });
                }
            }
            _context.Chats.AddRange(chats);
            await _context.SaveChangesAsync();

            var messages = new List<Message>();
            // Create messages with feedbacks
            foreach (var chat in chats)
            {
                int numMessages = random.Next(3, 8);
                for (int m = 0; m < numMessages; m++)
                {
                    var msgDate = chat.CreatedAt.AddDays(random.Next(0, 20));
                    
                    // User prompt
                    messages.Add(new Message
                    {
                        ChatId = chat.Id,
                        Type = "user",
                        Text = $"Món ăn {m} ở Đà Nẵng là gì?",
                        CreatedAt = msgDate
                    });

                    // Bot response
                    bool hasFeedback = random.Next(0, 10) > 3; // 70% chance of feedback
                    bool? isLiked = hasFeedback ? (random.Next(0, 10) > 2) : (bool?)null; // 70% likes

                    messages.Add(new Message
                    {
                        ChatId = chat.Id,
                        Type = "assistant",
                        Text = $"Đây là thông tin về món ăn {m}...",
                        ResponseHtml = $"<p>Đây là thông tin về món ăn {m}...</p>",
                        IsLiked = isLiked,
                        CreatedAt = msgDate.AddMinutes(1)
                    });
                }
            }
            _context.Messages.AddRange(messages);
            await _context.SaveChangesAsync();

            return Ok(new { success = true, message = "Created massive dummy data!" });
        }

        private async Task<bool> IsAdminAsync(int userId)
        {
            var user = await _context.Users.FindAsync(userId);
            return user != null && user.IsAdmin;
        }

        [HttpGet("users")]
        public async Task<IActionResult> GetUsers()
        {
            var userIdClaim = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userIdClaim) || !int.TryParse(userIdClaim, out int currentUserId) || !await IsAdminAsync(currentUserId))
            {
                return Forbid();
            }

            var users = await _context.Users
                .Select(u => new
                {
                    u.Id,
                    u.Name,
                    u.Email,
                    u.CreatedAt,
                    TotalChats = u.Chats.Count,
                    TotalMessages = u.Chats.SelectMany(c => c.Messages).Count()
                })
                .OrderByDescending(u => u.CreatedAt)
                .ToListAsync();

            return Ok(new { success = true, users });
        }

        [HttpGet("feedbacks")]
        public async Task<IActionResult> GetFeedbacks()
        {
            var userIdClaim = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userIdClaim) || !int.TryParse(userIdClaim, out int currentUserId) || !await IsAdminAsync(currentUserId))
            {
                return Forbid();
            }

            // Get all feedbacks (IsLiked is not null)
            var botMessagesWithFeedback = await _context.Messages
                .Include(m => m.Chat)
                .Where(m => m.Type == "assistant" && m.IsLiked != null)
                .OrderByDescending(m => m.CreatedAt)
                .ToListAsync();

            var feedbacks = new List<object>();

            foreach (var botMessage in botMessagesWithFeedback)
            {
                // Find the user prompt (message immediately before this bot message)
                var userPrompt = await _context.Messages
                    .Where(m => m.ChatId == botMessage.ChatId && m.Type == "user" && m.CreatedAt <= botMessage.CreatedAt)
                    .OrderByDescending(m => m.CreatedAt)
                    .FirstOrDefaultAsync();

                feedbacks.Add(new
                {
                    Id = botMessage.Id,
                    ChatId = botMessage.ChatId,
                    ChatTitle = botMessage.Chat?.Title,
                    UserId = botMessage.Chat?.UserId,
                    UserPrompt = userPrompt?.Text ?? "N/A",
                    BotResponse = botMessage.Text,
                    IsLiked = botMessage.IsLiked,
                    CreatedAt = botMessage.CreatedAt
                });
            }

            return Ok(new { success = true, feedbacks });
        }
    }
}
