# -*- coding: utf-8 -*-
"""
SINH DỮ LIỆU ĐÁNH GIÁ (REVIEW) cho toàn bộ quán ăn trong restaurants.csv.

Khác với bản cũ (chỉ 10 quán, review chung chung), bản này sinh review CÓ ĐỘ
NHẤT QUÁN VỚI HỒ SƠ VỊ của quán: quán có taste_man cao thì khách sẽ than
"hơi mặn", quán taste_man thấp thì khách khen "vị vừa, không quá mặn".

Nhờ vậy mô hình NLP (sentiment + aspect extraction) học được tín hiệu vị từ
văn bản, và chatbot có thể trích dẫn "bằng chứng" từ review thật khi tư vấn
câu hỏi kiểu "xôi không quá mặn".

Chạy: python generate_sample_data.py   ->   reviews.csv
"""
import csv
import os
import random

random.seed(7)

BASE = os.path.dirname(os.path.abspath(__file__))
REVIEWS_PER_RESTAURANT = (6, 14)

# ------------------------------------------------- câu review theo khía cạnh
POS_FOOD = ["món ăn rất ngon, đậm đà đúng vị", "đồ ăn tươi ngon, chế biến khéo léo",
            "hương vị tuyệt vời, ăn là ghiền", "nước dùng ngọt thanh tự nhiên",
            "nguyên liệu tươi, chất lượng ổn định", "món ăn trình bày đẹp mắt và ngon"]
NEG_FOOD = ["đồ ăn nhạt nhẽo, không có gì đặc sắc", "món ăn bị nguội, mất ngon",
            "nguyên liệu không tươi, có mùi lạ", "chất lượng món ăn giảm so với trước",
            "đồ ăn dở tệ, không đáng tiền"]

POS_PRICE = ["giá cả hợp lý, phù hợp túi tiền sinh viên", "giá rẻ mà chất lượng tốt",
             "giá hơi cao nhưng xứng đáng với chất lượng", "khẩu phần nhiều, đáng đồng tiền"]
NEG_PRICE = ["giá hơi đắt so với chất lượng", "giá cao mà khẩu phần ít",
             "tính tiền không rõ ràng, có phụ thu vô lý"]

POS_SERVICE = ["nhân viên phục vụ nhiệt tình, thân thiện", "phục vụ nhanh nhẹn, chu đáo",
               "chủ quán rất niềm nở, dễ thương", "gọi món là ra liền, không phải chờ"]
NEG_SERVICE = ["nhân viên phục vụ chậm chạp, thái độ khó chịu",
               "phải đợi rất lâu mới có món", "nhân viên không thân thiện, hay quên order"]

POS_AMB = ["không gian quán sạch sẽ, thoáng mát", "quán trang trí đẹp, view đẹp để chụp ảnh",
           "không gian yên tĩnh, phù hợp làm việc", "quán rộng rãi, có chỗ để xe"]
NEG_AMB = ["quán chật chội, ồn ào", "không gian hơi bí, không có máy lạnh",
           "chỗ ngồi ít, phải chờ bàn lâu"]

POS_HYG = ["quán rất sạch sẽ, vệ sinh tốt", "bàn ghế chén đũa sạch sẽ"]
NEG_HYG = ["quán khá bẩn, ruồi bay nhiều", "khu vực bếp không sạch sẽ lắm"]

# --------------------------------------- câu nhận xét VỊ (phần mới quan trọng)
TASTE_SENTENCES = {
    "man": {
        "low": ["vị vừa ăn, không quá mặn", "nêm nếm thanh, hợp người ăn nhạt",
                "không bị mặn như mấy chỗ khác", "vị nhẹ nhàng, dễ ăn"],
        "mid": ["nêm nếm vừa miệng", "vị đậm đà vừa phải, rất hợp gu"],
        "high": ["nêm hơi mặn tay, phải uống nhiều nước",
                 "món hơi mặn so với khẩu vị của mình", "vị đậm quá, ăn nhiều thấy gắt"],
    },
    "cay": {
        "low": ["không cay, trẻ con ăn cũng được", "vị dịu, không cay chút nào"],
        "mid": ["cay nhẹ vừa đủ kích thích", "độ cay vừa phải, dễ chịu"],
        "high": ["cay xé lưỡi luôn, ai không ăn cay nên dặn trước",
                 "cay quá mức, mình phải gọi thêm nước"],
    },
    "ngot": {
        "low": ["ít ngọt, uống không bị gắt", "vị thanh, không ngọt lịm"],
        "mid": ["độ ngọt cân bằng"],
        "high": ["hơi ngọt, nên dặn giảm đường", "ngọt gắt, ăn mau ngán"],
    },
    "beo": {
        "low": ["thanh đạm, ít dầu mỡ nên ăn nhẹ bụng", "không ngấy, ăn hoài không chán"],
        "mid": ["béo vừa phải, vẫn ngon"],
        "high": ["hơi nhiều dầu mỡ, ăn mau ngấy",
                 "béo ngậy quá mức, không hợp người ăn kiêng"],
    },
}

ADJUST_SENTENCES = ["báo trước là quán điều chỉnh vị theo yêu cầu luôn",
                    "mình dặn giảm mặn thì quán làm đúng ý",
                    "có thể yêu cầu nêm nhạt hơn, chủ quán vui vẻ"]


def taste_level(v: float) -> str:
    if v < 0.40:
        return "low"
    if v < 0.62:
        return "mid"
    return "high"


def gen_review(rating: int, taste: dict, adjustable: bool) -> str:
    parts = []
    if rating >= 4:
        parts.append(random.choice(POS_FOOD))
        if random.random() < 0.55:
            parts.append(random.choice(POS_SERVICE))
        if random.random() < 0.40:
            parts.append(random.choice(POS_PRICE))
        if random.random() < 0.30:
            parts.append(random.choice(POS_AMB))
        if random.random() < 0.20:
            parts.append(random.choice(POS_HYG))
    elif rating == 3:
        parts.append(random.choice(POS_FOOD))
        parts.append(random.choice(NEG_PRICE))
        parts.append(random.choice(NEG_SERVICE if random.random() < 0.5 else POS_AMB))
    else:
        parts.append(random.choice(NEG_FOOD))
        if random.random() < 0.6:
            parts.append(random.choice(NEG_SERVICE))
        if random.random() < 0.4:
            parts.append(random.choice(NEG_PRICE))
        if random.random() < 0.3:
            parts.append(random.choice(NEG_HYG))

    # 70% review có nhận xét về VỊ, lấy theo đúng hồ sơ vị của quán
    if random.random() < 0.7:
        dim = random.choices(["man", "cay", "ngot", "beo"], weights=[4, 3, 2, 3])[0]
        parts.append(random.choice(TASTE_SENTENCES[dim][taste_level(taste[dim])]))

    if adjustable and random.random() < 0.15:
        parts.append(random.choice(ADJUST_SENTENCES))

    random.shuffle(parts)
    return ". ".join(p.capitalize() for p in parts) + "."


def main():
    rest_path = os.path.join(BASE, "restaurants.csv")
    if not os.path.exists(rest_path):
        print("Chưa có restaurants.csv, đang sinh trước...")
        import generate_restaurants
        generate_restaurants.main()

    with open(rest_path, encoding="utf-8-sig") as f:
        restaurants = list(csv.DictReader(f))

    rows = []
    rid = 1
    for r in restaurants:
        taste = {d: float(r[f"taste_{d}"]) for d in ("man", "cay", "ngot", "beo")}
        adjustable = bool(r["adjustable"].strip())
        base = float(r["rating"])
        for _ in range(random.randint(*REVIEWS_PER_RESTAURANT)):
            rating = int(round(min(5, max(1, random.gauss(base, 0.85)))))
            rows.append({
                "review_id": f"REV{rid:06d}",
                "restaurant_id": r["restaurant_id"],
                "restaurant_name": r["name"],
                "area": r["district"],
                "cuisine": r["dish_name"],
                "rating": rating,
                "review_text": gen_review(rating, taste, adjustable),
            })
            rid += 1

    out = os.path.join(BASE, "reviews.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"Đã sinh {len(rows):,} review cho {len(restaurants):,} quán -> reviews.csv")


if __name__ == "__main__":
    main()
