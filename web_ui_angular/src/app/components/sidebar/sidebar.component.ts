import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatHistoryComponent } from './chat-history/chat-history.component';
import { UserMenuComponent } from './user-menu/user-menu.component';

@Component({
  selector: 'app-sidebar',
  imports: [CommonModule, ChatHistoryComponent, UserMenuComponent],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.css'
})
export class SidebarComponent {
  @Input() currentUser: any = null;
  @Input() chatHistory: any[] = [];
  @Input() currentChatId: number = 0;
  
  @Output() onNewChat = new EventEmitter<void>();
  @Output() onSelectChat = new EventEmitter<number>();
  @Output() onDeleteChat = new EventEmitter<number>();
  @Output() onRenameChat = new EventEmitter<{id: number, title: string}>();
  @Output() onPinChat = new EventEmitter<{id: number, isPinned: boolean}>();
  @Output() onLogin = new EventEmitter<void>();
  @Output() onProfile = new EventEmitter<void>();
  @Output() onAdmin = new EventEmitter<void>();
  @Output() onLogout = new EventEmitter<void>();
}
