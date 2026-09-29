# -*- coding: utf-8 -*-
"""
CƠ SỞ DỮ LIỆU QUÁN ĂN + BỘ MÁY TÌM KIẾM ĐA TIÊU CHÍ
====================================================

Nhận một FoodQuery (kết quả NLU) và trả về danh sách quán được XẾP HẠNG theo
ĐỘ PHÙ HỢP tổng hợp, chứ không phải chỉ lọc từ khóa.

Điểm phù hợp = trung bình có trọng số của các thành phần:

    | Thành phần    | Trọng số | Ý nghĩa                                       |
    |---------------|----------|-----------------------------------------------|
    | Khẩu vị       |   0.30   | khoảng cách giữa vị mong muốn và vị thực tế   |
    | Khoảng cách   |   0.24   | càng gần càng cao (hàm suy giảm theo km)      |
    | Đánh giá      |   0.22   | rating + độ tin cậy (số lượt đánh giá)        |
    | Giá           |   0.16   | mức khớp với ngân sách người dùng             |
    | Tiện ích      |   0.08   | máy lạnh / chỗ đậu xe / đi nhóm...            |

Chỉ những thành phần mà NGƯỜI DÙNG CÓ NÊU mới được tính (trọng số được chuẩn
hóa lại), nên câu hỏi càng cụ thể thì xếp hạng càng sát ý.
"""
import math
import os
from datetime import datetime

import pandas as pd

from food_catalog import DRINK_CATEGORIES
from geo import (DEFAULT_USER_LOCATION, format_distance, estimate_minutes,
                 maps_directions_url, maps_embed_url, maps_place_url,
                 travel_distance_km)

# DẢI VỊ CHẤP NHẬN ĐƯỢC ứng với mong muốn của người dùng.
#   ideal = vẫn được coi là "đúng ý" (điểm tuyệt đối)
#   zero  = lệch tới mức này thì coi như hoàn toàn trái ý (điểm 0)
# Các mốc này khớp với nhãn chữ hiển thị cho người dùng, ví dụ với độ mặn:
#   <0.32 "thanh/nhạt" | <0.50 "vừa, không quá mặn" | <0.68 "đậm đà" | else "rất mặn"
TASTE_BANDS = {
    "low": dict(ideal=0.42, zero=0.80),
    "high": dict(ideal=0.70, zero=0.30),
    "mid": dict(center=0.50, flat=0.12, zero=0.35),
}
TASTE_VN = {"man": "mặn", "cay": "cay", "ngot": "ngọt", "beo": "béo/dầu mỡ"}


def _taste_band_score(direction: str, actual: float) -> float:
    """Điểm khớp khẩu vị theo dải chấp nhận (0..1)."""
    if direction == "low":
        b = TASTE_BANDS["low"]
        if actual <= b["ideal"]:
            return 1.0
        return max(0.0, 1.0 - (actual - b["ideal"]) / (b["zero"] - b["ideal"]))
    if direction == "high":
        b = TASTE_BANDS["high"]
        if actual >= b["ideal"]:
            return 1.0
        return max(0.0, 1.0 - (b["ideal"] - actual) / (b["ideal"] - b["zero"]))
    b = TASTE_BANDS["mid"]
    d = abs(actual - b["center"])
    if d <= b["flat"]:
        return 1.0
    return max(0.0, 1.0 - (d - b["flat"]) / (b["zero"] - b["flat"]))


WEIGHTS = {"taste": 0.30, "distance": 0.24, "rating": 0.22,
           "price": 0.16, "utility": 0.08}

# Khi người dùng nêu rõ khẩu vị, tiêu chí này được nâng lên thành nặng nhất
TASTE_WEIGHT_EXPLICIT = 0.45


def _to_minutes(hhmm: str) -> int:
    h, m = str(hhmm).split(":")
    return int(h) * 60 + int(m)


class RestaurantDB:
    def __init__(self, restaurants_csv: str, stats_csv: str = None):
        self.df = pd.read_csv(restaurants_csv, encoding="utf-8-sig")
        self.df["adjustable"] = self.df["adjustable"].fillna("")
        self.df["utilities"] = self.df["utilities"].fillna("")
        for col, default in (("city", "TP.HCM"), ("photo_url", ""),
                             ("data_source", "simulated")):
            if col not in self.df.columns:
                self.df[col] = default
            self.df[col] = self.df[col].fillna(default)

        # gộp thêm thống kê rút ra từ phân tích NLP các review (nếu có)
        if stats_csv and os.path.exists(stats_csv):
            stats = pd.read_csv(stats_csv, encoding="utf-8-sig")
            self.df = self.df.merge(stats, on="restaurant_id", how="left")
        for col in ("positive_ratio", "quote_pos", "quote_neg"):
            if col not in self.df.columns:
                self.df[col] = None
        self.df["positive_ratio"] = self.df["positive_ratio"].fillna(0.0)

        self._open_min = self.df["open_time"].map(_to_minutes)
        self._close_min = self.df["close_time"].map(_to_minutes)

    # ------------------------------------------------------------ tiện ích
    def __len__(self):
        return len(self.df)

    def is_open_at(self, row, minutes: int) -> bool:
        o, c = _to_minutes(row["open_time"]), _to_minutes(row["close_time"])
        if c <= o:                       # quán mở xuyên đêm (vd 16:00 -> 00:30)
            return minutes >= o or minutes <= c
        return o <= minutes <= c

    # -------------------------------------------------------- chấm điểm con
    @staticmethod
    def _score_taste(row, taste_req: dict):
        """
        Chấm mức khớp khẩu vị.

        Khi người dùng NÓI RÕ khẩu vị ("không quá mặn"), đây là ràng buộc chính
        chứ không phải điểm cộng: quán đi ngược yêu cầu bị phạt mạnh, trừ khi
        quán có nhận điều chỉnh vị theo yêu cầu khách.
        """
        if not taste_req:
            return None, [], []
        scores, reasons, warns = [], [], []
        for dim, direction in taste_req.items():
            actual = float(row[f"taste_{dim}"])
            s = _taste_band_score(direction, actual)

            adjust_kw = {"man": "giảm mặn", "cay": "giảm cay",
                         "ngot": "giảm ngọt", "beo": "ít dầu mỡ"}[dim]
            can_adjust = adjust_kw in str(row["adjustable"])
            if direction == "low" and can_adjust:
                s = min(1.0, s + 0.12)   # quán chịu nêm nhạt lại theo yêu cầu

            if s >= 0.85:
                # nếu quán vốn hơi đậm nhưng nhận nêm lại theo yêu cầu thì nói rõ
                if direction == "low" and can_adjust and actual > 0.48:
                    reasons.append(f"Có thể yêu cầu {adjust_kw}")
                else:
                    reasons.append(_taste_reason(dim, direction, actual))
            elif s < 0.45:
                if can_adjust and direction == "low":
                    warns.append(f"Vị {TASTE_VN[dim]} khá đậm, nhưng quán nhận "
                                 f"yêu cầu {adjust_kw}")
                else:
                    warns.append(f"Lưu ý: quán này vị {TASTE_VN[dim]} "
                                 f"{'khá đậm' if direction == 'low' else 'khá nhẹ'}")
            scores.append(s)
        return sum(scores) / len(scores), reasons, warns

    @staticmethod
    def _score_price(row, q):
        if not (q.price_min or q.price_max):
            return None
        lo, hi = float(row["price_min"]), float(row["price_max"])
        want_lo = q.price_min or 0
        want_hi = q.price_max or 10 ** 9
        overlap = min(hi, want_hi) - max(lo, want_lo)
        if overlap <= 0:
            # lệch hoàn toàn -> điểm giảm theo mức lệch
            gap = (lo - want_hi) if lo > want_hi else (want_lo - hi)
            return max(0.0, 1.0 - gap / max(want_hi, 30000))
        span = max(hi - lo, 1)
        base = 0.55 + 0.45 * min(1.0, overlap / span)
        if q.price_max and hi <= q.price_max:
            base = min(1.0, base + 0.12)     # cả menu đều nằm trong ngân sách
        return base

    @staticmethod
    def _score_rating(row):
        rating = float(row["rating"])
        n = float(row["num_reviews"])
        confidence = min(1.0, math.log10(n + 1) / 2.6)   # ít review -> kém tin cậy
        base = (rating - 2.5) / 2.5
        return max(0.0, min(1.0, base * (0.65 + 0.35 * confidence)))

    @staticmethod
    def _score_distance(km, radius):
        if km is None:
            return None
        scale = radius if radius else 3.0
        return max(0.0, math.exp(-km / max(scale, 0.6)))

    # ---------------------------------------------------------------- tìm
    def search(self, q, user_location=None, now: datetime = None):
        now = now or datetime.now()
        minutes = (q.at_hour * 60) if q.at_hour is not None else (now.hour * 60 + now.minute)
        loc = user_location or (DEFAULT_USER_LOCATION if (q.near_me or q.radius_km) else None)

        df = self.df
        relaxed = []          # ghi lại các ràng buộc phải nới lỏng để báo người dùng

        # ---- lọc cứng: thành phố ----
        city = getattr(q, "city", None)
        if not city and q.district:
            from geo import CITY_OF
            city = CITY_OF.get(q.district)
        if not city and loc is not None:
            # suy ra vùng từ vị trí GPS: chọn vùng có tâm gần người dùng nhất
            from geo import CITIES, haversine_km
            city = min(CITIES, key=lambda c: haversine_km(
                loc[0], loc[1], *CITIES[c]["center"]))
        if city:
            sub = df[df["city"] == city]
            if len(sub):
                df = sub

        # ---- lọc cứng: món ăn ----
        if q.dishes:
            sub = df[df["dish_key"].isin(q.dishes)]
            if len(sub) == 0 and q.categories:
                sub = df[df["category"].isin(q.categories)]
            df = sub if len(sub) else df
        elif q.categories:
            df = df[df["category"].isin(q.categories)]
        else:
            # Không nêu món/nhóm món cụ thể -> KHÔNG trộn đồ ăn no bụng chung
            # với đồ uống/tráng miệng trong cùng một danh sách gợi ý. Mặc định
            # gợi ý đồ ăn; chỉ gợi ý đồ uống/tráng miệng khi người dùng thể
            # hiện rõ ý muốn uống (q.want_drink).
            wanted = df["category"].isin(DRINK_CATEGORIES) if q.want_drink \
                else ~df["category"].isin(DRINK_CATEGORIES)
            sub = df[wanted]
            if len(sub) >= 3:
                df = sub

        if q.veg_only:
            veg = df[(df["is_veg"] == 1) | (df["category"] == "Chay – Healthy")]
            if len(veg) >= 3:
                df = veg

        # ---- lọc cứng: khu vực ----
        if q.district:
            sub = df[df["district"] == q.district]
            if len(sub) >= 1:
                df = sub
            else:
                relaxed.append(f"không có quán phù hợp ngay tại {q.district}")

        if len(df) == 0:
            return [], relaxed

        # ---- khoảng cách ----
        dists = None
        if loc is not None:
            dists = df.apply(lambda r: travel_distance_km(loc[0], loc[1],
                                                          r["lat"], r["lng"]), axis=1)
            if q.radius_km:
                # cần đủ ứng viên thì việc xếp hạng theo khẩu vị/giá mới có ý nghĩa
                need = max(4, q.limit)
                inside = df[dists <= q.radius_km]
                if len(inside) >= need:
                    df, dists = inside, dists[dists <= q.radius_km]
                else:
                    limit_km = min(max(q.radius_km * 3, 3.0), 12.0)
                    wider = q.radius_km
                    while wider < limit_km and len(df[dists <= wider]) < need:
                        wider = min(wider * 1.6, limit_km)
                    wider = round(wider, 1)
                    inside = df[dists <= wider]
                    if len(inside) >= 1:
                        relaxed.append(f"mở rộng bán kính lên ~{wider:g}km vì gần bạn "
                                       f"có quá ít quán phù hợp")
                        df, dists = inside, dists[dists <= wider]

        # ---- giờ mở cửa ----
        if q.open_now or q.at_hour is not None:
            mask = df.apply(lambda r: self.is_open_at(r, minutes), axis=1)
            if mask.sum() >= max(3, q.limit):
                df = df[mask]
                if dists is not None:
                    dists = dists[mask]
            else:
                relaxed.append("ít quán đang mở vào giờ này nên mình liệt kê cả "
                               "quán sắp mở")

        if len(df) == 0:
            return [], relaxed

        # ---- chấm điểm ----
        results = []
        for i, (_, row) in enumerate(df.iterrows()):
            km = float(dists.iloc[i]) if dists is not None else None

            parts, weights, reasons, warns = [], [], [], []

            s, r_, w_ = self._score_taste(row, q.taste)
            if s is not None:
                parts.append(s); weights.append(TASTE_WEIGHT_EXPLICIT)
                reasons += r_; warns += w_

            s = self._score_distance(km, q.radius_km)
            if s is not None:
                parts.append(s); weights.append(WEIGHTS["distance"])

            s = self._score_rating(row)
            parts.append(s); weights.append(WEIGHTS["rating"])

            s = self._score_price(row, q)
            if s is not None:
                parts.append(s); weights.append(WEIGHTS["price"])
                if q.price_max and row["price_min"] <= q.price_max:
                    reasons.append(f"Giá từ {int(row['price_min'])//1000}k, "
                                   f"nằm trong ngân sách")

            if q.utilities:
                have = [u for u in q.utilities if u in str(row["utilities"])]
                parts.append(len(have) / len(q.utilities))
                weights.append(WEIGHTS["utility"])
                if have:
                    reasons.append(" · ".join(have))

            score = sum(p * w for p, w in zip(parts, weights)) / sum(weights)

            # điều kiện không thoả -> hạ điểm rõ rệt
            if q.min_rating and row["rating"] < q.min_rating:
                score *= 0.55
            if q.price_max and row["price_min"] > q.price_max * 1.15:
                score *= 0.6
                warns.append(f"Giá khởi điểm {int(row['price_min'])//1000}k, "
                             f"cao hơn ngân sách bạn nêu")

            results.append((score, row, km, reasons, warns))

        results.sort(key=lambda x: -x[0])
        top = results[:q.limit]
        cards = [self.to_card(r, km, score, reasons, warns, loc, minutes)
                 for score, r, km, reasons, warns in top]
        return cards, relaxed

    # ------------------------------------------------------- xuất thẻ (card)
    def to_card(self, row, km, score, reasons, warns, user_loc, minutes):
        lat, lng = float(row["lat"]), float(row["lng"])
        is_open = self.is_open_at(row, minutes)
        card = {
            "id": row["restaurant_id"],
            "name": row["name"],
            "city": row.get("city", "TP.HCM"),
            "data_source": row.get("data_source", "simulated"),
            "dish": row["dish_name"],
            "dish_key": row["dish_key"],
            "category": row["category"],
            "address": row["address"],
            "district": row["district"],
            "lat": lat, "lng": lng,
            "rating": float(row["rating"]),
            "num_reviews": int(row["num_reviews"]),
            "positive_ratio": float(row.get("positive_ratio") or 0),
            "price_min": int(row["price_min"]),
            "price_max": int(row["price_max"]),
            "price_text": f"{int(row['price_min'])//1000}k – {int(row['price_max'])//1000}k",
            "taste_tags": [t.strip() for t in str(row["taste_tags"]).split("|")],
            "taste": {d: float(row[f"taste_{d}"]) for d in ("man", "cay", "ngot", "beo")},
            "adjustable": row["adjustable"],
            "menu": [m.strip() for m in str(row["menu"]).split("|")],
            "utilities": [u.strip() for u in str(row["utilities"]).split(",") if u.strip()],
            "open_time": row["open_time"], "close_time": row["close_time"],
            "is_open": bool(is_open),
            "phone": row["phone"],
            "image_url": row["image_url"],
            "photo_url": row.get("photo_url") or "",
            "emoji": row["emoji"],
            "distance_km": round(km, 2) if km is not None else None,
            "distance_text": format_distance(km) if km is not None else None,
            "eta_min": estimate_minutes(km) if km is not None else None,
            "match_score": round(score * 100),
            "reasons": reasons[:3],
            "warnings": warns[:2],
            "quote": row.get("quote_pos") if isinstance(row.get("quote_pos"), str) else None,
            "maps_url": maps_place_url(row["name"], row["address"], lat, lng),
            "directions_url": maps_directions_url(
                lat, lng, row["name"],
                user_loc[0] if user_loc else None,
                user_loc[1] if user_loc else None),
            "embed_url": maps_embed_url(lat, lng),
        }
        card["warnings"] = warns[:2]
        card["why"] = _build_why(card, reasons)
        return card

    def get(self, restaurant_id: str):
        sub = self.df[self.df["restaurant_id"] == restaurant_id]
        return sub.iloc[0] if len(sub) else None

    def find_by_name(self, name_query: str):
        from food_catalog import strip_accents
        nq = strip_accents(name_query)
        if len(nq) < 3:
            return None
        mask = self.df["name"].map(lambda n: nq in strip_accents(n))
        sub = self.df[mask]
        return sub.iloc[0] if len(sub) else None


def _build_why(card, reasons):
    """
    Một câu giải thích NGẮN GỌN vì sao quán này được gợi ý — để người dùng hiểu
    logic xếp hạng thay vì phải tin vào một con số phần trăm.
    """
    parts = [f"đúng món {card['dish'].lower()}"]
    for r in reasons:
        parts.append(r[0].lower() + r[1:])
    if card.get("distance_text"):
        parts.append(f"cách bạn {card['distance_text']}")
    if card["rating"] >= 4.3:
        parts.append(f"{card['rating']} sao từ {card['num_reviews']} đánh giá")
    if card.get("warnings"):
        return "Mình chọn vì " + ", ".join(parts[:4]) + ". " + card["warnings"][0] + "."
    return "Mình chọn vì " + ", ".join(parts[:4]) + "."


def _taste_reason(dim, direction, actual):
    if dim == "man":
        return {"low": "Vị vừa, không quá mặn", "mid": "Nêm nếm vừa miệng",
                "high": "Vị đậm đà đúng gu"}[direction]
    if dim == "cay":
        return {"low": "Không cay / cay rất nhẹ", "mid": "Cay vừa phải",
                "high": "Cay đã miệng"}[direction]
    if dim == "ngot":
        return {"low": "Ít ngọt, không gắt", "mid": "Ngọt cân bằng",
                "high": "Ngọt đậm"}[direction]
    return {"low": "Thanh đạm, ít dầu mỡ", "mid": "Béo vừa phải",
            "high": "Béo ngậy đậm đà"}[direction]
