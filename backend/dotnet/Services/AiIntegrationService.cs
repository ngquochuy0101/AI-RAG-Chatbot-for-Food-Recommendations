using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using AI_RAG_Chatbot_for_Food_Recommendations.DTOs;
using Microsoft.AspNetCore.Http;
using System.IO;

namespace AI_RAG_Chatbot_for_Food_Recommendations.Services
{
    public interface IAiIntegrationService
    {
        Task<AiResponseDto?> GetAiResponseAsync(string message, int userId, int chatId);
        Task<AiSpeechResponseDto?> GetAiSpeechResponseAsync(IFormFile audio);
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

        public async Task<AiSpeechResponseDto?> GetAiSpeechResponseAsync(IFormFile audio)
        {
            try
            {
                using var multipartFormContent = new MultipartFormDataContent();
                
                var memoryStream = new MemoryStream();
                await audio.CopyToAsync(memoryStream);
                memoryStream.Position = 0;
                
                var audioStreamContent = new StreamContent(memoryStream);
                audioStreamContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue(audio.ContentType ?? "audio/webm");
                multipartFormContent.Add(audioStreamContent, "audio", audio.FileName);

                var response = await _httpClient.PostAsync($"{_pythonApiUrl}/chat/speech", multipartFormContent);
                
                if (response.IsSuccessStatusCode)
                {
                    using var responseStream = await response.Content.ReadAsStreamAsync();
                    var result = await JsonSerializer.DeserializeAsync<AiSpeechResponseDto>(responseStream, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
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
