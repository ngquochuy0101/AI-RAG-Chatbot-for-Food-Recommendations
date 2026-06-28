"""
generate_test_cases.py - Sinh bộ test tự động từ data_RAG.csv
==============================================================
Lấy ngẫu nhiên N quán ăn, tạo câu hỏi tự nhiên, lưu thành JSON.

Mỗi test case gồm:
  question                : Câu hỏi (input gửi cho chatbot)
  context                 : Thông tin gốc từ CSV (chỉ để debug)
  ground_truth_restaurants: Đáp án đúng (tên quán cần tìm)
  ai_response             : Để trống (benchmark sẽ điền)
  retrieved_restaurants    : Để trống (benchmark sẽ điền)
"""
import pandas as pd
import json
import random
import os
import sys

# Fix Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

CSV_PATH = "../../data/raw/data_RAG.csv"
OUTPUT_PATH = "../../data/test/test_dataset.json"

# Câu hỏi tự nhiên, đa dạng phong cách
QUESTION_TEMPLATES = [
    # --- Test Pure Retrieval (Chỉ gõ tên quán) ---
    "{name}",
    "Quán {name}",
    
    # --- Hỏi trực tiếp tên quán ---
    "Quán {name} có ngon không? Giá bao nhiêu?",
    "Cho tôi biết về quán {name}.",
    "{name} ở đâu? Mở cửa lúc mấy giờ?",
    "Review quán {name} giúp tôi.",
    "Quán {name} có gì đặc biệt?",
    "Tôi muốn ăn ở {name}, giá cả thế nào?",
    "Gợi ý quán {name} đi, nó nằm ở đâu?",
    
    # --- Hỏi đánh giá ---
    "Quán {name} điểm đánh giá bao nhiêu?",
    "Mọi người review quán {name} ra sao?",
    
    # --- Hỏi chi tiết ---
    "Cho tôi thông tin chi tiết quán {name}.",
    "Quán {name} nằm ở địa chỉ nào, giá cả ra sao?",
    "Tìm hiểu giúp tôi quán {name}, giờ mở cửa và ở đâu?",
]


def generate_test_dataset(n_samples: int = 100, seed: int = 42):
    """Sinh bộ test từ CSV."""
    if not os.path.exists(CSV_PATH):
        print(f"❌ Không tìm thấy {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)

    # Lọc dòng trống
    df = df.dropna(subset=["Tên"])
    df = df[df["Tên"].str.strip() != ""]

    n_samples = min(n_samples, len(df))
    sampled = df.sample(n=n_samples, random_state=seed)

    random.seed(seed)
    test_cases = []

    for _, row in sampled.iterrows():
        name = str(row.get("Tên", "")).strip()
        address = str(row.get("Địa chỉ", "")).strip()
        price = str(row.get("Giá tiền", "")).strip()
        rating = str(row.get("Đánh giá", "")).strip()

        if not name or name.lower() == "nan":
            continue

        question = random.choice(QUESTION_TEMPLATES).format(name=name)
        context = f"Tên: {name}. Địa chỉ: {address}. Giá: {price}. Đánh giá: {rating}."

        test_cases.append({
            "question": question,
            "context": context,
            "ground_truth_restaurants": [name],
            "ai_response": "",
            "retrieved_restaurants": [],
        })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(test_cases, f, ensure_ascii=False, indent=4)

    print(f"✅ Đã tạo {len(test_cases)} câu hỏi test → {OUTPUT_PATH}")


if __name__ == "__main__":
    generate_test_dataset()
