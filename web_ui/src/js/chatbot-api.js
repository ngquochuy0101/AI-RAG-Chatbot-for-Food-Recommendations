/**
 * ========================================
 * 🤖 AI CHATBOT API INTEGRATION
 * ========================================
 * Helper functions to interact with RAG Chatbot API
 */

const ChatbotAPI = {
    // API Configuration
    config: {
        baseURL: 'http://localhost:8001',
        timeout: 60000, // 60 seconds for AI processing
    },

    /**
     * Send message to chatbot and get response
     * @param {string} message - User's message
     * @param {number} userId - User ID (optional)
     * @param {number} chatId - Chat ID (optional)
     * @returns {Promise<Object>} Response from API
     */
    async sendMessage(message, userId = null, chatId = null) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

            const response = await fetch(`${this.config.baseURL}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    user_id: userId,
                    chat_id: chatId
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('✅ Received response from API:', data);
            return data;

        } catch (error) {
            console.error('❌ Error sending message:', error);
            
            if (error.name === 'AbortError') {
                return {
                    success: false,
                    response: 'Yêu cầu quá lâu. Vui lòng thử lại với câu hỏi ngắn hơn.',
                    response_html: `<div class="alert-danger">⚠️ Timeout: Vui lòng thử lại sau</div>`,
                    intent: 'error',
                    data: null
                };
            }
            
            return {
                success: false,
                response: 'Đã xảy ra lỗi khi kết nối với server AI. Vui lòng thử lại.',
                response_html: `<div class="alert-danger">⚠️ Lỗi kết nối: ${error.message}</div>`,
                intent: 'error',
                data: null
            };
        }
    },

    /**
     * Check if API server is online
     * @returns {Promise<boolean>}
     */
    async checkHealth() {
        try {
            const response = await fetch(`${this.config.baseURL}/health`, {
                method: 'GET',
                signal: AbortSignal.timeout(5000)
            });
            return response.ok;
        } catch (error) {
            console.error('❌ Health check failed:', error);
            return false;
        }
    }
};

/**
 * ========================================
 * 💬 CHAT UI CONTROLLER
 * ========================================
 */

class ChatController {
    constructor(chatContainerId, inputId, sendButtonId) {
        this.chatContainer = document.getElementById(chatContainerId);
        this.input = document.getElementById(inputId);
        this.sendButton = document.getElementById(sendButtonId);
        
        this.userId = this.getUserId();
        this.chatId = this.getChatId();
        
        this.init();
    }

    init() {
        // Event listeners
        this.sendButton?.addEventListener('click', () => this.handleSend());
        this.input?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            }
        });

        // Check API health on init
        this.checkAPIHealth();
    }

    async checkAPIHealth() {
        const isHealthy = await ChatbotAPI.checkHealth();
        if (!isHealthy) {
            this.showError('⚠️ Không thể kết nối với server AI. Vui lòng kiểm tra lại.');
        }
    }

    async handleSend() {
        const message = this.input?.value.trim();
        
        if (!message) {
            return;
        }

        // Disable input while processing
        this.setInputState(false);

        // Show user message
        this.addUserMessage(message);

        // Clear input
        if (this.input) this.input.value = '';

        // Show typing indicator
        const typingId = this.showTypingIndicator();

        try {
            // Send to API
            const response = await ChatbotAPI.sendMessage(
                message,
                this.userId,
                this.chatId
            );

            // Remove typing indicator
            this.removeTypingIndicator(typingId);

            // Show bot response
            if (response.success) {
                this.addBotMessage(response.response_html || response.response);
            } else {
                this.showError(response.response);
            }

        } catch (error) {
            this.removeTypingIndicator(typingId);
            this.showError('Đã xảy ra lỗi. Vui lòng thử lại.');
        } finally {
            // Re-enable input
            this.setInputState(true);
        }
    }

    addUserMessage(message) {
        if (!this.chatContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = 'user-message';
        messageDiv.innerHTML = `
            <div class="message-content">
                <p>${this.escapeHtml(message)}</p>
            </div>
            <div class="message-time">${this.getCurrentTime()}</div>
        `;
        
        this.chatContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addBotMessage(htmlContent) {
        if (!this.chatContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = 'bot-message';
        messageDiv.innerHTML = `
            <div class="message-content">
                ${htmlContent}
            </div>
            <div class="message-time">${this.getCurrentTime()}</div>
        `;
        
        this.chatContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showTypingIndicator() {
        if (!this.chatContainer) return null;

        const typingDiv = document.createElement('div');
        typingDiv.className = 'bot-message typing-indicator';
        typingDiv.id = `typing-${Date.now()}`;
        typingDiv.innerHTML = `
            <div class="message-content">
                <div class="typing-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        
        this.chatContainer.appendChild(typingDiv);
        this.scrollToBottom();
        
        return typingDiv.id;
    }

    removeTypingIndicator(typingId) {
        if (typingId) {
            const typingDiv = document.getElementById(typingId);
            typingDiv?.remove();
        }
    }

    showError(message) {
        if (!this.chatContainer) return;

        const errorDiv = document.createElement('div');
        errorDiv.className = 'bot-message error-message';
        errorDiv.innerHTML = `
            <div class="message-content">
                <div class="alert-danger">${message}</div>
            </div>
        `;
        
        this.chatContainer.appendChild(errorDiv);
        this.scrollToBottom();
    }

    setInputState(enabled) {
        if (this.input) {
            this.input.disabled = !enabled;
        }
        if (this.sendButton) {
            this.sendButton.disabled = !enabled;
        }
    }

    scrollToBottom() {
        if (this.chatContainer) {
            this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString('vi-VN', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }

    getUserId() {
        // TODO: Get from session/localStorage
        return parseInt(localStorage.getItem('userId')) || null;
    }

    getChatId() {
        // TODO: Get from URL or session
        return parseInt(sessionStorage.getItem('chatId')) || null;
    }
}

/**
 * ========================================
 * 🎨 TYPING INDICATOR CSS
 * ========================================
 * Add this CSS to your stylesheet:
 * 
 * .typing-indicator {
 *     padding: 10px;
 * }
 * 
 * .typing-dots {
 *     display: flex;
 *     gap: 4px;
 *     padding: 10px;
 * }
 * 
 * .typing-dots span {
 *     width: 8px;
 *     height: 8px;
 *     background: #667eea;
 *     border-radius: 50%;
 *     animation: typing 1.4s infinite;
 * }
 * 
 * .typing-dots span:nth-child(2) {
 *     animation-delay: 0.2s;
 * }
 * 
 * .typing-dots span:nth-child(3) {
 *     animation-delay: 0.4s;
 * }
 * 
 * @keyframes typing {
 *     0%, 60%, 100% { transform: translateY(0); }
 *     30% { transform: translateY(-10px); }
 * }
 */

/**
 * ========================================
 * 📝 USAGE EXAMPLE
 * ========================================
 * 
 * // Initialize chat controller
 * const chat = new ChatController('chat-messages', 'user-input', 'send-button');
 * 
 * // Or manually send messages
 * async function testChat() {
 *     const response = await ChatbotAPI.sendMessage('Tôi muốn ăn phở');
 *     console.log(response);
 * }
 */

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ChatbotAPI, ChatController };
}
