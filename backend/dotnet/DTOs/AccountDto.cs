namespace AI_RAG_Chatbot_for_Food_Recommendations.DTOs
{
    public class ForgotPasswordRequest
    {
        public string Email { get; set; } = string.Empty;
    }

    public class VerifyCodeRequest
    {
        public string Email { get; set; } = string.Empty;
        public string Code { get; set; } = string.Empty;
    }

    public class ResetPasswordRequest
    {
        public string Email { get; set; } = string.Empty;
        public string Code { get; set; } = string.Empty;
        public string NewPassword { get; set; } = string.Empty;
    }

    public class UpdateProfileRequest
    {
        public int UserId { get; set; }
        public string Name { get; set; } = string.Empty;
    }

    public class ChangePasswordRequest
    {
        public int UserId { get; set; }
        public string CurrentPassword { get; set; } = string.Empty;
        public string NewPassword { get; set; } = string.Empty;
    }

    public class DeleteAccountRequest
    {
        public int UserId { get; set; }
        public string Password { get; set; } = string.Empty;
    }

    public class LogLoginRequest
    {
        public int UserId { get; set; }
    }
}
