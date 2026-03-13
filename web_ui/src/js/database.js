// Database simulation using LocalStorage
class Database {
    constructor() {
        this.initializeDatabase();
    }

    initializeDatabase() {
        // Initialize default data if not exists
        if (!localStorage.getItem('ocean_chat_users')) {
            const defaultUsers = [
                {
                    id: 1,
                    name: 'Admin',
                    email: 'admin@oceanchat.com',
                    password: this.hashPassword('password'),
                    created_at: new Date().toISOString(),
                    last_login: null
                }
            ];
            localStorage.setItem('ocean_chat_users', JSON.stringify(defaultUsers));
        }

        if (!localStorage.getItem('ocean_chat_chats')) {
            localStorage.setItem('ocean_chat_chats', JSON.stringify([]));
        }

        if (!localStorage.getItem('ocean_chat_messages')) {
            localStorage.setItem('ocean_chat_messages', JSON.stringify([]));
        }

        if (!localStorage.getItem('ocean_chat_reports')) {
            localStorage.setItem('ocean_chat_reports', JSON.stringify([]));
        }

        if (!localStorage.getItem('ocean_chat_user_id_counter')) {
            localStorage.setItem('ocean_chat_user_id_counter', '2');
        }

        if (!localStorage.getItem('ocean_chat_chat_id_counter')) {
            localStorage.setItem('ocean_chat_chat_id_counter', '1');
        }

        if (!localStorage.getItem('ocean_chat_message_id_counter')) {
            localStorage.setItem('ocean_chat_message_id_counter', '1');
        }

        if (!localStorage.getItem('ocean_chat_report_id_counter')) {
            localStorage.setItem('ocean_chat_report_id_counter', '1');
        }
    }

    // Simple hash function (for demo purposes - in production use bcrypt)
    hashPassword(password) {
        let hash = 0;
        for (let i = 0; i < password.length; i++) {
            const char = password.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return hash.toString();
    }

    verifyPassword(password, hash) {
        return this.hashPassword(password) === hash;
    }

    generateId(counterKey) {
        const currentId = parseInt(localStorage.getItem(counterKey));
        localStorage.setItem(counterKey, (currentId + 1).toString());
        return currentId;
    }

    // Users
    getUsers() {
        return JSON.parse(localStorage.getItem('ocean_chat_users') || '[]');
    }

    saveUsers(users) {
        localStorage.setItem('ocean_chat_users', JSON.stringify(users));
    }

    findUserByEmail(email) {
        const users = this.getUsers();
        return users.find(user => user.email === email);
    }

    findUserById(id) {
        const users = this.getUsers();
        return users.find(user => user.id === id);
    }

    createUser(name, email, password) {
        const users = this.getUsers();
        
        // Check if email exists
        if (this.findUserByEmail(email)) {
            return { success: false, message: 'Email đã tồn tại!' };
        }

        const newUser = {
            id: this.generateId('ocean_chat_user_id_counter'),
            name: name,
            email: email,
            password: this.hashPassword(password),
            created_at: new Date().toISOString(),
            last_login: null
        };

        users.push(newUser);
        this.saveUsers(users);

        return { success: true, user: newUser };
    }

    updateLastLogin(userId) {
        const users = this.getUsers();
        const user = users.find(u => u.id === userId);
        if (user) {
            user.last_login = new Date().toISOString();
            this.saveUsers(users);
        }
    }

    // Chats
    getChats() {
        return JSON.parse(localStorage.getItem('ocean_chat_chats') || '[]');
    }

    saveChats(chats) {
        localStorage.setItem('ocean_chat_chats', JSON.stringify(chats));
    }

    getUserChats(userId) {
        const chats = this.getChats();
        return chats.filter(chat => chat.user_id === userId);
    }

    createChat(userId, title) {
        const chats = this.getChats();
        
        const newChat = {
            id: this.generateId('ocean_chat_chat_id_counter'),
            user_id: userId,
            title: title,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        };

        chats.push(newChat);
        this.saveChats(chats);

        return newChat;
    }

    updateChat(chatId) {
        const chats = this.getChats();
        const chat = chats.find(c => c.id === chatId);
        if (chat) {
            chat.updated_at = new Date().toISOString();
            this.saveChats(chats);
        }
    }

    // Messages
    getMessages() {
        return JSON.parse(localStorage.getItem('ocean_chat_messages') || '[]');
    }

    saveMessages(messages) {
        localStorage.setItem('ocean_chat_messages', JSON.stringify(messages));
    }

    getChatMessages(chatId) {
        const messages = this.getMessages();
        return messages.filter(msg => msg.chat_id === chatId);
    }

    createMessage(chatId, type, message) {
        const messages = this.getMessages();
        
        const newMessage = {
            id: this.generateId('ocean_chat_message_id_counter'),
            chat_id: chatId,
            type: type,
            message: message,
            created_at: new Date().toISOString()
        };

        messages.push(newMessage);
        this.saveMessages(messages);

        return newMessage;
    }

    // Reports
    getReports() {
        return JSON.parse(localStorage.getItem('ocean_chat_reports') || '[]');
    }

    saveReports(reports) {
        localStorage.setItem('ocean_chat_reports', JSON.stringify(reports));
    }

    createReport(userId, chatId, message) {
        const reports = this.getReports();
        
        const newReport = {
            id: this.generateId('ocean_chat_report_id_counter'),
            user_id: userId,
            chat_id: chatId,
            message: message,
            status: 'pending',
            created_at: new Date().toISOString()
        };

        reports.push(newReport);
        this.saveReports(reports);

        return newReport;
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Database;
}
