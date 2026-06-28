import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-chat-input',
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-input.component.html',
  styleUrl: './chat-input.component.css'
})
export class ChatInputComponent {
  @Input() isLoading: boolean = false;
  @Output() onSend = new EventEmitter<string>();

  messageInput: string = '';

  sendMessage() {
    if (this.isLoading) return;
    if (!this.messageInput.trim()) return;
    
    this.onSend.emit(this.messageInput);
    this.messageInput = '';
  }
}
