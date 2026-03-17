#  AI Travel & Dining Assistant (Hackathon 2025)

![Python](https://img.shields.io/badge/Python-3.10-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393)
![PHP](https://img.shields.io/badge/PHP-8.1-777bb3)
![MySQL](https://img.shields.io/badge/MySQL-8.0-e68817)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ed)

Hệ thống chatbot thông minh hỗ trợ gợi ý và lên lịch trình ẩm thực tại Đà Nẵng. Dự án kết hợp mô hình RAG (Retrieval-Augmented Generation) tiên tiến để trích xuất dữ liệu quán ăn địa phương và tổng hợp câu trả lời tự nhiên qua LLM.

## 🌟 Tính năng cốt lõi

- **Trợ lý Ẩm thực AI (RAG):** Đề xuất món ăn dựa trên vector database (FAISS) và context thực tế từ dữ liệu crawl, tổng hợp bằng Google Gemini.
- **Quản lý Tài khoản (PHP/MySQL):** Đăng nhập, đăng ký, quên/đổi mật khẩu an toàn, quản lý hồ sơ và theo dõi lịch sử truy cập.
- **Quản lý Lịch sử Chat:** Ghi nhớ nội dung hội thoại, render markdown/HTML trực tiếp trên UI, cho phép ghim (pin) và quản lý đoạn chat.
- **Microservices Deployment:** Đóng gói hoàn chỉnh bằng Docker Compose (Web UI, API PHP, ML Python API, Database).

---

## 🏗 Kiến trúc Hệ thống

**Luồng xử lý chính:**
1. **User** gửi câu hỏi từ **Web UI**.
2. **Web UI** gọi **PHP API** (`/chat.php`) để xác thực và lưu truy vết.
3. **PHP API** gọi nội bộ sang **Python ML API** (`/chat` qua FastAPI).
4. **Python ML API** trích xuất ngữ cảnh từ **FAISS VectorDB** bằng nhúng từ `SentenceTransformers`.
5. **Google Gemini LLM** nhận Prompt bao gồm (Context + History + User Query) để tạo câu trả lời.
6. Kết quả trả về PHP, lưu lịch sử vào **MySQL**, và hiển thị (text/markdown) trên UI.

*Tham khảo sơ đồ chi tiết tại: `architecture_diagram.drawio`*

---

## 📂 Cấu trúc Repository (Production-Ready)

```text
Hackathon2025/
├── backend/
│   ├── php/                 # Backend API Core (Auth, User, Chat History)
│   └── python/              # ML API (FastAPI, RAG, GenAI)
│       ├── build_faiss.py   # Script tạo FAISS vector index (ETL step)
│       └── main.py          # FastAPI Server entry point
├── data/
│   └── crawl/               # Pipeline thu thập dữ liệu (crawl.py CLI)
├── database/                # Schema MySQL và Seed data (database.sql)
├── infrastructure/          # Chứa cấu hình Docker chuyên sâu (Dockerfile cho Nginx/PHP)
├── web_ui/                  # Frontend App (Vanilla JS/CSS/HTML)
├── docker-compose.yml       # Orchestration file
└── README.md
```

*(Lưu ý: Các file artifact lớn như AI Models (`.safetensors`) và VectorStores (`.faiss`) đã được đưa vào `.gitignore` để giữ repo nhẹ tổi ưu. Bạn cần tự chạy pipeline init ở lần đầu tải repo về).*

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy (Getting Started)

### 1. Yêu cầu Hệ thống (Prerequisites)
- Docker & Docker Compose.
- Python 3.10+ (để chạy script tạo AI Artifacts lần đầu).
- API Key của Google Gemini.

### 2. Chuẩn bị Biến môi trường
Tạo file `.env` tại `backend/python/.env`:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 3. Khởi tạo Artifacts AI (Bắt buộc ở lần clone đầu tiên)
Vì Repository không chứa các file nặng (như Database nhúng FAISS), bạn cần sinh dữ liệu RAG trước khi chạy Docker:

```bash
# 1. Cài đặt Python Dependencies
cd backend/python
python -m venv .venv
# Activate venv: `.venv\Scripts\Activate.ps1` (Windows) hoặc `source .venv/bin/activate` (Mac/Linux)
pip install -r requirements.txt

# 2. Thu thập dữ liệu (Có thể bỏ qua nếu đã có data_RAG.csv)
cd ../../data/crawl
python crawl.py --pages 3 --threads 4

# 3. Build Vector Database (FAISS)
cd ../../backend/python
python build_faiss.py
# Script này sẽ sinh các file tại backend/python/vectorstores/ và tải Model HuggingFace về.
```

### 4. Khởi chạy Hệ thống toàn diện bằng Docker
Khi đã có đủ Artifacts, chỉ cần chạy command sau từ thư mục gốc:

```bash
docker compose up -d --build
```

**Các endpoints sau khi up:**
- **Web UI:** [http://localhost:8080](http://localhost:8080)
- **ML API Status:** [http://localhost:8001/health](http://localhost:8001/health) (Kiểm tra Model/FAISS loading)
- **MySQL port:** `3307` (Local host mapping)

**Xem logs hệ thống:**
```bash
docker logs --tail 50 hackathon_ml_api
docker logs --tail 50 hackathon_web
```

---

## 🔌 Tài liệu API Chính

### Python ML Service (`http://ml_api:8001`)
- `GET /health` : Trả về trạng thái load của Embedding Model và Vector DB.
- `POST /chat` :
  ```json
  // Request body
  {
      "message": "Quán bún chả cá nào ngon ở Liên Chiểu?",
      "user_id": 1,
      "chat_id": 12 
  }
  ```

### Backend PHP (`http://localhost:8080/backend/php/`)
- **Tài khoản:** `api/auth.php`, `api/account.php` (Đăng nhập, Quên pass, Thay đổi thông tin).
- **Trò chuyện:** `api/chat.php` (Lịch sử chat, Tải tin nhắn cũ, Edit title, Report nội dung vi phạm).


