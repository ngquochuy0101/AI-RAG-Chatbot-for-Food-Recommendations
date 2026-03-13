import argparse
import csv
import logging
import random
import re
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.foody.vn"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_INPUT_HTML = Path(__file__).resolve().parent / "hoavang.html"
DEFAULT_OUTPUT_CSV = Path(__file__).resolve().parent / "foody_danang_with_comments_hoavang.csv"

CSV_HEADER = [
    "Tên",
    "Link",
    "Địa chỉ",
    "Đánh giá",
    "Số review",
    "Mô tả ngắn",
    "Giờ mở cửa",
    "Giá tiền",
    "Bình luận 1",
    "Bình luận 2",
    "Bình luận 3",
]

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl restaurant details and comments from Foody listing HTML."
    )
    parser.add_argument("--input-html", type=Path, default=DEFAULT_INPUT_HTML)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--sleep-min", type=float, default=1.0)
    parser.add_argument("--sleep-max", type=float, default=2.0)
    parser.add_argument("--retry-sleep-min", type=float, default=0.8)
    parser.add_argument("--retry-sleep-max", type=float, default=2.2)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def safe_sleep(min_seconds: float, max_seconds: float) -> None:
    if max_seconds < min_seconds:
        min_seconds, max_seconds = max_seconds, min_seconds
    time.sleep(min_seconds + random.random() * (max_seconds - min_seconds))


def append_row(path: Path, row: dict[str, str], header: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def normalize_link(href: str) -> str:
    if href.startswith("/"):
        return BASE_URL + href
    return href


def load_listing_html(input_html: Path) -> BeautifulSoup:
    if not input_html.exists():
        raise FileNotFoundError(f"Không tìm thấy file HTML: {input_html}")

    logger.info("Đang đọc file HTML: %s", input_html)
    with input_html.open("r", encoding="utf-8") as file:
        return BeautifulSoup(file, "html.parser")


def extract_restaurants(soup: BeautifulSoup) -> list[tuple[str, str]]:
    restaurants: list[tuple[str, str]] = []

    for element in soup.select("div.content-item.ng-scope"):
        anchor = element.select_one("div.title.fd-text-ellip a")
        if anchor and anchor.get("href"):
            restaurants.append((anchor.get_text(strip=True), normalize_link(anchor["href"])))

    if restaurants:
        return restaurants

    # Foody có thể đổi layout, fallback selector.
    for element in soup.select(".ldc-item"):
        anchor = element.select_one("a")
        if anchor and anchor.get("href"):
            title = element.select_one(".ldc-item-title")
            name = title.get_text(strip=True) if title else anchor.get("title", "").strip()
            restaurants.append((name, normalize_link(anchor["href"])))

    return restaurants


def fetch_with_retry(
    session: requests.Session,
    url: str,
    timeout: float,
    max_retries: int,
    retry_sleep_min: float,
    retry_sleep_max: float,
) -> Optional[requests.Response]:
    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            if attempt >= max_retries:
                logger.error("Request failed after %s attempts for %s: %s", attempt, url, error)
                return None

            logger.warning(
                "Request failed (%s/%s) for %s: %s",
                attempt,
                max_retries,
                url,
                error,
            )
            safe_sleep(retry_sleep_min, retry_sleep_max)

    return None


def extract_first_text(soup: BeautifulSoup, selector: str) -> str:
    element = soup.select_one(selector)
    return element.get_text(strip=True) if element else ""


def extract_opening_hours(soup: BeautifulSoup) -> str:
    container = soup.select_one(".micro-timesopen")
    if not container:
        return ""

    spans = container.find_all("span")
    joined_text = " ".join(span.get_text(" ", strip=True) for span in spans)
    match = re.search(r"(\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})", joined_text)
    return match.group(1).strip() if match else ""


def extract_comments(soup: BeautifulSoup, max_comments: int = 3) -> list[str]:
    comments = [""] * max_comments
    raw_comments = [item.get_text(strip=True) for item in soup.find_all("div", class_="review-des")[:max_comments]]
    for index, comment in enumerate(raw_comments):
        comments[index] = comment
    return comments


def build_output_row(name: str, link: str, soup: BeautifulSoup) -> dict[str, str]:
    comments = extract_comments(soup, max_comments=3)
    logger.info("Đã lấy được %s bình luận cho %s", len([item for item in comments if item]), name)

    return {
        "Tên": name,
        "Link": link,
        "Địa chỉ": extract_first_text(soup, ".res-common-add, .address"),
        "Đánh giá": extract_first_text(soup, ".microsite-point-avg, .review-points span"),
        "Số review": extract_first_text(soup, ".microsite-review-count, .items-count a"),
        "Mô tả ngắn": extract_first_text(soup, ".desc, .short-description, .res-common-info .category"),
        "Giờ mở cửa": extract_opening_hours(soup),
        "Giá tiền": extract_first_text(soup, ".res-common-minmaxprice span[itemprop='priceRange']"),
        "Bình luận 1": comments[0],
        "Bình luận 2": comments[1],
        "Bình luận 3": comments[2],
    }


def crawl(
    restaurants: list[tuple[str, str]],
    output_csv: Path,
    timeout: float,
    max_retries: int,
    sleep_min: float,
    sleep_max: float,
    retry_sleep_min: float,
    retry_sleep_max: float,
) -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

    total = len(restaurants)
    for index, (name, link) in enumerate(restaurants, 1):
        logger.info("[%s/%s] %s -> %s", index, total, name, link)

        response = fetch_with_retry(
            session=session,
            url=link,
            timeout=timeout,
            max_retries=max_retries,
            retry_sleep_min=retry_sleep_min,
            retry_sleep_max=retry_sleep_max,
        )

        if not response:
            append_row(
                output_csv,
                {
                    "Tên": name,
                    "Link": link,
                    "Địa chỉ": "",
                    "Đánh giá": "",
                    "Số review": "",
                    "Mô tả ngắn": "ERROR: request failed",
                    "Giờ mở cửa": "",
                    "Giá tiền": "",
                    "Bình luận 1": "",
                    "Bình luận 2": "",
                    "Bình luận 3": "",
                },
                CSV_HEADER,
            )
            safe_sleep(retry_sleep_min, retry_sleep_max)
            continue

        try:
            detail_soup = BeautifulSoup(response.text, "html.parser")
            row = build_output_row(name, link, detail_soup)
            append_row(output_csv, row, CSV_HEADER)
            safe_sleep(sleep_min, sleep_max)
        except Exception as error:
            logger.exception("Lỗi khi parse dữ liệu %s: %s", link, error)
            append_row(
                output_csv,
                {
                    "Tên": name,
                    "Link": link,
                    "Địa chỉ": "",
                    "Đánh giá": "",
                    "Số review": "",
                    "Mô tả ngắn": f"ERROR: {error}",
                    "Giờ mở cửa": "",
                    "Giá tiền": "",
                    "Bình luận 1": "",
                    "Bình luận 2": "",
                    "Bình luận 3": "",
                },
                CSV_HEADER,
            )
            safe_sleep(retry_sleep_min, retry_sleep_max)


def main() -> int:
    args = parse_args()
    configure_logging(args.log_level)

    soup = load_listing_html(args.input_html)
    restaurants = extract_restaurants(soup)

    if not restaurants:
        logger.error("Không tìm thấy địa điểm nào trong file HTML: %s", args.input_html)
        return 1

    logger.info("Tìm thấy %s địa điểm.", len(restaurants))
    crawl(
        restaurants=restaurants,
        output_csv=args.output_csv,
        timeout=args.timeout,
        max_retries=args.max_retries,
        sleep_min=args.sleep_min,
        sleep_max=args.sleep_max,
        retry_sleep_min=args.retry_sleep_min,
        retry_sleep_max=args.retry_sleep_max,
    )
    logger.info("Hoàn tất. Dữ liệu lưu tại: %s", args.output_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())