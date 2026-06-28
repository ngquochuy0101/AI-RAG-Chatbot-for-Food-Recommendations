"""
evaluate.py - Hệ thống đánh giá hiệu năng RAG Chatbot Ẩm Thực Đà Nẵng
=========================================================================
Tính toán Precision, Recall, F2 Score với Fuzzy Matching (difflib).

Phương pháp:
- So khớp tên quán bằng SequenceMatcher (ngưỡng mặc định ≥ 0.80)
- Greedy matching: mỗi quán Ground Truth chỉ khớp tối đa 1 quán Retrieved
- Hỗ trợ thêm chỉ số Mention Rate (tỷ lệ nhắc đến trong toàn bộ response)
"""
import difflib
import re
import sys
from typing import List, Dict

# Fix Windows console utf-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


# ---------------------------------------------------------------------------
# Chuẩn hoá & So khớp mờ (Fuzzy Matching)
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """Chuẩn hóa tên quán ăn để so sánh công bằng."""
    name = name.strip().lower()
    name = re.sub(r'[""\'\"\']+', '', name)   # Bỏ dấu ngoặc kép
    name = re.sub(r'\s+', ' ', name)           # Gộp khoảng trắng liên tiếp
    return name


def fuzzy_score(name1: str, name2: str) -> float:
    """Tính điểm tương đồng giữa 2 chuỗi (0.0 → 1.0)."""
    return difflib.SequenceMatcher(
        None, normalize_name(name1), normalize_name(name2)
    ).ratio()


# ---------------------------------------------------------------------------
# Hàm tính điểm Truy hồi (Retrieval Metrics)
# ---------------------------------------------------------------------------

def calculate_retrieval_metrics(
    retrieved_names: List[str],
    ground_truth_names: List[str],
    threshold: float = 0.80
) -> Dict[str, float]:
    """
    Tính Precision, Recall và F2 với Fuzzy Matching.

    Công thức:
        Precision = TP / |retrieved|
        Recall    = TP / |ground_truth|
        F2        = (5 × P × R) / (4P + R)

    Greedy matching: ưu tiên các cặp có điểm tương đồng cao nhất trước,
    mỗi GT chỉ khớp tối đa 1 retrieved và ngược lại.
    """
    if not ground_truth_names:
        return {"precision": 0.0, "recall": 0.0, "f2": 0.0}
    if not retrieved_names:
        return {"precision": 0.0, "recall": 0.0, "f2": 0.0}

    # Tìm tất cả các cặp (retrieved_i, gt_j) vượt ngưỡng
    candidate_pairs = []
    for i, ret in enumerate(retrieved_names):
        for j, gt in enumerate(ground_truth_names):
            score = fuzzy_score(ret, gt)
            if score >= threshold:
                candidate_pairs.append((score, i, j))

    # Greedy: sắp xếp giảm dần theo score, gán từng cặp
    candidate_pairs.sort(reverse=True)
    matched_ret = set()
    matched_gt = set()
    for _score, i, j in candidate_pairs:
        if i not in matched_ret and j not in matched_gt:
            matched_ret.add(i)
            matched_gt.add(j)

    tp = len(matched_gt)
    precision = tp / len(retrieved_names)
    recall = tp / len(ground_truth_names)

    if precision + recall == 0:
        f2 = 0.0
    else:
        f2 = (5 * precision * recall) / ((4 * precision) + recall)

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f2": round(f2, 4),
    }


# ---------------------------------------------------------------------------
# Chỉ số bổ sung: Tỷ lệ nhắc đến (Mention Rate)
# ---------------------------------------------------------------------------

def check_mention_in_response(
    response_text: str,
    ground_truth_names: List[str],
) -> float:
    """
    Kiểm tra tên quán Ground Truth có xuất hiện (substring) trong response.

    Chỉ số này đo lường khả năng FAISS retrieval bất kể LLM có format
    đúng cấu trúc hay không. Nếu Mention Rate cao hơn Recall nhiều,
    nghĩa là lỗi nằm ở bước trích xuất / format chứ không phải retrieval.
    """
    if not response_text or not ground_truth_names:
        return 0.0

    response_norm = normalize_name(response_text)
    mentioned = sum(
        1 for gt in ground_truth_names
        if normalize_name(gt) in response_norm
    )
    return mentioned / len(ground_truth_names)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== DEMO HỆ THỐNG ĐÁNH GIÁ ===\n")

    # Test fuzzy matching
    pairs = [
        ("Bún Chả Cá Bà Phi", "bún chả cá bà phi"),
        ("Cháo Lòng Kho Đạn", "Cháo Lòng - Kho Đạn"),
        ("Seoul - Mì Cay 7 Cấp Độ", "Seoul Mì Cay 7 Cấp Độ"),
        ("Bánh Mì Tiến Thành", "Bánh Mì Tiến Thành - Phan Châu Trinh"),
    ]
    print("Fuzzy scores:")
    for a, b in pairs:
        print(f"  {a:40s} ↔ {b:40s} → {fuzzy_score(a, b):.2f}")

    print("\nRetrieval metrics (fuzzy):")
    scores = calculate_retrieval_metrics(
        ["Bún Chả Cá Bà Phi", "Mì Quảng 1A"],
        ["Bún Chả Cá Bà Phi", "Bún Chả Cá Nguyễn Chí Thanh"],
    )
    for k, v in scores.items():
        print(f"  {k:12s}: {v:.4f}")
