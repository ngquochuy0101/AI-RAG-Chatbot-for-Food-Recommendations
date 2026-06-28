# 🍲 AI RAG Chatbot for Food Recommendations

Hệ thống Chatbot AI gợi ý món ăn áp dụng công nghệ RAG (Retrieval-Augmented Generation) kết hợp với kiến trúc **Angular 21** và **.NET 10 (EF Core Code First)**.

---

## 🌟 Tính năng chính
- **Gợi ý món ăn thông minh**: Dựa vào ngữ cảnh (RAG) và dữ liệu thực tế.
- **Tài khoản người dùng**: Đăng ký, đăng nhập, lưu và ghim các cuộc trò chuyện.
- **Báo cáo tin nhắn**: Đánh dấu các tin nhắn không phù hợp.
- **Giao diện hiện đại (Angular)**: Single Page Application mượt mà, responsive.
- **Quản lý hệ thống (Admin)**: Dashboard thống kê người dùng, tin nhắn phản hồi, xuất báo cáo CSV.
- **Container hóa với Docker**: Triển khai dễ dàng bằng một lệnh duy nhất thông qua Docker Compose.

---

## 🚀 Hướng dẫn Cài đặt & Sử dụng (Cho người mới Clone)


### 1. Yêu cầu Hệ thống
- **Docker** & **Docker Compose** (Dùng để chạy Database, .NET Backend và Angular Frontend).
- **Python 3.10+** (Để chạy script fine-tune và RAG Backend).
- **Ollama** (Để chạy Local LLM cung cấp text generation).

### 2. Thiết lập Mô hình Ngôn ngữ Lớn (LLM) bằng Ollama

Dự án sử dụng mô hình Gemma 4 (phiên bản E2B). Bạn cần tải model này và cài đặt vào Ollama:

**Cách 1: Tải tự động qua HuggingFace CLI**
Mở Terminal/PowerShell ở thư mục gốc dự án:
```bash
# Cài đặt huggingface-cli
pip install -U "huggingface_hub[cli]"

# Tải model vào thư mục models/llm
huggingface-cli download google/gemma-4-E2B-it-qat-q4_0-gguf --local-dir "models/llm" --include "*.gguf"
```

**Cách 2: Tải thủ công**
Tải 2 file `gemma-4-E2B_q4_0-it.gguf` và `gemma-4-E2B-it-mmproj.gguf` từ repo HuggingFace và đặt vào thư mục `models/llm/`.

**Đưa vào Ollama:**
Mở terminal tại thư mục `models/llm/` và tạo Modelfile:
```bash
cd models/llm

# Cài đặt model vào Ollama với tên gọi 'gemma4-e2b' (Tên này phải khớp với cấu hình trong backend API)
ollama create gemma4-e2b -f Modelfile
```

### 3. Huấn luyện Mô hình Nhúng (Finetune Embedding Model)

Hệ thống RAG sử dụng một mô hình nhúng (Embedding) đã được tinh chỉnh (finetune) riêng cho dữ liệu ẩm thực.

1. Đảm bảo bạn đã cài các thư viện Python cần thiết (`sentence-transformers`, `pandas`, `jupyter` v.v.).
2. Mở file notebook: `notebooks/finetune_gemma.ipynb` (Dùng VSCode hoặc Jupyter Notebook).
3. Chạy tất cả các cell trong notebook. Quá trình này sẽ sử dụng file dữ liệu tại `data/raw/dataset_QA_finetuning.xlsx`.
4. Sau khi notebook chạy xong, nó sẽ xuất ra một thư mục chứa mô hình (ví dụ: `saved-embedding-model`).
5. Bạn hãy copy toàn bộ nội dung của thư mục vừa được sinh ra đó và dán vào:
   `models/embedding/google-embedding-300-finetuned/`

### 4. Xây dựng Vector Database (FAISS)

Khi đã có Embedding Model, bạn cần tạo Vector Database từ dữ liệu quán ăn:
```bash
# Cài đặt requirements cho Python backend
cd backend/python
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt

# Chạy script tạo FAISS vector store
python build_faiss.py
```
*(Vector DB sẽ được lưu tự động vào `data/vectorstores/`)*

### 5. Khởi chạy toàn bộ hệ thống bằng Docker

Khi các tệp AI đã sẵn sàng, việc còn lại rất đơn giản:

1. Quay lại thư mục gốc của dự án.
2. Chạy lệnh:
   ```bash
   docker-compose -f infrastructure/docker/docker-compose.yml up -d --build
   ```
3. Đợi Docker tải các image và khởi động các container. Lần chạy đầu tiên có thể mất vài phút.

---

## 🌐 Các Đường Dẫn Truy Cập

- **Frontend (Giao diện người dùng)**: [http://localhost:8080/](http://localhost:8080/)
- **.NET API (Swagger)**: [http://localhost:5200/swagger](http://localhost:5200/swagger)
- **Python AI API**: [http://localhost:8001/docs](http://localhost:8001/docs)

---

## 📚 Lưu ý Quan Trọng
- **Database Migrations**: Trong lần đầu tiên chạy .NET Container, công cụ Entity Framework sẽ tự động tạo bảng (Database Migration) vào SQL Server. Bạn không cần tự tạo script SQL.
- **Docker Compose Volume**: Dữ liệu SQL Server được lưu trữ dai dẳng thông qua volume `sql_data`. Nếu bạn muốn xóa trắng database, hãy dùng lệnh `docker-compose down -v`.
- **Thư mục models/**: Thư mục này đã được mount thẳng vào trong container của Python backend thông qua docker-compose nên bạn không cần lo lắng về việc build lại docker mỗi khi đổi model.

---

**Chúc bạn có một trải nghiệm tuyệt vời với AI RAG Chatbot! 🍲**
