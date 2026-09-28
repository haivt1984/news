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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

# =========================================================================
# 🌐 HỆ THỐNG NGUỒN TIN CHUYÊN TRANG AN NINH & PHÁP LUẬT CHÍNH THỐNG
# =========================================================================
NEWS_SOURCES = [
    # Báo Công An Nhân Dân
    {"url": "https://cand.com.vn/rss/Ban-tin-113-ct114.rss", "source": "Báo Công An Nhân Dân", "default_cat": "an_ninh_dia_phuong"},
    {"url": "https://cand.com.vn/rss/phap-luat-ct115.rss", "source": "Báo Công An Nhân Dân", "default_cat": "trong_an"},
    # Báo An Ninh Thủ Đô
    {"url": "https://anninthudo.vn/rss/phap-luat-4.rss", "source": "Báo An Ninh Thủ Đô", "default_cat": "trong_an"},
    # Báo Pháp Luật TP.HCM
    {"url": "https://plo.vn/rss/phap-luat-11.rss", "source": "Báo Pháp Luật TP.HCM", "default_cat": "phap_dinh"},
    # Báo VnExpress & Tuổi Trẻ (Chuyên mục Pháp luật)
    {"url": "https://vnexpress.net/rss/phap-luat.rss", "source": "VnExpress", "default_cat": "phap_dinh"},
    {"url": "https://tuoitre.vn/rss/phap-luat.rss", "source": "Báo Tuổi Trẻ", "default_cat": "giao_thong"}
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
            return True
    except Exception:
        pass
    return False

# =========================================================================
# 🖼️ BÓC TÁCH ẢNH VÀ NỘI DUNG TỪ BÁO CAND, AN NING THỦ ĐÔ, PLO
# =========================================================================
def parse_article_page(url, source_name):
    real_img = ""
    content_html = ""

    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=10)
        if r.status_code != 200:
            return "", ""

        soup = BeautifulSoup(r.text, "html.parser")

        # 1. Bóc ảnh đại diện thật từ meta og:image hoặc twitter:image
        og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"}) or soup.find("meta", attrs={"name": "twitter:image"})
        if og_img and og_img.get("content"):
            real_img = og_img["content"].strip()

        # 2. Bóc nội dung theo cấu trúc chuyên biệt từng báo
        body = None
        if "Công An Nhân Dân" in source_name:
            body = soup.find("div", class_=re.compile("detail-content|content-detail|box-content"))
        elif "An Ninh Thủ Đô" in source_name:
            body = soup.find("div", class_=re.compile("article__body|content|detail"))
        elif "Pháp Luật TP.HCM" in source_name:
            body = soup.find("div", class_=re.compile("article-content|content"))
        elif "VnExpress" in source_name:
            body = soup.find("article", class_="fck_detail")

        if not body:
            body = soup.find("article") or soup.find("div", class_=re.compile("detail|content|post-body"))

        if body:
            # Xóa các thành phần thừa
            for j in body.find_all(["script", "style", "iframe", "button", "nav", "aside", "form"]):
                j.decompose()

            # Nếu chưa có og:image thì lấy ảnh đầu tiên trong bài
            if not real_img:
                first_img = body.find("img")
                if first_img:
                    real_img = first_img.get("data-src") or first_img.get("src") or ""

            parts = []
            for el in body.find_all(["p", "figure"]):
                if el.find_parent(class_=re.compile("box-related|relate|ads|author|social")):
                    continue

                if el.name == "figure":
                    img = el.find("img")
                    if img:
                        src = img.get("data-src") or img.get("src") or ""
                        cap = el.find("figcaption")
                        cap_text = cap.get_text().strip() if cap else ""
                        if src.startswith("http"):
                            safe_src = make_proxy_url(src)
                            parts.append(f"""
                                <figure style="margin: 18px 0; text-align: center;">
                                    <img src="{safe_src}" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.08);">
                                    {f'<figcaption style="font-size: 13px; color: #64748b; font-style: italic; margin-top: 6px;">{cap_text}</figcaption>' if cap_text else ''}
                                </figure>
                            """)
                elif el.name == "p":
                    t = el.get_text().strip()
                    if len(t) > 25 and not any(x in t.lower() for x in ["theo dõi trên", "chia sẻ bài", "bấm để xem"]):
                        parts.append(f"<p style='margin-bottom: 1.1rem; line-height: 1.85; color: #334155; font-size: 1rem; text-align: justify;'>{t}</p>")

            if parts:
                content_html = "".join(parts)

    except Exception as e:
        print(f"      [!] Lỗi bóc bài chi tiết: {e}")

    return real_img, content_html

def sync_crime_news():
    print("=" * 75)
    print("=== BẮT ĐẦU CÀO BÁO CÔNG AN NHÂN DÂN, AN NINH THỦ ĐÔ, PHÁP LUẬT ===")
    print("=" * 75)

    all_items = []

    for src in NEWS_SOURCES:
        try:
            print(f"[*] Đang đọc nguồn: {src['source']}")
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

    print(f"\n[+] Tổng số tin thu thập được từ báo CAND & ANTD: {len(all_items)}")
    added = 0

    for idx, item in enumerate(all_items[:LIMIT_NEWS], 1):
        title = item["title"]
        print(f"\n[{idx:03d}/{len(all_items[:LIMIT_NEWS]):03d}] Xử lý: {title[:55]}...")

        if check_exists(title):
            print("   (-) Tin đã có trong cơ sở dữ liệu, bỏ qua.")
            continue

        raw_img, full_html = parse_article_page(item["link"], item["source"])
        origin_img = raw_img or item["desc_img"]

        # Nếu hoàn toàn không có ảnh từ bài báo, bỏ qua để bảo đảm chất lượng hiển thị
        if not origin_img or not origin_img.startswith("http"):
            print("   (!) Không có ảnh bài báo, bỏ qua.")
            continue

        # BỌC PROXY ĐẢM BẢO ẢNH BÁO CAND / ANTD LUÔN HIỂN THỊ ĐẸP
        final_cover_img = make_proxy_url(origin_img)

        if not full_html:
            full_html = f"""
                <p style="font-weight: 600; font-size: 1.05rem; line-height: 1.8; color: #1e293b; margin-bottom: 1.25rem;">
                    {item['summary']}
                </p>
                <figure style="margin: 18px 0; text-align: center;">
                    <img src="{final_cover_img}" alt="{title}" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.08);">
                    <figcaption style="font-size: 13px; color: #64748b; font-style: italic; margin-top: 6px;">Hình ảnh tư liệu điều tra từ {item['source']}.</figcaption>
                </figure>
                <p style="margin-bottom: 1rem; line-height: 1.8; color: #334155; font-size: 1rem; text-align: justify;">
                    Vụ việc đang được cơ quan chức năng phụ trách địa bàn ({item['location']}) tiếp tục mở rộng điều tra, củng cố hồ sơ xử lý theo đúng quy định của pháp luật.
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
            res = requests.post(f"{SUPABASE_URL}/rest/v1/crime_news", headers=HEADERS, json=payload)
            if res.status_code in [200, 201]:
                print(f"   ✔ ĐÃ LƯU: [{item['category']}] ({item['source']}) | ẢNH CHUẨN")
                added += 1
            else:
                print(f"   [!] Lỗi lưu Supabase: {res.text}")
        except Exception as e:
            print(f"   [!] Lỗi mạng: {e}")

        time.sleep(0.2)

    print("\n" + "=" * 75)
    print(f"=== ĐÃ ĐỒNG BỘ THÀNH CÔNG {added} TIN TỪ BÁO CÔNG AN & PHÁP LUẬT VỚI ẢNH CHUẨN ===")
    print("=" * 75)

if __name__ == "__main__":
    sync_crime_news()
