import os
import re
import json
import time
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import sys

sys.stdout.reconfigure(line_buffering=True)

# Số lượng tin thật cần lấy
LIMIT_NEWS = 60

SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://lleeibzegmnycuingzgx.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxsZWVpYnplZ21ueWN1aW5nemd4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMjc5OTUsImV4cCI6MjEwNTcwMzk5NX0.KrO8Y8qoKh0NIPYDL6wki7zGb-Lxi1xwWgQrX9xSXxE"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

RSS_FEEDS = [
    {"url": "https://dantri.com.vn/rss/phap-luat.rss", "source": "Báo Dân Trí", "category": "trong_an"},
    {"url": "https://vnexpress.net/rss/phap-luat.rss", "source": "VnExpress", "category": "phap_dinh"},
    {"url": "https://vietnamnet.vn/rss/phap-luat.rss", "source": "VietnamNet", "category": "lua_dao"}
]

def check_exists(title):
    try:
        url = f"{SUPABASE_URL}/rest/v1/crime_news?title=eq.{requests.utils.quote(title)}&select=id"
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200 and len(res.json()) > 0:
            return True
    except Exception:
        pass
    return False

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
    if any(k in full for k in ["tòa án", "xét xử", "tuyên án", "hội đồng xét xử", "viện kiểm sát"]):
        return "phap_dinh"
    if any(k in full for k in ["trộm", "cướp giật", "gây rối", "đánh nhau", "cờ bạc", "nồng độ cồn"]):
        return "an_ninh_dia_phuong"
    return "trong_an"

def parse_article_page(url, source_name):
    """Truy cập trang báo để lấy đúng ảnh thật (og:image) và toàn văn bài viết"""
    cover_image = ""
    content_html = ""

    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=10)
        if resp.status_code != 200:
            return "", ""

        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. Bóc ảnh đại diện thật từ thẻ meta og:image
        meta_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if meta_img and meta_img.get("content"):
            cover_image = meta_img["content"]

        # 2. Bóc nội dung bài viết theo cấu trúc từng báo
        body_container = None
        if "Dân Trí" in source_name:
            body_container = soup.find("div", class_="singular-content")
        elif "VnExpress" in source_name:
            body_container = soup.find("article", class_="fck_detail")
        elif "VietnamNet" in source_name:
            body_container = soup.find("div", class_=re.compile("maincontent|content-detail"))

        if not body_container:
            body_container = soup.find("article") or soup.find("div", class_=re.compile("content-detail|detail-content"))

        if body_container:
            for unwanted in body_container.find_all(["script", "style", "iframe", "button", "nav", "aside", "form"]):
                unwanted.decompose()

            cleaned = []
            for el in body_container.find_all(["p", "figure"]):
                if el.find_parent(class_=re.compile("box-related|relate|ads|banner|author")):
                    continue

                if el.name == "figure":
                    img = el.find("img")
                    if img:
                        src = img.get("data-src") or img.get("src") or ""
                        cap = el.find("figcaption")
                        cap_text = cap.get_text().strip() if cap else ""
                        if src.startswith("http"):
                            cleaned.append(f"""
                                <figure style="margin: 18px 0; text-align: center;">
                                    <img src="{src}" style="width: 100%; border-radius: 10px;">
                                    {f'<figcaption style="font-size: 12px; color: #64748b; font-style: italic; margin-top: 5px;">{cap_text}</figcaption>' if cap_text else ''}
                                </figure>
                            """)
                elif el.name == "p":
                    t = el.get_text().strip()
                    if len(t) > 25 and not any(k in t.lower() for k in ["theo dõi trên", "chia sẻ bài viết"]):
                        cleaned.append(f"<p style='margin-bottom: 1rem; line-height: 1.8; color: #334155; font-size: 0.95rem; text-align: justify;'>{t}</p>")

            if cleaned:
                content_html = "".join(cleaned)

    except Exception as e:
        print(f"      [!] Lỗi bóc trang chi tiết: {e}")

    return cover_image, content_html

def sync_crime_news():
    print("=" * 70)
    print("=== BẮT ĐẦU CÀO TIN THỰC TẾ & ẢNH ĐẠI DIỆN THẬT TỪ CÁC BÁO ===")
    print("=" * 70)

    articles = []

    for feed in RSS_FEEDS:
        try:
            resp = requests.get(feed["url"], headers=HTTP_HEADERS, timeout=8)
            if resp.status_code != 200:
                continue

            root = ET.fromstring(resp.content)
            for it in root.findall(".//item"):
                title = it.findtext("title", "").strip()
                link = it.findtext("link", "").strip()
                desc_raw = it.findtext("description", "").strip()

                if not title or not link:
                    continue

                soup_desc = BeautifulSoup(desc_raw, "html.parser")
                summary = soup_desc.get_text().strip()

                # Bóc ảnh nhanh từ description RSS (nếu có)
                desc_img = ""
                img_tag = soup_desc.find("img")
                if img_tag and img_tag.get("src"):
                    desc_img = img_tag["src"]

                articles.append({
                    "title": title,
                    "link": link,
                    "summary": summary if summary else title,
                    "desc_img": desc_img,
                    "source": feed["source"],
                    "location": extract_location(title + " " + summary),
                    "category": detect_category(title, summary)
                })
        except Exception as e:
            print(f"[!] Lỗi đọc RSS {feed['source']}: {e}")

    total_added = 0

    for idx, item in enumerate(articles[:LIMIT_NEWS], 1):
        title = item["title"]
        print(f"\n[{idx:02d}/{len(articles[:LIMIT_NEWS]):02d}] Đang lấy: {title[:50]}...")

        if check_exists(title):
            print("   (-) Tin đã có, bỏ qua.")
            continue

        # Lấy ảnh đại diện thật và nội dung thật từ trang báo gốc
        cover_img, full_html = parse_article_page(item["link"], item["source"])

        # Nếu không lấy được og:image thì dùng ảnh từ RSS description
        final_img = cover_img or item["desc_img"]
        if not final_img:
            # Bỏ qua nếu bài viết không có ảnh để tránh làm giao diện bị lỗi
            print("   (!) Bài báo không có ảnh minh họa, bỏ qua.")
            continue

        if not full_html:
            full_html = f"<p style='font-size:1.05rem; font-weight:600; line-height:1.8; color:#1e293b;'>{item['summary']}</p>"

        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') + f"-{int(time.time())}-{idx}"

        payload = {
            "title": title,
            "slug": slug,
            "category": item["category"],
            "location": item["location"],
            "summary": item["summary"],
            "cover_image": final_img,
            "content_html": full_html,
            "source_name": item["source"],
            "source_url": item["link"],
            "is_breaking": (idx % 5 == 0)
        }

        try:
            res = requests.post(f"{SUPABASE_URL}/rest/v1/crime_news", headers=HEADERS, json=payload)
            if res.status_code in [200, 201]:
                print(f"   ✔ ĐÃ LƯU THÀNH CÔNG (Ảnh thật: {final_img[:45]}...)")
                total_added += 1
            else:
                print(f"   [!] Lỗi ghi DB: {res.text}")
        except Exception as e:
            print(f"   [!] Lỗi mạng: {e}")

        time.sleep(0.3)

    print("\n" + "=" * 70)
    print(f"=== HOÀN TẤT! ĐÃ NẠP {total_added} BÀI BÁO THẬT VỚI ẢNH RIÊNG BIỆT LÊN SUPABASE ===")
    print("=" * 70)

if __name__ == "__main__":
    sync_crime_news()
