import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from './services/auth.service';
import { ChatService } from './services/chat.service';

import { SidebarComponent } from './components/sidebar/sidebar.component';
import { ChatPaneComponent } from './components/chat-pane/chat-pane.component';
import { LoginModalComponent } from './components/modals/login-modal/login-modal.component';
import { RegisterModalComponent } from './components/modals/register-modal/register-modal.component';
import { ProfileModalComponent } from './components/modals/profile-modal/profile-modal.component';
import { AdminModalComponent } from './components/modals/admin-modal/admin-modal.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule, 
    SidebarComponent, 
    ChatPaneComponent, 
    LoginModalComponent, 
    RegisterModalComponent,
    ProfileModalComponent,
    AdminModalComponent
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class AppComponent implements OnInit {
  title = 'Món ngon Đà Nẵng';
  
  currentUser: any = null;
  
  // Modals state
  showLoginModal = false;
  showRegisterModal = false;
  showProfileModal = false;
  showAdminModal = false;
  
  // Chat state
  chatHistory: any[] = [];
  currentChatId: number = 0;
  messages: any[] = [];
  isLoading = false;

  constructor(
    private authService: AuthService,
    private chatService: ChatService
  ) {}

  ngOnInit() {
    this.authService.currentUser$.subscribe(user => {
      this.currentUser = user;
      if (user) {
        this.loadHistory();
      } else {
        this.chatHistory = [];
        this.messages = [];
        this.currentChatId = 0;
      }
    });
  }

  // --- Auth Methods (Điều phối) ---
  
  openLogin() { this.showLoginModal = true; this.showRegisterModal = false; }
  closeLogin() { this.showLoginModal = false; }
  
  openRegister() {
    this.showLoginModal = false;
    this.showRegisterModal = true;
  }
  
  closeRegister() {
    this.showRegisterModal = false;
  }

  openProfile() {
    this.showProfileModal = true;
  }

  closeProfile() {
    this.showProfileModal = false;
  }

  openAdmin() {
    this.showAdminModal = true;
  }

  closeAdmin() {
    this.showAdminModal = false;
  }
  
  logout() {
    this.authService.logout();
  }

  // --- Chat Methods ---
  
  createNewChat() {
    this.currentChatId = 0;
    this.messages = [];
  }
  
  loadHistory() {
    if (!this.currentUser) return;
    this.chatService.getHistory(this.currentUser.id).subscribe(res => {
      if (res.success) this.chatHistory = res.chats;
    });
  }
  
  loadChat(chatId: number) {
    this.currentChatId = chatId;
    this.chatService.getMessages(chatId).subscribe(res => {
      if (res.success) this.messages = res.messages;
    });
  }

  deleteChat(chatId: number) {
    this.chatService.deleteChat(chatId).subscribe(res => {
      if (res.success) {
        if (this.currentChatId === chatId) {
          this.createNewChat();
        }
        this.loadHistory();
      }
    });
  }

  renameChat(event: {id: number, title: string}) {
    if (!this.currentUser) return;
    this.chatService.renameChat(event.id, event.title, this.currentUser.id).subscribe(res => {
      if (res.success) {
        this.loadHistory();
      }
    });
  }

  pinChat(event: {id: number, isPinned: boolean}) {
    if (!this.currentUser) return;
    this.chatService.pinChat(event.id, event.isPinned, this.currentUser.id).subscribe({
      next: (res) => {
        if (res.success) {
          this.loadHistory();
        }
      },
      error: (err) => {
        alert(err.error?.message || 'Có lỗi xảy ra khi ghim đoạn chat.');
      }
    });
  }
  
  sendMessage(text: string) {
    if (!text.trim()) return;
    if (!this.currentUser) {
      this.openLogin();
      return;
    }
    
    // Add user message optimistically
    const tempUserMsg = { type: 'user', text: text, createdAt: new Date() };
    this.messages.push(tempUserMsg);
    this.isLoading = true;
    
    this.chatService.sendMessage(text, this.currentUser.id, this.currentChatId).subscribe({
      next: (res) => {
        this.isLoading = false;
        if (res.success) {
          if (this.currentChatId === 0) {
            this.currentChatId = res.chatId;
            this.loadHistory();
          }
          // Assign IDs to messages for feedback functionality
          if (res.userMessageId) {
             (tempUserMsg as any).id = res.userMessageId;
          }
          this.messages.push({ 
            id: res.botMessageId,
            type: 'assistant', 
            text: res.response, 
            responseHtml: res.response_html 
          });
        }
      },
      error: () => {
        this.isLoading = false;
        alert('Lỗi khi gửi tin nhắn');
      }
    });
  }
}
