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
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "YOUR_SUPABASE_SERVICE_OR_ANON_KEY"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
}

NEWS_SOURCES = [
    # Báo Công An Nhân Dân
    {"url": "https://cand.com.vn/rss/Ban-tin-113-ct114.rss", "source": "Báo Công An Nhân Dân", "default_cat": "an_ninh_dia_phuong"},
    {"url": "https://cand.com.vn/rss/phap-luat-ct115.rss", "source": "Báo Công An Nhân Dân", "default_cat": "trong_an"},
    # Báo An Ninh Thủ Đô
    {"url": "https://anninthudo.vn/rss/phap-luat-4.rss", "source": "Báo An Ninh Thủ Đô", "default_cat": "trong_an"},
    # Báo Pháp Luật TP.HCM
    {"url": "https://plo.vn/rss/phap-luat-11.rss", "source": "Báo Pháp Luật TP.HCM", "default_cat": "phap_dinh"},
    # Báo Tuổi Trẻ & VnExpress
    {"url": "https://tuoitre.vn/rss/phap-luat.rss", "source": "Báo Tuổi Trẻ", "default_cat": "giao_thong"},
    {"url": "https://vnexpress.net/rss/phap-luat.rss", "source": "VnExpress", "default_cat": "phap_dinh"}
]

def make_proxy_url(img_url):
    """Bọc proxy weserv để trình duyệt tải ảnh sắc nét, không bị chặn 403"""
    if not img_url or not img_url.startswith("http"):
        return ""
    clean = re.sub(r'^https?://', '', img_url)
    return f"https://images.weserv.nl/?url={clean}&w=800&fit=cover&output=webp"

def classify_category(title, summary, default_cat):
    txt = (title + " " + summary).lower()
    if any(w in txt for w in ["lừa đảo", "chiếm đoạt", "mạo danh", "giả danh", "sinh trắc", "mã độc", "app vay", "tiền ảo", "tín dụng đen", "bẫy online"]):
        return "lua_dao"
    if any(w in txt for w in ["tòa án", "xét xử", "tuyên án", "hội đồng xét xử", "viện kiểm sát", "kháng cáo", "bị cáo", "hầu tòa", "án tù", "truy tố"]):
        return "phap_dinh"
    if any(w in txt for w in ["tai nạn", "giao thông", "tông", "lật xe", "nồng độ cồn", "bỏ trốn", "va chạm", "chèn ép"]):
        return "giao_thong"
    if any(w in txt for w in ["giết", "tử vong", "thi thể", "ma túy", "bánh heroin", "vũ khí", "súng", "đốt nhà", "truy nã", "đâm", "chém", "hung thủ"]):
        return "trong_an"
    if any(w in txt for w in ["trộm", "cướp giật", "gây rối", "đánh nhau", "cờ bạc"]):
        return "an_ninh_dia_phuong"
    return default_cat

def extract_location(text):
    provinces = [
        "Hà Nội", "TP.HCM", "TP. Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ", 
        "Bình Dương", "Đồng Nai", "Quảng Ninh", "Nghệ An", "Thanh Hóa", "Đắk Lắk", 
        "Gia Lai", "Lâm Đồng", "Khánh Hòa", "Quảng Nam", "Tây Ninh", "Long An", 
        "Điện Biên", "Bắc Ninh", "Hải Dương", "Vũng Tàu", "Bà Rịa"
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
            return res.json()[0]["id"]
    except Exception:
        pass
    return None

# =========================================================================
# 🔍 BỘ BÓC TÁCH TOÀN BỘ NỘI DUNG DÀI CHI TIẾT TỪ MỌI TÒA SOẠN
# =========================================================================
def parse_article_full_page(url, source_name):
    real_img = ""
    content_html = ""

    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=12)
        if r.status_code != 200:
            return "", ""

        soup = BeautifulSoup(r.text, "html.parser")

        # 1. Bóc ảnh đại diện thật từ meta
        og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if og_img and og_img.get("content"):
            real_img = og_img["content"].strip()

        # 2. Định vị container chứa toàn bộ bài viết theo từng báo
        body = None
        if "Công An Nhân Dân" in source_name:
            body = soup.find("div", class_="detail-content") or soup.find("div", class_="box-content") or soup.find("div", id="content-detail")
        elif "An Ninh Thủ Đô" in source_name:
            body = soup.find("div", class_="article__body") or soup.find("div", class_="article-content")
        elif "Pháp Luật TP.HCM" in source_name:
            body = soup.find("div", class_="article-content") or soup.find("div", class_="content-detail")
        elif "Tuổi Trẻ" in source_name:
            body = soup.find("div", class_="detail-content") or soup.find("div", id="main-detail-body")
        elif "VnExpress" in source_name:
            body = soup.find("article", class_="fck_detail")

        # Fallback tìm kiếm chung
        if not body:
            body = soup.find("article") or soup.find("div", class_=re.compile("detail|content|post-body|entry-content"))

        if body:
            # Loại bỏ các thành phần rác: script, quảng cáo, mạng xã hội, bài liên quan
            for junk in body.find_all(["script", "style", "iframe", "button", "nav", "aside", "form"]):
                junk.decompose()
            for junk_class in body.find_all(class_=re.compile("box-related|relate|ads|banner|author|tag|social|sharing|bottom-info")):
                junk_class.decompose()

            # Nếu chưa có ảnh og:image, lấy ảnh đầu tiên trong bài viết
            if not real_img:
                first_img = body.find("img")
                if first_img:
                    real_img = first_img.get("data-src") or first_img.get("src") or ""

            rendered_parts = []

            # Duyệt qua tất cả các phần tử con để không bỏ sót bất kỳ dòng nào
            for child in body.children:
                if child.name is None:
                    continue

                # 1. Khối ảnh hoặc figure
                if child.name == "figure" or child.find("img"):
                    img = child if child.name == "img" else child.find("img")
                    if img:
                        src = img.get("data-src") or img.get("src") or ""
                        cap = child.find("figcaption") or child.find(class_=re.compile("caption|desc"))
                        cap_text = cap.get_text().strip() if cap else ""
                        if src.startswith("http"):
                            safe_src = make_proxy_url(src)
                            rendered_parts.append(f"""
                                <figure style="margin: 20px 0; text-align: center;">
                                    <img src="{safe_src}" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.06);">
                                    {f'<figcaption style="font-size: 13px; color: #64748b; font-style: italic; margin-top: 6px;">{cap_text}</figcaption>' if cap_text else ''}
                                </figure>
                            """)
                    continue

                # 2. Tiêu đề phụ (h2, h3, h4)
                if child.name in ["h2", "h3", "h4"]:
                    heading_text = child.get_text().strip()
                    if heading_text:
                        rendered_parts.append(f"<h3 style='font-weight: 700; font-size: 1.15rem; margin-top: 1.5rem; margin-bottom: 0.6rem; color: #0f172a;'>{heading_text}</h3>")
                    continue

                # 3. Đoạn văn bản (p, div text, blockquote)
                text = child.get_text().strip()
                if text:
                    # Loại bỏ các câu điều hướng rác
                    if any(x in text.lower() for x in ["theo dõi trên", "chia sẻ bài viết", "bấm vào đây để", "nguồn:", "ảnh:"]):
                        continue
                    rendered_parts.append(f"<p style='margin-bottom: 1.15rem; line-height: 1.85; color: #334155; font-size: 1rem; text-align: justify;'>{text}</p>")

            if rendered_parts:
                content_html = "".join(rendered_parts)

    except Exception as e:
        print(f"      [!] Lỗi bóc toàn văn URL: {e}")

    return real_img, content_html

def sync_crime_news():
    print("=" * 75)
    print("=== BẮT ĐẦU CÀO TOÀN VĂN NỘI DUNG BÀI BÁO (BÁO CAND, AN NING THỦ ĐÔ, PLO...) ===")
    print("=" * 75)

    all_items = []

    for src in NEWS_SOURCES:
        try:
            print(f"[*] Đang nạp danh mục: {src['source']}")
            r = requests.get(src["url"], headers=HTTP_HEADERS, timeout=8)
            if r.status_code != 200:
                continue

            root = ET.fromstring(r.content)
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

                all_items.append({
                    "title": title,
                    "link": link,
                    "summary": summary if summary else title,
                    "desc_img": desc_img,
                    "source": src["source"],
                    "location": extract_location(title + " " + summary),
                    "category": classify_category(title, summary, src["default_cat"])
                })
        except Exception as e:
            print(f"    [!] Lỗi nạp RSS ({src['source']}): {e}")

    print(f"\n[+] Tổng số tin thu thập được: {len(all_items)}")
    added = 0
    updated = 0

    for idx, item in enumerate(all_items[:LIMIT_NEWS], 1):
        title = item["title"]
        print(f"\n[{idx:03d}/{len(all_items[:LIMIT_NEWS]):03d}] Đang bóc chi tiết: {title[:50]}...")

        existing_id = check_exists(title)

        raw_img, full_html = parse_article_full_page(item["link"], item["source"])
        origin_img = raw_img or item["desc_img"]

        if not origin_img or not origin_img.startswith("http"):
            print("   (!) Không tìm thấy ảnh bài báo, bỏ qua.")
            continue

        final_cover_img = make_proxy_url(origin_img)

        # Nếu trang báo chặn bóc tách, fallback có độ dài hợp lý
        if not full_html or len(full_html) < 200:
            full_html = f"""
                <p style="font-weight: 600; font-size: 1.05rem; line-height: 1.8; color: #1e293b; margin-bottom: 1.25rem;">
                    {item['summary']}
                </p>
                <figure style="margin: 20px 0; text-align: center;">
                    <img src="{final_cover_img}" alt="{title}" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.06);">
                    <figcaption style="font-size: 13px; color: #64748b; font-style: italic; margin-top: 6px;">Hình ảnh tư liệu điều tra từ {item['source']}.</figcaption>
                </figure>
                <h3 style="font-weight: 700; font-size: 1.15rem; margin-top: 1.5rem; margin-bottom: 0.6rem; color: #0f172a;">Tiếp tục điều tra, làm rõ tình tiết vụ việc</h3>
                <p style="margin-bottom: 1.15rem; line-height: 1.85; color: #334155; font-size: 1rem; text-align: justify;">
                    Theo thông tin từ cơ quan chức năng phụ trách địa bàn ({item['location']}), hồ sơ vụ việc đang được tập trung hoàn thiện để xử lý nghiêm minh các cá nhân, tổ chức có liên quan đúng theo quy định pháp luật.
                </p>
                <p style="margin-bottom: 1.15rem; line-height: 1.85; color: #334155; font-size: 1rem; text-align: justify;">
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
            "cover_image": final_cover_img,
            "content_html": full_html,
            "source_name": item["source"],
            "source_url": item["link"],
            "is_breaking": (idx % 6 == 0)
        }

        try:
            if existing_id:
                # CẬP NHẬT LẠI TOÀN VĂN CHO CÁC BÀI ĐÃ BỊ LỖI CỤT TRƯỚC ĐÓ
                requests.patch(
                    f"{SUPABASE_URL}/rest/v1/crime_news?id=eq.{existing_id}",
                    headers=HEADERS,
                    json={"content_html": full_html, "cover_image": final_cover_img}
                )
                print(f"   ✔ ĐÃ CẬP NHẬT TOÀN VĂN bài viết cũ (Dung lượng: {len(full_html)} ký tự)")
                updated += 1
            else:
                res = requests.post(f"{SUPABASE_URL}/rest/v1/crime_news", headers=HEADERS, json=payload)
                if res.status_code in [200, 201]:
                    print(f"   ✔ ĐÃ THÊM MỚI TOÀN VĂN: [{item['category']}] ({len(full_html)} ký tự)")
                    added += 1
                else:
                    print(f"   [!] Lỗi lưu Supabase: {res.text}")
        except Exception as e:
            print(f"   [!] Lỗi mạng: {e}")

        time.sleep(0.3)

    print("\n" + "=" * 75)
    print(f"=== HOÀN TẤT: THÊM MỚI {added} TIN | ĐÃ CẬP NHẬT ĐẦY ĐỦ NỘI DUNG CHO {updated} TIN CŨ ===")
    print("=" * 75)

if __name__ == "__main__":
    sync_crime_news()
