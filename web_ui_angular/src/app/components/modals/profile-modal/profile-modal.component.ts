import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../services/auth.service';

@Component({
  selector: 'app-profile-modal',
  imports: [CommonModule, FormsModule],
  templateUrl: './profile-modal.component.html',
  styleUrl: './profile-modal.component.css'
})
export class ProfileModalComponent {
  @Input() show = false;
  @Input() user: any = null;
  @Output() onClose = new EventEmitter<void>();

  name = '';
  oldPassword = '';
  newPassword = '';
  error = '';
  success = '';

  constructor(private authService: AuthService) {}

  ngOnChanges() {
    if (this.show && this.user) {
      this.name = this.user.name || '';
      this.oldPassword = '';
      this.newPassword = '';
      this.error = '';
      this.success = '';
    }
  }

  save() {
    this.error = '';
    this.success = '';
    
    if (!this.name.trim()) {
      this.error = 'Tên không được để trống';
      return;
    }

    const payload = {
      name: this.name,
      oldPassword: this.oldPassword,
      newPassword: this.newPassword
    };

    this.authService.updateProfile(payload).subscribe({
      next: (res) => {
        if (res.success) {
          this.success = 'Cập nhật thành công!';
          setTimeout(() => this.onClose.emit(), 1500);
        } else {
          this.error = res.message;
        }
      },
      error: (err) => {
        this.error = err.error?.message || 'Có lỗi xảy ra';
      }
    });
  }
}
