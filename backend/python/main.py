
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
from langchain_ollama import ChatOllama

configure_logging()
logger = logging.getLogger(__name__)

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4-e2b")
ALLOWED_ORIGINS_RAW = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_RAW.split(",") if origin.strip()] or ["*"]
ALLOW_CREDENTIALS = os.getenv("ALLOW_CREDENTIALS", "false").lower() == "true"

if "*" in ALLOWED_ORIGINS and ALLOW_CREDENTIALS:
    logger.warning(
        "allow_credentials=true không tương thích với wildcard ALLOWED_ORIGINS. "
        "Hệ thống tự chuyển allow_credentials=false."
    )
    ALLOW_CREDENTIALS = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
EMBEDDING_MODEL_PATH = os.path.join(PROJECT_ROOT, "Models", "google-embeding300-finetuning")
EMBEDDING_MODEL_FALLBACK = os.path.join(BASE_DIR, "models", "saved-embedding-model")
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
ollama_llm = None
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
    """Load embedding model: embeddinggemma-300m first, then fallback options."""
    logger.info("Đang tải mô hình embedding...")

    if not is_torch_runtime_compatible():
        logger.warning("Bỏ qua tải embedding model vì môi trường chưa tương thích.")
        return None

    # Try loading embeddinggemma-300m from Models/ directory
    for model_path, label in [
        (EMBEDDING_MODEL_PATH, "embeddinggemma-300m (local)"),
        (EMBEDDING_MODEL_FALLBACK, "saved-embedding-model (fallback local)"),
    ]:
        if os.path.exists(model_path):
            try:
                logger.info("Tìm thấy model tại: %s (%s)", model_path, label)
                embeddings = HuggingFaceEmbeddings(
                    model_name=model_path,
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True},
                )
                logger.info("Đã tải mô hình %s thành công.", label)
                return embeddings
            except Exception as error:
                error_msg = str(error)
                logger.warning("Lỗi khi tải %s: %s", label, error_msg)
                if "name 'nn' is not defined" in error_msg:
                    log_torch_upgrade_guide(get_torch_version())
        else:
            logger.warning("Không tìm thấy model tại: %s", model_path)

    # Final fallback: download from HuggingFace Hub
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


def load_ollama_llm():
    """Load local Ollama LLM client."""
    logger.info("Đang kết nối Ollama LLM (model: %s, url: %s)...", OLLAMA_MODEL, OLLAMA_BASE_URL)

    try:
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.3,
            num_ctx=4096,
        )
        logger.info("Đã kết nối Ollama LLM thành công (model: %s).", OLLAMA_MODEL)
        return llm
    except Exception:
        logger.exception("Lỗi khi kết nối Ollama LLM.")
        return None


def create_rag_chain(llm, retriever):
    """Create RAG chain using Ollama LLM and retrieved context."""
    logger.info("Đang tạo chuỗi RAG...")
    template = """Bạn là chuyên gia ẩm thực Đà Nẵng. Nhiệm vụ: tư vấn quán ăn dựa trên DỮ LIỆU ĐƯỢC CUNG CẤP.

**QUY TẮC BẮT BUỘC:**
1. CHỈ trả lời về ẩm thực Đà Nẵng. Câu hỏi khác → trả lời: "Xin lỗi, mình chỉ tư vấn về ẩm thực Đà Nẵng thôi nhé! 🍜"
2. CHỈ gợi ý ĐÚNG QUÁN phù hợp nhất từ dữ liệu.
3. NẾU không tìm thấy quán phù hợp trong dữ liệu → trả lời: "Mình chưa có thông tin về món này, bạn thử hỏi món khác nhé!"
4. KHÔNG được bịa thông tin. Chỉ dùng dữ liệu bên dưới.
5. Nếu dữ liệu thiếu trường nào (giá, đánh giá...) → ghi "Chưa có thông tin".

**FORMAT BẮT BUỘC (chỉ dùng khi có quán phù hợp):**
📍 [Tên món ăn]
🏪 Quán: [Tên quán chính xác từ dữ liệu]
📍 Địa chỉ: [Địa chỉ]
💰 Giá: [Giá tiền]
⭐ Đánh giá: [Điểm]/10
✨ Đặc điểm: [Mô tả ngắn]

💡 Mẹo thưởng thức (nếu có):
- [Mẹo]

**VÍ DỤ MẪU:**
Câu hỏi: "Bún chả cá ở đâu ngon?"
Trả lời:
📍 Bún Chả Cá
🏪 Quán: Bún chả cá Bà Lữ
📍 Địa chỉ: 66 Lê Hồng Phong, Hải Châu
💰 Giá: 30.000 - 45.000đ
⭐ Đánh giá: 8.5/10
✨ Đặc điểm: Nước dùng trong, ngọt tự nhiên, chả cá chiên giòn

💡 Mẹo thưởng thức:
- Ăn kèm rau sống và ớt xanh

---
**Dữ liệu tham khảo:**
{context}

**Câu hỏi của người dùng:**
{question}

**Trả lời:**"""

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


def markdown_to_html(text: str) -> str:
    # Force newlines before key emojis if the AI forgot them
    text = text.replace(" 🏪", "\n🏪").replace(" 📍 Địa chỉ", "\n📍 Địa chỉ").replace(" 💰", "\n💰").replace(" ⭐", "\n⭐").replace(" ✨", "\n✨").replace(" 💡", "\n💡")
    
    lines = text.split("\n")
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

        if (line_stripped.startswith("📍") or line_stripped.startswith("**📍")) and "Địa chỉ" not in line_stripped:
            flush_card()
            title = line_stripped.replace("**📍", "").replace("📍", "").replace("**", "").strip()
            current_card.append(f'<h3 class="food-title">📍 {escape(title)}</h3>')
            continue

        if line_stripped.startswith("🏪"):
            info = line_stripped.replace("🏪", "").strip()
            current_card.append(f'<p class="food-info"><span class="emoji">🏪</span> {escape(info)}</p>')
            continue

        if (line_stripped.startswith("📍") or line_stripped.startswith("**📍")) and "Địa chỉ" in line_stripped:
            info = line_stripped.replace("**📍", "").replace("📍", "").replace("**", "").strip()
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
    global embedding_model, vector_db, ollama_llm, rag_chain

    log_runtime_versions()
    logger.info("Đang khởi động RAG Chatbot API (Ollama backend)...")

    embedding_model = await run_in_threadpool(load_embedding_model)
    if embedding_model is None:
        logger.warning("Không thể tải embedding model.")

    if embedding_model:
        vector_db = await run_in_threadpool(load_vector_db)
        if vector_db is None:
            logger.warning("Không thể tải vector database.")

    ollama_llm = await run_in_threadpool(load_ollama_llm)
    if ollama_llm and vector_db:
        retriever = vector_db.as_retriever(search_kwargs={"k": 5})
        rag_chain = await run_in_threadpool(create_rag_chain, ollama_llm, retriever)
        if rag_chain:
            logger.info("Chuỗi Ollama RAG đã sẵn sàng.")

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
            "ollama_rag": rag_chain is not None,
            "ollama_model": OLLAMA_MODEL,
        },
        "endpoints": {"chat": "POST /chat (Ollama Local LLM)"},
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
