import logging
import os

from langchain_community.document_loaders import CSVLoader
from langchain_community.vectorstores import FAISS

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

configure_logging()
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DATA_PATH = os.path.join(BASE_DIR, "data", "data_RAG.csv")
VECTOR_DB_PATH = os.path.join(BASE_DIR, "vectorstores")
EMBEDDING_MODEL_PATH = os.path.join(BASE_DIR, "models", "saved-embedding-model")


def validate_torch(min_version: tuple[int, int, int] = MIN_TORCH_VERSION) -> None:
    """Raise clear error if torch runtime is incompatible."""
    compatible, current_version = is_torch_compatible(min_version)
    min_label = min_version_label(min_version)
    if not compatible:
        if not current_version:
            raise RuntimeError(
                f"PyTorch chưa được cài đặt. Cần torch>={min_label} để tải embedding model."
            )

        raise RuntimeError(
            f"PyTorch {current_version} không tương thích. Cần tối thiểu torch>={min_label}."
        )


def create_db_from_files() -> FAISS:
    """Build and persist FAISS vector database from CSV source."""
    logger.info("Loading data from: %s", CSV_DATA_PATH)
    loader = CSVLoader(file_path=CSV_DATA_PATH, encoding="utf-8")
    documents = loader.load()

    # Mỗi dòng CSV là một đơn vị quán ăn hoàn chỉnh, không split thêm.
    chunks = documents
    logger.info("Số lượng quán ăn (documents): %s", len(chunks))

    validate_torch()

    logger.info("Loading embedding model from: %s", EMBEDDING_MODEL_PATH)
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_PATH,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    except Exception as error:
        logger.warning("Failed to load local model at %s: %s", EMBEDDING_MODEL_PATH, error)
        logger.warning("Fallback to 'sentence-transformers/all-MiniLM-L6-v2'")
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        except Exception as fallback_error:
            if "name 'nn' is not defined" in str(fallback_error):
                torch_version = get_torch_version() or "not installed"
                min_label = min_version_label(MIN_TORCH_VERSION)
                raise RuntimeError(
                    "Không thể tải embedding model vì môi trường torch không tương thích "
                    f"(phiên bản hiện tại: {torch_version}, yêu cầu >= {min_label})."
                ) from fallback_error
            raise

    logger.info("Creating FAISS index...")
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(VECTOR_DB_PATH)
    logger.info("Vector database saved to: %s", VECTOR_DB_PATH)
    return db


if __name__ == "__main__":
    logger.info("Bắt đầu tạo vector database...")
    create_db_from_files()
    logger.info("Tạo vector database hoàn tất.")