import { Component, EventEmitter, Input, Output, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdminService, AdminUser, AdminFeedback } from '../../../services/admin.service';
import Chart from 'chart.js/auto';

@Component({
  selector: 'app-admin-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin-modal.component.html',
  styleUrl: './admin-modal.component.css'
})
export class AdminModalComponent implements OnInit {
  @Input() show: boolean = false;
  @Output() onClose = new EventEmitter<void>();

  activeTab: 'users' | 'feedbacks' = 'users';
  
  users: AdminUser[] = [];
  feedbacks: AdminFeedback[] = [];
  isLoading: boolean = false;

  chart: any;

  constructor(private adminService: AdminService) {}

  ngOnInit() {
  }

  ngOnChanges() {
    if (this.show) {
      this.loadData();
    }
  }

  loadData() {
    this.isLoading = true;
    if (this.activeTab === 'users') {
      this.adminService.getUsers().subscribe({
        next: (res) => {
          if (res.success) this.users = res.users;
          this.isLoading = false;
        },
        error: () => this.isLoading = false
      });
    } else {
      this.adminService.getFeedbacks().subscribe({
        next: (res) => {
          if (res.success) {
            this.feedbacks = res.feedbacks;
            setTimeout(() => this.renderChart(), 50);
          }
          this.isLoading = false;
        },
        error: () => this.isLoading = false
      });
    }
  }

  switchTab(tab: 'users' | 'feedbacks') {
    this.activeTab = tab;
    this.loadData();
  }

  exportUsersCsv() {
    const headers = ['ID', 'Tên', 'Email', 'Ngày Tham Gia', 'Số Cuộc Trò Chuyện', 'Tổng Tin Nhắn'];
    const rows = this.users.map(u => [
      u.id, 
      `"${u.name}"`, 
      u.email, 
      new Date(u.createdAt).toLocaleString(), 
      u.totalChats, 
      u.totalMessages
    ]);
    this.downloadCsv('users_export.csv', headers, rows);
  }

  exportFeedbacksCsv() {
    const headers = ['Chat ID', 'User ID', 'Câu Hỏi', 'Phản Hồi (AI)', 'Đánh Giá', 'Thời Gian'];
    const rows = this.feedbacks.map(f => [
      f.chatId, 
      f.userId, 
      `"${f.userPrompt?.replace(/"/g, '""') || ''}"`, 
      `"${f.botResponse?.replace(/"/g, '""') || ''}"`, 
      f.isLiked ? 'Thích' : 'Không Thích', 
      new Date(f.createdAt).toLocaleString()
    ]);
    this.downloadCsv('feedbacks_export.csv', headers, rows);
  }

  private downloadCsv(filename: string, headers: string[], rows: any[][]) {
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');
    
    // Add BOM for UTF-8 Excel support
    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  renderChart() {
    if (this.chart) {
      this.chart.destroy();
    }
    
    const canvas = document.getElementById('feedbackChart') as HTMLCanvasElement;
    if (!canvas) return;

    // Group feedbacks by date
    const countsByDate: { [key: string]: { likes: number, dislikes: number } } = {};
    
    // Sort ascending by date
    const sortedFeedbacks = [...this.feedbacks].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());

    sortedFeedbacks.forEach(f => {
      const dateStr = new Date(f.createdAt).toLocaleDateString('vi-VN');
      if (!countsByDate[dateStr]) {
        countsByDate[dateStr] = { likes: 0, dislikes: 0 };
      }
      if (f.isLiked) {
        countsByDate[dateStr].likes++;
      } else {
        countsByDate[dateStr].dislikes++;
      }
    });

    const labels = Object.keys(countsByDate);
    const likeData = labels.map(l => countsByDate[l].likes);
    const dislikeData = labels.map(l => countsByDate[l].dislikes);

    this.chart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Thích',
            data: likeData,
            borderColor: '#185635',
            backgroundColor: 'rgba(24, 86, 53, 0.2)',
            tension: 0.3,
            fill: true
          },
          {
            label: 'Không Thích',
            data: dislikeData,
            borderColor: '#E63A3A',
            backgroundColor: 'rgba(230, 58, 58, 0.2)',
            tension: 0.3,
            fill: true
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: {
            display: true,
            text: 'Biểu đồ phản hồi theo thời gian',
            font: {
              family: "'DM Sans', sans-serif",
              size: 16
            }
          }
        }
      }
    });
  }
}
