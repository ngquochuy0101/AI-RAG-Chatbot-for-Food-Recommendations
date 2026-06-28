import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../services/auth.service';

@Component({
  selector: 'app-login-modal',
  imports: [CommonModule, FormsModule],
  templateUrl: './login-modal.component.html',
  styleUrl: './login-modal.component.css'
})
export class LoginModalComponent {
  @Input() show: boolean = false;
  
  @Output() onClose = new EventEmitter<void>();
  @Output() onLoginSuccess = new EventEmitter<void>();
  @Output() onSwitchToRegister = new EventEmitter<void>();
  
  loginEmail = '';
  loginPassword = '';
  
  constructor(private authService: AuthService) {}
  
  login() {
    this.authService.login({ email: this.loginEmail, password: this.loginPassword }).subscribe({
      next: (res: any) => {
        if (res.success) {
          this.onLoginSuccess.emit();
          this.loginEmail = '';
          this.loginPassword = '';
        } else {
          alert(res.message);
        }
      },
      error: () => alert('Đăng nhập thất bại')
    });
  }
}
