import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../services/auth.service';

@Component({
  selector: 'app-register-modal',
  imports: [CommonModule, FormsModule],
  templateUrl: './register-modal.component.html',
  styleUrl: './register-modal.component.css'
})
export class RegisterModalComponent {
  @Input() show: boolean = false;
  
  @Output() onClose = new EventEmitter<void>();
  @Output() onRegisterSuccess = new EventEmitter<void>();
  @Output() onSwitchToLogin = new EventEmitter<void>();
  
  registerName = '';
  registerEmail = '';
  registerPassword = '';
  
  constructor(private authService: AuthService) {}
  
  register() {
    this.authService.register({ 
      name: this.registerName, 
      email: this.registerEmail, 
      password: this.registerPassword 
    }).subscribe({
      next: (res: any) => {
        if (res.success) {
          alert('Đăng ký thành công, vui lòng đăng nhập');
          this.onRegisterSuccess.emit();
          this.registerName = '';
          this.registerEmail = '';
          this.registerPassword = '';
        } else {
          alert(res.message);
        }
      },
      error: () => alert('Đăng ký thất bại')
    });
  }
}
