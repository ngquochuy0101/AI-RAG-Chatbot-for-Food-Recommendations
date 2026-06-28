import { Component, Input, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MessageBubbleComponent } from './message-bubble/message-bubble.component';

@Component({
  selector: 'app-messages-area',
  imports: [CommonModule, MessageBubbleComponent],
  templateUrl: './messages-area.component.html',
  styleUrls: ['./messages-area.component.css']
})
export class MessagesAreaComponent implements AfterViewChecked {
  @Input() messages: any[] = [];
  @Input() isLoading: boolean = false;
  
  @ViewChild('scrollContainer') private scrollContainer!: ElementRef;

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    try {
      this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
    } catch(err) { }
  }
}
