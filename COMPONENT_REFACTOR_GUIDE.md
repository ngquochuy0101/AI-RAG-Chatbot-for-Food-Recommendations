# 📦 Hướng Dẫn Refactor Angular Components

> **Mục tiêu:** Tách `AppComponent` (hiện đang chứa mọi thứ) thành các **Angular Standalone Components** nhỏ, tái sử dụng được, dễ maintain.

---

## 🗺️ Phân Tích Hiện Tại

### Cấu trúc file hiện tại

```
src/app/
├── app.component.html       ← 129 dòng HTML, chứa TẤT CẢ UI
├── app.component.ts         ← 158 dòng TS, chứa TẤT CẢ logic
├── app.component.css        ← chỉ có :host styles
├── app.config.ts
├── app.routes.ts
├── components/              ← ⚠️ ĐANG TRỐNG
└── services/
    ├── auth.service.ts
    └── chat.service.ts
```

### Vấn đề hiện tại

| Vấn đề | Mô tả |
|--------|-------|
| **God Component** | `AppComponent` đang làm quá nhiều việc: layout, auth, chat, modal |
| **Khó test** | Tất cả logic cùng một chỗ → không thể unit test từng phần |
| **Khó mở rộng** | Muốn thêm tính năng phải sửa file duy nhất lớn |
| **Khó đọc** | 129 dòng HTML lẫn lộn nhiều concerns khác nhau |

---

## 🎯 Kiến Trúc Đề Xuất

### Sơ đồ component tree sau khi refactor

```
AppComponent (Shell/Layout only)
├── SidebarComponent           ← Left pane (poster)
│   ├── ChatHistoryComponent   ← Danh sách lịch sử chat
│   └── UserMenuComponent      ← Thông tin user + các nút auth
├── ChatPaneComponent          ← Right pane (ticket)
│   ├── MessagesAreaComponent  ← Khu vực hiển thị tin nhắn
│   │   └── MessageBubbleComponent ← Mỗi tin nhắn (user/bot)
│   └── ChatInputComponent     ← Textarea + nút gửi
└── (Modals — 2 cách xử lý)
    ├── LoginModalComponent
    └── RegisterModalComponent
```

### Cấu trúc thư mục sau refactor

```
src/app/
├── app.component.{html,ts,css}
├── app.config.ts
├── app.routes.ts
├── components/
│   ├── sidebar/
│   │   ├── sidebar.component.{html,ts,css}
│   │   ├── chat-history/
│   │   │   └── chat-history.component.{html,ts,css}
│   │   └── user-menu/
│   │       └── user-menu.component.{html,ts,css}
│   ├── chat-pane/
│   │   ├── chat-pane.component.{html,ts,css}
│   │   ├── messages-area/
│   │   │   ├── messages-area.component.{html,ts,css}
│   │   │   └── message-bubble/
│   │   │       └── message-bubble.component.{html,ts,css}
│   │   └── chat-input/
│   │       └── chat-input.component.{html,ts,css}
│   └── modals/
│       ├── login-modal/
│       │   └── login-modal.component.{html,ts,css}
│       └── register-modal/
│           └── register-modal.component.{html,ts,css}
└── services/
    ├── auth.service.ts
    └── chat.service.ts
```

---

## 📋 Các Components Cần Tạo (Chi Tiết)

---

### 1. `SidebarComponent` — Left Pane

**Generate command:**
```bash
ng generate component components/sidebar --standalone
```

**HTML cần move vào** (từ `app.component.html` dòng 3–36):
```html
<div class="poster-pane">
  <div class="poster-header">...</div>
  <div class="chat-history" *ngIf="currentUser">...</div>
  <div class="poster-footer">...</div>
</div>
```

**Inputs/Outputs cần định nghĩa:**
| Tên | Loại | Mô tả |
|-----|------|--------|
| `currentUser` | `@Input()` | User hiện tại hoặc `null` |
| `chatHistory` | `@Input()` | Mảng các cuộc chat cũ |
| `currentChatId` | `@Input()` | ID chat đang active |
| `onNewChat` | `@Output() EventEmitter` | Khi bấm "+ TÌM MÓN MỚI" |
| `onSelectChat` | `@Output() EventEmitter<number>` | Khi chọn 1 chat trong lịch sử |
| `onLogin` | `@Output() EventEmitter` | Khi bấm "ĐĂNG NHẬP" |
| `onProfile` | `@Output() EventEmitter` | Khi bấm "THÔNG TIN" |
| `onLogout` | `@Output() EventEmitter` | Khi bấm "ĐĂNG XUẤT" |

---

### 2. `ChatHistoryComponent` — Danh sách lịch sử (con của Sidebar)

**Generate command:**
```bash
ng generate component components/sidebar/chat-history --standalone
```

**HTML cần move vào** (từ `app.component.html` dòng 12–19):
```html
<div class="chat-history" *ngIf="currentUser">
  <div class="history-title">Lịch Sử Gọi Món</div>
  <div class="history-list">
    <div *ngFor="let chat of chatHistory" ...>{{chat.title}}</div>
  </div>
</div>
```

**Inputs/Outputs:**
| Tên | Loại | Mô tả |
|-----|------|--------|
| `chatHistory` | `@Input()` | Danh sách chat |
| `currentChatId` | `@Input()` | Chat đang active |
| `onSelectChat` | `@Output() EventEmitter<number>` | Khi chọn chat |

---

### 3. `UserMenuComponent` — Footer của Sidebar

**Generate command:**
```bash
ng generate component components/sidebar/user-menu --standalone
```

**HTML cần move vào** (từ `app.component.html` dòng 21–35):
```html
<div class="poster-footer">
  <div class="user-info">...</div>
  <button *ngIf="!currentUser" ...>ĐĂNG NHẬP</button>
  <button *ngIf="currentUser" ...>THÔNG TIN</button>
  <button *ngIf="currentUser" ...>ĐĂNG XUẤT</button>
</div>
```

**Inputs/Outputs:**
| Tên | Loại | Mô tả |
|-----|------|--------|
| `currentUser` | `@Input()` | User hiện tại hoặc `null` |
| `onLogin` | `@Output() EventEmitter` | Emit khi click đăng nhập |
| `onProfile` | `@Output() EventEmitter` | Emit khi click thông tin |
| `onLogout` | `@Output() EventEmitter` | Emit khi click đăng xuất |

---

### 4. `ChatPaneComponent` — Right Pane

**Generate command:**
```bash
ng generate component components/chat-pane --standalone
```

**HTML cần move vào** (từ `app.component.html` dòng 39–79):
```html
<div class="ticket-pane">
  <div class="chat-container">
    <!-- messages area -->
    <!-- input area -->
  </div>
</div>
```

**Inputs/Outputs:**
| Tên | Loại | Mô tả |
|-----|------|--------|
| `messages` | `@Input()` | Mảng tin nhắn |
| `isLoading` | `@Input()` | Đang chờ AI trả lời |
| `currentUser` | `@Input()` | User hiện tại |
| `onSendMessage` | `@Output() EventEmitter<string>` | Emit text khi user gửi |

---

### 5. `MessagesAreaComponent` — Vùng hiển thị tin nhắn

**Generate command:**
```bash
ng generate component components/chat-pane/messages-area --standalone
```

**HTML cần move vào** (từ `app.component.html` dòng 41–64):
```html
<div class="messages-area">
  <div class="welcome-message" *ngIf="messages.length === 0">...</div>
  <div class="messages">
    <div *ngFor="let msg of messages" ...>...</div>
    <div class="typing-indicator" *ngIf="isLoading">...</div>
  </div>
</div>
```

**Inputs:**
| Tên | Loại | Mô tả |
|-----|------|--------|
| `messages` | `@Input()` | Mảng tin nhắn |
| `isLoading` | `@Input()` | Đang chờ AI |

> **💡 Lưu ý:** Component này cần inject `DomSanitizer` để render `responseHtml`

---

### 6. `MessageBubbleComponent` — Từng tin nhắn

**Generate command:**
```bash
ng generate component components/chat-pane/messages-area/message-bubble --standalone
```

**HTML cần move vào** (từ `app.component.html` dòng 48–57):
```html
<div class="message" [class.user]="msg.type === 'user'" [class.bot]="msg.type === 'assistant'">
  <div class="message-header">{{ msg.type === 'user' ? '[THỰC KHÁCH]' : '[ĐẦU BẾP AI]' }}</div>
  <div class="message-content">
    <div *ngIf="msg.type === 'user'">{{ msg.text }}</div>
    <div *ngIf="msg.type === 'assistant' && !msg.responseHtml">{{ msg.text }}</div>
    <div *ngIf="msg.type === 'assistant' && msg.responseHtml" [innerHTML]="sanitizeHtml(msg.responseHtml)"></div>
  </div>
</div>
```

**Inputs:**
| Tên | Loại | Mô tả |
|-----|------|--------|
| `message` | `@Input()` | Object `{ type, text, responseHtml }` |

---

### 7. `ChatInputComponent` — Textarea + Nút Gửi

**Generate command:**
```bash
ng generate component components/chat-pane/chat-input --standalone
```

**HTML cần move vào** (từ `app.component.html` dòng 67–77):
```html
<div class="input-area">
  <textarea [(ngModel)]="messageInput" placeholder="Ghi chú cho đầu bếp..." rows="2"
    (keyup.enter)="sendMessage()"></textarea>
  <button class="brutal-btn brutal-btn-primary send-btn" (click)="sendMessage()" [disabled]="isLoading">
    GỬI
  </button>
</div>
```

**Inputs/Outputs:**
| Tên | Loại | Mô tả |
|-----|------|--------|
| `isLoading` | `@Input()` | Disable nút gửi khi đang chờ |
| `onSend` | `@Output() EventEmitter<string>` | Emit text khi gửi |

> **💡 Lưu ý:** `messageInput` và `sendMessage()` sẽ là state/logic **nội bộ** của component này.

---

### 8. `LoginModalComponent` — Modal Đăng Nhập

**Generate command:**
```bash
ng generate component components/modals/login-modal --standalone
```

**HTML cần move vào** (từ `app.component.html` dòng 82–102):
```html
<div class="modal" [class.show]="show">
  <div class="modal-content">
    <span class="close" (click)="close()">×</span>
    <h2>Đăng nhập</h2>
    <form (ngSubmit)="login()">...</form>
  </div>
</div>
```

**Inputs/Outputs:**
| Tên | Loại | Mô tả |
|-----|------|--------|
| `show` | `@Input()` | Hiển thị hay ẩn modal |
| `onClose` | `@Output() EventEmitter` | Khi đóng modal |
| `onLoginSuccess` | `@Output() EventEmitter` | Khi đăng nhập thành công |
| `onSwitchToRegister` | `@Output() EventEmitter` | Khi click "Đăng ký ngay" |

> **💡 Lưu ý:** `loginEmail`, `loginPassword`, `login()` là state/logic **nội bộ** của component này. Inject `AuthService` trực tiếp vào đây.

---

### 9. `RegisterModalComponent` — Modal Đăng Ký

**Generate command:**
```bash
ng generate component components/modals/register-modal --standalone
```

**HTML cần move vào** (từ `app.component.html` dòng 104–128):
```html
<div class="modal" [class.show]="show">
  <div class="modal-content">
    ...form đăng ký...
  </div>
</div>
```

**Inputs/Outputs:**
| Tên | Loại | Mô tả |
|-----|------|--------|
| `show` | `@Input()` | Hiển thị hay ẩn modal |
| `onClose` | `@Output() EventEmitter` | Khi đóng modal |
| `onRegisterSuccess` | `@Output() EventEmitter` | Khi đăng ký thành công |
| `onSwitchToLogin` | `@Output() EventEmitter` | Khi click "Đăng nhập" |

---

## 🔄 AppComponent Sau Khi Refactor

Sau khi tách xong, `app.component.html` sẽ chỉ còn khoảng ~20 dòng:

```html
<div class="app-container">
  <app-sidebar
    [currentUser]="currentUser"
    [chatHistory]="chatHistory"
    [currentChatId]="currentChatId"
    (onNewChat)="createNewChat()"
    (onSelectChat)="loadChat($event)"
    (onLogin)="openLogin()"
    (onProfile)="openProfile()"
    (onLogout)="logout()">
  </app-sidebar>

  <app-chat-pane
    [messages]="messages"
    [isLoading]="isLoading"
    [currentUser]="currentUser"
    (onSendMessage)="sendMessage($event)">
  </app-chat-pane>
</div>

<app-login-modal
  [show]="showLoginModal"
  (onClose)="closeLogin()"
  (onLoginSuccess)="closeLogin()"
  (onSwitchToRegister)="openRegister()">
</app-login-modal>

<app-register-modal
  [show]="showRegisterModal"
  (onClose)="closeRegister()"
  (onRegisterSuccess)="openLogin()"
  (onSwitchToLogin)="openLogin()">
</app-register-modal>
```

---

## ⚡ Logic Cần Di Chuyển Từ `app.component.ts`

| Logic hiện tại | Di chuyển đến |
|----------------|---------------|
| `showLoginModal`, `showRegisterModal`, `openLogin()`, `closeLogin()`, `openRegister()`, `closeRegister()` | Giữ lại ở `AppComponent` (điều phối modal) |
| `loginEmail`, `loginPassword`, `login()` | `LoginModalComponent` (inject `AuthService`) |
| `registerName`, `registerEmail`, `registerPassword`, `register()` | `RegisterModalComponent` (inject `AuthService`) |
| `messageInput`, nút gửi | `ChatInputComponent` |
| `sanitizeHtml()` | `MessageBubbleComponent` (inject `DomSanitizer`) |
| `chatHistory`, `currentChatId`, `loadHistory()`, `loadChat()` | Giữ ở `AppComponent` hoặc move vào `SidebarComponent` |
| `messages`, `isLoading`, `sendMessage()` | Giữ ở `AppComponent` (emit xuống `ChatPaneComponent`) |
| `currentUser$` subscription, `logout()` | Giữ ở `AppComponent` |

---

## 📝 Thứ Tự Thực Hiện (Khuyến Nghị)

Để tránh lỗi khi refactor, hãy làm theo thứ tự từ **lá** lên **gốc**:

```
Bước 1: MessageBubbleComponent    (không có component con)
Bước 2: MessagesAreaComponent     (dùng MessageBubbleComponent)
Bước 3: ChatInputComponent        (không có component con)
Bước 4: ChatHistoryComponent      (không có component con)
Bước 5: UserMenuComponent         (không có component con)
Bước 6: ChatPaneComponent         (dùng MessagesArea + ChatInput)
Bước 7: SidebarComponent          (dùng ChatHistory + UserMenu)
Bước 8: LoginModalComponent       (không có component con)
Bước 9: RegisterModalComponent    (không có component con)
Bước 10: Cập nhật AppComponent    (dùng tất cả components trên)
```

---

## 🛠️ CSS — Cách Xử Lý Styles

Hiện tại tất cả CSS nằm ở `src/assets/css/style.css` và được import global qua `styles.css`.

**Có 2 lựa chọn:**

### Lựa chọn A: Giữ nguyên (Đơn giản, khuyến nghị trước)
- Không cần di chuyển CSS
- Mỗi component dùng `ViewEncapsulation.None` (như hiện tại)
- CSS global tiếp tục hoạt động

### Lựa chọn B: Di chuyển CSS vào từng component (Tốt hơn về lâu dài)
- Mỗi component có file `.css` riêng
- Chỉ chứa CSS liên quan đến component đó
- Dùng `ViewEncapsulation.Emulated` (default)
- Cần thêm `:host` wrapper nếu cần

**Ví dụ mapping CSS → Component:**

| CSS Class | Di chuyển vào |
|-----------|---------------|
| `.poster-pane`, `.poster-header`, `.poster-footer` | `sidebar.component.css` |
| `.chat-history`, `.history-title`, `.history-item` | `chat-history.component.css` |
| `.user-info` | `user-menu.component.css` |
| `.ticket-pane`, `.chat-container` | `chat-pane.component.css` |
| `.messages-area`, `.welcome-message`, `.message`, `.message-header`, `.message-content`, `.typing-indicator` | `messages-area.component.css` |
| `.input-area`, `textarea`, `.send-btn` | `chat-input.component.css` |
| `.modal`, `.modal-content`, `.close`, `.form-group`, `.switch-auth` | `login-modal.component.css` + `register-modal.component.css` |
| `.brutal-btn*`, `.mono`, scrollbar | Giữ global trong `styles.css` |

---

## ✅ Checklist Kiểm Tra Sau Refactor

```
[ ] npm start không có lỗi compile
[ ] Giao diện trông giống hệt trước khi refactor
[ ] Đăng nhập / đăng ký hoạt động
[ ] Gửi tin nhắn hoạt động
[ ] Lịch sử chat hiển thị và click được
[ ] Responsive mobile vẫn hoạt động
[ ] Không còn logic nào bị duplicate giữa các components
```

---

## 🚨 Các Lỗi Thường Gặp

| Lỗi | Nguyên nhân | Giải pháp |
|-----|-------------|-----------|
| `Can't bind to 'ngModel'` | Thiếu `FormsModule` trong imports | Thêm `FormsModule` vào `imports[]` của component |
| `CommonModule` not found | Thiếu import | Thêm `CommonModule` vào `imports[]` |
| CSS không áp dụng | `ViewEncapsulation.Emulated` không match selector | Dùng `ViewEncapsulation.None` hoặc `:host` |
| Output không trigger | Dùng sai tên event binding | Kiểm tra tên `@Output()` và `(eventName)` trong template |
| `HttpClient` not provided | Thiếu provider | Đảm bảo `provideHttpClient()` trong `app.config.ts` |
