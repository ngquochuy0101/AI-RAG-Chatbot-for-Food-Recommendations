import os
import pandas as pd
# pyrefly: ignore [missing-import]
import emoji
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
INPUT_CSV = os.path.join(PROJECT_ROOT, "data", "raw", "data_RAG.csv")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
OUTPUT_CSV = os.path.join(PROCESSED_DIR, "data_RAG_cleaned.csv")

def preprocess():
    if not os.path.exists(INPUT_CSV):
        logger.error(f"Không tìm thấy file dữ liệu gốc tại: {INPUT_CSV}")
        return

    logger.info(f"Đọc dữ liệu từ: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV, encoding="utf-8")
    
    # Xóa các cột không cần thiết
    columns_to_drop = ['Link', 'Bình luận 1', 'Bình luận 2', 'Bình luận 3','Số review']
    dropped_count = 0
    for col in columns_to_drop:
        if col in df.columns:
            df = df.drop(columns=[col])
            dropped_count += 1
    logger.info(f"Đã xóa {dropped_count} cột chứa thông tin không cần thiết (như Link, Bình luận).")
            
    # Xóa các biểu tượng cảm xúc
    logger.info("Đang loại bỏ các biểu tượng cảm xúc (emoji) khỏi văn bản...")
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(lambda x: emoji.replace_emoji(str(x), replace='') if pd.notnull(x) else x)
            
    # Tạo thư mục chứa dữ liệu đã xử lý nếu chưa có
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    # Lưu ra file mới
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    logger.info(f"Xử lý hoàn tất. Đã lưu dữ liệu sạch tại: {OUTPUT_CSV}")

if __name__ == "__main__":
    logger.info("=== Bắt đầu tiến trình tiền xử lý dữ liệu ===")
    preprocess()
