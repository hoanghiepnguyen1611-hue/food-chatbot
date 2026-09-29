# -*- coding: utf-8 -*-
"""
SINH CƠ SỞ DỮ LIỆU QUÁN ĂN QUY MÔ LỚN (~850 quán tại TP.HCM).

Mỗi quán gồm đầy đủ các trường mà chatbot cần để tư vấn:
  tên quán, địa chỉ, quận, toạ độ (lat/lng), món chính, các món trong menu,
  khoảng giá, đánh giá sao, số lượt đánh giá, ĐẶC ĐIỂM VỊ (mặn/cay/ngọt/béo),
  khả năng điều chỉnh vị theo yêu cầu, giờ mở cửa, tiện ích, ảnh.

Điểm quan trọng: trường "taste_*" cho phép chatbot trả lời được những yêu cầu
như "ăn xôi nhưng không quá mặn" — thứ mà tìm kiếm theo từ khóa không làm được.

Chạy: python generate_restaurants.py   ->   restaurants.csv
"""
import csv
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from food_catalog import DISH_CATALOG, dishes_for_region  # noqa: E402
from geo import CITIES, CITY_OF, DISTRICTS  # noqa: E402

random.seed(2024)

# Số quán sinh cho từng vùng
TARGET_PER_CITY = {"TP.HCM": 1600, "Quảng Ngãi": 620}

# Ảnh minh hoạ theo từ khoá (loremflickr trả ảnh thật theo keyword)
IMAGE_KEYWORDS = {
    "xoi": ("sticky,rice,vietnamese", "🍚"), "banh_mi": ("banhmi,sandwich", "🥖"),
    "banh_cuon": ("vietnamese,food,steamed", "🥟"), "chao": ("porridge,congee", "🥣"),
    "banh_bao": ("bun,steamed,bao", "🥟"), "pho": ("pho,noodle,soup", "🍜"),
    "bun_bo": ("vietnamese,noodle,soup", "🍜"), "bun_cha": ("grilled,pork,noodle", "🍢"),
    "bun_rieu": ("crab,noodle,soup", "🦀"), "bun_thit_nuong": ("grilled,pork,vermicelli", "🍖"),
    "bun_dau": ("tofu,vietnamese,food", "🍢"), "hu_tieu": ("noodle,soup,asian", "🍜"),
    "mi_quang": ("vietnamese,noodle", "🍜"), "banh_canh": ("noodle,soup,crab", "🍲"),
    "mi_cay": ("spicy,noodle,ramen", "🌶️"), "com_tam": ("broken,rice,pork", "🍛"),
    "com_ga": ("chicken,rice", "🍗"), "com_van_phong": ("rice,lunch,vietnamese", "🍱"),
    "com_nieu": ("clay,pot,rice", "🍚"), "com_chien": ("fried,rice", "🍚"),
    "com_chay": ("vegetarian,food,rice", "🥬"), "salad": ("salad,healthy,bowl", "🥗"),
    "lau": ("hotpot,soup", "🍲"), "nuong": ("bbq,grill,meat", "🍖"),
    "oc": ("seafood,snail,shellfish", "🦐"), "bo_kho": ("beef,stew,vietnamese", "🍲"),
    "pha_lau": ("stew,offal,vietnamese", "🍲"), "banh_xeo": ("banhxeo,pancake", "🥞"),
    "goi_cuon": ("springroll,fresh", "🌯"), "banh_beo": ("hue,vietnamese,cake", "🍥"),
    "vit_quay": ("roast,duck", "🦆"), "banh_trang": ("streetfood,snack,vietnam", "🥠"),
    "xien_que": ("skewer,streetfood,fried", "🍡"), "ga_ran": ("fried,chicken", "🍗"),
    "pizza": ("pizza", "🍕"), "mi_y": ("pasta,spaghetti", "🍝"),
    "burger": ("burger", "🍔"), "sushi": ("sushi,sashimi", "🍣"),
    "ramen": ("ramen,noodle", "🍜"), "han_quoc": ("korean,food,tteokbokki", "🇰🇷"),
    "dimsum": ("dimsum,dumpling", "🥟"), "thai": ("thai,food,tomyum", "🇹🇭"),
    "tra_sua": ("bubble,tea,milktea", "🧋"), "ca_phe": ("coffee,cafe", "☕"),
    "don": ("clam,soup,vietnamese", "🐚"), "ram_bap": ("springroll,fried", "🌽"),
    "ca_bong": ("fish,braised,clay", "🐟"), "ca_nuc": ("fish,steamed,rollup", "🐠"),
    "bun_ca": ("fishcake,noodle,soup", "🐟"), "dac_san_qn": ("candy,sweets,gift", "🎁"),
    "che": ("dessert,sweet,soup", "🍧"), "kem_banh": ("icecream,cake,bakery", "🍰"),
    "sinh_to": ("smoothie,juice", "🥤"),
}

HONORIFICS = ["Cô", "Chú", "Dì", "Bà", "Anh", "Chị", "Ông", "Út", "Má"]
PERSON = ["Ba", "Tư", "Năm", "Sáu", "Bảy", "Tám", "Chín", "Mười", "Hoa", "Lan",
          "Mai", "Hùng", "Dũng", "Tâm", "Thảo", "Hạnh", "Nga", "Loan", "Phúc",
          "Khoa", "Minh", "Trang", "Yến", "Bình", "Sang", "Tèo", "Móm", "Mập",
          "Xị", "Lệ", "Thu", "Hà", "Vân", "Quý", "Tuấn", "Linh", "Nhàn"]
BRANDS = ["Ngon", "Xưa", "Phố Cổ", "Sài Gòn", "Quê Hương", "Gia Truyền", "3 Miền",
          "Nhà Làm", "Hội An", "Hà Nội", "Miền Tây", "Cô Tấm", "Mộc", "An Nhiên",
          "Thảo Điền", "Hương Việt", "Đất Việt", "Bà Chiểu", "Chợ Lớn", "Bến Thành",
          "Nam Bộ", "Đồng Quê", "Thành Phát", "Hạnh Phúc", "Tân Định", "Hoa Sen"]
LATIN = ["House", "Corner", "Garden", "Station", "Express", "Kitchen", "Deli",
         "Bistro", "Home", "Studio", "Lab", "Plus", "Signature"]
NUMBERS = ["68", "79", "86", "168", "39", "99", "123", "1985", "2000", "24h"]

# Trọng số phân bố quán theo khu vực: nơi trung tâm có mật độ hàng quán cao hơn
AREA_WEIGHTS = {
    # Quảng Ngãi (địa bàn TP Quảng Ngãi cũ, theo đơn vị hành chính từ 01/7/2025)
    "Phường Cẩm Thành": 14, "Phường Nghĩa Lộ": 11, "Phường Trương Quang Trọng": 7,
    "Xã Tịnh Khê": 5, "Xã An Phú": 4, "Xã Đông Sơn": 2,
    # TP.HCM
    "Quận 1": 12, "Quận 3": 10, "Quận 10": 9, "Bình Thạnh": 10, "Phú Nhuận": 8,
    "Tân Bình": 9, "Quận 5": 7, "Quận 4": 5, "Quận 7": 8, "Gò Vấp": 8,
    "Quận 11": 5, "Tân Phú": 6, "Quận 6": 4, "Quận 8": 4, "Bình Tân": 5,
    "Quận 12": 4, "Thủ Đức": 8, "Nhà Bè": 2,
}

UTILITIES = ["Máy lạnh", "Chỗ đậu xe hơi", "Giao hàng", "Nhận đặt bàn", "Wifi mạnh",
             "Có phòng riêng", "Bình dân", "View đẹp", "Mở khuya", "Không gian rộng",
             "Phù hợp nhóm đông", "Take away", "Thanh toán QR", "Phù hợp gia đình"]

ADJUSTABLE_POOL = {
    "man": "giảm mặn", "cay": "giảm cay", "ngot": "giảm ngọt / ít đường",
    "beo": "ít dầu mỡ",
}


def clamp(v, lo=0.02, hi=0.98):
    return max(lo, min(hi, v))


def taste_tag(dim: str, v: float) -> str:
    """Chuyển điểm số vị -> nhãn chữ dễ đọc cho người dùng."""
    if dim == "man":
        if v < 0.32: return "Vị thanh, nhạt"
        if v < 0.50: return "Vị vừa, không quá mặn"
        if v < 0.68: return "Vị đậm đà vừa phải"
        return "Vị rất đậm, hơi mặn"
    if dim == "cay":
        if v < 0.20: return "Không cay"
        if v < 0.45: return "Cay nhẹ"
        if v < 0.70: return "Cay vừa"
        return "Rất cay"
    if dim == "ngot":
        if v < 0.28: return "Ít ngọt"
        if v < 0.55: return "Ngọt vừa"
        if v < 0.75: return "Khá ngọt"
        return "Rất ngọt"
    if dim == "beo":
        if v < 0.30: return "Thanh đạm, ít dầu mỡ"
        if v < 0.55: return "Béo vừa"
        if v < 0.75: return "Khá nhiều dầu mỡ"
        return "Rất béo, nhiều dầu mỡ"
    return ""


def shift_time(hhmm: str, minutes: int) -> str:
    h, m = map(int, hhmm.split(":"))
    total = (h * 60 + m + minutes) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def gen_names(dish, n):
    """Sinh n tên quán khác nhau cho 1 loại món."""
    d = dish["name"]
    out = set()
    guard = 0
    while len(out) < n and guard < n * 60:
        guard += 1
        p = random.random()
        if p < 0.30:
            out.add(f"{d} {random.choice(HONORIFICS)} {random.choice(PERSON)}")
        elif p < 0.48:
            out.add(f"{d} {random.choice(BRANDS)}")
        elif p < 0.62:
            out.add(f"Quán {d} {random.choice(PERSON)}")
        elif p < 0.72:
            out.add(f"{d} {random.choice(NUMBERS)}")
        elif p < 0.82:
            out.add(f"{d} {random.choice(BRANDS)} {random.choice(NUMBERS)}")
        elif p < 0.92:
            out.add(f"{d} {random.choice(LATIN)}")
        else:
            out.add(f"{random.choice(BRANDS)} {d}")
    return list(out)


def main():
    rows = []
    idx = 0

    for city, target in TARGET_PER_CITY.items():
        areas = CITIES[city]["areas"]
        weights = [AREA_WEIGHTS.get(a, 3) for a in areas]
        catalog = dishes_for_region(city)
        per_dish = max(5, target // len(catalog))

        for dish in catalog:
            # đặc sản vùng thì mở nhiều quán hơn, món ngoại nhập thì ít hơn
            count = per_dish + random.randint(-4, 10)
            if dish.get("regions") and city in dish["regions"]:
                count = int(count * 1.6)
            if city == "Quảng Ngãi" and dish["category"] in (
                    "Món Âu – Fast food", "Món Á"):
                count = max(2, int(count * 0.45))

            names = gen_names(dish, count)
            img_kw, emoji = IMAGE_KEYWORDS.get(dish["key"], ("food", "🍽️"))

            for name in names:
                idx += 1
                rows.append(make_row(idx, name, dish, city, areas, weights, emoji))

    return finish(rows)


def make_row(idx, name, dish, city, areas, weights, emoji):
    rid = f"R{idx:05d}"
    area = random.choices(areas, weights=weights)[0]
    dinfo = DISTRICTS[area]
    street = random.choice(dinfo["streets"])
    house_no = random.choice([
        f"{random.randint(1, 450)}", f"{random.randint(1, 250)}A",
        f"{random.randint(1, 99)}/{random.randint(1, 60)}",
        f"{random.randint(1, 99)}/{random.randint(1, 30)}A",
    ])
    if city == "TP.HCM":
        address = f"{house_no} {street}, {area}, TP.HCM"
    else:
        address = f"{house_no} {street}, {area}, tỉnh Quảng Ngãi"

    spread = 0.020 if city == "TP.HCM" else 0.013
    lat = round(dinfo["lat"] + random.uniform(-spread, spread), 6)
    lng = round(dinfo["lng"] + random.uniform(-spread, spread), 6)

    lo, hi = dish["price"]
    span = hi - lo
    # mặt bằng giá ở Quảng Ngãi thấp hơn TP.HCM khoảng 15%
    factor = 1.0 if city == "TP.HCM" else 0.85
    pmin = int(round((lo + random.uniform(-0.12, 0.35) * span) * factor / 1000) * 1000)
    pmin = max(10000, pmin)
    pmax = int(round((pmin + random.uniform(0.35, 1.0) * span * factor) / 1000) * 1000)

    taste = {}
    for dim, base in dish["taste"].items():
        taste[dim] = round(clamp(base + random.gauss(0, 0.17)), 3)

    adjustable = []
    for dim in ("man", "cay", "ngot", "beo"):
        if taste[dim] > 0.45 and random.random() < 0.5:
            adjustable.append(ADJUSTABLE_POOL[dim])

    rating = round(clamp(random.gauss(4.05, 0.45), 2.6, 5.0), 1)
    num_reviews = int(max(8, random.lognormvariate(4.6 if city == "TP.HCM" else 3.9,
                                                   0.95)))

    open_t = shift_time(dish["hours"][0], random.choice([-60, -30, 0, 0, 30, 60]))
    close_t = shift_time(dish["hours"][1], random.choice([-60, -30, 0, 0, 30, 60]))
    utils = random.sample(UTILITIES, k=random.randint(2, 5))
    menu = random.sample(dish["items"], k=min(len(dish["items"]), random.randint(2, 4)))
    tags = [taste_tag(d_, taste[d_]) for d_ in ("man", "cay", "ngot", "beo")]

    return {
        "restaurant_id": rid,
        "name": name,
        "city": city,
        "dish_key": dish["key"],
        "dish_name": dish["name"],
        "category": dish["category"],
        "address": address,
        "district": area,
        "street": street,
        "lat": lat,
        "lng": lng,
        "price_min": pmin,
        "price_max": pmax,
        "price_avg": int((pmin + pmax) / 2),
        "rating": rating,
        "num_reviews": num_reviews,
        "taste_man": taste["man"],
        "taste_cay": taste["cay"],
        "taste_ngot": taste["ngot"],
        "taste_beo": taste["beo"],
        "taste_tags": " | ".join(tags),
        "adjustable": ", ".join(adjustable),
        "open_time": open_t,
        "close_time": close_t,
        "menu": " | ".join(menu),
        "utilities": ", ".join(utils),
        "is_veg": int(bool(dish.get("is_veg", False))),
        "phone": f"0{random.choice([9,8,7,3,5])}{random.randint(10**7, 10**8-1)}",
        # Ảnh nằm trong project (SVG do generate_dish_images.py sinh ra) nên
        # không phụ thuộc website bên ngoài. Muốn dùng ảnh thật thì thay giá trị
        # cột photo_url bằng URL ảnh của quán.
        "image_url": f"/static/img/dishes/{dish['key']}.svg",
        "photo_url": "",
        "emoji": emoji,
        # Ghi rõ nguồn gốc dữ liệu: đây là dữ liệu MÔ PHỎNG, không phải quán thật
        "data_source": "simulated",
    }


def finish(rows):
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "restaurants.csv")
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Xuất kèm bản JSON để frontend/demo tĩnh dùng trực tiếp
    json_path = os.path.join(os.path.dirname(out_path), "restaurants.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)

    from collections import Counter
    by_city = Counter(r["city"] for r in rows)
    print(f"Đã sinh {len(rows):,} quán ăn mô phỏng -> restaurants.csv")
    for c, n in by_city.items():
        print(f"   · {c}: {n:,} quán")


if __name__ == "__main__":
    main()
