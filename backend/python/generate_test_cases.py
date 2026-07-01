"""
generate_test_cases.py - Sinh bộ test tự động từ data_RAG.csv
==============================================================
Lấy ngẫu nhiên N quán ăn, tạo câu hỏi tự nhiên, lưu thành JSON.

Mỗi test case gồm:
  question                : Câu hỏi (input gửi cho chatbot)
  context                 : Thông tin gốc từ CSV (chỉ để debug)
  ground_truth_restaurants: Đáp án đúng (tên quán cần tìm)
  category                : Loại câu hỏi (direct/review/detail/category/greeting)
  ai_response             : Để trống (benchmark sẽ điền)
  retrieved_restaurants    : Để trống (benchmark sẽ điền)
"""
import pandas as pd
import json
import random
import os
import sys
import argparse

# Fix Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

CSV_PATH = "../../data/processed/data_RAG_cleaned.csv"
OUTPUT_PATH = "../../data/test/test_dataset.json"

# ---------------------------------------------------------------------------
# Template câu hỏi phân loại theo category
# ---------------------------------------------------------------------------

# Template map: {category: [(template, requires_fields), ...]}
# requires_fields = danh sách column phải có giá trị hợp lệ
QUESTION_TEMPLATES = {
    "direct": [
        # --- Hỏi trực tiếp / Pure Retrieval ---
        ("{name}", []),
        ("Quán {name}", []),
        ("Cho tôi biết về quán {name}.", []),
        ("Quán {name} có gì đặc biệt?", []),
        ("Gợi ý quán {name} đi, nó nằm ở đâu?", []),
        ("Tôi muốn ăn ở {name}, giá cả thế nào?", []),
    ],
    "review": [
        # --- Hỏi đánh giá / Review ---
        ("Quán {name} có ngon không? Giá bao nhiêu?", []),
        ("Review quán {name} giúp tôi.", []),
        ("Quán {name} điểm đánh giá bao nhiêu?", []),
        ("Mọi người review quán {name} ra sao?", []),
        ("Quán {name} có đáng ăn không? Review thử đi.", []),
    ],
    "detail": [
        # --- Hỏi chi tiết ---
        ("{name} ở đâu? Mở cửa lúc mấy giờ?", []),
        ("Cho tôi thông tin chi tiết quán {name}.", []),
        ("Quán {name} nằm ở địa chỉ nào, giá cả ra sao?", []),
        ("Tìm hiểu giúp tôi quán {name}, giờ mở cửa và ở đâu?", []),
        ("Quán {name} địa chỉ chính xác ở đâu vậy?", []),
    ],
    "category": [
        # --- Hỏi theo loại món ăn (dùng category) ---
        ("Tôi muốn ăn {food_type} ngon ở Đà Nẵng, gợi ý đi!", ["food_type"]),
        ("Ở Đà Nẵng ăn {food_type} ở đâu ngon?", ["food_type"]),
        ("Có quán {food_type} nào ngon không?", ["food_type"]),
        ("Gợi ý quán {food_type} giá rẻ ở Đà Nẵng.", ["food_type"]),
    ],
}

# Danh sách từ khóa loại món ăn phổ biến để extract từ tên quán
FOOD_KEYWORDS = [
    "bún chả cá", "bún bò", "phở", "mì quảng", "bánh mì",
    "bánh xèo", "bánh tráng", "cơm gà", "cơm tấm", "bún riêu",
    "bún mắm", "cháo lòng", "nem nướng", "hải sản", "lẩu",
    "gà nướng", "nướng", "kem", "chè", "trà sữa",
    "bánh canh", "bánh cuốn", "cơm niêu", "bò né",
]


def _extract_food_type(name: str) -> str:
    """Trích xuất loại món ăn từ tên quán (dùng cho category questions)."""
    name_lower = name.lower()
    for keyword in FOOD_KEYWORDS:
        if keyword in name_lower:
            return keyword
    return ""


def generate_test_dataset(n_samples: int = 50, seed: int = 42):
    """
    Sinh bộ test từ CSV.

    - Phân bổ đều câu hỏi theo category
    - Đảm bảo mỗi quán chỉ xuất hiện 1 lần
    """
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

    # Tính phân bổ category
    categories = list(QUESTION_TEMPLATES.keys())
    category_counts = {c: 0 for c in categories}

    for idx, (_, row) in enumerate(sampled.iterrows()):
        name = str(row.get("Tên", "")).strip()
        address = str(row.get("Địa chỉ", "")).strip()
        price = str(row.get("Giá tiền", "")).strip()
        rating = str(row.get("Đánh giá", "")).strip()

        if not name or name.lower() == "nan":
            continue

        # Chọn category theo round-robin để phân bổ đều
        # Ưu tiên category ít câu hỏi nhất
        food_type = _extract_food_type(name)

        # Chọn category
        available_cats = list(categories)
        if not food_type:
            # Loại bỏ "category" nếu không extract được food_type
            available_cats = [c for c in available_cats if c != "category"]

        # Sắp xếp theo count tăng dần để cân bằng
        available_cats.sort(key=lambda c: category_counts[c])
        chosen_cat = available_cats[0]
        category_counts[chosen_cat] += 1

        # Chọn template ngẫu nhiên trong category
        templates = QUESTION_TEMPLATES[chosen_cat]

        # Lọc template phù hợp
        valid_templates = []
        for tmpl, req_fields in templates:
            if "food_type" in req_fields and not food_type:
                continue
            valid_templates.append(tmpl)

        if not valid_templates:
            # Fallback về direct
            chosen_cat = "direct"
            valid_templates = [t for t, _ in QUESTION_TEMPLATES["direct"]]

        template = random.choice(valid_templates)
        question = template.format(name=name, food_type=food_type)

        context = f"Tên: {name}. Địa chỉ: {address}. Giá: {price}. Đánh giá: {rating}."

        test_cases.append({
            "question": question,
            "context": context,
            "category": chosen_cat,
            "ground_truth_restaurants": [name],
            "ai_response": "",
            "retrieved_restaurants": [],
        })

    # Tạo thư mục output nếu chưa có
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(test_cases, f, ensure_ascii=False, indent=4)

    print(f"✅ Đã tạo {len(test_cases)} câu hỏi test → {OUTPUT_PATH}")
    print(f"\n📊 Phân bổ theo category:")
    for cat, count in sorted(category_counts.items()):
        print(f"   {cat:12s}: {count} câu")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sinh bộ test tự động từ data_RAG.csv"
    )
    parser.add_argument(
        "--n_samples", type=int, default=50,
        help="Số lượng câu hỏi test cần sinh (mặc định: 50)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed để đảm bảo reproducibility (mặc định: 42)"
    )
    args = parser.parse_args()
    generate_test_dataset(n_samples=args.n_samples, seed=args.seed)
