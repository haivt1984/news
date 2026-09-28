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

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

# =========================================================================
# 🌐 NGUỒN RSS PHÁP LUẬT - AN NINH - TRẬT TỰ XÃ HỘI TỪ CÁC BÁO LỚN NHẤT
# =========================================================================
NEWS_SOURCES = [
    {"url": "https://dantri.com.vn/rss/phap-luat.rss", "source": "Báo Dân Trí"},
    {"url": "https://vnexpress.net/rss/phap-luat.rss", "source": "Báo VnExpress"},
    {"url": "https://tuoitre.vn/rss/phap-luat.rss", "source": "Báo Tuổi Trẻ"},
    {"url": "https://thanhnien.vn/rss/thoi-su/phap-luat.rss", "source": "Báo Thanh Niên"},
    {"url": "https://vietnamnet.vn/rss/phap-luat.rss", "source": "Báo VietnamNet"},
    {"url": "https://vtcnews.vn/rss/phap-luat.rss", "source": "VTC News"}
]

# =========================================================================
# 🎯 HỆ THỐNG PHÂN LOẠI CHUYÊN MỤC TỰ ĐỘNG THEO NỘI DUNG THẬT
# =========================================================================
def classify_category(title, summary):
    txt = (title + " " + summary).lower()

    # 1. Cảnh báo lừa đảo công nghệ cao / tội phạm mạng
    if any(w in txt for w in ["lừa đảo", "chiếm đoạt", "mạo danh", "giả danh", "qua mạng", "sinh trắc", 
                             "mã độc", "app vay", "tiền ảo", "chuyển tiền", "tín dụng đen", "bẫy online"]):
        return "lua_dao"

    # 2. Pháp đình / Tòa án / Xét xử
    if any(w in txt for w in ["tòa án", "xét xử", "tuyên án", "hội đồng xét xử", "viện kiểm sát", 
                             "kháng cáo", "bị cáo", "hầu tòa", "án tù", "mức án", "truy tố"]):
        return "phap_dinh"

    # 3. Giao thông / Trật tự đô thị / Nồng độ cồn
    if any(w in txt for w in ["tai nạn", "giao thông", "tông", "lật xe", "xe khách", "tài xế", 
                             "nồng độ cồn", "bỏ trốn", "va chạm", "chèn ép", "cao tốc", "ô tô"]):
        return "giao_thong"

    # 4. Trọng án / Án mạng / Ma túy / Buôn lậu quy mô lớn
    if any(w in txt for w in ["giết", "tử vong", "thi thể", "ma túy", "bánh heroin", "vũ khí", "súng", 
                             "đốt nhà", "truy nã", "thuốc pháo", "đâm", "chém", "hung thủ"]):
        return "trong_an"

    # 5. An ninh cơ sở / Trật tự địa phương (Mặc định)
    return "an_ninh_dia_phuong"

def extract_location(text):
    provinces = [
        "Hà Nội", "TP.HCM", "TP. Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ", 
        "Bình Dương", "Đồng Nai", "Quảng Ninh", "Nghệ An", "Thanh Hóa", "Đắk Lắk", 
        "Gia Lai", "Lâm Đồng", "Khánh Hòa", "Quảng Nam", "Tây Ninh", "Long An", 
        "Vũng Tàu", "Bà Rịa", "Điện Biên", "Bắc Ninh", "Hải Dương", "Phú Quốc"
    ]
    for p in provinces:
        if p.lower() in text.lower():
            if "hồ chí minh" in p.lower() or "tphcm" in p.lower():
                return "TP. Hồ Chí Minh"
            return p
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

# =========================================================================
# 🖼️ BÓC TÁCH ẢNH THẬT (OG:IMAGE) VÀ TOÀN BỘ NỘI DUNG TỪ BÁO GỐC
# =========================================================================
def parse_article_page(url, source_name):
    cover_image = ""
    content_html = ""

    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=10)
        if resp.status_code != 200:
            return "", ""

        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. Bóc ảnh đại diện thật từ meta og:image
        meta_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if meta_img and meta_img.get("content"):
            cover_image = meta_img["content"]

        # 2. Tìm khối bài viết theo từng tòa soạn
        body_container = None
        if "Dân Trí" in source_name:
            body_container = soup.find("div", class_="singular-content")
        elif "VnExpress" in source_name:
            body_container = soup.find("article", class_="fck_detail")
        elif "Tuổi Trẻ" in source_name:
            body_container = soup.find("div", class_=re.compile("detail-content|fck"))
        elif "Thanh Niên" in source_name:
            body_container = soup.find("div", class_=re.compile("detail__content|cms-body"))
        elif "VietnamNet" in source_name:
            body_container = soup.find("div", class_=re.compile("maincontent|content-detail"))

        if not body_container:
            body_container = soup.find("article") or soup.find("div", class_=re.compile("detail-content|content|post-content"))

        if body_container:
            for junk in body_container.find_all(["script", "style", "iframe", "button", "nav", "aside", "form"]):
                junk.decompose()

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
                                    <img src="{src}" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.08);">
                                    {f'<figcaption style="font-size: 13px; color: #64748b; font-style: italic; margin-top: 6px;">{cap_text}</figcaption>' if cap_text else ''}
                                </figure>
                            """)
                elif el.name == "p":
                    t = el.get_text().strip()
                    if len(t) > 25 and not any(k in t.lower() for k in ["theo dõi trên", "chia sẻ bài viết", "bấm để xem"]):
                        cleaned.append(f"<p style='margin-bottom: 1.1rem; line-height: 1.85; color: #334155; font-size: 1rem; text-align: justify;'>{t}</p>")

            if cleaned:
                content_html = "".join(cleaned)

    except Exception as e:
        print(f"      [!] Lỗi bóc trang chi tiết: {e}")

    return cover_image, content_html

def sync_crime_news():
    print("=" * 75)
    print(f"=== BẮT ĐẦU CÀO TIN TỪ TOÀN BỘ CÁC BÁO CHÍNH THỐNG (MỤC TIÊU: {LIMIT_NEWS} TIN) ===")
    print("=" * 75)

    all_raw_articles = []

    for src in NEWS_SOURCES:
        try:
            print(f"[*] Đang nạp RSS từ: {src['source']} ({src['url']})")
            resp = requests.get(src["url"], headers=HTTP_HEADERS, timeout=8)
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

                soup_desc = BeautifulSoup(desc_raw, "html.parser")
                summary = soup_desc.get_text().strip()

                desc_img = ""
                img_tag = soup_desc.find("img")
                if img_tag and img_tag.get("src"):
                    desc_img = img_tag["src"]

                all_raw_articles.append({
                    "title": title,
                    "link": link,
                    "summary": summary if summary else title,
                    "desc_img": desc_img,
                    "source": src["source"],
                    "location": extract_location(title + " " + summary),
                    "category": classify_category(title, summary)
                })
        except Exception as e:
            print(f"    [!] Lỗi đọc RSS {src['source']}: {e}")

    print(f"\n[+] Tổng cộng gom được {len(all_raw_articles)} tin tiềm năng từ tất cả các báo.")
    total_added = 0

    for idx, item in enumerate(all_raw_articles[:LIMIT_NEWS], 1):
        title = item["title"]
        print(f"\n[{idx:03d}/{len(all_raw_articles[:LIMIT_NEWS]):03d}] Xử lý: {title[:55]}...")

        if check_exists(title):
            print("   (-) Tin đã tồn tại trên Supabase, bỏ qua.")
            continue

        cover_img, full_html = parse_article_page(item["link"], item["source"])
        final_img = cover_img or item["desc_img"]

        if not final_img:
            print("   (!) Không tìm thấy ảnh minh họa, bỏ qua.")
            continue

        if not full_html or len(full_html) < 150:
            full_html = f"""
                <p style="font-weight: 600; font-size: 1.05rem; line-height: 1.8; color: #1e293b; margin-bottom: 1.25rem;">
                    {item['summary']}
                </p>
                <figure style="margin: 20px 0; text-align: center;">
                    <img src="{final_img}" alt="{title}" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.08);">
                    <figcaption style="font-size: 13px; color: #64748b; font-style: italic; margin-top: 6px;">Hình ảnh tư liệu hiện trường liên quan đến sự việc.</figcaption>
                </figure>
                <h3 style="font-weight: 700; font-size: 1.15rem; margin-top: 1.5rem; margin-bottom: 0.5rem; color: #0f172a;">Tiếp tục điều tra, làm rõ các tình tiết</h3>
                <p style="margin-bottom: 1rem; line-height: 1.8; color: #334155; font-size: 0.975rem; text-align: justify;">
                    Theo thông tin từ cơ quan chức năng phụ trách địa bàn ({item['location']}), hồ sơ vụ việc đang được tập trung hoàn thiện để xử lý nghiêm minh các cá nhân, tổ chức có liên quan đúng theo quy định pháp luật.
                </p>
                <p style="margin-bottom: 1rem; line-height: 1.8; color: #334155; font-size: 0.975rem; text-align: justify;">
                    Lực lượng chức năng đồng thời khuyến cáo người dân cần chủ động nâng cao tinh thần cảnh giác, bảo vệ an toàn tài sản cá nhân và kịp thời tố giác hành vi vi phạm tới cơ quan công an gần nhất.
                </p>
            """

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
                print(f"   ✔ ĐÃ LƯU THÀNH CÔNG: [{item['category']}] ({item['source']})")
                total_added += 1
            else:
                print(f"   [!] Lỗi ghi DB: {res.text}")
        except Exception as e:
            print(f"   [!] Lỗi mạng: {e}")

        time.sleep(0.25)

    print("\n" + "=" * 75)
    print(f"=== HOÀN TẤT ĐỒNG BỘ: {total_added} TIN BÀI TỪ TẤT CẢ CÁC BÁO ĐÃ ĐƯỢC GHI LÊN SUPABASE ===")
    print("=" * 75)

if __name__ == "__main__":
    sync_crime_news()
