# -*- coding: utf-8 -*-
"""
NHẬP DỮ LIỆU QUÁN ĂN THẬT TỪ GOOGLE PLACES API.

Dữ liệu trong `restaurants.csv` mặc định là DỮ LIỆU MÔ PHỎNG (cột
`data_source = simulated`) — tên quán, địa chỉ, toạ độ đều do máy sinh ra để
chạy thử hệ thống, KHÔNG phải quán có thật.

Muốn có danh sách quán thật ở một địa bàn (ví dụ khu vực TP Quảng Ngãi cũ), hãy
chạy script này. Nó gọi Google Places API (Text Search + Place Details), chuyển
kết quả về đúng định dạng cột mà chatbot đang dùng, và ghi ra
`restaurants_real.csv` với `data_source = google_places`.

CHUẨN BỊ
--------
1. Tạo API key tại Google Cloud Console, bật "Places API (New)".
2. Đặt biến môi trường:   export GOOGLE_MAPS_API_KEY="..."
3. pip install requests
4. Chạy:  python import_places.py --city "Quảng Ngãi" --max-per-query 60

LƯU Ý QUAN TRỌNG
----------------
- Places API tính phí theo số lượt gọi; hãy xem bảng giá trước khi quét rộng.
- Mỗi truy vấn Text Search chỉ trả tối đa 60 kết quả (3 trang × 20). Muốn phủ
  hết một địa bàn thì phải chia nhỏ theo từ khoá món ăn và theo ô lưới toạ độ —
  tham số `--grid` bên dưới làm việc đó.
- Điều khoản của Google KHÔNG cho phép lưu trữ dài hạn phần lớn dữ liệu Places
  (trừ place_id). Với khoá luận/demo thì dùng tạm được, nhưng nếu triển khai
  thật cần đọc kỹ Google Maps Platform Terms of Service.
- Google KHÔNG cung cấp "độ mặn / độ cay" của món. Script điền hồ sơ vị bằng
  giá trị mặc định của nhóm món trong `food_catalog.py` và đánh dấu
  `taste_source = dish_default`. Muốn có hồ sơ vị đúng theo từng quán, cần chạy
  mô hình ABSA trên chính các review lấy về (xem `src/aspect_extraction.py`).
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from food_catalog import DISH_CATALOG, find_dishes  # noqa: E402
from geo import CITIES, DISTRICTS  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
TEXT_SEARCH = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = ",".join([
    "places.id", "places.displayName", "places.formattedAddress",
    "places.location", "places.rating", "places.userRatingCount",
    "places.priceLevel", "places.primaryTypeDisplayName",
    "places.regularOpeningHours", "places.nationalPhoneNumber",
    "places.photos", "places.googleMapsUri",
])

# Ước lượng khoảng giá theo priceLevel của Google (VND) — Google chỉ cho mức
# 1..4 chứ không cho con số, nên đây là quy đổi thô, cần hiệu chỉnh theo địa bàn.
PRICE_BY_LEVEL = {
    "PRICE_LEVEL_INEXPENSIVE": (20000, 60000),
    "PRICE_LEVEL_MODERATE": (60000, 150000),
    "PRICE_LEVEL_EXPENSIVE": (150000, 400000),
    "PRICE_LEVEL_VERY_EXPENSIVE": (400000, 1000000),
}


def guess_dish(name: str, type_name: str):
    """Đoán nhóm món từ tên quán / loại hình mà Google trả về."""
    for text in (name, type_name or ""):
        keys = find_dishes(text)
        if keys:
            return next(d for d in DISH_CATALOG if d["key"] == keys[0])
    return None


def parse_hours(opening):
    """Lấy giờ mở–đóng của ngày thường từ regularOpeningHours."""
    try:
        periods = opening.get("periods", [])
        for p in periods:
            o, c = p.get("open", {}), p.get("close", {})
            if "hour" in o and "hour" in c:
                return (f"{o['hour']:02d}:{o.get('minute', 0):02d}",
                        f"{c['hour']:02d}:{c.get('minute', 0):02d}")
    except Exception:
        pass
    return ("08:00", "21:00")


def search(session, api_key, query, lat, lng, radius_m, page_token=None):
    headers = {"Content-Type": "application/json",
               "X-Goog-Api-Key": api_key,
               "X-Goog-FieldMask": FIELD_MASK + ",nextPageToken"}
    body = {"textQuery": query, "languageCode": "vi", "regionCode": "VN",
            "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng},
                                        "radius": radius_m}}}
    if page_token:
        body["pageToken"] = page_token
    r = session.post(TEXT_SEARCH, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="Quảng Ngãi", choices=list(CITIES))
    ap.add_argument("--max-per-query", type=int, default=60)
    ap.add_argument("--radius", type=int, default=6000, help="bán kính mỗi ô lưới (m)")
    ap.add_argument("--grid", type=int, default=1,
                    help="số ô lưới mỗi chiều; tăng lên để phủ rộng hơn")
    ap.add_argument("--out", default="restaurants_real.csv")
    args = ap.parse_args()

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print("Thiếu GOOGLE_MAPS_API_KEY. Xem hướng dẫn ở đầu file này.")
        return 1
    try:
        import requests
    except ImportError:
        print("Cần cài: pip install requests")
        return 1

    session = requests.Session()
    center = CITIES[args.city]["center"]
    areas = CITIES[args.city]["areas"]

    # điểm quét: tâm từng phường/xã, giúp phủ đều địa bàn thay vì dồn vào trung tâm
    spots = [(a, DISTRICTS[a]["lat"], DISTRICTS[a]["lng"]) for a in areas] or \
            [(args.city, center[0], center[1])]

    seen, rows = set(), []
    queries = [f"{d['name']} {args.city}" for d in DISH_CATALOG] + \
              [f"quán ăn {args.city}", f"nhà hàng {args.city}"]

    for area, lat, lng in spots:
        for q in queries:
            token, got = None, 0
            while got < args.max_per_query:
                try:
                    data = search(session, api_key, q, lat, lng, args.radius, token)
                except Exception as e:
                    print(f"  ! lỗi khi tìm '{q}': {e}")
                    break
                places = data.get("places", [])
                if not places:
                    break
                for p in places:
                    pid = p.get("id")
                    if not pid or pid in seen:
                        continue
                    seen.add(pid)
                    name = (p.get("displayName") or {}).get("text", "")
                    type_name = (p.get("primaryTypeDisplayName") or {}).get("text", "")
                    dish = guess_dish(name, type_name)
                    if dish is None:
                        continue                     # không xác định được nhóm món
                    loc = p.get("location", {})
                    lo, hi = PRICE_BY_LEVEL.get(p.get("priceLevel", ""),
                                                dish["price"])
                    open_t, close_t = parse_hours(p.get("regularOpeningHours", {}))
                    rows.append({
                        "restaurant_id": pid,
                        "name": name,
                        "city": args.city,
                        "dish_key": dish["key"],
                        "dish_name": dish["name"],
                        "category": dish["category"],
                        "address": p.get("formattedAddress", ""),
                        "district": area,
                        "street": "",
                        "lat": loc.get("latitude"),
                        "lng": loc.get("longitude"),
                        "price_min": lo, "price_max": hi,
                        "price_avg": int((lo + hi) / 2),
                        "rating": p.get("rating") or 0,
                        "num_reviews": p.get("userRatingCount") or 0,
                        # Google không có dữ liệu khẩu vị -> dùng mặc định của món
                        "taste_man": dish["taste"]["man"],
                        "taste_cay": dish["taste"]["cay"],
                        "taste_ngot": dish["taste"]["ngot"],
                        "taste_beo": dish["taste"]["beo"],
                        "taste_tags": "", "adjustable": "",
                        "open_time": open_t, "close_time": close_t,
                        "menu": " | ".join(dish["items"][:3]),
                        "utilities": "", "is_veg": int(bool(dish.get("is_veg"))),
                        "phone": p.get("nationalPhoneNumber", ""),
                        "image_url": f"/static/img/dishes/{dish['key']}.svg",
                        "photo_url": "",       # cần gọi Place Photo API riêng
                        "emoji": "🍽️",
                        "data_source": "google_places",
                        "taste_source": "dish_default",
                        "maps_uri": p.get("googleMapsUri", ""),
                    })
                    got += 1
                token = data.get("nextPageToken")
                if not token:
                    break
                time.sleep(2)     # Google yêu cầu chờ giữa các trang
            print(f"  {area} · {q}: tổng cộng {len(rows)} quán")

    if not rows:
        print("Không lấy được quán nào.")
        return 1

    out = os.path.join(BASE, args.out)
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nĐã ghi {len(rows):,} quán THẬT -> {args.out}")
    print("Để chatbot dùng file này: đổi tên thành restaurants.csv (nên giữ bản "
          "mô phỏng lại để so sánh), rồi chạy lại python train.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
