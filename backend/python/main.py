
import logging
import os
from contextlib import asynccontextmanager
from html import escape
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from shared_utils import (
        MIN_TORCH_VERSION,
        configure_logging,
        get_torch_version,
        is_torch_compatible,
        min_version_label,
    )
except ImportError:
    from .shared_utils import (
        MIN_TORCH_VERSION,
        configure_logging,
        get_torch_version,
        is_torch_compatible,
        min_version_label,
    )

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI

configure_logging()
logger = logging.getLogger(__name__)

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ALLOWED_ORIGINS_RAW = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_RAW.split(",") if origin.strip()] or ["*"]
ALLOW_CREDENTIALS = os.getenv("ALLOW_CREDENTIALS", "false").lower() == "true"

if "*" in ALLOWED_ORIGINS and ALLOW_CREDENTIALS:
    logger.warning(
        "allow_credentials=true không tương thích với wildcard ALLOWED_ORIGINS. "
        "Hệ thống tự chuyển allow_credentials=false."
    )
    ALLOW_CREDENTIALS = False

if not GOOGLE_API_KEY:
    logger.warning("Không tìm thấy GOOGLE_API_KEY trong file .env")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMBEDDING_MODEL_PATH = os.path.join(BASE_DIR, "models", "saved-embedding-model")
VECTOR_DB_PATH = os.path.join(BASE_DIR, "vectorstores")


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = None
    chat_id: Optional[int] = None


class ChatResponse(BaseModel):
    success: bool
    response: str
    response_html: str
    intent: str = "general"
    data: Optional[dict] = None


embedding_model = None
vector_db = None
gemini_llm = None
rag_chain = None


def log_runtime_versions() -> None:
    """Log runtime package versions for troubleshooting startup issues."""
    try:
        import numpy

        logger.info("NumPy version: %s", numpy.__version__)
        if int(numpy.__version__.split(".")[0]) >= 2:
            logger.warning("NumPy 2.x detected; verify compatibility with installed PyTorch.")
    except ImportError:
        logger.warning("NumPy not found in current environment.")

    torch_version = get_torch_version()
    if torch_version:
        logger.info("PyTorch version: %s", torch_version)
    else:
        logger.warning("PyTorch not found in current environment.")


def log_torch_upgrade_guide(
    current_version: Optional[str],
    min_version: tuple[int, int, int] = MIN_TORCH_VERSION,
) -> None:
    """Log actionable guide when torch runtime is incompatible."""
    detected = current_version or "not installed"
    min_label = min_version_label(min_version)
    logger.error("PyTorch không tương thích cho sentence-transformers/transformers.")
    logger.error("Phiên bản phát hiện: %s | Yêu cầu tối thiểu: %s", detected, min_label)
    logger.info("Cách sửa:")
    logger.info("- Docker: docker compose build --no-cache ml_api")
    logger.info("- Docker: docker compose up -d ml_api")
    logger.info("- Local: pip install --upgrade \"torch>=%s\"", min_label)


def is_torch_runtime_compatible(
    min_version: tuple[int, int, int] = MIN_TORCH_VERSION,
) -> bool:
    """Validate torch runtime compatibility for sentence-transformers."""
    compatible, current_version = is_torch_compatible(min_version)
    if compatible:
        return True

    if not current_version:
        logger.error("Không tìm thấy PyTorch trong môi trường hiện tại.")

    log_torch_upgrade_guide(current_version, min_version)
    return False


def load_embedding_model():
    """Load embedding model (local model first, then fallback HuggingFace)."""
    logger.info("Đang tải mô hình embedding...")

    if not is_torch_runtime_compatible():
        logger.warning("Bỏ qua tải embedding model vì môi trường chưa tương thích.")
        return None

    if os.path.exists(EMBEDDING_MODEL_PATH):
        try:
            logger.info("Tìm thấy model local tại: %s", EMBEDDING_MODEL_PATH)
            embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL_PATH,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info("Đã tải mô hình fine-tuned thành công.")
            return embeddings
        except Exception as error:
            error_msg = str(error)
            logger.warning("Lỗi khi tải model local: %s", error_msg)
            if "name 'nn' is not defined" in error_msg:
                log_torch_upgrade_guide(get_torch_version())
    else:
        logger.warning("Không tìm thấy model tại: %s", EMBEDDING_MODEL_PATH)

    try:
        logger.info("Đang tải model backup: sentence-transformers/all-MiniLM-L6-v2")
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        logger.info("Đã tải mô hình backup thành công.")
        return embeddings
    except Exception as error:
        error_msg = str(error)
        logger.error("Không thể tải bất kỳ embedding model nào: %s", error_msg)
        if "name 'nn' is not defined" in error_msg:
            log_torch_upgrade_guide(get_torch_version())
        return None


def load_vector_db():
    """Load FAISS vector database and auto-build if missing/corrupted."""
    logger.info("Đang tải cơ sở dữ liệu FAISS...")

    index_path = os.path.join(VECTOR_DB_PATH, "index.faiss")
    if not os.path.exists(index_path):
        logger.warning("Không tìm thấy Vector DB. Tự động tạo mới từ dữ liệu gốc...")
        try:
            try:
                import build_faiss
            except ImportError:
                from . import build_faiss

            db = build_faiss.create_db_from_files()
            logger.info("Đã tạo và tải cơ sở dữ liệu mới thành công.")
            return db
        except Exception:
            logger.exception("Lỗi khi tự động tạo Vector DB.")
            return None

    try:
        db = FAISS.load_local(
            VECTOR_DB_PATH,
            embedding_model,
            allow_dangerous_deserialization=True,
        )
        logger.info("Đã tải cơ sở dữ liệu FAISS thành công.")
        return db
    except Exception:
        logger.exception("Lỗi khi tải cơ sở dữ liệu. Đang thử tạo lại database...")
        try:
            try:
                import build_faiss
            except ImportError:
                from . import build_faiss

            return build_faiss.create_db_from_files()
        except Exception:
            logger.exception("Không thể khôi phục Vector DB.")
            return None


def format_docs(docs) -> str:
    """Format retrieved documents into a single context string."""
    return "\n\n".join(doc.page_content for doc in docs)


def load_gemini_llm():
    """Load Google Gemini LLM client."""
    logger.info("Đang kết nối Gemini API...")
    if not GOOGLE_API_KEY:
        logger.error("Chưa cấu hình GOOGLE_API_KEY.")
        return None

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.6,
            convert_system_message_to_human=True,
        )
        logger.info("Đã kết nối Gemini API thành công.")
        return llm
    except Exception:
        logger.exception("Lỗi khi kết nối Gemini API.")
        return None


def create_gemini_rag_chain(llm, retriever):
    """Create RAG chain using Gemini and retrieved context."""
    logger.info("Đang tạo chuỗi RAG...")
    template = """Bạn là chuyên gia ẩm thực Việt Nam, am hiểu sâu về các món ăn đặc trưng của từng vùng miền. Ưu tiên các quán có lượt bình luận tích cực khi gợi ý quán.

**FORMAT BẮT BUỘC - TUÂN THỦ NGHIÊM NGẶT:**

Trả lời theo đúng cấu trúc sau (KHÔNG được bỏ qua bất kỳ phần nào):

📍 [TÊN MÓN #1]
🏪 Quán: [tên quán]
📍 Địa chỉ: [địa chỉ đầy đủ]
💰 Giá: [khoảng giá cụ thể]
⭐ Đánh giá: [điểm]/10
✨ Đặc điểm: [mô tả chi tiết]
📝 Ghi chú: [lưu ý nếu có]

📍 [TÊN MÓN #2]
...

💡 Mẹo thưởng thức:
- [Mẹo 1: Thời gian nên đi]
- [Mẹo 2: Cách gọi món]
- [Mẹo 3: Món ăn kèm]
- [Mẹo 4: Lưu ý giá cả]
- [Mẹo 5: Đặt chỗ/đậu xe]

**LƯU Ý QUAN TRỌNG:**
1. LUÔN LUÔN kết thúc bằng phần "💡 Mẹo thưởng thức:" - KHÔNG được thiếu
2. Phần mẹo phải có ít nhất 3 gạch đầu dòng (-)
3. Chỉ dùng thông tin từ ngữ cảnh, không bịa đặt
4. Nếu không đủ thông tin, vẫn phải có phần mẹo chung chung

**Ngữ cảnh:**
{context}

**Câu hỏi:**
{question}

**Trả lời (tuân thủ format trên):**"""

    try:
        prompt = PromptTemplate(template=template, input_variables=["context", "question"])

        chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        logger.info("Đã tạo chuỗi RAG thành công.")
        return chain
    except Exception:
        logger.exception("Lỗi khi tạo chuỗi RAG.")
        return None


def markdown_to_html(markdown_text: str) -> str:
    """Convert markdown-style answer to rich HTML for Web UI rendering."""
    lines = markdown_text.strip().split("\n")
    html_parts = ['<div class="food-recommendations">']
    in_tips = False
    current_card = []
    has_food_card = False

    def flush_card() -> None:
        nonlocal current_card, has_food_card
        if current_card:
            html_parts.append('<div class="food-card">')
            html_parts.extend(current_card)
            html_parts.append("</div>")
            current_card = []
            has_food_card = True

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        if line_stripped.startswith("📍") or line_stripped.startswith("**📍"):
            flush_card()
            title = line_stripped.replace("**📍", "").replace("📍", "").replace("**", "").strip()
            current_card.append(f'<h3 class="food-title">📍 {escape(title)}</h3>')
            continue

        if line_stripped.startswith("🏪"):
            info = line_stripped.replace("🏪", "").strip()
            current_card.append(f'<p class="food-info"><span class="emoji">🏪</span> {escape(info)}</p>')
            continue

        if line_stripped.startswith("📍") and "📍" in line_stripped[:3]:
            info = line_stripped.replace("📍", "", 1).strip()
            current_card.append(f'<p class="food-info"><span class="emoji">📍</span> {escape(info)}</p>')
            continue

        if line_stripped.startswith("💰"):
            info = line_stripped.replace("💰", "").strip()
            current_card.append(f'<p class="food-info price"><span class="emoji">💰</span> {escape(info)}</p>')
            continue

        if line_stripped.startswith("⭐"):
            info = line_stripped.replace("⭐", "").strip()
            current_card.append(f'<p class="food-info rating"><span class="emoji">⭐</span> {escape(info)}</p>')
            continue

        if line_stripped.startswith("✨"):
            info = line_stripped.replace("✨", "").strip()
            current_card.append(f'<p class="food-info feature"><span class="emoji">✨</span> {escape(info)}</p>')
            continue

        if line_stripped.startswith("📝"):
            info = line_stripped.replace("📝", "").strip()
            current_card.append(f'<p class="food-info note"><span class="emoji">📝</span> {escape(info)}</p>')
            continue

        if not in_tips and (
            "💡" in line_stripped
            or (
                "Mẹo" in line_stripped
                and (
                    "thưởng thức" in line_stripped.lower()
                    or "lưu ý" in line_stripped.lower()
                )
            )
        ):
            flush_card()
            html_parts.append("</div>")
            html_parts.append('<div class="tips">')
            title = line_stripped.replace("**", "").replace("#", "").strip()
            if "💡" not in title:
                title = "💡 " + title
            html_parts.append(f"<h4>{escape(title)}</h4>")
            html_parts.append("<ul>")
            in_tips = True
            continue

        if in_tips and (
            line_stripped.startswith("-")
            or line_stripped.startswith("•")
            or line_stripped.startswith("*")
            or line_stripped.startswith("💡")
        ):
            tip = line_stripped.lstrip("-•*💡 ").strip()
            if tip:
                html_parts.append(f"<li>{escape(tip)}</li>")
            continue

        if not in_tips and not current_card:
            html_parts.append(f"<p>{escape(line_stripped)}</p>")

    flush_card()

    if in_tips:
        html_parts.append("</ul></div>")
    else:
        html_parts.append("</div>")
        if has_food_card:
            html_parts.append('<div class="tips">')
            html_parts.append("<h4>💡 Mẹo thưởng thức:</h4>")
            html_parts.append("<ul>")
            html_parts.append("<li>Nên đi vào giờ sáng sớm hoặc chiều tối để tránh đông đúc</li>")
            html_parts.append("<li>Hỏi chủ quán về món đặc sản hoặc combo tiết kiệm</li>")
            html_parts.append("<li>Mang theo tiền mặt để dễ thanh toán</li>")
            html_parts.append("</ul></div>")

    return "\n".join(html_parts)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize heavy resources at startup and release on shutdown."""
    global embedding_model, vector_db, gemini_llm, rag_chain

    log_runtime_versions()
    logger.info("Đang khởi động RAG Chatbot API...")

    embedding_model = await run_in_threadpool(load_embedding_model)
    if embedding_model is None:
        logger.warning("Không thể tải embedding model.")

    if embedding_model:
        vector_db = await run_in_threadpool(load_vector_db)
        if vector_db is None:
            logger.warning("Không thể tải vector database.")

    gemini_llm = await run_in_threadpool(load_gemini_llm)
    if gemini_llm and vector_db:
        retriever = vector_db.as_retriever(search_kwargs={"k": 5})
        rag_chain = await run_in_threadpool(create_gemini_rag_chain, gemini_llm, retriever)
        if rag_chain:
            logger.info("Chuỗi Gemini RAG đã sẵn sàng.")

    logger.info("API đã sẵn sàng phục vụ.")
    yield
    logger.info("Đang tắt RAG Chatbot API...")


app = FastAPI(
    title="RAG Chatbot API",
    description="API cho chatbot du lịch với RAG system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RAG Chatbot API đang chạy!",
        "version": "1.0.0",
        "endpoints": {"health": "/health", "chat": "/chat (POST)"},
    }


@app.get("/health")
async def health_check():
    """Kiểm tra tình trạng hệ thống."""
    return {
        "status": "healthy",
        "models": {
            "embedding": embedding_model is not None,
            "vector_db": vector_db is not None,
            "gemini_rag": rag_chain is not None,
        },
        "endpoints": {"chat": "POST /chat (Gemini API - Nhanh)"},
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Endpoint chat chính: retrieve + generate qua RAG chain."""
    try:
        if rag_chain is None:
            raise HTTPException(status_code=503, detail="Chuỗi RAG chưa sẵn sàng")

        user_message = request.message.strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="Tin nhắn không được để trống")

        logger.info(
            "Nhận tin nhắn chat. user_id=%s chat_id=%s message_len=%s",
            request.user_id,
            request.chat_id,
            len(user_message),
        )

        response_text = await run_in_threadpool(rag_chain.invoke, user_message)
        response_html = await run_in_threadpool(markdown_to_html, response_text)

        return ChatResponse(
            success=True,
            response=response_text,
            response_html=response_html,
            intent="food_recommendation",
            data={"user_id": request.user_id, "chat_id": request.chat_id},
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Lỗi tại endpoint /chat")
        return ChatResponse(
            success=False,
            response="Đã xảy ra lỗi khi xử lý câu hỏi của bạn. Vui lòng thử lại sau.",
            response_html='<div class="alert-danger">⚠️ Hệ thống đang bận, vui lòng thử lại.</div>',
            intent="error",
            data=None,
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )
