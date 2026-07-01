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
        [System.Text.Json.Serialization.JsonPropertyName("response")]
        public string Response { get; set; } = string.Empty;
        
        [System.Text.Json.Serialization.JsonPropertyName("response_html")]
        public string ResponseHtml { get; set; } = string.Empty;
        
        [System.Text.Json.Serialization.JsonPropertyName("intent")]
        public string Intent { get; set; } = string.Empty;
        
        [System.Text.Json.Serialization.JsonPropertyName("data")]
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
        [System.Text.Json.Serialization.JsonPropertyName("isLiked")]
        public bool? IsLiked { get; set; } // true = like, false = dislike, null = remove feedback
    }
}
