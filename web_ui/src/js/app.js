// API Base URL
const API_BASE = 'api';

// Global State
let currentUser = null;
let currentChatId = null;
let chatHistory = [];
let selectedMessage = null;

// DOM Elements
const sidebar = document.getElementById('sidebar');
const menuToggle = document.getElementById('menuToggle');
const newChatBtn = document.getElementById('newChatBtn');
const chatContainer = document.getElementById('chatContainer');
const welcomeMessage = document.getElementById('welcomeMessage');
const messagesContainer = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const authBtn = document.getElementById('authBtn');
const userInfo = document.getElementById('userInfo');
const username = document.getElementById('username');
const historyList = document.getElementById('historyList');

// Modal Elements
const loginModal = document.getElementById('loginModal');
const registerModal = document.getElementById('registerModal');
const closeLoginModal = document.getElementById('closeLoginModal');
const closeRegisterModal = document.getElementById('closeRegisterModal');
const showRegister = document.getElementById('showRegister');
const showLogin = document.getElementById('showLogin');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');

// Report Modal Elements
const reportModal = document.getElementById('reportModal');
const closeReportModal = document.getElementById('closeReportModal');
const reportForm = document.getElementById('reportForm');
const cancelReport = document.getElementById('cancelReport');

// Edit Title Modal Elements
const editTitleModal = document.getElementById('editTitleModal');
const closeEditTitleModal = document.getElementById('closeEditTitleModal');
const editTitleForm = document.getElementById('editTitleForm');
const cancelEditTitle = document.getElementById('cancelEditTitle');
const newTitleInput = document.getElementById('newTitleInput');
let currentEditChatId = null;

// Context Menu
const contextMenu = document.getElementById('contextMenu');
const copyMessage = document.getElementById('copyMessage');
const reportMessage = document.getElementById('reportMessage');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Loaded');
    console.log('contextMenu:', contextMenu);
    console.log('copyMessage:', copyMessage);
    console.log('reportMessage:', reportMessage);
    
    initializeApp();
    setupEventListeners();
    setupReportModalListeners();
    checkAuth();
});

// Initialize App
function initializeApp() {
    // Auto-resize textarea
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // Load chat history
    loadChatHistory();
}

// Setup Event Listeners
function setupEventListeners() {
    // Sidebar Toggle
    menuToggle.addEventListener('click', () => {
        sidebar.classList.toggle('show');
    });

    // New Chat
    newChatBtn.addEventListener('click', createNewChat);

    // Send Message
    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auth Buttons
    authBtn.addEventListener('click', handleAuthClick);
    
    // Modal Events
    closeLoginModal.addEventListener('click', () => closeModal(loginModal));
    closeRegisterModal.addEventListener('click', () => closeModal(registerModal));
    showRegister.addEventListener('click', (e) => {
        e.preventDefault();
        closeModal(loginModal);
        openModal(registerModal);
    });
    showLogin.addEventListener('click', (e) => {
        e.preventDefault();
        closeModal(registerModal);
        openModal(loginModal);
    });

    // Form Submissions
    loginForm.addEventListener('submit', handleLogin);
    registerForm.addEventListener('submit', handleRegister);

    // Context Menu
    document.addEventListener('click', (e) => {
        // Don't close if clicking inside context menu
        if (!contextMenu.contains(e.target)) {
            contextMenu.classList.remove('show');
        }
    });

    if (copyMessage) {
        copyMessage.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('Copy message clicked');
            handleCopyMessage();
            contextMenu.classList.remove('show');
        });
    }
    
    if (reportMessage) {
        reportMessage.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('Report message clicked');
            handleReportMessage();
            contextMenu.classList.remove('show');
        });
    }

    // Close modal on outside click
    window.addEventListener('click', (e) => {
        if (e.target === loginModal) closeModal(loginModal);
        if (e.target === registerModal) closeModal(registerModal);
    });
}

// Authentication
function checkAuth() {
    const savedUser = localStorage.getItem('user');
    const savedToken = localStorage.getItem('token');

    if (savedUser && savedToken) {
        try {
            currentUser = JSON.parse(savedUser);
            updateUIForLoggedIn();
            profileBtn.style.display = 'flex';
            loadChatHistory();
            return;
        } catch (error) {
            console.error('Auth state parse error:', error);
        }
    }

    currentUser = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    updateUIForLoggedOut();
}

function handleAuthClick() {
    if (currentUser) {
        logout();
    } else {
        openModal(loginModal);
    }
}

async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const response = await fetch(`${API_BASE}/auth.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: 'login',
                email: email,
                password: password
            })
        });

        const data = await response.json();

        if (data.success) {
            currentUser = data.user;
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            
            closeModal(loginModal);
            updateUIForLoggedIn();
            showNotification('Đăng nhập thành công!', 'success');
            loadChatHistory();
        } else {
            showNotification(data.message || 'Đăng nhập thất bại!', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showNotification('Có lỗi xảy ra khi kết nối server!', 'error');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    
    const name = document.getElementById('registerName').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const confirmPassword = document.getElementById('registerConfirmPassword').value;

    if (password !== confirmPassword) {
        showNotification('Mật khẩu không khớp!', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/auth.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: 'register',
                name: name,
                email: email,
                password: password
            })
        });

        const data = await response.json();

        if (data.success) {
            closeModal(registerModal);
            showNotification('Đăng ký thành công! Vui lòng đăng nhập.', 'success');
            openModal(loginModal);
            
            // Clear form
            document.getElementById('registerForm').reset();
        } else {
            showNotification(data.message || 'Đăng ký thất bại!', 'error');
        }
    } catch (error) {
        console.error('Register error:', error);
        showNotification('Có lỗi xảy ra khi kết nối server!', 'error');
    }
}

function logout() {
    currentUser = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    updateUIForLoggedOut();
    showNotification('Đã đăng xuất!', 'info');
    createNewChat();
}

function updateUIForLoggedIn() {
    username.textContent = currentUser.name;
    authBtn.innerHTML = '<i class="fas fa-sign-out-alt"></i> Đăng xuất';
    authBtn.classList.add('logout');
    
    // Enable message input when logged in
    messageInput.disabled = false;
    sendBtn.disabled = false;
    messageInput.placeholder = 'Nhập tin nhắn...';
}

function updateUIForLoggedOut() {
    username.textContent = 'Khách';
    authBtn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Đăng nhập';
    authBtn.classList.remove('logout');
    chatHistory = [];
    renderChatHistory();
    
    // Disable message input when logged out
    messageInput.disabled = true;
    sendBtn.disabled = true;
    messageInput.placeholder = 'Vui lòng đăng nhập để gửi tin nhắn...';
}

// Chat Functions
function createNewChat() {
    currentChatId = null;
    messagesContainer.innerHTML = '';
    welcomeMessage.style.display = 'block';
    messageInput.value = '';
    
    // Remove active class from all history items
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.remove('active');
    });
}

async function sendMessage() {
    const message = messageInput.value.trim();
    
    if (!message) return;

    // Check if user is logged in before sending
    if (!currentUser) {
        showNotification('Vui lòng đăng nhập để gửi tin nhắn!', 'info');
        openModal(loginModal);
        return;
    }

    // Add user message to UI
    addMessage(message, 'user');
    messageInput.value = '';
    messageInput.style.height = 'auto';
    welcomeMessage.style.display = 'none';

    // Auto scroll to bottom
    scrollToBottom();

    // Show loading
    const loadingId = addLoadingMessage();

    try {
        // Send to backend API
        const response = await fetch(`${API_BASE}/chat.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                action: 'sendMessage',
                message: message,
                chatId: currentChatId,
                userId: currentUser?.id
            })
        });

        const data = await response.json();

        // Remove loading
        removeLoadingMessage(loadingId);

        if (data.success) {
            // Add assistant response - use response_html if available
            const displayContent = data.response_html || data.response;
            addMessage(displayContent, 'assistant', true); // true = isHTML
            
            // Auto scroll to bottom
            scrollToBottom();
            
            // Update chat ID if new chat
            if (!currentChatId && data.chatId) {
                currentChatId = data.chatId;
                if (currentUser) {
                    loadChatHistory();
                }
            }
        } else {
            showNotification('Có lỗi xảy ra!', 'error');
        }
    } catch (error) {
        console.error('Send message error:', error);
        removeLoadingMessage(loadingId);

        addMessage('Xin lỗi, hiện không thể kết nối máy chủ AI. Vui lòng thử lại sau.', 'assistant');
        showNotification('Không thể kết nối đến AI API', 'error');
        scrollToBottom();
    }
}

// Function to auto scroll to bottom
function scrollToBottom(instant = false) {
    const chatContainer = document.getElementById('chatContainer');
    const messagesEl = document.getElementById('messages');

    if (!chatContainer) return;

    const doScroll = () => {
        // Use smooth scrolling with scrollTo for better animation
        if (!instant && chatContainer.scrollTo) {
            chatContainer.scrollTo({
                top: chatContainer.scrollHeight,
                behavior: 'smooth'
            });
        } else {
            // Instant scroll fallback
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        // Also try scrollIntoView for the last message as backup
        if (messagesEl) {
            const last = messagesEl.lastElementChild;
            if (last && typeof last.scrollIntoView === 'function') {
                try {
                    last.scrollIntoView({ 
                        behavior: instant ? 'auto' : 'smooth', 
                        block: 'end', 
                        inline: 'nearest' 
                    });
                } catch (e) {
                    // Ignore errors
                }
            }
        }
    };

    // Use requestAnimationFrame for smooth animation timing
    requestAnimationFrame(() => {
        doScroll();
        // One more attempt after a short delay to ensure content is fully rendered
        setTimeout(() => {
            if (!instant) {
                chatContainer.scrollTo({
                    top: chatContainer.scrollHeight,
                    behavior: 'smooth'
                });
            }
        }, 100);
    });
}

function addMessage(text, type, isHTML = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const avatarIcon = type === 'user' ? 'fa-user' : 'fa-robot';
    
    // Only show report button for assistant messages
    const reportButton = type === 'assistant' 
        ? `<button class="message-action report-btn" title="Báo cáo">
                <i class="fas fa-flag"></i>
           </button>`
        : '';
    
    // Use innerHTML directly for HTML content, otherwise escape text
    const messageContent = isHTML ? text : escapeHtmlContent(text);
    
    // For data-message attribute, always use plain text (strip HTML tags)
    const plainText = text.replace(/<[^>]*>/g, '').substring(0, 100);
    
    messageDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fas ${avatarIcon}"></i>
        </div>
        <div class="message-content">
            <div class="message-bubble" data-message="${plainText}">
                <div class="message-text">${messageContent}</div>
            </div>
            <div class="message-actions">
                <button class="message-action copy-btn" title="Sao chép">
                    <i class="fas fa-copy"></i>
                </button>
                ${reportButton}
            </div>
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom after adding message
    scrollToBottom();

    // Add event listeners for actions
    const copyBtn = messageDiv.querySelector('.copy-btn');
    const reportBtn = messageDiv.querySelector('.report-btn');

    copyBtn.addEventListener('click', () => copyMessageText(text));
    
    // Only add report listener if button exists (assistant messages only)
    if (reportBtn) {
        reportBtn.addEventListener('click', () => {
            selectedMessage = text;
            openReportModal();
        });
    }

    // Right-click context menu
    const messageBubble = messageDiv.querySelector('.message-bubble');
    messageBubble.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showContextMenu(e.pageX, e.pageY, text);
    });
}

function addLoadingMessage() {
    const loadingId = 'loading-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.id = loadingId;
    
    messageDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-robot"></i>
        </div>
        <div class="message-content">
            <div class="message-bubble">
                <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom after adding loading message
    scrollToBottom();
    
    return loadingId;
}

function removeLoadingMessage(loadingId) {
    const loadingMsg = document.getElementById(loadingId);
    if (loadingMsg) {
        loadingMsg.remove();
    }
}

// Chat History
async function loadChatHistory() {
    if (!currentUser) {
        chatHistory = [];
        renderChatHistory();
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/chat.php?action=getHistory&userId=${currentUser.id}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        const data = await response.json();

        if (data.success) {
            chatHistory = data.history;
            renderChatHistory();
        }
    } catch (error) {
        console.error('Load history error:', error);
    }
}

function renderChatHistory() {
    historyList.innerHTML = '';
    
    if (chatHistory.length === 0) {
        historyList.innerHTML = '<p style="color: #657786; font-size: 14px; text-align: center;">Chưa có lịch sử</p>';
        return;
    }

    chatHistory.forEach(chat => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.setAttribute('data-chat-id', chat.id);
        
        if (chat.id === currentChatId) {
            historyItem.classList.add('active');
        }
        
        // Add pinned class if chat is pinned
        if (chat.is_pinned == 1 || chat.is_pinned === true) {
            historyItem.classList.add('pinned');
        }
        
        historyItem.innerHTML = `
            <div class="history-item-content">
                <div class="history-item-title">
                    ${chat.is_pinned == 1 || chat.is_pinned === true ? '<i class="fas fa-thumbtack pin-indicator"></i> ' : ''}
                    <span class="chat-title-text">${chat.title || 'Cuộc trò chuyện'}</span>
                    <button class="edit-title-btn" title="Sửa tiêu đề">
                        <i class="fas fa-pencil-alt"></i>
                    </button>
                </div>
                <div class="history-item-date">${formatDate(chat.created_at)}</div>
            </div>
            <div class="history-item-actions">
                <button class="history-action-btn pin-btn" title="${chat.is_pinned == 1 || chat.is_pinned === true ? 'Bỏ ghim' : 'Ghim'}">
                    <i class="fas fa-thumbtack"></i>
                </button>
                <button class="history-action-btn delete-btn" title="Xóa">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        // Click to load chat
        const contentArea = historyItem.querySelector('.history-item-content');
        contentArea.addEventListener('click', (e) => {
            // Don't load chat if clicking edit button
            if (!e.target.closest('.edit-title-btn')) {
                loadChat(chat.id);
            }
        });
        
        // Edit title button
        const editTitleBtn = historyItem.querySelector('.edit-title-btn');
        editTitleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            openEditTitleModal(chat.id, chat.title || 'Cuộc trò chuyện');
        });
        
        // Pin button
        const pinBtn = historyItem.querySelector('.pin-btn');
        pinBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            togglePinChat(chat.id, chat.is_pinned == 1 || chat.is_pinned === true);
        });
        
        // Delete button
        const deleteBtn = historyItem.querySelector('.delete-btn');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            confirmDeleteChat(chat.id, chat.title);
        });
        
        historyList.appendChild(historyItem);
    });
}

async function loadChat(chatId) {
    try {
        const response = await fetch(`${API_BASE}/chat.php?action=getMessages&chatId=${chatId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        const data = await response.json();

        if (data.success) {
            currentChatId = chatId;
            messagesContainer.innerHTML = '';
            welcomeMessage.style.display = 'none';
            
            data.messages.forEach(msg => {
                // Check if message contains HTML (has response_html or contains HTML tags)
                const isHTML = msg.response_html || (msg.message && msg.message.includes('<'));
                const displayContent = msg.response_html || msg.message;
                addMessage(displayContent, msg.type, isHTML);
            });

            // Scroll to bottom after loading messages
            scrollToBottom();

            // Update active state
            document.querySelectorAll('.history-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Find and mark active history item by chatId
            const historyItems = document.querySelectorAll('.history-item');
            historyItems.forEach(item => {
                const itemChatId = item.getAttribute('data-chat-id');
                if (itemChatId == chatId) {
                    item.classList.add('active');
                }
            });
        }
    } catch (error) {
        console.error('Load chat error:', error);
    }
}

// Delete Chat Function
async function confirmDeleteChat(chatId, chatTitle) {
    if (!currentUser) {
        showNotification('Vui lòng đăng nhập!', 'info');
        return;
    }
    
    const confirmed = confirm(`Bạn có chắc muốn xóa cuộc trò chuyện "${chatTitle || 'Cuộc trò chuyện'}"?`);
    
    if (!confirmed) return;
    
    try {
        const response = await fetch(`${API_BASE}/chat.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                action: 'deleteChat',
                chatId: chatId,
                userId: currentUser.id
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Đã xóa cuộc trò chuyện!', 'success');
            
            // If deleted chat is current, create new chat
            if (currentChatId === chatId) {
                createNewChat();
            }
            
            // Reload history
            loadChatHistory();
        } else {
            showNotification(data.message || 'Không thể xóa cuộc trò chuyện!', 'error');
        }
    } catch (error) {
        console.error('Delete chat error:', error);
        showNotification('Có lỗi xảy ra!', 'error');
    }
}

// Pin Chat Function
async function togglePinChat(chatId, currentPinStatus) {
    if (!currentUser) {
        showNotification('Vui lòng đăng nhập!', 'info');
        return;
    }
    
    const newPinStatus = !currentPinStatus;
    
    try {
        const response = await fetch(`${API_BASE}/chat.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                action: 'pinChat',
                chatId: chatId,
                userId: currentUser.id,
                isPinned: newPinStatus
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            
            // Reload history to show updated pin status
            loadChatHistory();
        } else {
            showNotification(data.message || 'Không thể cập nhật trạng thái ghim!', 'error');
        }
    } catch (error) {
        console.error('Pin chat error:', error);
        showNotification('Có lỗi xảy ra!', 'error');
    }
}

// Context Menu
function showContextMenu(x, y, message) {
    console.log('showContextMenu called', {x, y, message});
    selectedMessage = message;
    contextMenu.style.left = x + 'px';
    contextMenu.style.top = y + 'px';
    contextMenu.classList.add('show');
    console.log('Context menu should be visible now');
}

function handleCopyMessage() {
    console.log('handleCopyMessage called');
    if (selectedMessage) {
        copyMessageText(selectedMessage);
    }
}

async function handleReportMessage() {
    console.log('handleReportMessage called');
    console.log('selectedMessage:', selectedMessage);
    
    // Just open report modal directly without validation
    console.log('About to call openReportModal()');
    openReportModal();
}

// Helper function to escape HTML
function escapeHtmlContent(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function copyMessageText(text) {
    // Strip HTML tags if present
    const plainText = text.replace(/<[^>]*>/g, '');
    
    navigator.clipboard.writeText(plainText).then(() => {
        showNotification('Đã sao chép!', 'success');
    }).catch(err => {
        console.error('Copy error:', err);
        showNotification('Không thể sao chép!', 'error');
    });
}

function reportMessageContent(text) {
    if (!currentUser) {
        showNotification('Vui lòng đăng nhập để báo cáo!', 'info');
        return;
    }
    handleReportMessage();
}

// Modal Functions
function openModal(modal) {
    modal.classList.add('show');
}

function closeModal(modal) {
    modal.classList.remove('show');
    
    // Clear resend timer if closing reset password modal
    if (modal === resetPasswordModal) {
        if (resendTimer) {
            clearInterval(resendTimer);
            resendTimer = null;
        }
        resendCountdown = 0;
        const resendHint = document.getElementById('resendHint');
        if (resendHint) resendHint.textContent = '';
    }
}

// Utility Functions
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) {
        return 'Hôm nay';
    } else if (days === 1) {
        return 'Hôm qua';
    } else if (days < 7) {
        return `${days} ngày trước`;
    } else {
        return date.toLocaleDateString('vi-VN');
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    const iconMap = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle'
    };
    
    notification.innerHTML = `
        <i class="fas ${iconMap[type]}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// Add animation for slide out
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ============================================
// ACCOUNT MANAGEMENT FEATURES
// ============================================

// Modal Elements - Account Management
const forgotPasswordModal = document.getElementById('forgotPasswordModal');
const resetPasswordModal = document.getElementById('resetPasswordModal');
const profileModal = document.getElementById('profileModal');
const deleteAccountModal = document.getElementById('deleteAccountModal');

const closeForgotPasswordModal = document.getElementById('closeForgotPasswordModal');
const closeResetPasswordModal = document.getElementById('closeResetPasswordModal');
const closeProfileModal = document.getElementById('closeProfileModal');
const closeDeleteAccountModal = document.getElementById('closeDeleteAccountModal');

const showForgotPassword = document.getElementById('showForgotPassword');
const backToLogin = document.getElementById('backToLogin');
const profileBtn = document.getElementById('profileBtn');
const deleteAccountBtn = document.getElementById('deleteAccountBtn');
const cancelDeleteAccount = document.getElementById('cancelDeleteAccount');

// Forms
const forgotPasswordForm = document.getElementById('forgotPasswordForm');
const resetPasswordForm = document.getElementById('resetPasswordForm');
const updateProfileForm = document.getElementById('updateProfileForm');
const changePasswordForm = document.getElementById('changePasswordForm');
const deleteAccountForm = document.getElementById('deleteAccountForm');

// Temporary storage for password reset
let resetEmail = '';
let resendTimer = null;
let resendCountdown = 0;

// Setup Account Management Event Listeners
function setupAccountManagementListeners() {
    // Show Forgot Password Modal
    if (showForgotPassword) {
        showForgotPassword.addEventListener('click', (e) => {
            e.preventDefault();
            closeModal(loginModal);
            openModal(forgotPasswordModal);
        });
    }

    // Back to Login from Forgot Password
    if (backToLogin) {
        backToLogin.addEventListener('click', (e) => {
            e.preventDefault();
            closeModal(forgotPasswordModal);
            openModal(loginModal);
        });
    }

    // Profile Button
    if (profileBtn) {
        profileBtn.addEventListener('click', () => {
            openProfileModal();
        });
    }

    // Delete Account Button
    if (deleteAccountBtn) {
        deleteAccountBtn.addEventListener('click', () => {
            closeModal(profileModal);
            openModal(deleteAccountModal);
        });
    }

    // Cancel Delete Account
    if (cancelDeleteAccount) {
        cancelDeleteAccount.addEventListener('click', () => {
            closeModal(deleteAccountModal);
            openModal(profileModal);
        });
    }

    // Close Modal Buttons
    if (closeForgotPasswordModal) {
        closeForgotPasswordModal.addEventListener('click', () => closeModal(forgotPasswordModal));
    }
    if (closeResetPasswordModal) {
        closeResetPasswordModal.addEventListener('click', () => closeModal(resetPasswordModal));
    }
    if (closeProfileModal) {
        closeProfileModal.addEventListener('click', () => closeModal(profileModal));
    }
    if (closeDeleteAccountModal) {
        closeDeleteAccountModal.addEventListener('click', () => closeModal(deleteAccountModal));
    }

    // Form Submissions
    if (forgotPasswordForm) {
        forgotPasswordForm.addEventListener('submit', handleForgotPassword);
    }
    if (resetPasswordForm) {
        resetPasswordForm.addEventListener('submit', handleResetPassword);
    }
    if (updateProfileForm) {
        updateProfileForm.addEventListener('submit', handleUpdateProfile);
    }
    if (changePasswordForm) {
        changePasswordForm.addEventListener('submit', handleChangePassword);
    }
    if (deleteAccountForm) {
        deleteAccountForm.addEventListener('submit', handleDeleteAccount);
    }

    // Resend Code Button
    const resendCodeBtn = document.getElementById('resendCodeBtn');
    if (resendCodeBtn) {
        resendCodeBtn.addEventListener('click', handleResendCode);
    }

    // Profile Tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
}

// Call setup after DOM loaded
document.addEventListener('DOMContentLoaded', () => {
    setupAccountManagementListeners();
});

// Switch Profile Tabs
function switchTab(tabName) {
    // Remove active class from all tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Add active class to selected tab
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`${tabName}Tab`).classList.add('active');

    // Load specific tab data
    if (tabName === 'security') {
        loadLoginHistory();
    }
}

// Handle Forgot Password
async function handleForgotPassword(e) {
    e.preventDefault();

    const email = document.getElementById('forgotEmail').value;
    resetEmail = email; // Store for later use

    try {
        const response = await fetch(`${API_BASE}/account.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'forgotPassword',
                email: email
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');

            // Switch to reset password modal
            closeModal(forgotPasswordModal);
            openModal(resetPasswordModal);
            forgotPasswordForm.reset();
            
            // Start resend timer
            startResendTimer();
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Forgot password error:', error);
        showNotification('Có lỗi xảy ra!', 'error');
    }
}

// Handle Resend Code
async function handleResendCode() {
    if (!resetEmail) {
        showNotification('Vui lòng bắt đầu lại từ đầu!', 'error');
        closeModal(resetPasswordModal);
        openModal(forgotPasswordModal);
        return;
    }

    if (resendCountdown > 0) {
        showNotification(`Vui lòng đợi ${resendCountdown} giây để gửi lại mã!`, 'info');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/account.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'forgotPassword',
                email: resetEmail
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            
            // Clear old code input
            document.getElementById('resetCode').value = '';
            
            // Start resend timer again
            startResendTimer();
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Resend code error:', error);
        showNotification('Có lỗi xảy ra!', 'error');
    }
}

// Start Resend Timer (60 seconds cooldown)
function startResendTimer() {
    const resendBtn = document.getElementById('resendCodeBtn');
    const resendHint = document.getElementById('resendHint');
    
    if (!resendBtn || !resendHint) return;
    
    resendCountdown = 60;
    resendBtn.disabled = true;
    
    // Clear existing timer if any
    if (resendTimer) clearInterval(resendTimer);
    
    resendTimer = setInterval(() => {
        resendCountdown--;
        
        if (resendCountdown > 0) {
            resendHint.textContent = `Có thể gửi lại mã sau ${resendCountdown} giây`;
            resendHint.style.color = 'var(--dark-gray)';
        } else {
            resendHint.textContent = 'Bạn có thể gửi lại mã bây giờ';
            resendHint.style.color = 'var(--primary-blue)';
            resendBtn.disabled = false;
            clearInterval(resendTimer);
        }
    }, 1000);
}

// Handle Reset Password
async function handleResetPassword(e) {
    e.preventDefault();

    const code = document.getElementById('resetCode').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmNewPassword = document.getElementById('confirmNewPassword').value;

    // Validate passwords match
    if (newPassword !== confirmNewPassword) {
        showNotification('Mật khẩu xác nhận không khớp!', 'error');
        return;
    }

    if (newPassword.length < 6) {
        showNotification('Mật khẩu phải có ít nhất 6 ký tự!', 'error');
        return;
    }

    try {
        const requestData = {
            action: 'resetPassword',
            email: resetEmail,
            code: code,
            newPassword: newPassword
        };
        
        console.log('🔧 Reset Password Request:', requestData);
        
        const response = await fetch(`${API_BASE}/account.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        const data = await response.json();
        
        console.log('📥 Reset Password Response:', data);

        if (data.success) {
            showNotification(data.message, 'success');
            closeModal(resetPasswordModal);
            openModal(loginModal);
            resetPasswordForm.reset();
            resetEmail = '';
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Reset password error:', error);
        showNotification('Có lỗi xảy ra!', 'error');
    }
}

// Open Profile Modal
async function openProfileModal() {
    if (!currentUser) {
        showNotification('Vui lòng đăng nhập!', 'info');
        return;
    }

    openModal(profileModal);

    // Load user data
    try {
        // Load profile info
        const profileResponse = await fetch(`${API_BASE}/account.php?action=getProfile&userId=${currentUser.id}`);
        const profileData = await profileResponse.json();

        if (profileData.success) {
            const user = profileData.user;
            document.getElementById('profileName').value = user.name;
            document.getElementById('profileEmail').value = user.email;
            
            // Format member since date
            const memberSince = new Date(user.created_at);
            document.getElementById('memberSince').textContent = formatDate(memberSince);
        }

        // Load stats
        const statsResponse = await fetch(`${API_BASE}/account.php?action=getStats&userId=${currentUser.id}`);
        const statsData = await statsResponse.json();

        if (statsData.success) {
            document.getElementById('totalChats').textContent = statsData.stats.totalChats;
            document.getElementById('totalMessages').textContent = statsData.stats.totalMessages;
        }

    } catch (error) {
        console.error('Load profile error:', error);
        showNotification('Không thể tải thông tin tài khoản!', 'error');
    }
}

// Handle Update Profile
async function handleUpdateProfile(e) {
    e.preventDefault();

    if (!currentUser) return;

    const name = document.getElementById('profileName').value;

    try {
        const response = await fetch(`${API_BASE}/account.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'updateProfile',
                userId: currentUser.id,
                name: name
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            currentUser.name = name;
            username.textContent = name;
            localStorage.setItem('user', JSON.stringify(currentUser));
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Update profile error:', error);
        showNotification('Có lỗi xảy ra!', 'error');
    }
}

// Handle Change Password
async function handleChangePassword(e) {
    e.preventDefault();

    if (!currentUser) return;

    const currentPassword = document.getElementById('currentPassword').value;
    const newPasswordChange = document.getElementById('newPasswordChange').value;
    const confirmPasswordChange = document.getElementById('confirmPasswordChange').value;

    // Validate passwords match
    if (newPasswordChange !== confirmPasswordChange) {
        showNotification('Mật khẩu xác nhận không khớp!', 'error');
        return;
    }

    if (newPasswordChange.length < 6) {
        showNotification('Mật khẩu mới phải có ít nhất 6 ký tự!', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/account.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'changePassword',
                userId: currentUser.id,
                currentPassword: currentPassword,
                newPassword: newPasswordChange
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            changePasswordForm.reset();
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Change password error:', error);
        showNotification('Có lỗi xảy ra!', 'error');
    }
}

// Handle Delete Account
async function handleDeleteAccount(e) {
    e.preventDefault();

    if (!currentUser) return;

    const password = document.getElementById('deletePassword').value;
    const confirmDelete = document.getElementById('confirmDelete').checked;

    if (!confirmDelete) {
        showNotification('Vui lòng xác nhận bạn hiểu hành động này!', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/account.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'deleteAccount',
                userId: currentUser.id,
                password: password
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');
            
            // Logout after 2 seconds
            setTimeout(() => {
                logout();
                closeModal(deleteAccountModal);
            }, 2000);
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Delete account error:', error);
        showNotification('Có lỗi xảy ra!', 'error');
    }
}

// Load Login History
async function loadLoginHistory() {
    if (!currentUser) return;

    try {
        const response = await fetch(`${API_BASE}/account.php?action=getLoginHistory&userId=${currentUser.id}`);
        const data = await response.json();

        if (data.success) {
            const historyContainer = document.getElementById('loginHistory');
            
            if (data.history.length === 0) {
                historyContainer.innerHTML = '<p style="color: var(--dark-gray); text-align: center;">Chưa có lịch sử đăng nhập</p>';
                return;
            }

            historyContainer.innerHTML = data.history.map(item => {
                const loginDate = new Date(item.login_at);
                return `
                    <div class="login-item">
                        <strong>${formatDateTime(loginDate)}</strong>
                        <span class="login-ip">IP: ${item.ip_address}</span>
                        <span>${truncateText(item.user_agent, 50)}</span>
                    </div>
                `;
            }).join('');
        }
    } catch (error) {
        console.error('Load login history error:', error);
    }
}

// Log Login (call after successful login)
async function logLoginActivity() {
    if (!currentUser) return;

    try {
        await fetch(`${API_BASE}/account.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'logLogin',
                userId: currentUser.id
            })
        });
    } catch (error) {
        console.error('Log login error:', error);
    }
}

// Update handleLogin to include login logging and show profile button
const originalHandleLogin = handleLogin;
async function handleLogin(e) {
    e.preventDefault();
    
    // Call original login logic
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        const response = await fetch(`${API_BASE}/auth.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: 'login',
                email: email,
                password: password
            })
        });

        const data = await response.json();

        if (data.success) {
            currentUser = data.user;
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            
            username.textContent = data.user.name;
            authBtn.innerHTML = '<i class="fas fa-sign-out-alt"></i> Đăng xuất';
            messageInput.disabled = false;
            
            // Show profile button
            profileBtn.style.display = 'flex';
            
            closeModal(loginModal);
            showNotification('Đăng nhập thành công!', 'success');
            
            // Load chat history
            loadChatHistory();
            
            // Log login activity
            logLoginActivity();
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showNotification('Có lỗi xảy ra!', 'error');
    }
}

// Update logout to hide profile button
function logout() {
    currentUser = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    
    username.textContent = 'Khách';
    authBtn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Đăng nhập';
    messageInput.disabled = true;
    
    // Hide profile button
    profileBtn.style.display = 'none';
    
    // Clear chat
    messagesContainer.innerHTML = '';
    welcomeMessage.style.display = 'block';
    historyList.innerHTML = '';
    
    showNotification('Đã đăng xuất!', 'info');
}

// Utility Functions
function formatDateTime(date) {
    return date.toLocaleString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// ============================================
// REPORT MESSAGE FEATURE
// ============================================

// ============================================
// REPORT MESSAGE FEATURE
// ============================================

// Setup Report Modal Listeners
function setupReportModalListeners() {
    if (closeReportModal) {
        closeReportModal.addEventListener('click', () => closeModal(reportModal));
    }
    
    if (cancelReport) {
        cancelReport.addEventListener('click', () => closeModal(reportModal));
    }
    
    if (reportForm) {
        reportForm.addEventListener('submit', handleReportSubmit);
    }
    
    // Close on outside click
    window.addEventListener('click', (e) => {
        if (e.target === reportModal) closeModal(reportModal);
    });
    
    // Limit textarea characters
    const reportDetails = document.getElementById('reportDetails');
    if (reportDetails) {
        reportDetails.addEventListener('input', function() {
            if (this.value.length > 500) {
                this.value = this.value.substring(0, 500);
            }
        });
    }
    
    // === Edit Title Modal Setup ===
    if (closeEditTitleModal) {
        closeEditTitleModal.addEventListener('click', () => closeModal(editTitleModal));
    }
    
    if (cancelEditTitle) {
        cancelEditTitle.addEventListener('click', () => closeModal(editTitleModal));
    }
    
    if (editTitleForm) {
        editTitleForm.addEventListener('submit', handleEditTitleSubmit);
    }
    
    // Close on outside click
    window.addEventListener('click', (e) => {
        if (e.target === editTitleModal) closeModal(editTitleModal);
    });
}

// Open Report Modal
function openReportModal() {
    console.log('openReportModal called');
    console.log('reportModal:', reportModal);
    console.log('selectedMessage:', selectedMessage);
    
    // Reset form
    if (reportForm) {
        reportForm.reset();
    }
    
    // Open modal directly
    openModal(reportModal);
}

// Handle Report Submit
async function handleReportSubmit(e) {
    e.preventDefault();
    
    const reason = document.querySelector('input[name="reportReason"]:checked')?.value;
    const details = document.getElementById('reportDetails').value.trim();
    
    if (!reason) {
        showNotification('Vui lòng chọn lý do báo cáo!', 'error');
        return;
    }
    
    // Get reason text
    const reasonTexts = {
        'inappropriate': 'Nội dung không phù hợp',
        'harmful': 'Thông tin gây hại',
        'false': 'Thông tin sai lệch',
        'offensive': 'Ngôn từ thô tục',
        'spam': 'Spam hoặc quảng cáo',
        'other': 'Lý do khác'
    };
    
    try {
        // Allow guests to report, use userId 0 if not logged in
        const userId = currentUser ? currentUser.id : 0;
        const chatId = currentChatId || null;
        
        const response = await fetch(`${API_BASE}/chat.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
            },
            body: JSON.stringify({
                action: 'reportMessage',
                message: selectedMessage,
                reason: reason,
                reasonText: reasonTexts[reason],
                details: details,
                userId: userId,
                chatId: chatId
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Cảm ơn bạn đã báo cáo! Chúng tôi sẽ xem xét sớm nhất.', 'success');
            closeModal(reportModal);
            reportForm.reset();
            selectedMessage = null;
        } else {
            showNotification(data.message || 'Không thể gửi báo cáo!', 'error');
        }
    } catch (error) {
        console.error('Report error:', error);
        showNotification('Có lỗi xảy ra khi gửi báo cáo!', 'error');
    }
}

// === Edit Title Functions ===
function openEditTitleModal(chatId, currentTitle) {
    currentEditChatId = chatId;
    newTitleInput.value = currentTitle;
    openModal(editTitleModal);
    newTitleInput.focus();
    newTitleInput.select();
}

async function handleEditTitleSubmit(e) {
    e.preventDefault();
    
    if (!currentUser) {
        showNotification('Vui lòng đăng nhập để sửa tiêu đề!', 'error');
        return;
    }
    
    const newTitle = newTitleInput.value.trim();
    
    if (!newTitle) {
        showNotification('Vui lòng nhập tiêu đề mới!', 'error');
        return;
    }
    
    if (newTitle.length > 255) {
        showNotification('Tiêu đề không được quá 255 ký tự!', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/chat.php`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                action: 'updateChatTitle',
                chatId: currentEditChatId,
                userId: currentUser.id,
                title: newTitle
            })
        });

        const data = await response.json();

        if (data.success) {
            const editedChatId = currentEditChatId;
            showNotification('Đã cập nhật tiêu đề!', 'success');
            closeModal(editTitleModal);
            editTitleForm.reset();
            
            // Reload chat history to show new title
            loadChatHistory();
            
            // Update current chat title if this is the active chat
            if (currentChatId === editedChatId) {
                // Update title in UI if needed
                const titleElements = document.querySelectorAll('.chat-title-text');
                titleElements.forEach(el => {
                    if (el.closest('[data-chat-id="' + editedChatId + '"]')) {
                        el.textContent = newTitle;
                    }
                });
            }

            currentEditChatId = null;
        } else {
            showNotification(data.message || 'Không thể cập nhật tiêu đề!', 'error');
        }
    } catch (error) {
        console.error('Edit title error:', error);
        showNotification('Có lỗi xảy ra khi cập nhật tiêu đề!', 'error');
    }
}

