import logging
import os
import sys
from contextlib import asynccontextmanager
from html import escape
from typing import Optional, Dict, Any

import markdown
import tempfile
import base64
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
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
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

configure_logging()
logger = logging.getLogger(__name__)

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4-e2b")

ROUTER9_BASE_URL = os.getenv("ROUTER9_BASE_URL", "http://localhost:20128/v1")
ROUTER9_MODEL = os.getenv("ROUTER9_MODEL", "gemini")
ROUTER9_API_KEY = os.getenv("ROUTER9_API_KEY", "dummy")

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
EMBEDDING_MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "embedding", "google-embedding-300-finetuned")
EMBEDDING_MODEL_FALLBACK = os.path.join(BASE_DIR, "models", "saved-embedding-model")
VECTOR_DB_PATH = os.path.join(PROJECT_ROOT, "data", "vectorstores")


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = None
    chat_id: Optional[int] = None
    model: Optional[str] = "ollama"


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
voice_llm = None
voice_rag_chain = None

store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


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
        logger.info("Đang tải model backup: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
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


def load_voice_llm():
    """Load 9router LLM client for voice."""
    logger.info("Đang kết nối 9router LLM cho Voice (model: %s, url: %s)...", ROUTER9_MODEL, ROUTER9_BASE_URL)
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=ROUTER9_MODEL,
            base_url=ROUTER9_BASE_URL,
            api_key=ROUTER9_API_KEY,
            temperature=0.3,
        )
        logger.info("Đã kết nối 9router LLM thành công.")
        return llm
    except ImportError:
        logger.error("Thiếu thư viện langchain-openai. Vui lòng cài đặt: pip install langchain-openai")
        return None
    except Exception:
        logger.exception("Lỗi khi kết nối 9router LLM.")
        return None


def create_rag_chain(llm, retriever):
    """Create RAG chain using Ollama LLM and retrieved context."""
    logger.info("Đang tạo chuỗi Conversational RAG...")
    
    try:
        # 1. Prompt để contextualize câu hỏi
        contextualize_q_system_prompt = (
            "Dựa vào lịch sử trò chuyện và câu hỏi mới nhất của người dùng, "
            "có thể câu hỏi mới tham chiếu đến ngữ cảnh trước đó. "
            "Hãy viết lại một câu hỏi độc lập có thể hiểu được mà không cần lịch sử trò chuyện. "
            "KHÔNG trả lời câu hỏi, chỉ định dạng lại nếu cần, nếu không thì trả về nguyên bản."
        )
        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])
        history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)

        # 2. Prompt cho RAG QA
        qa_system_prompt = """Bạn là chuyên gia ẩm thực Đà Nẵng. Nhiệm vụ: tư vấn quán ăn dựa trên DỮ LIỆU ĐƯỢC CUNG CẤP.

        **QUY TẮC BẮT BUỘC:**
        1. NẾU người dùng chỉ chào hỏi (xin chào, hi, hello...), hãy chào lại thân thiện, giới thiệu bạn là chuyên gia ẩm thực Đà Nẵng và hỏi họ muốn ăn món gì hôm nay.
        2. CHỈ tư vấn về ẩm thực Đà Nẵng. Nếu người dùng hỏi chủ đề hoàn toàn không liên quan đến ẩm thực (thời tiết, toán học...), trả lời: "Xin lỗi, mình chỉ tư vấn về ẩm thực Đà Nẵng thôi nhé!
        3. KHÔNG được bịa thông tin. Chỉ dùng dữ liệu Nếu có. Nếu không có quán phù hợp thì trả lời: "Xin lỗi bạn, hiện tại hệ thống chưa có thông tin về món ăn này. Bạn muốn tìm món khác không?"
        4. Giới hạn gợi ý 3 quán ăn.

        **FORMAT BẮT BUỘC (chỉ dùng khi có quán phù hợp - sử dụng Markdown):**
        **Quán:** [Tên quán chính xác từ dữ liệu]
        **Địa chỉ:** [Địa chỉ]
        **Giá:** [Giá tiền]
        **Đánh giá:** [Điểm]/10
        **Đặc điểm:** [Mô tả ngắn]

        **VÍ DỤ MẪU:**
        Câu hỏi: "Bún chả cá ở đâu ngon?"
        Trả lời:
        **Quán:** Bún chả cá Bà Lữ
        **Địa chỉ:** 66 Lê Hồng Phong, Hải Châu
        **Giá:** 30.000 - 45.000đ
        **Đánh giá:** 8.5/10
        **Đặc điểm:** Nước dùng trong, ngọt tự nhiên, chả cá chiên giòn

        {context}"""
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ])

        question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
        rag_chain_retrieval = create_retrieval_chain(history_aware_retriever, question_answer_chain)

        # 3. Bọc chain với bộ nhớ
        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain_retrieval,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer"
        )

        logger.info("Đã tạo chuỗi Conversational RAG thành công.")
        return conversational_rag_chain
    except Exception:
        logger.exception("Lỗi khi tạo chuỗi RAG.")
        return None


def markdown_to_html(text: str) -> str:
    """Chuyển đổi text Markdown tiêu chuẩn thành HTML"""
    # Sử dụng thư viện markdown với các extension hỗ trợ ngắt dòng và table
    html = markdown.markdown(text, extensions=['extra', 'nl2br'])
    return f'<div class="markdown-body">\n{html}\n</div>'

def process_audio_to_text(audio_file_path: str) -> str:
    """Chuyển đổi file âm thanh (bất kỳ) thành văn bản dùng mô hình Sherpa-Vietnamese-ASR Offline"""
    try:
        from local_asr import process_audio_sherpa
    except ImportError:
        from .local_asr import process_audio_sherpa
    return process_audio_sherpa(audio_file_path)

def process_text_to_audio(text: str) -> str:
    """Chuyển đổi văn bản thành giọng nói (gTTS) và trả về Base64 string"""
    logger.info("Đang xử lý TTS...")
    # Bỏ các ký tự Markdown khỏi văn bản đọc
    clean_text = text.replace('*', '').replace('#', '').replace('\n', ' ')
    
    tts = gTTS(text=clean_text, lang='vi', slow=False)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        temp_path = fp.name
        
    tts.save(temp_path)
    
    with open(temp_path, "rb") as audio_file:
        audio_bytes = audio_file.read()
        base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
        
    os.remove(temp_path)
    logger.info("Hoàn tất TTS.")
    return base64_audio


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize heavy resources at startup and release on shutdown."""
    global embedding_model, vector_db, ollama_llm, rag_chain, voice_llm, voice_rag_chain

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
    voice_llm = await run_in_threadpool(load_voice_llm)

    if ollama_llm and vector_db:
        retriever = vector_db.as_retriever(search_kwargs={"k": 15})
        rag_chain = await run_in_threadpool(create_rag_chain, ollama_llm, retriever)
        if rag_chain:
            logger.info("Chuỗi Ollama RAG đã sẵn sàng.")

    if voice_llm and vector_db:
        retriever = vector_db.as_retriever(search_kwargs={"k": 15})
        voice_rag_chain = await run_in_threadpool(create_rag_chain, voice_llm, retriever)
        if voice_rag_chain:
            logger.info("Chuỗi Voice RAG (9router) đã sẵn sàng.")

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
        current_chain = voice_rag_chain if request.model == "9router" else rag_chain
        if current_chain is None:
            raise HTTPException(status_code=503, detail=f"Chuỗi RAG cho model '{request.model}' chưa sẵn sàng")

        user_message = request.message.strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="Tin nhắn không được để trống")

        logger.info(
            "Nhận tin nhắn chat. user_id=%s chat_id=%s message_len=%s",
            request.user_id,
            request.chat_id,
            len(user_message),
        )

        session_id = str(request.chat_id) if request.chat_id else (str(request.user_id) if request.user_id else "default_session")
        
        result = await run_in_threadpool(
            current_chain.invoke, 
            {"input": user_message}, 
            {"configurable": {"session_id": session_id}}
        )
        response_text = result["answer"]
        
        if not response_text.strip():
            response_text = "Xin lỗi bạn, hiện tại hệ thống chưa có thông tin về món ăn này. Bạn có muốn thử món khác không? 🍲"

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
    except Exception as e:
        error_msg = str(e)
        logger.exception("Lỗi tại endpoint /chat")
        if "Network is unreachable" in error_msg or "ConnectError" in error_msg:
            return ChatResponse(
                success=False,
                response="Máy chủ AI (Ollama) không khả dụng. Vui lòng kiểm tra Ollama đã chạy chưa.",
                response_html='<div class="alert-danger">🤖 Máy chủ AI (Ollama) chưa sẵn sàng. Hãy chắc chắn Ollama đang chạy trên host và bind trên 0.0.0.0:11434. Thử lại sau vài giây!</div>',
                intent="error",
                data=None,
            )
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

@app.post("/chat/speech")
async def chat_speech(audio: UploadFile = File(...)):
    """Endpoint xử lý chat bằng giọng nói (Speech-to-Speech)"""
    try:
        current_chain = voice_rag_chain if voice_rag_chain else rag_chain
        if current_chain is None:
            raise HTTPException(status_code=503, detail="Cả chuỗi Voice RAG và Ollama RAG đều chưa sẵn sàng")

        # Lưu file tải lên vào temp
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            fp.write(await audio.read())
            temp_input_path = fp.name
            
        try:
            # 1. Speech to Text
            user_text = await run_in_threadpool(process_audio_to_text, temp_input_path)
        except ValueError as e:
            os.remove(temp_input_path)
            raise HTTPException(status_code=400, detail=str(e))
            
        os.remove(temp_input_path)
        
        if not user_text.strip():
            raise HTTPException(status_code=400, detail="Không nghe thấy bạn nói gì.")
            
        # 2. Text to Text (LLM / RAG)
        logger.info(f"Voice RAG Chain xử lý yêu cầu (từ giọng nói): {user_text}")
        session_id = "default_voice_session"
        result = await run_in_threadpool(
            current_chain.invoke, 
            {"input": user_text},
            {"configurable": {"session_id": session_id}}
        )
        response_text = result["answer"]
        
        # 3. Text to HTML
        response_html = await run_in_threadpool(markdown_to_html, response_text)
        
        # 4. Text to Speech
        ai_audio_base64 = await run_in_threadpool(process_text_to_audio, response_text)

        return {
            "success": True,
            "user_text": user_text,
            "ai_text": response_text,
            "ai_text_html": response_html,
            "ai_audio_base64": ai_audio_base64
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi xử lý Speech-to-Speech: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Đã xảy ra lỗi không xác định từ hệ thống.")
