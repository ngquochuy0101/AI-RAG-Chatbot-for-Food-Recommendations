# 📖 Backend .NET API - Documentation

> Backend cho hệ thống **AI RAG Chatbot for Food Recommendations**.  
> Được viết lại hoàn toàn từ PHP sang **.NET 10 (C#) Web API** kết hợp **Entity Framework Core (Code First)**.

---

## 📁 Cấu trúc thư mục

```
AI-RAG-Chatbot-for-Food-Recommendations/
├── Controllers/
│   ├── AuthController.cs     # Xử lý Đăng ký / Đăng nhập
│   ├── AccountController.cs  # Quản lý tài khoản, Profile, Forgot Password
│   └── ChatController.cs     # Xử lý tin nhắn, lịch sử chat, liên kết AI
├── DTOs/                     # Data Transfer Objects (Request/Response models)
├── Models/
│   ├── ChatbotDbContext.cs   # EF Core DbContext
│   └── (User, Chat, Message...) # Các Entities Code First
├── Services/
│   └── AiIntegrationService.cs # HttpClient gọi sang Python FastAPI
├── appsettings.json          # Cấu hình Database & JWT
└── Program.cs                # Entry point, cấu hình DI, CORS, JWT
```

---

## 🚀 Công nghệ sử dụng

1. **.NET 9/10 Web API**: Framework backend tốc độ cao, strongly-typed.
2. **Entity Framework Core (Code First)**: Quản lý Database MySQL bằng C# Models và Migrations, không cần viết script SQL thủ công. Thư viện sử dụng: `Pomelo.EntityFrameworkCore.MySql`.
3. **JWT (JSON Web Token)**: Xác thực người dùng, bảo mật API.
4. **BCrypt.Net-Next**: Băm và bảo mật mật khẩu.
5. **HttpClient**: Tích hợp với hệ thống AI viết bằng Python.

## Cấu hình Database

- Thay vì chạy file `database.sql`, hệ thống sử dụng **EF Core Code First**.
- Lệnh chạy: `dotnet ef migrations add InitialCreate` và `dotnet ef database update`.

## Cách chạy

```bash
dotnet build
dotnet run
```
API sẽ lắng nghe tại `http://localhost:5247/api` (hoặc HTTPS).
