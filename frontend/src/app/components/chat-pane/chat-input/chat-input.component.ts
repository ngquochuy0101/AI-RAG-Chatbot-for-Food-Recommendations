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
  @Output() onSendSpeech = new EventEmitter<Blob>();

  messageInput: string = '';
  isRecording = false;
  mediaRecorder: MediaRecorder | null = null;
  audioChunks: Blob[] = [];

  sendMessage() {
    if (this.isLoading) return;
    if (!this.messageInput.trim()) return;
    
    this.onSend.emit(this.messageInput);
    this.messageInput = '';
  }

  async startRecording() {
    if (this.isLoading) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream);
      this.audioChunks = [];

      this.mediaRecorder.addEventListener('dataavailable', event => {
        this.audioChunks.push(event.data);
      });

      this.mediaRecorder.addEventListener('stop', () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.onSendSpeech.emit(audioBlob);
        
        // Dọn dẹp stream để tắt mic
        stream.getTracks().forEach(track => track.stop());
      });

      this.isRecording = true;
      this.mediaRecorder.start();
    } catch (err) {
      console.error('Lỗi khi truy cập Microphone:', err);
      alert('Không thể truy cập Microphone. Vui lòng cấp quyền trong trình duyệt.');
    }
  }

  stopRecording() {
    if (this.mediaRecorder && this.isRecording) {
      this.isRecording = false;
      this.mediaRecorder.stop();
    }
  }
}
