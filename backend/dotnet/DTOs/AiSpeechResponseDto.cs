namespace AI_RAG_Chatbot_for_Food_Recommendations.DTOs
{
    public class AiSpeechResponseDto
    {
        public bool Success { get; set; }
        public string? User_Text { get; set; }
        public string? Ai_Text { get; set; }
        public string? Ai_Audio_Base64 { get; set; }
    }
}
