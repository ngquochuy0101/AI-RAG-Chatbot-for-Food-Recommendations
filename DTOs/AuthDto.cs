namespace AI_RAG_Chatbot_for_Food_Recommendations.DTOs
{
    public class RegisterRequest
    {
        public string Name { get; set; } = string.Empty;
        public string Email { get; set; } = string.Empty;
        public string Password { get; set; } = string.Empty;
    }

    public class LoginRequest
    {
        public string Email { get; set; } = string.Empty;
        public string Password { get; set; } = string.Empty;
    }

    public class AuthResponse
    {
        public bool Success { get; set; }
        public string Message { get; set; } = string.Empty;
        public string? Token { get; set; }
        public object? User { get; set; }
    }

    public class UpdateUserProfileRequest
    {
        public string Name { get; set; } = string.Empty;
        public string? OldPassword { get; set; }
        public string? NewPassword { get; set; }
    }
}
