import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../services/auth.service';

@Component({
  selector: 'app-forgot-password-modal',
  imports: [CommonModule, FormsModule],
  templateUrl: './forgot-password-modal.component.html',
  styleUrl: './forgot-password-modal.component.css'
})
export class ForgotPasswordModalComponent {
  @Input() show: boolean = false;
  
  @Output() onClose = new EventEmitter<void>();
  @Output() onSwitchToLogin = new EventEmitter<void>();
  @Output() onSuccess = new EventEmitter<string>();
  
  email = '';
  isLoading = false;
  message = '';
  isError = false;
  otpSent = false;
  
  constructor(private authService: AuthService) {}
  
  requestReset() {
    if (!this.email.trim()) {
      this.showMessage('Vui lòng nhập email', true);
      return;
    }
    
    this.isLoading = true;
    this.message = '';
    
    this.authService.forgotPassword(this.email).subscribe({
      next: (res: any) => {
        this.isLoading = false;
        if (res.success) {
          this.showMessage('Mã xác nhận đã được tạo. Kiểm tra console để xem mã OTP (dev mode).', false);
          // In dev mode, show the reset code
          if (res.resetCode) {
            this.message += `\nMã OTP (dev): ${res.resetCode}`;
          }
          this.otpSent = true;
        } else {
          this.showMessage(res.message || 'Có lỗi xảy ra', true);
        }
      },
      error: (err) => {
        this.isLoading = false;
        this.showMessage(err.error?.message || 'Có lỗi xảy ra khi gửi yêu cầu', true);
      }
    });
  }
  
  private showMessage(msg: string, error: boolean) {
    this.message = msg;
    this.isError = error;
  }

  continueToReset() {
    this.onSuccess.emit(this.email);
  }
  
  goToLogin() {
    this.email = '';
    this.message = '';
    this.onSwitchToLogin.emit();
  }
  
  ngOnChanges() {
    if (!this.show) {
      this.email = '';
      this.message = '';
      this.isError = false;
      this.otpSent = false;
    }
  }
}