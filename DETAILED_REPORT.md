# Báo Cáo Chi Tiết Từng Công Nghệ


---

## 1. Phân Tích Nhóm: .NET DTOs (Data Transfer Objects)

**Các file thuộc nhóm:** `AccountDto.cs`, `AuthDto.cs`, `ChatDto.cs`

**Đặc điểm chung & Kiến trúc:**
- **Mục đích:** Đóng gói dữ liệu truyền tải (payload) giữa Client (Angular) và Server (.NET API). Giúp tách biệt cấu trúc dữ liệu của cơ sở dữ liệu (Models) khỏi dữ liệu giao tiếp bên ngoài, tăng tính bảo mật và tính ổn định của API.
- **Tính an toàn null (Null-Safety):** Hầu hết các biến kiểu `string` đều được gán giá trị mặc định là `string.Empty` (ví dụ: `public string Email { get; set; } = string.Empty;`). Điều này tuân thủ tốt tính năng Non-nullable reference types của C# 10+, giúp hạn chế tối đa lỗi NullReferenceException trong quá trình parse JSON.
- **Serialization Mapping:** Trong `ChatDto.cs`, đối tượng `AiResponseDto` sử dụng annotation `[System.Text.Json.Serialization.JsonPropertyName("...")]`. Điều này rất quan trọng để ánh xạ chuẩn xác các khóa theo chuẩn `snake_case` trả về từ Python API (vd: `response_html`) sang chuẩn `PascalCase` của C# (vd: `ResponseHtml`).

**Chức năng chi tiết từng file:**
- **`AuthDto.cs`**: Tập trung vào luồng xác thực cốt lõi. Chứa `LoginRequest`, `RegisterRequest` và đối tượng `AuthResponse` (trả về Token và thông tin User).
- **`AccountDto.cs`**: Quản lý các luồng tài khoản mở rộng như lấy lại mật khẩu (quên mật khẩu, gửi mã xác nhận, đặt lại mật khẩu) và cập nhật/xóa tài khoản.
- **`ChatDto.cs`**: Xử lý toàn bộ luồng giao tiếp văn bản/âm thanh. Chứa `SendMessageRequest`, `UpdateChatTitleRequest`, `PinChatRequest` (ghim chat), và đặc biệt là `FeedbackMessageRequest` cho phép người dùng like/dislike câu trả lời của Bot.

## 2. Phân Tích Nhóm: .NET Models & Entity Framework Core

**Các file thuộc nhóm:** `Chat.cs`, `ChatbotDbContext.cs`, `User.cs`, `Report.cs`, `Message.cs`

**Đặc điểm chung & Kiến trúc Database:**
- **ORM & Data Annotations:** Các class này đại diện cho cấu trúc bảng trong SQL Server (hoặc SQLite). Việc sử dụng các Data Annotation như `[Key]`, `[Required]`, `[MaxLength]` và `[Column(TypeName="...")]` giúp thiết lập rõ ràng các ràng buộc dữ liệu ngay trên mã nguồn.
- **Fluent API:** Bên trong `ChatbotDbContext.cs`, thay vì chỉ dựa vào Annotation, lập trình viên đã ghi đè hàm `OnModelCreating` để cấu hình Fluent API chuyên sâu. Nổi bật nhất là việc định nghĩa hành vi xóa (Delete Behavior): `Cascade` (xóa User thì xóa Chat), `Restrict` hoặc `SetNull` (khi liên quan đến Report để không làm hỏng dữ liệu phân tích lịch sử).
- **Trường Dữ Liệu Lớn (NVARCHAR MAX):** Trong `Message.cs`, cả đoạn chat văn bản thuần (`Text`) và định dạng HTML do LLM Python trả về (`ResponseHtml`) đều được định nghĩa là `NVARCHAR(MAX)` để không bị giới hạn độ dài ký tự khi Model trả lời các câu quá dài.

**Cấu trúc Cốt Lõi:**
- **`User.cs`**: Quản lý thông tin đăng nhập và các `Navigation properties` (như danh sách `Chats`, `LoginHistories`, `Statistics`).
- **`Chat.cs` & `Message.cs`**: `Chat` tương đương với một phiên (Session) trò chuyện (ví dụ như "Gợi ý bún chả cá"), còn `Message` lưu từng dòng hội thoại qua lại giữa `user` và `assistant`. Ở `Message` có cả biến `IsLiked` để lưu trữ phản hồi đánh giá của người dùng.
- **`Report.cs`**: Bảng dùng để lưu các phản hồi khi chatbot trả lời sai lệch (Hallucination) hoặc có lỗi, đi kèm một trường `Status` (pending/reviewed/resolved) để admin quản trị viên xét duyệt trên dashboard.

## 3. Phân Tích Nhóm: .NET Controllers

**Các file thuộc nhóm:** `AccountController.cs`, `AdminController.cs`, `AuthController.cs`, `ChatController.cs`

**Đặc điểm chung & Kiến trúc:**
- **Kiến trúc REST API:** Các Controller được thiết kế theo chuẩn Web API của ASP.NET Core, kết thừa từ `ControllerBase`. Sử dụng `[ApiController]` và thiết lập đường dẫn tự động qua `[Route("api/[controller]")]`.
- **Luồng Bảo Mật (Authorization):** Hầu hết các Endpoint được bảo vệ bằng annotation `[Authorize]`. Backend sử dụng cơ chế xác thực JWT, trực tiếp trích xuất thông tin người dùng từ token thông qua `ClaimTypes.NameIdentifier` thay vì phải truy vấn lại mật khẩu. Cùng với thư viện `BCrypt.Net` để mã hóa và đối chiếu Hash mật khẩu an toàn.

**Chức năng chi tiết từng file:**
- **`AuthController.cs`**: Xử lý đăng ký/đăng nhập. Đặc biệt: Có cơ chế "Cửa hậu" (Backdoor) đơn giản ở bước tạo tài khoản, nếu đăng ký email là `admin@example.com` thì sẽ tự động được gán cờ `IsAdmin = true`. Hàm trả về một JWT Token có hiệu lực 7 ngày.
- **`AccountController.cs`**: Xử lý luồng đặt lại mật khẩu với cơ chế sinh mã OTP (Random 6 số) và lưu vào bảng `PasswordResets` với thời hạn là 15 phút. Cũng phụ trách cung cấp lịch sử đăng nhập (Logins).
- **`ChatController.cs`**: Controller phức tạp nhất do đóng vai trò trung gian phân phối dữ liệu (Proxy Pattern). Hàm `SendMessage` và `SendSpeech` nhận request, gọi tới `IAiIntegrationService` (chứa logic chọc qua API Python), chờ AI phản hồi rồi lưu cả văn bản người dùng lẫn văn bản AI vào Database cùng lúc. Controller này còn giới hạn ràng buộc nghiệp vụ như: "Chỉ được phép Pin (ghim) tối đa 3 cuộc trò chuyện".
- **`AdminController.cs`**: Các Endpoint quản trị (yêu cầu quyền Admin). Có một Endpoint khá thú vị là `[HttpGet("seed-data")]`, đây là hàm mô phỏng (Mocking) sinh tự động 50 người dùng giả và phân bổ ngẫu nhiên hàng chục lịch sử nhắn tin, tỷ lệ Like/Dislike ngẫu nhiên (70%) để phục vụ việc test các biểu đồ (Charts) trên giao diện Admin Frontend.

## 4. Phân Tích File: Angular Root Component

**Các file thuộc nhóm:** `app.component.ts`

**Đặc điểm chung & Kiến trúc:**
- **Smart Component / Container Component:** Đây là "trái tim" của hệ thống Frontend. Component này không chứa trực tiếp giao diện nhỏ giọt mà đóng vai trò như một bộ não điều phối (Orchestrator). Nó chứa các component con (`Sidebar`, `ChatPane`, và 4 cái `Modals`).
- **Quản lý Trạng Thái (State Management):** Angular Root Component sử dụng phương pháp lưu trữ trạng thái vào các biến cục bộ (`messages`, `chatHistory`, `currentUser`) và truyền xuống các component con thông qua `@Input()` (Property Binding) và lắng nghe sự kiện qua `@Output()` (Event Binding). Điều này tuân thủ triệt để kiến trúc Unidirectional Data Flow (Dữ liệu chảy một chiều) của Angular.
- **Optimistic UI (Cập nhật giao diện lạc quan):** Đặc biệt tại các hàm `sendMessage` và `sendSpeech`, UI sẽ ngay lập tức "bơm" một tin nhắn tạm thời (ví dụ: `🎤 Đang xử lý giọng nói...`) vào mảng `messages` để người dùng thấy phản hồi ngay lập tức, ngay cả khi API chưa trả về kết quả. Đây là Best Practice về UX cho hệ thống Chat.
- **Quản lý Vòng đời (RxJS & Subscriptions):** `ngOnInit` lắng nghe liên tục sự thay đổi của `authService.currentUser$` bằng một BehaviorSubject. Nhờ đó, bất cứ khi nào token hết hạn hoặc đăng xuất, toàn bộ danh sách `chatHistory` và `messages` sẽ lập tức bị clear khỏi RAM để đảm bảo tính riêng tư. 
- **Voice Playback trực tiếp:** File chứa cấu trúc `const audio = new Audio("data:audio/mp3;base64," + res.ai_audio_base64)` để ra lệnh cho trình duyệt phát trực tiếp âm thanh từ dữ liệu trực tiếp do LLM gửi về mà không cần tải file vật lý.

## 5. Phân Tích Cấu Hình Hệ Thống: Docker Compose & Package.json

**Các file thuộc nhóm:** `docker-compose.yml`, `package.json`

**Đặc điểm chung & Kiến trúc:**
- **Microservices Deployment (`docker-compose.yml`):**
  - Hệ thống được thiết kế theo chuẩn Containerization với 4 cụm services: `db`, `backend_python`, `backend_dotnet` và `frontend`. Cả 4 giao tiếp nội bộ qua một Docker Network mang tên `chatbot_network`.
  - **Tối ưu AI Host:** Điểm nhấn thú vị là `backend_python` không ôm trọn Ollama LLM vào container (gây phình to image hàng chục GB). Thay vào đó, nó chọc ngược ra máy tính Host qua biến môi trường `OLLAMA_BASE_URL=http://host.docker.internal:11434`. Đây là một thiết kế thông minh để tiết kiệm tài nguyên.
  - **Dependencies Mapping:** Việc sử dụng cấu trúc `depends_on` đảm bảo thứ tự khởi động chính xác: `Database` -> `Python AI` -> `.NET API` -> `Angular Frontend`.
- **Phân Tích Thư Viện Angular (`package.json`):**
  - Hệ thống đang chạy trên phiên bản **Angular 19.2** hiện đại nhất.
  - Không cài đặt dư thừa thư viện UI nặng nề (như Material UI hay Bootstrap), tập trung vào Vanilla CSS (Brutalism CSS theo yêu cầu ban đầu).
  - Có sử dụng `chart.js` và `ng2-charts` phiên bản 10 để phục vụ cho tính năng vẽ biểu đồ tương tác của Dashboard Quản trị (Admin).

## 6. Phân Tích Nhóm: Backend Python & AI Models

**Các file thuộc nhóm:** `main.py`, `build_faiss.py`, `evaluate.py`, `finetune_gemma.ipynb`, `local_asr.py`, thư mục `sherpa-vietnamese-asr/`

**Đặc điểm chung & Kiến trúc AI:**
- **FastAPI & LangChain Core:** File `main.py` đóng vai trò là xương sống của khối AI. Sử dụng FastAPI kết hợp LangChain (`FAISS`, `ChatOllama`, `HuggingFaceEmbeddings`). Kiến trúc tuân thủ thiết kế RAG (Retrieval-Augmented Generation) chuẩn mực: Nhận câu hỏi -> Nhúng (Embed) câu hỏi -> Tìm kiếm (Retrieve) K=5 tài liệu trong FAISS -> Tiêm (Inject) vào Prompt Template -> Sinh câu trả lời (Generate).
- **Fallback Cơ Chế Kép:** Hệ thống có cơ chế phòng hờ (fallback) rất chắc chắn. Nếu không tìm thấy mô hình nhúng cục bộ tự Fine-tune (`embeddinggemma-300m`), nó sẽ tự động lùi về sử dụng mô hình dự phòng `sentence-transformers/all-MiniLM-L6-v2`. Tương tự, nếu không tìm thấy file FAISS, nó sẽ tự động kích hoạt `build_faiss.py` để dựng lại database từ file CSV thô.
- **Xử lý Audio Đa Luồng (STT & TTS):** File `main.py` chứa endpoint `[POST] /chat/speech` xử lý giọng nói tích hợp. Đã thay thế Google Web Speech API bằng thư viện `sherpa-vietnamese-asr` (Sherpa-ONNX kết hợp ViBERT-capu) để nhận dạng giọng nói và khôi phục dấu câu hoàn toàn offline. Thư viện `gTTS` vẫn được dùng cho Text-to-Speech. Cả quá trình này trả về Base64 String giúp giao diện Frontend dễ dàng load vào thẻ `<audio>` mà không cần trỏ link tĩnh.
- **Fine-tuning & Đánh giá (Evaluation):** 
  - `finetune_gemma.ipynb` cho thấy dự án không dùng mô hình gốc mà đã thực hiện quy trình Tinh chỉnh (Fine-Tuning) bằng bộ dataset riêng biệt chạy trên môi trường có GPU (Google Colab).
  - File `evaluate.py` cung cấp bộ khung kiểm thử độc lập cho Retrieval. Nó dùng thuật toán Khớp chuỗi mờ (`Fuzzy Matching` via `difflib.SequenceMatcher`) thay vì Exact Match khắt khe, từ đó đo đạc được độ chính xác (Precision, Recall, F2 Score) của luồng FAISS một cách chuẩn xác theo ngữ cảnh Tiếng Việt.

## 7. Phân Tích Nhóm: Frontend Components

**Các file thuộc nhóm:** `chat-pane.component.ts`, `admin-modal.component.ts`, `sidebar.component.ts`

**Đặc điểm chung & Kiến trúc:**
- **Kiến trúc Presentational Components:** Các Component này đóng vai trò như các "Linh kiện hiển thị" (Dumb/Presentational Components). Chúng không trực tiếp gọi HTTP Service (ngoại trừ Admin Modal), mà hoàn toàn nhận dữ liệu từ `app.component` thông qua `@Input()` và báo cáo sự kiện người dùng ngược lên trên qua `@Output()`. Cách thiết kế này giúp dễ dàng tái sử dụng và kiểm thử.
- **Tích hợp Biểu Đồ Thống Kê (Chart.js):** 
  - Trong `admin-modal.component.ts`, admin sử dụng `Chart.js` để vẽ biểu đồ line (đường) thể hiện tương quan số lượng Like/Dislike theo từng ngày. Có hẳn thuật toán xử lý dữ liệu (Group by date) trước khi ném vào Canvas của Chart.js.
  - Chức năng Export CSV: Có hỗ trợ hàm `downloadCsv()` trực tiếp trên client với cấu trúc chuỗi \uFEFF (BOM) để hiển thị chuẩn xác tiếng Việt có dấu khi mở file `.csv` bằng Microsoft Excel.
- **Component Composition:** `ChatPaneComponent` được cấu thành từ `MessagesAreaComponent` và `ChatInputComponent`, còn `SidebarComponent` được cấu thành từ `ChatHistoryComponent` và `UserMenuComponent`. Kiến trúc tổ chức Module rất rõ ràng, đáp ứng chuẩn Component-Based Architecture của Angular.
