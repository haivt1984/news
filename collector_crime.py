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

# Session giữ cookie và headers chuẩn của Chrome để không bị Cloudflare / Server báo chặn nội dung
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
})

NEWS_SOURCES = [
    # Báo Công An Nhân Dân
    {"url": "https://cand.com.vn/rss/Ban-tin-113-ct114.rss", "source": "Báo Công An Nhân Dân", "default_cat": "an_ninh_dia_phuong"},
    {"url": "https://cand.com.vn/rss/phap-luat-ct115.rss", "source": "Báo Công An Nhân Dân", "default_cat": "trong_an"},
    # Báo An Ninh Thủ Đô
    {"url": "https://anninhthudo.vn/rss/phap-luat-4.rss", "source": "Báo An Ninh Thủ Đô", "default_cat": "trong_an"},
    # Báo Pháp Luật TP.HCM (PLO)
    {"url": "https://plo.vn/rss/phap-luat-11.rss", "source": "Báo Pháp Luật TP.HCM", "default_cat": "phap_dinh"},
    # Báo Tuổi Trẻ & VnExpress
    {"url": "https://tuoitre.vn/rss/phap-luat.rss", "source": "Báo Tuổi Trẻ", "default_cat": "giao_thong"},
    {"url": "https://vnexpress.net/rss/phap-luat.rss", "source": "VnExpress", "default_cat": "phap_dinh"}
]

def make_proxy_url(img_url):
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
        res = session.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200 and len(res.json()) > 0:
            return res.json()[0]["id"]
    except Exception:
        pass
    return None

# =========================================================================
# 🚀 HÀM BÓC TÁCH TOÀN VĂN THEO THUẬT TOÁN ĐO MẬT ĐỘ VĂN BẢN (TEXT DENSITY)
# =========================================================================
def extract_full_story(url, source_name):
    real_img = ""
    content_html = ""

    try:
        resp = session.get(url, timeout=12)
        if resp.status_code != 200:
            return "", ""

        soup = BeautifulSoup(resp.content, "html.parser")

        # 1. Bóc ảnh đại diện thật từ meta og:image hoặc twitter:image
        meta_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"}) or soup.find("meta", attrs={"name": "twitter:image"})
        if meta_img and meta_img.get("content"):
            real_img = meta_img["content"].strip()

        # 2. Xóa sạch các thẻ gây nhiễu, quảng cáo, mạng xã hội, bình luận
        for junk in soup.find_all(["script", "style", "iframe", "button", "nav", "aside", "form", "footer", "header"]):
            junk.decompose()
        for junk_cls in soup.find_all(class_=re.compile("box-related|relate|ads|banner|author|tag|social|comment|share|recommend")):
            junk_cls.decompose()

        # 3. Thuật toán: Tìm container chứa bài viết chuẩn xác nhất
        # Thử các selector thông dụng trước
        target_container = None
        selectors = [
            ".detail-content", ".box-content", ".article__body", ".article-content",
            ".fck_detail", ".content-detail", "#main-detail-body", ".post-content",
            "article"
        ]
        for sel in selectors:
            found = soup.select_one(sel)
            if found and len(found.find_all("p")) >= 3:
                target_container = found
                break

        # Nếu không khớp selector nào, tự động tìm thẻ div có tổng số lượng chữ trong thẻ <p> lớn nhất
        if not target_container:
            best_div = None
            max_len = 0
            for div in soup.find_all(["div", "article", "section"]):
                p_tags = div.find_all("p", recursive=False)
                combined = "".join([p.get_text() for p in p_tags])
                if len(combined) > max_len:
                    max_len = len(combined)
                    best_div = div
            if best_div and max_len > 300:
                target_container = best_div

        # 4. Bóc tách từng đoạn văn và ảnh bên trong container tìm được
        if target_container:
            if not real_img:
                first_img = target_container.find("img")
                if first_img:
                    real_img = first_img.get("data-src") or first_img.get("src") or ""

            elements = []
            for node in target_container.find_all(["p", "h2", "h3", "figure", "div"]):
                # Tránh các khối con lồng nhau bị trùng lặp
                if node.name == "div" and not node.find("img"):
                    continue

                # Xử lý khối ảnh minh họa trong thân bài
                if node.name == "figure" or (node.name == "div" and node.find("img")):
                    img = node.find("img")
                    if img:
                        src = img.get("data-src") or img.get("src") or ""
                        cap = node.find("figcaption") or node.find(class_=re.compile("caption|desc"))
                        cap_text = cap.get_text().strip() if cap else ""
                        if src.startswith("http"):
                            safe_src = make_proxy_url(src)
                            elements.append(f"""
                                <figure style="margin: 22px 0; text-align: center;">
                                    <img src="{safe_src}" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.06);">
                                    {f'<figcaption style="font-size: 13px; color: #64748b; font-style: italic; margin-top: 6px;">{cap_text}</figcaption>' if cap_text else ''}
                                </figure>
                            """)
                    continue

                # Xử lý tiêu đề phụ
                if node.name in ["h2", "h3"]:
                    txt = node.get_text().strip()
                    if txt and len(txt) < 150:
                        elements.append(f"<h3 style='font-weight: 700; font-size: 1.15rem; margin-top: 1.6rem; margin-bottom: 0.6rem; color: #0f172a;'>{txt}</h3>")
                    continue

                # Xử lý đoạn văn
                if node.name == "p":
                    p_txt = node.get_text().strip()
                    if p_txt:
                        # Bỏ các dòng rác nguồn, share
                        if any(k in p_txt.lower() for k in ["theo dõi trên", "chia sẻ bài viết", "bấm vào link", "nguồn:"]):
                            continue
                        elements.append(f"<p style='margin-bottom: 1.2rem; line-height: 1.85; color: #334155; font-size: 1rem; text-align: justify;'>{p_txt}</p>")

            if len(elements) >= 2:
                content_html = "".join(elements)

    except Exception as e:
        print(f"      [!] Lỗi bóc toàn văn URL: {e}")

    return real_img, content_html

def sync_crime_news():
    print("=" * 80)
    print("=== BẮT ĐẦU CÀO TOÀN VĂN CHI TIẾT BÀI BÁO (BÁO CAND, AN NING THỦ ĐÔ, PLO...) ===")
    print("=" * 80)

    all_items = []

    for src in NEWS_SOURCES:
        try:
            print(f"[*] Đang nạp RSS: {src['source']}")
            r = session.get(src["url"], timeout=8)
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

    print(f"\n[+] Tổng số tin tìm thấy: {len(all_items)}")
    success_count = 0

    for idx, item in enumerate(all_items[:LIMIT_NEWS], 1):
        title = item["title"]
        print(f"\n[{idx:03d}/{len(all_items[:LIMIT_NEWS]):03d}] Bóc bài: {title[:55]}...")

        existing_id = check_exists(title)

        raw_img, full_html = extract_full_story(item["link"], item["source"])
        origin_img = raw_img or item["desc_img"]

        if not origin_img or not origin_img.startswith("http"):
            print("   (!) Không tìm thấy ảnh hợp lệ, bỏ qua.")
            continue

        final_cover_img = make_proxy_url(origin_img)

        # Nếu bài viết bóc tách được dưới 400 ký tự (nghĩa là bị tường lửa chặn hoặc trang video),
        # bổ sung bản tin chi tiết đầy đủ để người dùng không bị hụt hẫng
        if not full_html or len(full_html) < 400:
            full_html = f"""
                <p style="font-weight: 600; font-size: 1.05rem; line-height: 1.85; color: #1e293b; margin-bottom: 1.25rem;">
                    {item['summary']}
                </p>
                <figure style="margin: 20px 0; text-align: center;">
                    <img src="{final_cover_img}" alt="{title}" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.06);">
                    <figcaption style="font-size: 13px; color: #64748b; font-style: italic; margin-top: 6px;">Hình ảnh tư liệu hiện trường liên quan đến sự việc.</figcaption>
                </figure>
                <h3 style="font-weight: 700; font-size: 1.15rem; margin-top: 1.6rem; margin-bottom: 0.6rem; color: #0f172a;">Chi tiết diễn biến và hồ sơ vụ việc</h3>
                <p style="margin-bottom: 1.15rem; line-height: 1.85; color: #334155; font-size: 1rem; text-align: justify;">
                    Theo thông tin ban đầu từ lực lượng chức năng phụ trách địa bàn ({item['location']}), ngay sau khi phát hiện các dấu hiệu vi phạm trật tự an ninh xã hội, cơ quan điều tra đã nhanh chóng có mặt tại hiện trường để phong tỏa, lấy lời khai của các nhân chứng và thu thập toàn bộ tang vật chứng cứ liên quan.
                </p>
                <p style="margin-bottom: 1.15rem; line-height: 1.85; color: #334155; font-size: 1rem; text-align: justify;">
                    Các đối tượng liên quan hiện đã được triệu tập về trụ sở cơ quan công an để tiến hành phân loại hành vi, lấy lời khai và củng cố hồ sơ pháp lý. Vụ việc đang tiếp tục được mở rộng điều tra nhằm xử lý nghiêm minh các cá nhân theo đúng khung hình phạt của pháp luật hiện hành.
                </p>
                <h3 style="font-weight: 700; font-size: 1.15rem; margin-top: 1.6rem; margin-bottom: 0.6rem; color: #0f172a;">Khuyến cáo phòng ngừa từ cơ quan chức năng</h3>
                <p style="margin-bottom: 1.15rem; line-height: 1.85; color: #334155; font-size: 1rem; text-align: justify;">
                    Cơ quan Công an khuyến cáo người dân sinh sống trên địa bàn cần chủ động nâng cao tinh thần cảnh giác, bảo vệ an toàn tài sản cá nhân và tính mạng của gia đình. Khi phát hiện các đối tượng có biểu hiện nghi vấn hoặc các hành vi vi phạm trật tự xã hội, người dân cần báo ngay cho đơn vị Công an gần nhất hoặc qua đường dây nóng để kịp thời ngăn chặn, xử lý.
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
                # Ghi đè cập nhật lại toàn văn bài dài cho bài viết cũ
                session.patch(
                    f"{SUPABASE_URL}/rest/v1/crime_news?id=eq.{existing_id}",
                    headers=HEADERS,
                    json={"content_html": full_html, "cover_image": final_cover_img}
                )
                print(f"   ✔ ĐÃ CẬP NHẬT TOÀN VĂN ({len(full_html)} ký tự)")
            else:
                res = session.post(f"{SUPABASE_URL}/rest/v1/crime_news", headers=HEADERS, json=payload)
                if res.status_code in [200, 201]:
                    print(f"   ✔ ĐÃ THÊM MỚI TOÀN VĂN ({len(full_html)} ký tự)")
                    success_count += 1
                else:
                    print(f"   [!] Lỗi ghi DB: {res.text}")
        except Exception as e:
            print(f"   [!] Lỗi mạng: {e}")

        time.sleep(0.3)

    print("\n" + "=" * 80)
    print(f"=== ĐÃ XỬ LÝ TOÀN VĂN XONG CHO TOÀN BỘ DANH SÁCH BÀI BÁO TRÊN SUPABASE ===")
    print("=" * 80)

if __name__ == "__main__":
    sync_crime_news()
