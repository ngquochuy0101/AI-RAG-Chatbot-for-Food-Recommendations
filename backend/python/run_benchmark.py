"""
run_benchmark.py - Chạy benchmark RAG Chatbot Ẩm Thực qua API
================================================================
Gửi N câu hỏi → Thu thập câu trả lời → Trích xuất tên quán → Chấm điểm.

Hỗ trợ 2 chế độ:
  python run_benchmark.py          # Gửi request mới tới API (mất ~30 phút)
  python run_benchmark.py --reeval # Tính lại điểm từ kết quả cũ (tức thì)
"""
import json
import time
import re
import sys
import statistics
import argparse

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
    check_mention_in_response,
    fuzzy_score,
    normalize_name,
)

API_URL = "http://localhost:8001/chat"
INPUT_FILE = "../../data/test/test_dataset.json"
OUTPUT_FILE = "../../data/test/test_dataset_evaluated.json"


# ---------------------------------------------------------------------------
# Trích xuất tên quán ăn từ câu trả lời AI
# ---------------------------------------------------------------------------

def extract_restaurants_from_response(response_text: str) -> list:
    """
    Trích xuất tên quán ăn từ câu trả lời AI bằng nhiều pattern.

    AI có thể format theo nhiều cách:
      1. 🏪 Quán: [Tên]                     (format chuẩn trong prompt)
      2. 🏪 Tên quán: [Tên]                 (biến thể)
      3. 📍 **[Tên quán]**                   (dòng tiêu đề bold)
      4. 📍 [Tên quán]                       (dòng tiêu đề không bold)
      5. 🏪 [Tên]                            (emoji + tên trực tiếp)

    KHÔNG lấy:
      - Dòng chứa "Địa chỉ:" (đó là địa chỉ, không phải tên quán)
      - Dòng quá ngắn (< 3 ký tự)
      - Text trùng lặp
    """
    if not response_text:
        return []

    restaurants = []
    seen = set()

    def add_name(name: str):
        name = name.strip().rstrip('.').strip()
        # Bỏ prefix thừa
        for prefix in ['Quán:', 'Tên quán:', 'Tên:']:
            if name.lower().startswith(prefix.lower()):
                name = name[len(prefix):].strip()
        if not name or len(name) < 3:
            return
        key = normalize_name(name)
        if key not in seen:
            seen.add(key)
            restaurants.append(name)

    # --- Pattern 1: 🏪 Quán: NAME / 🏪 Tên quán: NAME ---
    for m in re.findall(r'🏪\s*(?:Quán|Tên quán|Tên)\s*:\s*(.+)', response_text):
        add_name(m)

    # --- Pattern 2: 🏪 NAME (emoji + tên trực tiếp, không có ":") ---
    for m in re.findall(r'🏪\s+([^:\n]{3,})', response_text):
        # Loại trừ nếu đã match ở pattern 1
        candidate = m.strip()
        if not any(candidate.lower().startswith(w) for w in ['quán:', 'tên']):
            add_name(candidate)

    # --- Pattern 3 & 4: 📍 tiêu đề (bold hoặc không bold) ---
    for line in response_text.split('\n'):
        line_stripped = line.strip()

        # Bỏ qua dòng địa chỉ
        if 'địa chỉ' in line_stripped.lower():
            continue

        # 📍 **Restaurant Name**
        m = re.match(r'^📍\s*\*\*(.+?)\*\*', line_stripped)
        if m:
            add_name(m.group(1))
            continue

        # 📍 Restaurant Name (không bold, không có : phía sau)
        m = re.match(r'^📍\s+([^:]{4,})$', line_stripped)
        if m:
            candidate = m.group(1).replace('**', '').strip()
            # Loại trừ dòng bắt đầu bằng số (thường là địa chỉ)
            if not re.match(r'^\d', candidate) and not candidate.startswith(('P.', 'Q.', 'Tầng')):
                add_name(candidate)

    return restaurants


# ---------------------------------------------------------------------------
# Chạy Benchmark
# ---------------------------------------------------------------------------

def run_benchmark(reeval: bool = False):
    """Chạy benchmark chính hoặc tính lại điểm từ kết quả cũ."""

    if reeval:
        # ---- Chế độ tính lại (không gọi API) ----
        print(f"📂 Đang đọc kết quả cũ từ {OUTPUT_FILE}...")
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                dataset = json.load(f)
        except FileNotFoundError:
            print(f"❌ Không tìm thấy {OUTPUT_FILE}. Hãy chạy benchmark trước.")
            return

        # Re-extract với logic cải tiến
        for item in dataset:
            item["retrieved_restaurants"] = extract_restaurants_from_response(
                item.get("ai_response", "")
            )
        print(f"✅ Đã trích xuất lại tên quán cho {len(dataset)} câu.\n")

    else:
        # ---- Chế độ chạy mới (gọi API) ----
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

        for i, item in enumerate(dataset, 1):
            question = item.get("question", "")
            label = question[:65] + "..." if len(question) > 65 else question
            print(f"[{i:3d}/{total}] {label}")

            start = time.time()
            try:
                resp = requests.post(
                    API_URL,
                    json={"message": question},
                    timeout=120,
                )
                resp.raise_for_status()
                ai_text = resp.json().get("response", "")
            except Exception as e:
                print(f"         ⚠ Lỗi: {e}")
                ai_text = ""

            latency = time.time() - start
            item["ai_response"] = ai_text
            item["latency_seconds"] = round(latency, 2)
            item["retrieved_restaurants"] = extract_restaurants_from_response(ai_text)

            n = len(item["retrieved_restaurants"])
            print(f"         ✓ {latency:.1f}s | Trích xuất: {n} quán")

        # Lưu kết quả
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=4)
        print(f"\n💾 Đã lưu kết quả vào {OUTPUT_FILE}")

    # ---- Tính toán & In báo cáo ----
    _print_report(dataset)


# ---------------------------------------------------------------------------
# Báo cáo kết quả
# ---------------------------------------------------------------------------

def _print_report(dataset: list):
    """Tính toán macro-average và in báo cáo chi tiết."""

    all_p, all_r, all_f2 = [], [], []
    all_mention = []
    latencies = []
    hit_count = 0  # câu có Recall > 0

    for item in dataset:
        retrieved = item.get("retrieved_restaurants", [])
        gt = item.get("ground_truth_restaurants", [])
        response = item.get("ai_response", "")
        lat = item.get("latency_seconds", 0)

        scores = calculate_retrieval_metrics(retrieved, gt)
        all_p.append(scores["precision"])
        all_r.append(scores["recall"])
        all_f2.append(scores["f2"])

        mention = check_mention_in_response(response, gt)
        all_mention.append(mention)

        if scores["recall"] > 0:
            hit_count += 1
        if lat > 0:
            latencies.append(lat)

    total = len(dataset)
    avg_p = statistics.mean(all_p) if all_p else 0
    avg_r = statistics.mean(all_r) if all_r else 0
    avg_f2 = statistics.mean(all_f2) if all_f2 else 0
    avg_mention = statistics.mean(all_mention) if all_mention else 0
    hit_rate = hit_count / total if total else 0

    w = 60
    print("\n" + "=" * w)
    print("   BÁO CÁO KẾT QUẢ ĐÁNH GIÁ  (BENCHMARK REPORT)")
    print("=" * w)

    print(f"\n{'📊 TỔNG QUAN':}")
    print(f"   Số câu truy vấn          : {total}")

    if latencies:
        print(f"\n{'⏱  THỜI GIAN PHẢN HỒI':}")
        print(f"   Trung bình  (Mean)       : {statistics.mean(latencies):.2f} giây")
        print(f"   Trung vị    (Median)     : {statistics.median(latencies):.2f} giây")
        print(f"   Nhanh nhất  (Min)        : {min(latencies):.2f} giây")
        print(f"   Chậm nhất   (Max)        : {max(latencies):.2f} giây")

    print(f"\n{'📈 ĐIỂM TRUY HỒI (Macro-Average, Fuzzy ≥ 0.80)':}")
    print(f"   Precision                : {avg_p:.4f}  ({avg_p*100:.1f}%)")
    print(f"   Recall                   : {avg_r:.4f}  ({avg_r*100:.1f}%)")
    print(f"   F2 Score                 : {avg_f2:.4f}  ({avg_f2*100:.1f}%)")

    print(f"\n{'📋 CHỈ SỐ BỔ SUNG':}")
    print(f"   Hit Rate   (Recall > 0)  : {hit_rate:.4f}  ({hit_rate*100:.1f}%)")
    print(f"   Mention Rate             : {avg_mention:.4f}  ({avg_mention*100:.1f}%)")

    print(f"\n{'💡 GIẢI THÍCH':}")
    print(f"   Precision  : Trong số quán AI gợi ý, bao nhiêu % đúng?")
    print(f"   Recall     : Trong số quán cần tìm, AI tìm được bao nhiêu %?")
    print(f"   F2 Score   : Điểm tổng hợp (ưu tiên Recall, trọng số ×2)")
    print(f"   Hit Rate   : % câu hỏi AI tìm đúng ≥ 1 quán")
    print(f"   Mention    : % câu mà tên quán GT xuất hiện trong response")
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
    args = parser.parse_args()
    run_benchmark(reeval=args.reeval)
