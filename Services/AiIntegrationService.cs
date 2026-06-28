using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using AI_RAG_Chatbot_for_Food_Recommendations.DTOs;

namespace AI_RAG_Chatbot_for_Food_Recommendations.Services
{
    public interface IAiIntegrationService
    {
        Task<AiResponseDto?> GetAiResponseAsync(string message, int userId, int chatId);
    }

    public class AiIntegrationService : IAiIntegrationService
    {
        private readonly HttpClient _httpClient;
        private readonly string _pythonApiUrl;

        public AiIntegrationService(HttpClient httpClient, Microsoft.Extensions.Configuration.IConfiguration configuration)
        {
            _httpClient = httpClient;
            _pythonApiUrl = configuration["PythonApiUrl"] ?? "http://localhost:8001";
        }

        public async Task<AiResponseDto?> GetAiResponseAsync(string message, int userId, int chatId)
        {
            try
            {
                var payload = new
                {
                    message = message,
                    user_id = userId,
                    chat_id = chatId
                };

                var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
                
                // Call Python FastAPI
                var response = await _httpClient.PostAsync($"{_pythonApiUrl}/chat", content);
                
                if (response.IsSuccessStatusCode)
                {
                    using var responseStream = await response.Content.ReadAsStreamAsync();
                    var result = await JsonSerializer.DeserializeAsync<AiResponseDto>(responseStream, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
                    return result;
                }
                
                return null;
            }
            catch
            {
                return null;
            }
        }
    }
}
