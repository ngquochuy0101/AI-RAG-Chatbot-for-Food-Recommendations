import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MessagesAreaComponent } from './messages-area/messages-area.component';
import { ChatInputComponent } from './chat-input/chat-input.component';

@Component({
  selector: 'app-chat-pane',
  imports: [CommonModule, MessagesAreaComponent, ChatInputComponent],
  templateUrl: './chat-pane.component.html',
  styleUrl: './chat-pane.component.css'
})
export class ChatPaneComponent {
  @Input() messages: any[] = [];
  @Input() isLoading: boolean = false;
  @Input() currentUser: any = null;
  
  @Output() onSendMessage = new EventEmitter<string>();
  @Output() onSendSpeech = new EventEmitter<Blob>();
}
