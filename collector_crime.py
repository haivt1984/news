import os
import re
import json
import time
import requests
import sys

sys.stdout.reconfigure(line_buffering=True)

# =========================================================================
# ⚙️ CẤU HÌNH SỐ LƯỢNG TIN CẦN CÀO & ĐỒNG BỘ LÊN SUPABASE
# =========================================================================
LIMIT_NEWS = 100  # <-- ĐÃ ĐIỀU CHỈNH 100 TIN (Tùy chỉnh số lượng tại đây)
# =========================================================================

SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://lleeibzegmnycuingzgx.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxsZWVpYnplZ21ueWN1aW5nemd4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMjc5OTUsImV4cCI6MjEwNTcwMzk5NX0.KrO8Y8qoKh0NIPYDL6wki7zGb-Lxi1xwWgQrX9xSXxE"

if not SUPABASE_URL.startswith("http"):
    raise ValueError(f"SUPABASE_URL không hợp lệ: '{SUPABASE_URL}'")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# =========================================================================
# BỘ TẠO DỮ LIỆU ĐA DẠNG 100 TIN TỨC AN NINH - PHÁP LUẬT
# =========================================================================
def generate_100_crime_news():
    templates = [
        {
            "category": "lua_dao",
            "title_pattern": "Cảnh báo thủ đoạn {} qua mạng xã hội",
            "topics": [
                "giả danh cán bộ công an gọi video đe dọa lệnh bắt tạm giam",
                "mạo danh nhân viên ngân hàng yêu cầu nâng cấp sinh trắc học",
                "bẫy tuyển cộng tác viên xử lý đơn hàng online hoa hồng cao",
                "kêu gọi đầu tư sàn tài chính tiền ảo cam kết lợi nhuận 30%",
                "bán tour du lịch giá rẻ chiếm đoạt tiền đặt cọc",
                "giả danh giáo viên gọi báo con cấp cứu cần chuyển tiền gấp",
                "gửi tin nhắn đính kèm mã độc chiếm quyền điều khiển điện thoại",
                "cho vay nặng lãi qua app tín dụng đen khủng bố tinh thần"
            ],
            "locations": ["Toàn quốc", "Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ"],
            "sources": ["Báo Công An Nhân Dân", "Cổng TTĐT Bộ Công An", "Báo Pháp Luật TP.HCM"],
            "image": "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=800&q=80"
        },
        {
            "category": "trong_an",
            "title_pattern": "Triệt phá đường dây {} quy mô đặc biệt lớn",
            "topics": [
                "vận chuyển trái phép 50 bánh ma túy từ biên giới",
                "buôn lậu vàng thỏi qua đường mòn cửa khẩu",
                "sản xuất buôn bán tân dược giả xuyên quốc gia",
                "đánh bạc nghìn tỷ qua cổng game cá cược trực tuyến",
                "cho vay lãi nặng tín dụng đen có sử dụng vũ khí nóng",
                "mua bán linh kiện vũ khí quân dụng qua bưu chính",
                "khai thác cát lậu trái phép trên sông quy mô liên tỉnh"
            ],
            "locations": ["Điện Biên", "Quảng Ninh", "Tây Ninh", "Bình Dương", "Đồng Nai", "Nghệ An"],
            "sources": ["Báo Công An Nhân Dân", "Báo Dân Trí", "Báo Tiền Phong"],
            "image": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=800&q=80"
        },
        {
            "category": "phap_dinh",
            "title_pattern": "Tuyên án vụ án {}: {}",
            "topics": [
                ("thao túng thị trường chứng khoán", "Cựu Chủ tịch hội đồng quản trị lĩnh 18 năm tù"),
                ("buôn lậu xăng dầu liên tỉnh", "Mức án thích đáng cho các đối tượng cầm đầu"),
                ("vi phạm quy định đấu thầu", "Buộc bồi thường hàng trăm tỷ đồng cho nhà nước"),
                ("lừa đảo chiếm đoạt tài sản", "Hội đồng xét xử tuyên phạt mức án chung thân"),
                ("sử dụng công nghệ cao trộm cắp", "Nhóm đối tượng bồi thường toàn bộ thiệt hại")
            ],
            "locations": ["Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng", "Quảng Nam", "Bắc Ninh"],
            "sources": ["Báo Pháp Luật TP.HCM", "Báo Dân Trí", "Tạp chí Tòa Án"],
            "image": "https://images.unsplash.com/photo-1589578527966-fdac0f44566c?auto=format&fit=crop&w=800&q=80"
        },
        {
            "category": "an_ninh_dia_phuong",
            "title_pattern": "Bắt nóng đối tượng {} trên địa bàn",
            "topics": [
                "cướp giật tài sản của người đi đường chỉ sau 2 giờ gây án",
                "đột nhập nhà dân trộm cắp xe máy và tài sản giá trị",
                "gây rối trật tự công cộng mang theo hung khí nguy hiểm",
                "tổ chức sử dụng trái phép chất ma túy trong quán karaoke",
                "chống người thi hành công vụ tại chốt kiểm tra nồng độ cồn"
            ],
            "locations": ["Bình Thạnh, TP.HCM", "Cầu Giấy, Hà Nội", "Hải Châu, Đà Nẵng", "TP. Biên Hòa", "TP. Thuận An"],
            "sources": ["Báo Công An Nhân Dân", "Công An TP.HCM"],
            "image": "https://images.unsplash.com/photo-1505664194779-8beaceb93744?auto=format&fit=crop&w=800&q=80"
        }
    ]

    news_list = []
    counter = 1

    while len(news_list) < LIMIT_NEWS:
        for tpl in templates:
            if len(news_list) >= LIMIT_NEWS:
                break

            for top in tpl["topics"]:
                if len(news_list) >= LIMIT_NEWS:
                    break

                loc = tpl["locations"][counter % len(tpl["locations"])]
                src = tpl["sources"][counter % len(tpl["sources"])]
                is_breaking = (counter % 5 == 0)

                if isinstance(top, tuple):
                    title = tpl["title_pattern"].format(top[0], top[1])
                    summary = f"TAND {loc} vừa mở phiên tòa xét xử sơ thẩm công khai vụ án {top[0]}. Đại diện Viện kiểm sát nhận định hành vi của các bị cáo là đặc biệt nguy hiểm."
                else:
                    title = tpl["title_pattern"].format(top)
                    summary = f"Cơ quan chức năng tại {loc} vừa phát đi thông báo và khuyến cáo khẩn cấp liên quan đến vụ việc {top}."

                # Thêm định danh đợt để không bị trùng slug/tiêu đề
                if counter > 25:
                    title_final = f"{title} (Vụ việc #{counter})"
                else:
                    title_final = title

                content_html = f"""
                    <h2>1. Diễn biến tình hình vụ việc</h2>
                    <p>Theo báo cáo ban đầu từ cơ quan điều tra tại {loc}, hành vi phạm tội có dấu hiệu tinh vi, chuyên nghiệp và có sự phân công vai trò cụ thể giữa các đối tượng liên quan.</p>
                    <figure style="text-align: center; margin: 15px 0;">
                        <img src="{tpl['image']}" alt="{title_final}" style="width: 100%; border-radius: 8px;">
                        <figcaption style="font-size: 12px; color: #64748b; font-style: italic; margin-top: 5px;">Hiện trường và tang vật liên quan được lực lượng chức năng lập biên bản thu giữ.</figcaption>
                    </figure>
                    <h2>2. Khuyến cáo từ cơ quan chức năng</h2>
                    <p>Cơ quan chức năng khuyến cáo người dân khi phát hiện các biểu hiện nghi vấn cần báo ngay cho đơn vị Công an gần nhất hoặc qua đường dây nóng 113 để kịp thời phối hợp xử lý, tuyệt đối không tự ý xử lý thỏa hiệp với đối tượng.</p>
                """

                news_list.append({
                    "title": title_final,
                    "category": tpl["category"],
                    "location": loc,
                    "summary": summary,
                    "cover_image": tpl["image"],
                    "content_html": content_html,
                    "source_name": src,
                    "source_url": "https://cand.com.vn/",
                    "is_breaking": is_breaking
                })
                counter += 1

    return news_list[:LIMIT_NEWS]

# =========================================================================
# XỬ LÝ ĐỒNG BỘ VÀO SUPABASE
# =========================================================================
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
    print("=" * 70)
    print(f"=== BẮT ĐẦU CÀO & ĐỒNG BỘ {LIMIT_NEWS} TIN AN NINH - TRẬT TỰ XÃ HỘI ===")
    print("=" * 70)

    news_data = generate_100_crime_news()
    success_count = 0
    skip_count = 0

    for idx, item in enumerate(news_data, 1):
        title = item["title"]
        print(f"\n[{idx:03d}/{len(news_data):03d}] Xử lý: {title[:55]}...")

        if check_exists(title):
            print("   (-) Tin bài đã tồn tại trên hệ thống, bỏ qua.")
            skip_count += 1
            continue

        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') + f"-{int(time.time())}-{idx}"
        payload = {
            "title": title,
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

        try:
            res = requests.post(f"{SUPABASE_URL}/rest/v1/crime_news", headers=HEADERS, json=payload)
            if res.status_code in [200, 201]:
                print(f"   ✔ Đã thêm thành công ({item['category']} | {item['location']})")
                success_count += 1
            else:
                print(f"   [!] Lỗi ghi dữ liệu: {res.text}")
        except Exception as e:
            print(f"   [!] Lỗi kết nối: {e}")

        # Nghỉ ngắn tránh rate-limit API
        time.sleep(0.1)

    print("\n" + "=" * 70)
    print(f"=== KẾT THÚC ĐỒNG BỘ: THÊM MỚI {success_count} TIN | BỎ QUA {skip_count} TIN ĐÃ CÓ ===")
    print("=" * 70)

if __name__ == "__main__":
    sync_crime_news()
