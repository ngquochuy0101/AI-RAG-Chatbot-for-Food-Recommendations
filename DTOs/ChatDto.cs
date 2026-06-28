namespace AI_RAG_Chatbot_for_Food_Recommendations.DTOs
{
    public class SendMessageRequest
    {
        public string Message { get; set; } = string.Empty;
        public int UserId { get; set; }
        public int ChatId { get; set; }
    }

    public class AiResponseDto
    {
        public string Response { get; set; } = string.Empty;
        public string ResponseHtml { get; set; } = string.Empty;
        public string Intent { get; set; } = string.Empty;
        public object? Data { get; set; }
    }

    public class ReportMessageRequest
    {
        public string Message { get; set; } = string.Empty;
        public int UserId { get; set; }
        public int ChatId { get; set; }
        public string Reason { get; set; } = string.Empty;
        public string ReasonText { get; set; } = string.Empty;
        public string Details { get; set; } = string.Empty;
    }

    public class UpdateChatTitleRequest
    {
        public int ChatId { get; set; }
        public int UserId { get; set; }
        public string Title { get; set; } = string.Empty;
    }
    
    public class PinChatRequest
    {
        public int ChatId { get; set; }
        public int UserId { get; set; }
        public bool IsPinned { get; set; }
    }

    public class FeedbackMessageRequest
    {
        public bool? IsLiked { get; set; } // true = like, false = dislike, null = remove feedback
    }
}
