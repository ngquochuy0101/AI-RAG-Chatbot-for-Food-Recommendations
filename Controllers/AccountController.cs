using AI_RAG_Chatbot_for_Food_Recommendations.DTOs;
using AI_RAG_Chatbot_for_Food_Recommendations.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace AI_RAG_Chatbot_for_Food_Recommendations.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class AccountController : ControllerBase
    {
        private readonly ChatbotDbContext _context;

        public AccountController(ChatbotDbContext context)
        {
            _context = context;
        }

        [HttpPost("forgotPassword")]
        public async Task<IActionResult> ForgotPassword([FromBody] ForgotPasswordRequest request)
        {
            var user = await _context.Users.FirstOrDefaultAsync(u => u.Email == request.Email);
            if (user == null) return BadRequest(new { success = false, message = "Email không tồn tại!" });

            var code = new Random().Next(100000, 999999).ToString();
            var reset = new PasswordReset
            {
                Email = request.Email,
                Code = code,
                ExpiresAt = DateTime.UtcNow.AddMinutes(15)
            };

            _context.PasswordResets.Add(reset);
            await _context.SaveChangesAsync();

            return Ok(new { success = true, message = "Mã xác nhận đã được tạo.", resetCode = code });
        }

        [HttpPost("resetPassword")]
        public async Task<IActionResult> ResetPassword([FromBody] ResetPasswordRequest request)
        {
            var reset = await _context.PasswordResets
                .Where(r => r.Email == request.Email && r.Code == request.Code && !r.Used && r.ExpiresAt > DateTime.UtcNow)
                .FirstOrDefaultAsync();

            if (reset == null) return BadRequest(new { success = false, message = "Mã xác nhận không hợp lệ hoặc đã hết hạn!" });

            var user = await _context.Users.FirstOrDefaultAsync(u => u.Email == request.Email);
            if (user != null)
            {
                user.Password = BCrypt.Net.BCrypt.HashPassword(request.NewPassword);
                reset.Used = true;
                await _context.SaveChangesAsync();
                return Ok(new { success = true, message = "Đặt lại mật khẩu thành công!" });
            }

            return BadRequest(new { success = false, message = "Lỗi xác thực người dùng." });
        }

        [Authorize]
        [HttpPost("updateProfile")]
        public async Task<IActionResult> UpdateProfile([FromBody] UpdateProfileRequest request)
        {
            var user = await _context.Users.FindAsync(request.UserId);
            if (user == null) return NotFound();

            user.Name = request.Name;
            await _context.SaveChangesAsync();
            return Ok(new { success = true, message = "Cập nhật hồ sơ thành công!" });
        }

        [Authorize]
        [HttpGet("profile/{id}")]
        public async Task<IActionResult> GetProfile(int id)
        {
            var user = await _context.Users.FindAsync(id);
            if (user == null) return NotFound();

            return Ok(new { success = true, user = new { id = user.Id, name = user.Name, email = user.Email, created_at = user.CreatedAt, last_login = user.LastLogin } });
        }
        
        [Authorize]
        [HttpGet("loginHistory/{id}")]
        public async Task<IActionResult> GetLoginHistory(int id)
        {
            var history = await _context.LoginHistories
                .Where(l => l.UserId == id)
                .OrderByDescending(l => l.LoginAt)
                .Take(10)
                .ToListAsync();

            return Ok(new { success = true, history });
        }
    }
}
