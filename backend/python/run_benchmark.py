"""
run_benchmark.py - Chạy benchmark RAG Chatbot Ẩm Thực qua API
================================================================
Gửi N câu hỏi → Thu thập câu trả lời → Trích xuất tên quán → Chấm điểm.

Hỗ trợ 3 chế độ:
  python run_benchmark.py                # Gửi request mới tới API
  python run_benchmark.py --reeval       # Tính lại điểm từ kết quả cũ (tức thì)
  python run_benchmark.py --detailed     # In chi tiết từng câu hỏi

API endpoint: POST /chat  (theo main.py)
  Request:  {"message": str, "user_id": int|null, "chat_id": int|null}
  Response: {"success": bool, "response": str, "response_html": str, ...}
"""
import json
import time
import re
import sys
import statistics
import argparse
import os
from datetime import datetime

# Fix Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import requests
except ImportError:
    print("Cần cài requests: pip install requests")
    sys.exit(1)

from evaluate import (
    calculate_retrieval_metrics,
    calculate_latency_stats,
    check_mention_in_response,
    fuzzy_score,
    normalize_name,
    score_single_question,
)

# ---------------------------------------------------------------------------
# Cấu hình - phải khớp với main.py endpoints
# ---------------------------------------------------------------------------

API_BASE_URL = os.getenv("BENCHMARK_API_URL", "http://localhost:8001")
API_CHAT_URL = f"{API_BASE_URL}/chat"
API_HEALTH_URL = f"{API_BASE_URL}/health"

INPUT_FILE = "../../data/test/test_dataset.json"
OUTPUT_FILE = "../../data/test/test_dataset_evaluated.json"
REPORT_FILE = "../../data/test/benchmark_report.json"


# ---------------------------------------------------------------------------
# Kiểm tra API Health (theo main.py GET /health)
# ---------------------------------------------------------------------------

def check_api_health() -> bool:
    """
    Kiểm tra API sẵn sàng trước khi chạy benchmark.
    Gọi GET /health theo main.py, kiểm tra:
      - status == "healthy"
      - models.ollama_rag == True
    """
    try:
        resp = requests.get(API_HEALTH_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        status = data.get("status", "")
        models = data.get("models", {})

        if status != "healthy":
            print(f"⚠ API status: {status} (cần 'healthy')")
            return False

        if not models.get("ollama_rag", False):
            print("⚠ RAG chain chưa sẵn sàng (ollama_rag=False)")
            print(f"   Thông tin models: {json.dumps(models, ensure_ascii=False)}")
            return False

        embedding_ok = models.get("embedding", False)
        vector_db_ok = models.get("vector_db", False)
        ollama_model = models.get("ollama_model", "unknown")

        print(f"✅ API healthy | Model: {ollama_model}")
        print(f"   Embedding: {'✓' if embedding_ok else '✗'} | "
              f"VectorDB: {'✓' if vector_db_ok else '✗'} | "
              f"RAG: ✓")
        return True

    except requests.ConnectionError:
        print(f"❌ Không thể kết nối tới {API_HEALTH_URL}")
        print("   Hãy chắc chắn API đang chạy (docker-compose up hoặc python main.py)")
        return False
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra health: {e}")
        return False


# ---------------------------------------------------------------------------
# Gọi API Chat (theo main.py POST /chat)
# ---------------------------------------------------------------------------

def call_chat_api(question: str, timeout: int = 120, model: str = "ollama") -> dict:
    """
    Gọi POST /chat theo format ChatRequest trong main.py.

    Request body:
        {"message": str, "user_id": null, "chat_id": null, "model": str}
    Response body (ChatResponse):
        {"success": bool, "response": str, "response_html": str,
         "intent": str, "data": dict|null}

    Returns:
        {"response": str, "success": bool, "intent": str, "latency": float}
    """
    start = time.time()
    try:
        resp = requests.post(
            API_CHAT_URL,
            json={
                "message": question,
                "user_id": None,
                "chat_id": None,
                "model": model,
            },
            timeout=timeout,
        )
        latency = time.time() - start
        resp.raise_for_status()
        data = resp.json()

        return {
            "response": data.get("response", ""),
            "success": data.get("success", False),
            "intent": data.get("intent", ""),
            "latency": round(latency, 2),
        }

    except requests.Timeout:
        return {
            "response": "",
            "success": False,
            "intent": "error",
            "latency": round(time.time() - start, 2),
            "error": f"Timeout sau {timeout}s",
        }
    except Exception as e:
        return {
            "response": "",
            "success": False,
            "intent": "error",
            "latency": round(time.time() - start, 2),
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Trích xuất tên quán ăn từ câu trả lời AI
# ---------------------------------------------------------------------------
# AI response format theo prompt trong main.py (create_rag_chain):
#
#   **Quán:** [Tên quán chính xác từ dữ liệu]
#   **Địa chỉ:** [Địa chỉ]
#   **Giá:** [Giá tiền]
#   **Đánh giá:** [Điểm]/10
#   **Đặc điểm:** [Mô tả ngắn]
#
# Tuy nhiên LLM có thể format khác (numbered list, bold header, etc.)
# ---------------------------------------------------------------------------

def extract_restaurants_from_response(response_text: str) -> list:
    """
    Trích xuất tên quán ăn từ câu trả lời AI.

    Hỗ trợ nhiều format mà LLM có thể output:

    Pattern 1 (format chuẩn từ prompt main.py):
        **Quán:** Bún Chả Cá Bà Lữ

    Pattern 2 (bold header + colon):
        **Tên quán:** Bún Chả Cá Bà Lữ

    Pattern 3 (Markdown heading dạng ###):
        ### Bún Chả Cá Bà Lữ

    Pattern 4 (numbered list với bold):
        1. **Bún Chả Cá Bà Lữ**

    Pattern 5 (bullet list với bold):
        * **Rảnh Rảnh - Nướng Bơ Hà Nội:** mô tả

    Pattern 6 (emoji markers):
        🏪 Quán: Bún Chả Cá Bà Lữ
        📍 **Bún Chả Cá Bà Lữ**

    KHÔNG lấy:
      - Dòng chứa "Địa chỉ:", "Giá:", "Đánh giá:", "Đặc điểm:"
      - Tên quá ngắn (< 3 ký tự)
      - Text trùng lặp
    """
    if not response_text:
        return []

    restaurants = []
    seen = set()

    # Danh sách label KHÔNG phải tên quán
    EXCLUDE_LABELS = [
        "địa chỉ", "giá", "đánh giá", "đặc điểm", "mô tả",
        "lưu ý", "mẹo", "ghi chú", "giờ", "liên hệ", "sdt",
        "điện thoại", "website", "menu", "thực đơn",
    ]

    def add_name(name: str):
        """Chuẩn hóa và thêm tên quán vào danh sách."""
        # Bỏ trailing punctuation
        name = name.strip().rstrip('.:,;!?').strip()
        # Bỏ prefix thừa
        for prefix in ['Quán:', 'Tên quán:', 'Tên:', 'quán:', 'tên:']:
            if name.lower().startswith(prefix.lower()):
                name = name[len(prefix):].strip()
        # Bỏ markdown bold
        name = name.replace('**', '').strip()
        # Validate
        if not name or len(name) < 3:
            return
        # Kiểm tra không phải label
        name_lower = name.lower()
        for excl in EXCLUDE_LABELS:
            if name_lower.startswith(excl):
                return
        # Dedup
        key = normalize_name(name)
        if key not in seen:
            seen.add(key)
            restaurants.append(name)

    # === Pattern 1: **Quán:** Tên quán (format chuẩn từ main.py prompt) ===
    for m in re.findall(
        r'\*\*(?:Quán|Tên quán|Tên)\s*:\*\*\s*(.+?)(?:\n|$)',
        response_text
    ):
        add_name(m)

    # === Pattern 2: **Quán:** (bold cả label+colon) ===
    for m in re.findall(
        r'\*\*(?:Quán|Tên quán)\*\*\s*:\s*(.+?)(?:\n|$)',
        response_text
    ):
        add_name(m)

    # === Pattern 3: Markdown heading ### Restaurant Name ===
    for m in re.findall(r'^#{1,4}\s+(.+?)$', response_text, re.MULTILINE):
        candidate = m.strip()
        # Bỏ heading mà là category (ví dụ: ### Bánh Mì, ### Hải Sản)
        # Chỉ lấy nếu tên >= 5 ký tự (loại trừ heading ngắn)
        if len(candidate) >= 5:
            candidate_lower = candidate.lower().replace('**', '').strip()
            is_label = any(candidate_lower.startswith(excl) for excl in EXCLUDE_LABELS)
            if not is_label:
                add_name(candidate)

    # === Pattern 4: Numbered list: 1. **Name** hoặc 1. **Name:** mô tả ===
    for m in re.findall(
        r'^\d+\.\s+\*\*(.+?)\*\*',
        response_text, re.MULTILINE
    ):
        add_name(m)

    # === Pattern 5: Bullet list: * **Name:** mô tả hoặc - **Name** ===
    for m in re.findall(
        r'^[\*\-]\s+\*\*(.+?)\*\*',
        response_text, re.MULTILINE
    ):
        add_name(m)

    # === Pattern 6: Emoji markers (🏪, 📍) ===
    for m in re.findall(r'🏪\s*(?:Quán|Tên quán|Tên)?\s*:?\s*(.+)', response_text):
        add_name(m)
    for m in re.findall(r'📍\s*\*?\*?(.+?)\*?\*?\s*$', response_text, re.MULTILINE):
        candidate = m.strip()
        if not any(candidate.lower().startswith(excl) for excl in EXCLUDE_LABELS):
            add_name(candidate)

    return restaurants


# ---------------------------------------------------------------------------
# Chạy Benchmark
# ---------------------------------------------------------------------------

def run_benchmark(reeval: bool = False, detailed: bool = False, model: str = "ollama"):
    """
    Chạy benchmark chính hoặc tính lại điểm từ kết quả cũ.

    Args:
        reeval: True = tính lại từ file cũ, không gọi API
        detailed: True = in chi tiết từng câu hỏi
        model: Model name ('ollama' or '9router')
    """
    
    # Adjust file paths based on model
    current_output_file = OUTPUT_FILE if model == "ollama" else OUTPUT_FILE.replace(".json", f"_{model}.json")
    current_report_file = REPORT_FILE if model == "ollama" else REPORT_FILE.replace(".json", f"_{model}.json")

    if reeval:
        # ---- Chế độ tính lại (không gọi API) ----
        print(f"📂 Đang đọc kết quả cũ từ {current_output_file}...")
        try:
            with open(current_output_file, "r", encoding="utf-8") as f:
                dataset = json.load(f)
        except FileNotFoundError:
            print(f"❌ Không tìm thấy {current_output_file}. Hãy chạy benchmark trước.")
            return

        # Re-extract với logic cải tiến (khớp format main.py)
        for item in dataset:
            item["retrieved_restaurants"] = extract_restaurants_from_response(
                item.get("ai_response", "")
            )
        print(f"✅ Đã trích xuất lại tên quán cho {len(dataset)} câu.\n")

    else:
        # ---- Chế độ chạy mới (gọi API) ----
        # Kiểm tra API health trước
        print("🔍 Kiểm tra API health...")
        if not check_api_health():
            print("\n❌ API chưa sẵn sàng. Hãy kiểm tra và thử lại.")
            return
        print()

        # Đọc test dataset
        print(f"📂 Đang đọc dữ liệu từ {INPUT_FILE}...")
        try:
            with open(INPUT_FILE, "r", encoding="utf-8") as f:
                dataset = json.load(f)
        except FileNotFoundError:
            print(f"❌ Không tìm thấy {INPUT_FILE}. Hãy chạy generate_test_cases.py trước.")
            return

        total = len(dataset)
        est_minutes = total * 20 // 60
        print(f"🚀 Bắt đầu benchmark {total} câu (ước tính ~{est_minutes} phút)...\n")

        error_count = 0
        for i, item in enumerate(dataset, 1):
            question = item.get("question", "")
            category = item.get("category", "unknown")
            label = question[:60] + "..." if len(question) > 60 else question
            print(f"[{i:3d}/{total}] [{category:8s}] {label}")

            # Gọi API theo format main.py POST /chat
            result = call_chat_api(question, model=model)

            ai_text = result["response"]
            latency = result["latency"]

            if not result["success"]:
                error_msg = result.get("error", "API returned success=False")
                print(f"         ⚠ Lỗi: {error_msg}")
                error_count += 1

            item["ai_response"] = ai_text
            item["latency_seconds"] = latency
            item["api_success"] = result["success"]
            item["api_intent"] = result["intent"]
            item["retrieved_restaurants"] = extract_restaurants_from_response(ai_text)

            n = len(item["retrieved_restaurants"])
            status = "✓" if result["success"] else "✗"
            print(f"         {status} {latency:.1f}s | Trích xuất: {n} quán"
                  + (f" → {item['retrieved_restaurants']}" if n > 0 else ""))

        # Lưu kết quả
        with open(current_output_file, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=4)
        print(f"\n💾 Đã lưu kết quả vào {current_output_file}")

        if error_count:
            print(f"⚠ Có {error_count}/{total} câu bị lỗi API.")

    # ---- Tính toán & In báo cáo ----
    report = _compute_report(dataset)
    _print_report(report, detailed=detailed)

    # Lưu report JSON
    report["timestamp"] = datetime.now().isoformat()
    report["model"] = model
    with open(current_report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=4)
    print(f"\n📄 Report JSON đã lưu tại {current_report_file}")


# ---------------------------------------------------------------------------
# Tính toán báo cáo
# ---------------------------------------------------------------------------

def _compute_report(dataset: list) -> dict:
    """Tính toán tất cả metrics từ dataset đã đánh giá."""

    all_scores = []
    latencies = []
    error_count = 0
    category_stats = {}  # {category: {scores...}}

    for item in dataset:
        retrieved = item.get("retrieved_restaurants", [])
        gt = item.get("ground_truth_restaurants", [])
        response = item.get("ai_response", "")
        lat = item.get("latency_seconds", 0)
        category = item.get("category", "unknown")
        api_success = item.get("api_success", True)

        if not api_success:
            error_count += 1

        # Chấm điểm từng câu
        q_score = score_single_question(retrieved, gt, response, lat)
        all_scores.append(q_score)

        if lat > 0:
            latencies.append(lat)

        # Nhóm theo category
        if category not in category_stats:
            category_stats[category] = []
        category_stats[category].append(q_score)

    total = len(dataset)

    # Macro-average
    avg_p = statistics.mean([s["precision"] for s in all_scores]) if all_scores else 0
    avg_r = statistics.mean([s["recall"] for s in all_scores]) if all_scores else 0
    avg_f2 = statistics.mean([s["f2"] for s in all_scores]) if all_scores else 0
    avg_mention = statistics.mean([s["mention_rate"] for s in all_scores]) if all_scores else 0
    hit_count = sum(1 for s in all_scores if s["is_hit"])
    hit_rate = hit_count / total if total else 0

    # Latency stats
    lat_stats = calculate_latency_stats(latencies) if latencies else {}

    # Category breakdown
    cat_report = {}
    for cat, scores in category_stats.items():
        cat_n = len(scores)
        cat_report[cat] = {
            "count": cat_n,
            "precision": round(statistics.mean([s["precision"] for s in scores]), 4),
            "recall": round(statistics.mean([s["recall"] for s in scores]), 4),
            "f2": round(statistics.mean([s["f2"] for s in scores]), 4),
            "mention_rate": round(statistics.mean([s["mention_rate"] for s in scores]), 4),
            "hit_rate": round(sum(1 for s in scores if s["is_hit"]) / cat_n, 4),
        }

    return {
        "total_questions": total,
        "error_count": error_count,
        "metrics": {
            "precision": round(avg_p, 4),
            "recall": round(avg_r, 4),
            "f2": round(avg_f2, 4),
            "mention_rate": round(avg_mention, 4),
            "hit_rate": round(hit_rate, 4),
        },
        "latency": lat_stats,
        "category_breakdown": cat_report,
        "per_question": all_scores,
    }


# ---------------------------------------------------------------------------
# In báo cáo
# ---------------------------------------------------------------------------

def _print_report(report: dict, detailed: bool = False):
    """In báo cáo benchmark ra console."""

    w = 65
    metrics = report["metrics"]
    lat = report.get("latency", {})
    cat_report = report.get("category_breakdown", {})
    total = report["total_questions"]
    errors = report["error_count"]

    print("\n" + "=" * w)
    print("   BÁO CÁO KẾT QUẢ ĐÁNH GIÁ  (BENCHMARK REPORT)")
    print("=" * w)

    print(f"\n{'📊 TỔNG QUAN':}")
    print(f"   Model                    : {report.get('model', 'unknown')}")
    print(f"   Số câu truy vấn          : {total}")
    if errors:
        print(f"   Số câu lỗi API           : {errors}")

    if lat:
        print(f"\n{'⏱  THỜI GIAN PHẢN HỒI':}")
        print(f"   Trung bình  (Mean)       : {lat.get('mean', 0):.2f} giây")
        print(f"   Trung vị    (Median)     : {lat.get('median', 0):.2f} giây")
        print(f"   P95                      : {lat.get('p95', 0):.2f} giây")
        print(f"   P99                      : {lat.get('p99', 0):.2f} giây")
        print(f"   Nhanh nhất  (Min)        : {lat.get('min', 0):.2f} giây")
        print(f"   Chậm nhất   (Max)        : {lat.get('max', 0):.2f} giây")
        if 'stdev' in lat:
            print(f"   Độ lệch chuẩn (Stdev)   : {lat.get('stdev', 0):.2f} giây")

    print(f"\n{'📈 ĐIỂM TRUY HỒI (Macro-Average, Fuzzy ≥ 0.80)':}")
    print(f"   Precision                : {metrics['precision']:.4f}  ({metrics['precision']*100:.1f}%)")
    print(f"   Recall                   : {metrics['recall']:.4f}  ({metrics['recall']*100:.1f}%)")
    print(f"   F2 Score                 : {metrics['f2']:.4f}  ({metrics['f2']*100:.1f}%)")

    print(f"\n{'📋 CHỈ SỐ BỔ SUNG':}")
    print(f"   Hit Rate   (Recall > 0)  : {metrics['hit_rate']:.4f}  ({metrics['hit_rate']*100:.1f}%)")
    print(f"   Mention Rate             : {metrics['mention_rate']:.4f}  ({metrics['mention_rate']*100:.1f}%)")

    # Category breakdown
    if cat_report:
        print(f"\n{'📂 PHÂN TÍCH THEO CATEGORY':}")
        print(f"   {'Category':<12} {'N':>4} {'Prec':>7} {'Recall':>7} {'F2':>7} {'Hit%':>7} {'Mention%':>8}")
        print(f"   {'─'*12} {'─'*4} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*8}")
        for cat, stats in sorted(cat_report.items()):
            print(f"   {cat:<12} {stats['count']:>4} "
                  f"{stats['precision']:>6.1%} {stats['recall']:>6.1%} "
                  f"{stats['f2']:>6.1%} {stats['hit_rate']:>6.1%} "
                  f"{stats['mention_rate']:>7.1%}")

    print(f"\n{'💡 GIẢI THÍCH':}")
    print(f"   Precision  : Trong số quán AI gợi ý, bao nhiêu % đúng?")
    print(f"   Recall     : Trong số quán cần tìm, AI tìm được bao nhiêu %?")
    print(f"   F2 Score   : Điểm tổng hợp (ưu tiên Recall, trọng số ×2)")
    print(f"   Hit Rate   : % câu hỏi AI tìm đúng ≥ 1 quán")
    print(f"   Mention    : % câu mà tên quán GT xuất hiện trong response")
    print(f"   P95/P99    : 95%/99% request hoàn thành trong thời gian này")
    print("=" * w)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="RAG Chatbot Benchmark - Đo hiệu năng & chấm điểm"
    )
    parser.add_argument(
        "--reeval",
        action="store_true",
        help="Tính lại điểm từ file kết quả cũ (không gọi API, chạy tức thì)",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="In chi tiết kết quả từng câu hỏi",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="ollama",
        choices=["ollama", "9router"],
        help="Model dùng để benchmark (mặc định: ollama)",
    )
    args = parser.parse_args()
    run_benchmark(reeval=args.reeval, detailed=args.detailed, model=args.model)
