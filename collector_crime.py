import os
import re
import requests
from bs4 import BeautifulSoup
import sys

sys.stdout.reconfigure(line_buffering=True)

SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://lleeibzegmnycuingzgx.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "YOUR_SUPABASE_SERVICE_OR_ANON_KEY"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# Nguồn tin mẫu RSS / Web chính thống (Pháp luật, An ninh trật tự)
CRIME_SOURCES = [
    {
        "url": "https://cand.com.vn/Ban-tin-113/", # Báo CAND
        "source": "Báo Công An Nhân Dân",
        "category": "an_ninh_dia_phuong"
    },
    {
        "url": "https://dantri.com.vn/phap-luat.htm", # Dân Trí Pháp Luật
        "source": "Dân Trí",
        "category": "trong_an"
    }
]

def check_exists(title):
    try:
        url = f"{SUPABASE_URL}/rest/v1/crime_news?title=eq.{requests.utils.quote(title)}&select=id"
        res = requests.get(url, headers=HEADERS, timeout=8)
        if res.status_code == 200 and len(res.json()) > 0:
            return True
    except Exception:
        pass
    return False

def sync_crime_news():
    print("=== BẮT ĐẦU CÀO & ĐỒNG BỘ TIN AN NINH - TRẬT TỰ XÃ HỘI ===")
    
    # Dữ liệu mẫu chuẩn hóa để nạp ban đầu
    sample_news = [
        {
            "title": "Cảnh báo thủ đoạn giả danh công an gọi video đe dọa lệnh bắt tạm giam",
            "category": "lua_dao",
            "location": "Toàn quốc",
            "summary": "Bộ Công an khuyến cáo người dân không cung cấp mã OTP, thông tin tài khoản ngân hàng khi nhận các cuộc gọi tự xưng cơ quan điều tra.",
            "cover_image": "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=800&q=80",
            "source_name": "Báo Công An Nhân Dân",
            "source_url": "https://cand.com.vn/",
            "is_breaking": True,
            "content_html": "<p>Thời gian gần đây, tội phạm công nghệ cao tiếp tục sử dụng chiêu thức gọi điện mạo danh cơ quan tố tụng, đe dọa nạn nhân liên quan đến các đường dây rửa tiền...</p>"
        },
        {
            "title": "Triệt phá đường dây vận chuyển 20 bánh ma túy từ biên giới",
            "category": "trong_an",
            "location": "Điện Biên",
            "summary": "Lực lượng chức năng vừa bắt quả tang 2 đối tượng đang vận chuyển số lượng lớn chất cấm qua đường mòn biên giới.",
            "cover_image": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=800&q=80",
            "source_name": "Báo Pháp Luật",
            "source_url": "https://plo.vn/",
            "is_breaking": False,
            "content_html": "<p>Khoảng 2h sáng cùng ngày, tại khu vực mốc biên giới, tổ chuyên án phát hiện 2 người đàn ông di chuyển với nhiều biểu hiện nghi vấn...</p>"
        }
    ]

    for item in sample_news:
        if not check_exists(item["title"]):
            slug = re.sub(r'[^a-z0-9]+', '-', item["title"].lower()).strip('-')
            payload = {
                "title": item["title"],
                "slug": slug,
                "category": item["category"],
                "location": item["location"],
                "summary": item["summary"],
                "cover_image": item["cover_image"],
                "content_html": item["content_html"],
                "source_name": item["source_name"],
                "source_url": item["source_url"],
                "is_breaking": item.get("is_breaking", False)
            }
            res = requests.post(f"{SUPABASE_URL}/rest/v1/crime_news", headers=HEADERS, json=payload)
            if res.status_code in [200, 201]:
                print(f"✔ Đã thêm tin: {item['title'][:50]}...")
            else:
                print(f"❌ Lỗi ghi tin: {res.text}")
        else:
            print(f"(-) Tin đã tồn tại: {item['title'][:40]}...")

    print("=== HOÀN TẤT THU THẬP TIN TỨC ===")

if __name__ == "__main__":
    sync_crime_news()
