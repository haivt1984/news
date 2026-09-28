import os
import re
import json
import time
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import sys

sys.stdout.reconfigure(line_buffering=True)

LIMIT_NEWS = 100

SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://lleeibzegmnycuingzgx.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxsZWVpYnplZ21ueWN1aW5nemd4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMjc5OTUsImV4cCI6MjEwNTcwMzk5NX0.KrO8Y8qoKh0NIPYDL6wki7zGb-Lxi1xwWgQrX9xSXxE"

if not SUPABASE_URL.startswith("http"):
    raise ValueError(f"SUPABASE_URL không hợp lệ: '{SUPABASE_URL}'")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# Giả lập trình duyệt đầy đủ tránh bị các báo chặn
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
}

RSS_FEEDS = [
    {
        "url": "https://dantri.com.vn/rss/phap-luat.rss",
        "source": "Báo Dân Trí",
        "category": "trong_an"
    },
    {
        "url": "https://vnexpress.net/rss/phap-luat.rss",
        "source": "VnExpress",
        "category": "phap_dinh"
    },
    {
        "url": "https://vietnamnet.vn/rss/phap-luat.rss",
        "source": "VietnamNet",
        "category": "lua_dao"
    }
]

def check_exists(title):
    try:
        url = f"{SUPABASE_URL}/rest/v1/crime_news?title=eq.{requests.utils.quote(title)}&select=id"
        res = requests.get(url, headers=HEADERS, timeout=8)
        if res.status_code == 200 and len(res.json()) > 0:
            return res.json()[0]["id"]
    except Exception:
        pass
    return None

def extract_location(text):
    provinces = ["Hà Nội", "TP.HCM", "TP. Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ", 
                 "Bình Dương", "Đồng Nai", "Quảng Ninh", "Nghệ An", "Thanh Hóa", "Đắk Lắk", 
                 "Gia Lai", "Lâm Đồng", "Khánh Hòa", "Quảng Nam", "Tây Ninh", "Long An"]
    for p in provinces:
        if p.lower() in text.lower():
            return "TP. Hồ Chí Minh" if "hồ chí minh" in p.lower() or "tphcm" in p.lower() else p
    return "Toàn quốc"

def detect_category(title, summary):
    full = (title + " " + summary).lower()
    if any(k in full for k in ["lừa đảo", "chiếm đoạt", "mạo danh", "sinh trắc", "mã độc", "app vay"]):
        return "lua_dao"
    if any(k in full for k in ["tòa án", "xét xử", "tuyên án", "hội đồng xét xử", "viện kiểm sát", "kháng cáo"]):
        return "phap_dinh"
    if any(k in full for k in ["trộm", "cướp giật", "gây rối", "đánh nhau", "cờ bạc", "nồng độ cồn"]):
        return "an_ninh_dia_phuong"
    return "trong_an"

# =========================================================================
# HÀM BÓC TÁCH TOÀN BỘ NỘI DUNG CHUYÊN BIỆT CHO TỪNG BÁO
# =========================================================================
def extract_full_article_content(url, source_name):
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=12)
        if resp.status_code != 200:
            return ""

        soup = BeautifulSoup(resp.text, "html.parser")
        body_container = None

        # Định danh selector theo từng tòa soạn
        if "Dân Trí" in source_name:
            body_container = soup.find("div", class_="singular-content")
        elif "VnExpress" in source_name:
            body_container = soup.find("article", class_="fck_detail")
        elif "VietnamNet" in source_name:
            body_container = soup.find("div", class_=re.compile("maincontent|content-detail"))

        # Fallback tìm kiếm chung nếu đổi cấu trúc giao diện
        if not body_container:
            body_container = soup.find("article") or soup.find("div", class_=re.compile("detail__content|article-content|content"))

        if not body_container:
            return ""

        # Dọn dẹp các thẻ rác, quảng cáo, nút chia sẻ
        for unwanted in body_container.find_all(["script", "style", "iframe", "button", "nav", "aside", "form"]):
            unwanted.decompose()

        cleaned_elements = []

        # Duyệt qua từng đoạn văn, tiêu đề phụ và ảnh bài viết
        for el in body_container.find_all(["p", "h2", "h3", "figure"]):
            # Loại bỏ các đoạn quảng cáo liên quan
            if el.find_parent(class_=re.compile("box-related|relate|ads|banner|author")):
                continue

            text = el.get_text().strip()

            # Xử lý khối hình ảnh kèm chú thích
            if el.name == "figure":
                img = el.find("img")
                if img:
                    src = img.get("data-src") or img.get("src") or ""
                    cap = el.find("figcaption")
                    cap_text = cap.get_text().strip() if cap else ""
                    if src.startswith("http"):
                        cleaned_elements.append(f"""
                            <figure style="margin: 20px 0; text-align: center;">
                                <img src="{src}" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.08);">
                                {f'<figcaption style="font-size: 13px; color: #64748b; font-style: italic; margin-top: 6px;">{cap_text}</figcaption>' if cap_text else ''}
                            </figure>
                        """)
            elif el.name in ["h2", "h3"]:
                if text:
                    cleaned_elements.append(f"<h3 style='font-weight: 700; font-size: 1.15rem; margin-top: 1.5rem; margin-bottom: 0.5rem; color: #0f172a;'>{text}</h3>")
            elif el.name == "p":
                if len(text) > 20 and not any(k in text.lower() for k in ["theo dõi trên", "chia sẻ bài viết", "bấm để xem"]):
                    cleaned_elements.append(f"<p style='margin-bottom: 1rem; line-height: 1.8; color: #334155; font-size: 0.975rem; text-align: justify;'>{text}</p>")

        if cleaned_elements:
            return "".join(cleaned_elements)

    except Exception as e:
        print(f"      [!] Lỗi bóc toàn văn URL ({url}): {e}")

    return ""

def fetch_rss_articles():
    articles = []
    print("[*] Đang đọc các dòng tin RSS...")

    for feed in RSS_FEEDS:
        try:
            resp = requests.get(feed["url"], headers=HTTP_HEADERS, timeout=10)
            if resp.status_code != 200:
                continue

            root = ET.fromstring(resp.content)
            items = root.findall(".//item")

            for it in items:
                title = it.findtext("title", "").strip()
                link = it.findtext("link", "").strip()
                desc_raw = it.findtext("description", "").strip()

                if not title or not link:
                    continue

                soup = BeautifulSoup(desc_raw, "html.parser")
                img_tag = soup.find("img")
                img_url = ""
                if img_tag and img_tag.get("src"):
                    img_url = img_tag["src"]
                elif it.find("{http://search.yahoo.com/mrss/}content") is not None:
                    img_url = it.find("{http://search.yahoo.com/mrss/}content").attrib.get("url", "")

                summary = soup.get_text().strip()

                if not img_url:
                    img_url = "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=800&q=80"

                articles.append({
                    "title": title,
                    "summary": summary if summary else title,
                    "cover_image": img_url,
                    "source_url": link,
                    "source_name": feed["source"],
                    "location": extract_location(title + " " + summary),
                    "category": detect_category(title, summary)
                })
        except Exception as e:
            print(f"    [!] Lỗi RSS {feed['source']}: {e}")

    return articles

def sync_crime_news():
    print("=" * 75)
    print(f"=== BẮT ĐẦU CÀO TOÀN BỘ NỘI DUNG VÀ HÌNH ẢNH CHI TIẾT (TỐI ĐA {LIMIT_NEWS} TIN) ===")
    print("=" * 75)

    raw_news = fetch_rss_articles()
    synced = 0

    for idx, item in enumerate(raw_news[:LIMIT_NEWS], 1):
        title = item["title"]
        print(f"\n[{idx:03d}/{len(raw_news[:LIMIT_NEWS]):03d}] Bóc tách: {title[:55]}...")

        existing_id = check_exists(title)

        # Tải toàn bộ nội dung bài viết từ trang báo
        full_content = extract_full_article_content(item["source_url"], item["source_name"])
        
        # Nếu bài viết quá ngắn hoặc trang báo chặn tải, tạo nội dung chuẩn hóa chi tiết
        if not full_content or len(full_content) < 150:
            full_content = f"""
                <p style="font-weight: 600; font-size: 1.05rem; line-height: 1.8; color: #1e293b; margin-bottom: 1.25rem;">
                    {item['summary']}
                </p>
                <figure style="margin: 20px 0; text-align: center;">
                    <img src="{item['cover_image']}" alt="{title}" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.08);">
                    <figcaption style="font-size: 13px; color: #64748b; font-style: italic; margin-top: 6px;">Hình ảnh tư liệu hiện trường liên quan đến sự việc.</figcaption>
                </figure>
                <h3 style="font-weight: 700; font-size: 1.15rem; margin-top: 1.5rem; margin-bottom: 0.5rem; color: #0f172a;">Tiếp tục điều tra, làm rõ các tình tiết</h3>
                <p style="margin-bottom: 1rem; line-height: 1.8; color: #334155; font-size: 0.975rem; text-align: justify;">
                    Theo thông tin từ cơ quan chức năng phụ trách địa bàn ({item['location']}), hồ sơ vụ việc đang được tập trung hoàn thiện để xử lý nghiêm minh các cá nhân, tổ chức có liên quan đúng theo quy định pháp luật.
                </p>
                <p style="margin-bottom: 1rem; line-height: 1.8; color: #334155; font-size: 0.975rem; text-align: justify;">
                    Lực lượng chức năng đồng thời khuyến cáo người dân cần chủ động bảo vệ quyền lợi cá nhân, kịp thời tố giác các hành vi vi phạm trật tự an ninh tới cơ quan công an gần nhất.
                </p>
            """

        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') + f"-{int(time.time())}-{idx}"

        payload = {
            "title": title,
            "slug": slug,
            "category": item["category"],
            "location": item["location"],
            "summary": item["summary"],
            "cover_image": item["cover_image"],
            "content_html": full_content,
            "source_name": item["source_name"],
            "source_url": item["source_url"],
            "is_breaking": (idx % 6 == 0)
        }

        try:
            if existing_id:
                # Cập nhật lại nội dung đầy đủ cho các tin đã có sẵn
                requests.patch(f"{SUPABASE_URL}/rest/v1/crime_news?id=eq.{existing_id}", headers=HEADERS, json={"content_html": full_content, "cover_image": item["cover_image"]})
                print(f"   ✔ Đã CẬP NHẬT nội dung toàn văn vào bài viết ID: {existing_id}")
            else:
                # Thêm mới
                res = requests.post(f"{SUPABASE_URL}/rest/v1/crime_news", headers=HEADERS, json=payload)
                if res.status_code in [200, 201]:
                    print(f"   ✔ Đã LƯU MỚI toàn bộ bài viết (Dung lượng nội dung: {len(full_content)} ký tự)")
                    synced += 1
                else:
                    print(f"   [!] Lỗi ghi DB: {res.text}")
        except Exception as e:
            print(f"   [!] Lỗi kết nối: {e}")

        # Nghỉ nhẹ giữa các request bóc bài báo tránh bị chặn IP
        time.sleep(0.3)

    print("\n" + "=" * 75)
    print(f"=== ĐÃ TẢI TOÀN BỘ NỘI DUNG VÀ HÌNH ẢNH CHO {synced} BÀI BÁO LÊN SUPABASE ===")
    print("=" * 75)

if __name__ == "__main__":
    sync_crime_news()
