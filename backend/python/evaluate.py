"""
evaluate.py - Hệ thống đánh giá hiệu năng RAG Chatbot Ẩm Thực Đà Nẵng
=========================================================================
Tính toán Precision, Recall, F2 Score với Fuzzy Matching (difflib).

Phương pháp:
- So khớp tên quán bằng SequenceMatcher (ngưỡng mặc định ≥ 0.80)
- Greedy matching: mỗi quán Ground Truth chỉ khớp tối đa 1 quán Retrieved
- Hỗ trợ thêm chỉ số Mention Rate (tỷ lệ nhắc đến trong toàn bộ response)
- Hỗ trợ tính latency percentile (P50, P95, P99)
"""
import difflib
import re
import sys
import statistics
from typing import List, Dict, Optional

# Fix Windows console utf-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


# ---------------------------------------------------------------------------
# Chuẩn hoá & So khớp mờ (Fuzzy Matching)
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """
    Chuẩn hóa tên quán ăn để so sánh công bằng.

    Bước xử lý:
      1. Lowercase + strip
      2. Bỏ dấu ngoặc kép và dấu ngoặc vuông
      3. Bỏ emoji (Unicode range)
      4. Gộp khoảng trắng liên tiếp
      5. Bỏ dấu gạch ngang thừa ở đầu/cuối
    """
    name = name.strip().lower()
    # Bỏ dấu ngoặc kép, ngoặc vuông
    name = re.sub(r'[""\'\"\'\\[\\]]+', '', name)
    # Bỏ emoji (giữ lại ký tự tiếng Việt, ASCII, dấu gạch ngang)
    name = re.sub(
        r'[^\w\s\-àáảãạăắằẵặâấầẩẫậèéẻẽẹêếềểễệ'
        r'ìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữự'
        r'ỳýỷỹỵđ]',
        '', name
    )
    # Gộp khoảng trắng
    name = re.sub(r'\s+', ' ', name).strip()
    # Bỏ dấu gạch ngang ở đầu/cuối
    name = name.strip('-').strip()
    return name


def fuzzy_score(name1: str, name2: str) -> float:
    """Tính điểm tương đồng giữa 2 chuỗi (0.0 → 1.0)."""
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    if not n1 or not n2:
        return 0.0
    return difflib.SequenceMatcher(None, n1, n2).ratio()


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
# Latency Metrics
# ---------------------------------------------------------------------------

def calculate_latency_stats(latencies: List[float]) -> Dict[str, float]:
    """
    Tính toán thống kê latency chi tiết.

    Trả về dict gồm:
      mean, median, min, max, p95, p99, stdev
    """
    if not latencies:
        return {}

    sorted_lat = sorted(latencies)
    n = len(sorted_lat)

    def percentile(p: float) -> float:
        """Tính percentile thứ p (0-100)."""
        idx = (p / 100) * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return sorted_lat[lo] + frac * (sorted_lat[hi] - sorted_lat[lo])

    result = {
        "mean": round(statistics.mean(latencies), 2),
        "median": round(statistics.median(latencies), 2),
        "min": round(min(latencies), 2),
        "max": round(max(latencies), 2),
        "p95": round(percentile(95), 2),
        "p99": round(percentile(99), 2),
    }
    if n >= 2:
        result["stdev"] = round(statistics.stdev(latencies), 2)
    return result


# ---------------------------------------------------------------------------
# Per-question scoring (dùng cho detailed report)
# ---------------------------------------------------------------------------

def score_single_question(
    retrieved: List[str],
    ground_truth: List[str],
    response: str,
    latency: float = 0.0,
    threshold: float = 0.80,
) -> Dict[str, object]:
    """
    Chấm điểm cho 1 câu hỏi đơn lẻ.

    Trả về dict gồm:
      precision, recall, f2, mention_rate, latency, is_hit
    """
    metrics = calculate_retrieval_metrics(retrieved, ground_truth, threshold)
    mention = check_mention_in_response(response, ground_truth)

    return {
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f2": metrics["f2"],
        "mention_rate": mention,
        "latency": latency,
        "is_hit": metrics["recall"] > 0,
    }


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

    print("\nLatency stats:")
    lat_stats = calculate_latency_stats([12.5, 15.2, 8.1, 20.3, 18.7, 10.0, 25.1, 13.4])
    for k, v in lat_stats.items():
        print(f"  {k:12s}: {v}")

    print("\nPer-question scoring:")
    q_score = score_single_question(
        retrieved=["Bún Chả Cá Bà Phi"],
        ground_truth=["Bún Chả Cá Bà Phi"],
        response="**Quán:** Bún Chả Cá Bà Phi\n**Địa chỉ:** 123 ABC",
        latency=15.2,
    )
    for k, v in q_score.items():
        print(f"  {k:12s}: {v}")
