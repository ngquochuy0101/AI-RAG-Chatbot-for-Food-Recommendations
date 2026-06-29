import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../services/auth.service';

@Component({
  selector: 'app-reset-password-modal',
  imports: [CommonModule, FormsModule],
  templateUrl: './reset-password-modal.component.html',
  styleUrl: './reset-password-modal.component.css'
})
export class ResetPasswordModalComponent {
  @Input() show: boolean = false;
  @Input() email: string = '';
  
  @Output() onClose = new EventEmitter<void>();
  @Output() onSwitchToLogin = new EventEmitter<void>();
  
  code = '';
  newPassword = '';
  confirmPassword = '';
  isLoading = false;
  message = '';
  isError = false;
  
  constructor(private authService: AuthService) {}
  
  resetPassword() {
    if (!this.code.trim()) {
      this.showMessage('Vui lòng nhập mã OTP', true);
      return;
    }
    
    if (!this.newPassword) {
      this.showMessage('Vui lòng nhập mật khẩu mới', true);
      return;
    }
    
    if (this.newPassword !== this.confirmPassword) {
      this.showMessage('Mật khẩu xác nhận không khớp', true);
      return;
    }
    
    if (this.newPassword.length < 6) {
      this.showMessage('Mật khẩu phải có ít nhất 6 ký tự', true);
      return;
    }
    
    this.isLoading = true;
    this.message = '';
    
    this.authService.resetPassword({
      email: this.email,
      code: this.code,
      newPassword: this.newPassword
    }).subscribe({
      next: (res: any) => {
        this.isLoading = false;
        if (res.success) {
          this.showMessage('Đặt lại mật khẩu thành công! Chuyển về đăng nhập...', false);
          setTimeout(() => {
            this.onSwitchToLogin.emit();
          }, 1500);
        } else {
          this.showMessage(res.message || 'Có lỗi xảy ra', true);
        }
      },
      error: (err) => {
        this.isLoading = false;
        this.showMessage(err.error?.message || 'Có lỗi xảy ra khi đặt lại mật khẩu', true);
      }
    });
  }
  
  private showMessage(msg: string, error: boolean) {
    this.message = msg;
    this.isError = error;
  }
  
  goToLogin() {
    this.code = '';
    this.newPassword = '';
    this.confirmPassword = '';
    this.message = '';
    this.onSwitchToLogin.emit();
  }
  
  ngOnChanges() {
    if (!this.show) {
      this.code = '';
      this.newPassword = '';
      this.confirmPassword = '';
      this.message = '';
      this.isError = false;
    }
  }
}