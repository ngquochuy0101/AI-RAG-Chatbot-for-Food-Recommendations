import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-chat-history',
  imports: [CommonModule],
  templateUrl: './chat-history.component.html',
  styleUrl: './chat-history.component.css'
})
export class ChatHistoryComponent {
  @Input() currentUser: any = null;
  @Input() chatHistory: any[] = [];
  @Input() currentChatId: number = 0;
  
  @Output() onSelectChat = new EventEmitter<number>();
  @Output() onDelete = new EventEmitter<number>();
  @Output() onRename = new EventEmitter<{id: number, title: string}>();
  @Output() onPin = new EventEmitter<{id: number, isPinned: boolean}>();

  editingChatId: number | null = null;

  togglePin(event: Event, chat: any) {
    event.stopPropagation();
    this.onPin.emit({ id: chat.id, isPinned: !chat.isPinned });
  }

  onDeleteChat(event: Event, chatId: number) {
    event.stopPropagation();
    if (confirm('Bạn có chắc chắn muốn xóa đoạn chat này không?')) {
      this.onDelete.emit(chatId);
    }
  }

  startRename(event: Event, chatId: number) {
    event.stopPropagation();
    this.editingChatId = chatId;
    // Let Angular render the input first, then we can focus it.
    // Focusing is handled natively or user clicks.
  }

  saveRename(chatId: number, event: any) {
    const newTitle = event.target.value.trim();
    if (newTitle) {
      this.onRename.emit({ id: chatId, title: newTitle });
    }
    this.editingChatId = null;
  }

  cancelRename() {
    this.editingChatId = null;
  }
}
