import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-user-menu',
  imports: [CommonModule],
  templateUrl: './user-menu.component.html',
  styleUrl: './user-menu.component.css'
})
export class UserMenuComponent {
  @Input() currentUser: any = null;
  
  @Output() onLogin = new EventEmitter<void>();
  @Output() onProfile = new EventEmitter<void>();
  @Output() onAdmin = new EventEmitter<void>();
  @Output() onLogout = new EventEmitter<void>();
}
