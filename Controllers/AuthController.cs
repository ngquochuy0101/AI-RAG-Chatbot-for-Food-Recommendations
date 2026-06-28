using AI_RAG_Chatbot_for_Food_Recommendations.DTOs;
using AI_RAG_Chatbot_for_Food_Recommendations.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.AspNetCore.Authorization;

namespace AI_RAG_Chatbot_for_Food_Recommendations.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class AuthController : ControllerBase
    {
        private readonly ChatbotDbContext _context;
        private readonly IConfiguration _configuration;

        public AuthController(ChatbotDbContext context, IConfiguration configuration)
        {
            _context = context;
            _configuration = configuration;
        }

        [HttpPost("register")]
        public async Task<IActionResult> Register([FromBody] RegisterRequest request)
        {
            if (string.IsNullOrWhiteSpace(request.Name) || string.IsNullOrWhiteSpace(request.Email) || string.IsNullOrWhiteSpace(request.Password))
                return BadRequest(new AuthResponse { Success = false, Message = "Vui lòng điền đầy đủ thông tin!" });

            if (await _context.Users.AnyAsync(u => u.Email == request.Email))
                return BadRequest(new AuthResponse { Success = false, Message = "Email đã tồn tại!" });

            var user = new User
            {
                Name = request.Name,
                Email = request.Email,
                Password = BCrypt.Net.BCrypt.HashPassword(request.Password),
                CreatedAt = DateTime.UtcNow,
                IsAdmin = request.Email.ToLower() == "admin@example.com"
            };

            _context.Users.Add(user);
            await _context.SaveChangesAsync();

            return Ok(new AuthResponse { Success = true, Message = "Đăng ký thành công!" });
        }

        [HttpPost("login")]
        public async Task<IActionResult> Login([FromBody] LoginRequest request)
        {
            var user = await _context.Users.FirstOrDefaultAsync(u => u.Email == request.Email);
            
            if (user == null || !BCrypt.Net.BCrypt.Verify(request.Password, user.Password))
                return Unauthorized(new AuthResponse { Success = false, Message = "Email hoặc mật khẩu không đúng!" });

            user.LastLogin = DateTime.UtcNow;
            await _context.SaveChangesAsync();

            var tokenHandler = new JwtSecurityTokenHandler();
            var key = Encoding.UTF8.GetBytes(_configuration["Jwt:Key"]!);
            var tokenDescriptor = new SecurityTokenDescriptor
            {
                Subject = new ClaimsIdentity(new[]
                {
                    new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
                    new Claim(ClaimTypes.Email, user.Email),
                    new Claim(ClaimTypes.Name, user.Name)
                }),
                Expires = DateTime.UtcNow.AddDays(7),
                Issuer = _configuration["Jwt:Issuer"],
                Audience = _configuration["Jwt:Audience"],
                SigningCredentials = new SigningCredentials(new SymmetricSecurityKey(key), SecurityAlgorithms.HmacSha256Signature)
            };
            
            var token = tokenHandler.CreateToken(tokenDescriptor);

            return Ok(new AuthResponse
            {
                Success = true,
                Message = "Đăng nhập thành công!",
                Token = tokenHandler.WriteToken(token),
                User = new { id = user.Id, name = user.Name, email = user.Email, isAdmin = user.IsAdmin }
            });
        }
        [Authorize]
        [HttpPut("profile")]
        public async Task<IActionResult> UpdateProfile([FromBody] UpdateUserProfileRequest request)
        {
            var userIdString = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userIdString) || !int.TryParse(userIdString, out int userId))
            {
                return Unauthorized(new AuthResponse { Success = false, Message = "Không thể xác thực người dùng." });
            }

            var user = await _context.Users.FindAsync(userId);
            if (user == null)
            {
                return NotFound(new AuthResponse { Success = false, Message = "Không tìm thấy người dùng." });
            }

            if (string.IsNullOrWhiteSpace(request.Name))
            {
                return BadRequest(new AuthResponse { Success = false, Message = "Tên không được để trống." });
            }

            user.Name = request.Name;

            // Update password if provided
            if (!string.IsNullOrEmpty(request.OldPassword) && !string.IsNullOrEmpty(request.NewPassword))
            {
                if (!BCrypt.Net.BCrypt.Verify(request.OldPassword, user.Password))
                {
                    return BadRequest(new AuthResponse { Success = false, Message = "Mật khẩu cũ không chính xác." });
                }
                user.Password = BCrypt.Net.BCrypt.HashPassword(request.NewPassword);
            }

            await _context.SaveChangesAsync();

            return Ok(new AuthResponse
            {
                Success = true,
                Message = "Cập nhật thông tin thành công!",
                User = new { id = user.Id, name = user.Name, email = user.Email }
            });
        }
    }
}
