# 🍲 AI RAG Chatbot for Food Recommendations

Hệ thống Chatbot AI gợi ý món ăn áp dụng công nghệ RAG (Retrieval-Augmented Generation) kết hợp với kiến trúc **Angular 19** và **.NET 10 (EF Core Code First)**.

---

## 🌟 Tính năng chính

- **Gợi ý món ăn thông minh**: Dựa vào ngữ cảnh (RAG) và dữ liệu thực tế.
- **Tài khoản người dùng**: Đăng ký, đăng nhập, bảo mật với JWT và BCrypt.
- **Lịch sử hội thoại**: Lưu trữ, xem lại và ghim các cuộc trò chuyện.
- **Báo cáo tin nhắn**: Đánh dấu các tin nhắn không phù hợp.
- **Giao diện hiện đại (Angular)**: Single Page Application mượt mà, responsive.
- **Quản lý hệ thống (Admin)**: Dashboard thống kê người dùng, tin nhắn phản hồi, xuất báo cáo CSV.
- **Container hóa với Docker**: Triển khai dễ dàng bằng một lệnh duy nhất thông qua Docker Compose.

---

## 🛠️ Kiến trúc Hệ thống

Dự án được xây dựng với cấu trúc Microservices/Containers, bao gồm:

1. **Frontend (`/web_ui_angular`)**: 
   - Angular 19 (Standalone Components).
   - Quản lý trạng thái, Routing bảo mật, giao diện tương tác người dùng và trang Admin Dashboard.

2. **Backend API (.NET)**: 
   - .NET 9/10 C# Web API.
   - Xử lý JWT Auth, lưu trữ lịch sử chat, phân quyền Admin.
   - Giao tiếp với Database qua Entity Framework Core.

3. **Database (SQL Server 2022)**: 
   - Tự động thiết lập và chạy qua Docker.
   - Entity Framework Core Migrations (Tự động sinh ra cấu trúc bảng).

4. **AI Engine (`/backend/python`)**: 
   - Python FastAPI xử lý thuật toán RAG.
   - Kết nối với Local LLM (Ollama) và Vector Database (FAISS).

---

## 🚀 Hướng dẫn khởi chạy bằng Docker

Hệ thống đã được đóng gói và cấu hình hoàn chỉnh bằng `docker-compose`. Bạn không cần cài đặt tay từng framework phức tạp.

### Yêu cầu tiên quyết:
- Đã cài đặt **Docker** và **Docker Compose** (Docker Desktop trên Windows/Mac).
- Đã chạy sẵn **Ollama** ở máy thật (host) cho RAG model.

### Cách chạy:
1. Mở Terminal (PowerShell/CMD) tại thư mục gốc của dự án.
2. Gõ lệnh:
   ```bash
   docker-compose up -d --build
   ```
3. Đợi vài phút để Docker tự động tải về và biên dịch các container (quá trình này rất nhanh trong các lần chạy sau).

### Truy cập:
- **Frontend (Giao diện người dùng)**: `http://localhost:8080/`
- **.NET API (Swagger)**: `http://localhost:5200/swagger`
- **Python AI API**: `http://localhost:8001/docs`

### Cách dừng hệ thống:
```bash
docker-compose down
```

---

## 📚 Lưu ý
- Trong lần đầu tiên chạy .NET Container, công cụ Entity Framework sẽ tự động tạo bảng (Database Migration) vào SQL Server.
- Thư mục `Models/` (chứa các file mô hình `.gguf` khổng lồ) đã được bỏ qua trong quá trình build Docker (`.dockerignore`) để tiết kiệm thời gian khởi động, do ứng dụng kết nối trực tiếp với Ollama trên host.
