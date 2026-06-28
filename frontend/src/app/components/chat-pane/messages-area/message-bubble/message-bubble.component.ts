import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ChatService } from '../../../../services/chat.service';

@Component({
  selector: 'app-message-bubble',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './message-bubble.component.html',
  styleUrls: ['./message-bubble.component.css']
})
export class MessageBubbleComponent {
  @Input() message: any;

  constructor(private sanitizer: DomSanitizer, private chatService: ChatService) {}

  sanitizeHtml(html: string): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }

  onFeedback(isLiked: boolean) {
    if (this.message.type !== 'assistant') return;
    
    // Toggle if same button clicked
    const newValue = this.message.isLiked === isLiked ? null : isLiked;
    
    this.chatService.feedbackMessage(this.message.id, newValue).subscribe({
      next: (res: any) => {
        if (res.success) {
          this.message.isLiked = newValue;
        }
      },
      error: (err: any) => {
        alert('Có lỗi khi gửi phản hồi.');
      }
    });
  }
}
