import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private apiUrl = 'http://localhost:5200/api/Chat';

  constructor(private http: HttpClient, private authService: AuthService) { }

  private getHeaders() {
    const token = localStorage.getItem('token');
    return {
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      })
    };
  }

  getHistory(userId: number): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/history/${userId}`, this.getHeaders());
  }

  getMessages(chatId: number): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/messages/${chatId}`, this.getHeaders());
  }

  sendMessage(message: string, userId: number, chatId: number): Observable<any> {
    const payload = { message, userId, chatId };
    return this.http.post<any>(`${this.apiUrl}/sendMessage`, payload, this.getHeaders());
  }

  sendSpeech(audioBlob: Blob, userId: number, chatId: number): Observable<any> {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'voice.webm');
    formData.append('userId', userId.toString());
    formData.append('chatId', chatId.toString());

    const token = localStorage.getItem('token');
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
    return this.http.post<any>(`${this.apiUrl}/sendSpeech`, formData, { headers });
  }

  deleteChat(chatId: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/${chatId}`, this.getHeaders());
  }

  renameChat(chatId: number, title: string, userId: number): Observable<any> {
    const payload = { chatId, userId, title };
    return this.http.put<any>(`${this.apiUrl}/${chatId}/rename`, payload, this.getHeaders());
  }

  pinChat(chatId: number, isPinned: boolean, userId: number): Observable<any> {
    const payload = { chatId, userId, isPinned };
    return this.http.put<any>(`${this.apiUrl}/${chatId}/pin`, payload, this.getHeaders());
  }

  feedbackMessage(messageId: number, isLiked: boolean | null): Observable<any> {
    const payload = { isLiked };
    return this.http.put<any>(`${this.apiUrl}/message/${messageId}/feedback`, payload, this.getHeaders());
  }
}
