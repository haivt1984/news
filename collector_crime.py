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
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "YOUR_KEY"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

NEWS_SOURCES = [
    {"url": "https://dantri.com.vn/rss/phap-luat.rss", "source": "Báo Dân Trí"},
    {"url": "https://vnexpress.net/rss/phap-luat.rss", "source": "Báo VnExpress"},
    {"url": "https://tuoitre.vn/rss/phap-luat.rss", "source": "Báo Tuổi Trẻ"},
    {"url": "https://thanhnien.vn/rss/thoi-su/phap-luat.rss", "source": "Báo Thanh Niên"},
    {"url": "https://vietnamnet.vn/rss/phap-luat.rss", "source": "Báo VietnamNet"}
]

def make_proxy_url(img_url):
    """Bọc proxy vượt cơ chế chặn hotlink 403 của các báo"""
    if not img_url:
        return ""
    clean_url = img_url.replace("https://", "").replace("http://", "")
    return f"https://images.weserv.nl/?url={clean_url}&default=https://images.unsplash.com/photo-1589829545856-d10d557cf95f"

def classify_category(title, summary):
    txt = (title + " " + summary).lower()
    if any(w in txt for w in ["lừa đảo", "chiếm đoạt", "mạo danh", "giả danh", "sinh trắc", "mã độc", "app vay", "tiền ảo", "tín dụng đen"]):
        return "lua_dao"
    if any(w in txt for w in ["tòa án", "xét xử", "tuyên án", "hội đồng xét xử", "viện kiểm sát", "kháng cáo", "bị cáo", "hầu tòa", "án tù"]):
        return "phap_dinh"
    if any(w in txt for w in ["tai nạn", "giao thông", "tông", "lật xe", "nồng độ cồn", "bỏ trốn", "va chạm"]):
        return "giao_thong"
    if any(w in txt for w in ["giết", "tử vong", "thi thể", "ma túy", "bánh heroin", "vũ khí", "súng", "đốt nhà", "truy nã", "đâm", "chém"]):
        return "trong_an"
    return "an_ninh_dia_phuong"

def extract_location(text):
    provinces = [
        "Hà Nội", "TP.HCM", "TP. Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ", 
        "Bình Dương", "Đồng Nai", "Quảng Ninh", "Nghệ An", "Thanh Hóa", "Đắk Lắk", 
        "Gia Lai", "Lâm Đồng", "Khánh Hòa", "Quảng Nam", "Tây Ninh", "Long An", 
        "Điện Biên", "Bắc Ninh", "Hải Dương"
    ]
    for p in provinces:
        if p.lower() in text.lower():
            return "TP. Hồ Chí Minh" if "hồ chí minh" in p.lower() or "tphcm" in p.lower() else p
    return "Toàn quốc"

def check_exists(title):
    try:
        url = f"{SUPABASE_URL}/rest/v1/crime_news?title=eq.{requests.utils.quote(title)}&select=id"
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200 and len(res.json()) > 0:
            return True
    except Exception:
        pass
    return False

def get_real_image_and_content(url, source_name):
    real_img = ""
    content_html = ""
    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            
            # 1. Tìm thẻ meta ảnh og:image chuẩn nhất của bài báo
            og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
            if og_img and og_img.get("content"):
                real_img = og_img["content"].strip()

            # 2. Tìm khối bài viết
            body = None
            if "Dân Trí" in source_name:
                body = soup.find("div", class_="singular-content")
            elif "VnExpress" in source_name:
                body = soup.find("article", class_="fck_detail")
            elif "VietnamNet" in source_name:
                body = soup.find("div", class_=re.compile("maincontent|content-detail"))

            if not body:
                body = soup.find("article") or soup.find("div", class_=re.compile("detail-content|content"))

            if body:
                for j in body.find_all(["script", "style", "iframe", "button", "nav", "aside", "form"]):
                    j.decompose()
                
                parts = []
                for el in body.find_all(["p", "figure"]):
                    if el.find_parent(class_=re.compile("box-related|relate|ads|author")):
                        continue
                    if el.name == "p":
                        t = el.get_text().strip()
                        if len(t) > 20 and not any(x in t.lower() for x in ["theo dõi trên", "chia sẻ bài"]):
                            parts.append(f"<p style='margin-bottom: 1rem; line-height: 1.8; color: #334155; font-size: 1rem; text-align: justify;'>{t}</p>")
                if parts:
                    content_html = "".join(parts)
    except Exception as e:
        print(f"      [!] Lỗi bóc trang: {e}")

    return real_img, content_html

def sync_crime_news():
    print("=" * 75)
    print("=== BẮT ĐẦU CÀO TIN VÀ XỬ LÝ ẢNH THẬT BẰNG PROXY (CHỐNG CHẶN 403) ===")
    print("=" * 75)

    all_articles = []

    for src in NEWS_SOURCES:
        try:
            res = requests.get(src["url"], headers=HTTP_HEADERS, timeout=8)
            if res.status_code != 200:
                continue
            root = ET.fromstring(res.content)
            for it in root.findall(".//item"):
                title = it.findtext("title", "").strip()
                link = it.findtext("link", "").strip()
                desc_raw = it.findtext("description", "").strip()
                if not title or not link:
                    continue

                soup_desc = BeautifulSoup(desc_raw, "html.parser")
                summary = soup_desc.get_text().strip()

                desc_img = ""
                img_tag = soup_desc.find("img")
                if img_tag and img_tag.get("src"):
                    desc_img = img_tag["src"]

                all_articles.append({
                    "title": title,
                    "link": link,
                    "summary": summary if summary else title,
                    "desc_img": desc_img,
                    "source": src["source"],
                    "location": extract_location(title + " " + summary),
                    "category": classify_category(title, summary)
                })
        except Exception as e:
            print(f"[!] Lỗi RSS {src['source']}: {e}")

    print(f"[*] Tìm thấy {len(all_articles)} tin tức từ các báo.")
    added_count = 0

    for idx, item in enumerate(all_articles[:LIMIT_NEWS], 1):
        title = item["title"]
        print(f"\n[{idx:03d}/{len(all_articles[:LIMIT_NEWS]):03d}] Xử lý: {title[:55]}...")

        if check_exists(title):
            print("   (-) Bài đã có, bỏ qua.")
            continue

        raw_img, full_html = get_real_image_and_content(item["link"], item["source"])
        origin_img = raw_img or item["desc_img"]

        # Nếu hoàn toàn không có ảnh từ bài báo, bỏ qua bài này
        if not origin_img or not origin_img.startswith("http"):
            print("   (!) Bài không có ảnh, bỏ qua.")
            continue

        # BỌC PROXY CHO ẢNH ĐỂ TRÌNH DUYỆT LOAD MƯỢT MÀ KHÔNG BỊ LỖI 403
        final_img = make_proxy_url(origin_img)

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
            "is_breaking": (idx % 6 == 0)
        }

        try:
            res = requests.post(f"{SUPABASE_URL}/rest/v1/crime_news", headers=HEADERS, json=payload)
            if res.status_code in [200, 201]:
                print(f"   ✔ ĐÃ LƯU VỚI ẢNH THẬT ĐƯỢC PROXY: {final_img[:60]}...")
                added_count += 1
            else:
                print(f"   [!] Lỗi ghi DB: {res.text}")
        except Exception as e:
            print(f"   [!] Lỗi mạng: {e}")

        time.sleep(0.2)

    print("\n" + "=" * 75)
    print(f"=== ĐÃ ĐỒNG BỘ THÀNH CÔNG {added_count} BÀI BÁO VỚI ẢNH RIÊNG BIỆT 100% ===")
    print("=" * 75)

if __name__ == "__main__":
    sync_crime_news()
