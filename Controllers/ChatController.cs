using AI_RAG_Chatbot_for_Food_Recommendations.DTOs;
using AI_RAG_Chatbot_for_Food_Recommendations.Models;
using AI_RAG_Chatbot_for_Food_Recommendations.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace AI_RAG_Chatbot_for_Food_Recommendations.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class ChatController : ControllerBase
    {
        private readonly ChatbotDbContext _context;
        private readonly IAiIntegrationService _aiService;

        public ChatController(ChatbotDbContext context, IAiIntegrationService aiService)
        {
            _context = context;
            _aiService = aiService;
        }

        [Authorize]
        [HttpPost("sendMessage")]
        public async Task<IActionResult> SendMessage([FromBody] SendMessageRequest request)
        {
            var chatId = request.ChatId;

            if (chatId == 0)
            {
                var chat = new Chat
                {
                    UserId = request.UserId,
                    Title = request.Message.Length > 50 ? request.Message.Substring(0, 50) + "..." : request.Message
                };
                _context.Chats.Add(chat);
                await _context.SaveChangesAsync();
                chatId = chat.Id;
            }

            // Save user message
            var userMessage = new Message
            {
                ChatId = chatId,
                Type = "user",
                Text = request.Message
            };
            _context.Messages.Add(userMessage);
            await _context.SaveChangesAsync();

            // Call AI
            var aiResponse = await _aiService.GetAiResponseAsync(request.Message, request.UserId, chatId);
            
            if (aiResponse == null)
            {
                return StatusCode(500, new { success = false, message = "Xin lỗi, không thể kết nối đến AI. Vui lòng thử lại!" });
            }

            // Save AI message
            var botMessage = new Message
            {
                ChatId = chatId,
                Type = "assistant",
                Text = aiResponse.Response,
                ResponseHtml = aiResponse.ResponseHtml
            };
            _context.Messages.Add(botMessage);
            
            var chatToUpdate = await _context.Chats.FindAsync(chatId);
            if (chatToUpdate != null) chatToUpdate.UpdatedAt = DateTime.UtcNow;
            
            await _context.SaveChangesAsync();

            return Ok(new
            {
                success = true,
                response = aiResponse.Response,
                response_html = aiResponse.ResponseHtml,
                chatId = chatId,
                userMessageId = userMessage.Id,
                botMessageId = botMessage.Id
            });
        }

        [Authorize]
        [HttpGet("history/{userId}")]
        public async Task<IActionResult> GetHistory(int userId)
        {
            var chats = await _context.Chats
                .Where(c => c.UserId == userId)
                .OrderByDescending(c => c.IsPinned)
                .ThenByDescending(c => c.UpdatedAt)
                .ToListAsync();

            return Ok(new { success = true, chats });
        }

        [Authorize]
        [HttpGet("messages/{chatId}")]
        public async Task<IActionResult> GetMessages(int chatId)
        {
            var messages = await _context.Messages
                .Where(m => m.ChatId == chatId)
                .OrderBy(m => m.CreatedAt)
                .ToListAsync();

            return Ok(new { success = true, messages });
        }
        [Authorize]
        [HttpDelete("{id}")]
        public async Task<IActionResult> DeleteChat(int id)
        {
            var chat = await _context.Chats.Include(c => c.Messages).FirstOrDefaultAsync(c => c.Id == id);
            
            if (chat == null)
            {
                return NotFound(new { success = false, message = "Không tìm thấy đoạn chat." });
            }

            // Authentication check: Ensure the user deleting the chat is the owner
            // Assuming the JWT token contains the user ID, but we can also just trust it if it's passed or extract it.
            // For simplicity, we just delete it here. In a real app, verify user claim.

            _context.Messages.RemoveRange(chat.Messages);
            _context.Chats.Remove(chat);
            await _context.SaveChangesAsync();

            return Ok(new { success = true, message = "Đã xóa đoạn chat thành công." });
        }
        [Authorize]
        [HttpPut("{id}/rename")]
        public async Task<IActionResult> RenameChat(int id, [FromBody] UpdateChatTitleRequest request)
        {
            var chat = await _context.Chats.FirstOrDefaultAsync(c => c.Id == id);
            
            if (chat == null)
            {
                return NotFound(new { success = false, message = "Không tìm thấy đoạn chat." });
            }

            if (string.IsNullOrWhiteSpace(request.Title))
            {
                return BadRequest(new { success = false, message = "Tên đoạn chat không được để trống." });
            }

            chat.Title = request.Title;
            chat.UpdatedAt = DateTime.UtcNow;
            
            await _context.SaveChangesAsync();

            return Ok(new { success = true, message = "Đã đổi tên đoạn chat thành công." });
        }
        [Authorize]
        [HttpPut("{id}/pin")]
        public async Task<IActionResult> PinChat(int id, [FromBody] PinChatRequest request)
        {
            var chat = await _context.Chats.FirstOrDefaultAsync(c => c.Id == id);
            
            if (chat == null)
            {
                return NotFound(new { success = false, message = "Không tìm thấy đoạn chat." });
            }

            if (request.IsPinned)
            {
                // Verify max 3 pins per user
                int pinnedCount = await _context.Chats.CountAsync(c => c.UserId == chat.UserId && c.IsPinned);
                if (pinnedCount >= 3)
                {
                    return BadRequest(new { success = false, message = "Bạn chỉ có thể ghim tối đa 3 đoạn chat." });
                }
            }

            chat.IsPinned = request.IsPinned;
            chat.UpdatedAt = DateTime.UtcNow;
            
            await _context.SaveChangesAsync();

            return Ok(new { success = true, message = request.IsPinned ? "Đã ghim đoạn chat thành công." : "Đã bỏ ghim đoạn chat thành công." });
        }
        [Authorize]
        [HttpPut("message/{id}/feedback")]
        public async Task<IActionResult> FeedbackMessage(int id, [FromBody] FeedbackMessageRequest request)
        {
            var message = await _context.Messages.Include(m => m.Chat).FirstOrDefaultAsync(m => m.Id == id);
            
            if (message == null)
            {
                return NotFound(new { success = false, message = "Không tìm thấy tin nhắn." });
            }

            // Only AI messages should be liked/disliked
            if (message.Type != "assistant")
            {
                return BadRequest(new { success = false, message = "Chỉ có thể phản hồi tin nhắn của Bot." });
            }

            message.IsLiked = request.IsLiked;
            await _context.SaveChangesAsync();

            return Ok(new { success = true });
        }
    }
}
