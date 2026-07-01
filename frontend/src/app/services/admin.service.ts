import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface AdminUser {
  id: number;
  name: string;
  email: string;
  createdAt: Date;
  totalChats: number;
  totalMessages: number;
}

export interface AdminFeedback {
  id: number;
  chatId: number;
  chatTitle: string;
  userId: number;
  userEmail: string;
  userPrompt: string;
  botResponse: string;
  isLiked: boolean;
  createdAt: Date;
}

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  private apiUrl = 'http://localhost:5200/api/Admin';

  constructor(private http: HttpClient) { }

  private getHeaders() {
    const token = localStorage.getItem('token');
    return {
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      })
    };
  }

  getUsers(): Observable<{success: boolean, users: AdminUser[]}> {
    return this.http.get<{success: boolean, users: AdminUser[]}>(`${this.apiUrl}/users?t=${new Date().getTime()}`, this.getHeaders());
  }

  getFeedbacks(): Observable<{success: boolean, feedbacks: AdminFeedback[]}> {
    return this.http.get<{success: boolean, feedbacks: AdminFeedback[]}>(`${this.apiUrl}/feedbacks?t=${new Date().getTime()}`, this.getHeaders());
  }
}
