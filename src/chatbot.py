# -*- coding: utf-8 -*-
"""
CHATBOT TƯ VẤN ẨM THỰC — lớp điều phối hội thoại.

Luồng xử lý một câu người dùng:

    câu nói tự nhiên
        │
        ▼
    nlu.parse()            -> FoodQuery (món, khẩu vị, giá, vị trí, giờ...)
        │
        ▼
    RestaurantDB.search()  -> danh sách quán đã xếp hạng theo độ phù hợp
        │
        ▼
    respond()              -> {reply, understood, cards, suggestions}
                              (JSON cho giao diện web dựng thẻ quán)

Điểm khác biệt so với bản cũ: chatbot KHÔNG trả về một khối text dài nữa mà
trả về DỮ LIỆU CÓ CẤU TRÚC, nhờ vậy giao diện có thể hiển thị thẻ quán kèm
ảnh, khoảng cách, giá, rating và nút "Xem quán" / "Chỉ đường" trên Google Maps.
"""
import copy
import os
import re
import random
from datetime import datetime

import nlu
from food_catalog import DISH_BY_KEY, DISH_CATALOG, DRINK_CATEGORIES, strip_accents
from geo import maps_directions_url, maps_embed_url, maps_place_url
from restaurant_db import RestaurantDB

try:
    from sentiment_model import SentimentAnalyzer
except Exception:                                    # pragma: no cover
    SentimentAnalyzer = None


GREETINGS = [
    "Chào bạn. Hôm nay bạn muốn ăn gì? Cứ gõ như nhắn tin thôi, kiểu “xôi ít mặn, dưới 30k, gần đây”.",
    "Ừ chào, đang đói hả? Nói món với chỗ bạn ở, mình tìm giúp. Chưa biết ăn gì thì gõ “tư vấn”.",
    "Chào nha. Bạn thèm món gì, tầm giá bao nhiêu, cứ nói luôn cho mình.",
]

HELP_REPLY = (
    "Bạn cứ gõ tự nhiên thôi. Vài kiểu mình hiểu được:\n"
    "• món + khẩu vị: “bún bò thật cay”, “xôi không quá mặn”\n"
    "• giá: “dưới 30k”, “tầm 200k”, “quán bình dân”\n"
    "• chỗ: “gần tôi”, “trong 1km”, “ở Quận 3”\n"
    "• giờ giấc, tiện ích: “đang mở cửa”, “có máy lạnh”, “đi nhóm đông”\n"
    "• hỏi kỹ về một quán: “cho tôi biết về Xôi Cô Tấm”\n"
    "• dán một đoạn review, mình đoán xem người ta khen hay chê\n"
    "Chưa biết ăn gì thì gõ “tư vấn”, mình hỏi vài câu rồi gợi ý."
)

FALLBACK_TIPS = [
    "xôi không quá mặn, dưới 30k, gần tôi",
    "bún bò thật cay ở Quận 1, trên 4 sao",
    "quán lẩu đi nhóm đông, có máy lạnh, tầm 300k",
    "cơm trưa văn phòng bình dân đang mở cửa",
]

# ===================================================================
# TƯ VẤN: khi người dùng chưa nói rõ muốn ăn/uống gì, bot hỏi lại vài câu
# ngắn rồi mới gợi ý, thay vì liệt kê đại một danh sách.
# ===================================================================
CONSULT_INTRO = ("Ok, mình hỏi nhanh vài câu nha. Bạn đang thèm ăn no bụng, "
                 "hay chỉ muốn uống gì đó, ăn vặt tráng miệng?")
CONSULT_TYPE_CHIPS = ["Ăn no bụng", "Uống hoặc tráng miệng", "Gì cũng được"]

CONSULT_TASTE_QUESTION = "Rồi. Khẩu vị thì sao, bạn thích đậm đà hay nhẹ nhàng?"
CONSULT_TASTE_CHIPS = ["Đậm đà, mặn", "Thanh nhạt, ít dầu mỡ", "Cay", "Gì cũng được"]

CONSULT_BUDGET_QUESTION = "Còn tiền nong, bạn tính chi khoảng bao nhiêu một người?"
CONSULT_BUDGET_CHIPS = ["Dưới 30k", "30k – 70k", "70k – 150k", "Không giới hạn"]

# các câu bấm nhanh trong buổi tư vấn (đã bỏ dấu) — để phân biệt với câu hỏi mới
_CONSULT_CHIP_KEYS = {strip_accents(c).lower() for c in
                      CONSULT_TYPE_CHIPS + CONSULT_TASTE_CHIPS + CONSULT_BUDGET_CHIPS}


def _pick(*variants):
    return random.choice(variants)


class FoodChatbot:
    def __init__(self, data_dir: str, model_path: str = None):
        self.db = RestaurantDB(
            os.path.join(data_dir, "restaurants.csv"),
            os.path.join(data_dir, "review_stats.csv"),
        )
        self.sentiment = None
        if model_path and os.path.exists(model_path) and SentimentAnalyzer:
            try:
                self.sentiment = SentimentAnalyzer(model_path)
            except Exception:
                self.sentiment = None
        self.last_query = None
        # trạng thái cuộc hội thoại "tư vấn" đang dở dang (None = không có)
        self.consult = None

    # ----------------------------------------------------------- công khai
    def respond(self, text: str, user_location=None, now: datetime = None) -> dict:
        text = (text or "").strip()
        if not text:
            return self._pack("Bạn muốn ăn gì hôm nay?")

        # Nếu đang giữa buổi tư vấn dở dang -> ưu tiên xử lý câu trả lời này
        # như một bước tư vấn, thay vì phân tích lại từ đầu.
        if self.consult is not None:
            result = self._consult_step(text, user_location=user_location, now=now)
            if result is not None:
                return result
            self.consult = None   # người dùng gõ hẳn câu khác -> huỷ tư vấn dở

        q = nlu.parse(text, user_location=user_location)

        if q.intent == "SEARCH" and self._is_vague(q):
            return self._start_consult()

        if q.intent == "GREETING":
            return self._pack(_pick(*GREETINGS), suggestions=FALLBACK_TIPS)
        if q.intent == "HELP":
            return self._pack(HELP_REPLY, suggestions=FALLBACK_TIPS)
        if q.intent == "THANKS":
            return self._pack(_pick("Không có gì, ăn ngon nha.",
                                    "Ok bạn, ăn ngon miệng. Cần tìm chỗ khác cứ nhắn.",
                                    "Có gì đâu. Ăn xong nhớ chấm điểm quán nha."))
        if q.intent == "DETAIL":
            card = self._detail(text)
            if card:
                return self._pack(f"Quán **{card['name']}** đây:",
                                  cards=[card], query=q,
                                  suggestions=["Tìm quán tương tự gần đây",
                                               "Quán nào rẻ hơn?"])

        if q.intent == "FALLBACK":
            # có thể người dùng dán 1 câu đánh giá -> chạy mô hình cảm xúc
            if self.sentiment and len(text.split()) >= 5:
                r = self.sentiment.predict(text)
                label = r["label"].replace("_", " ")
                return self._pack(
                    f"Câu này nghe giống một đoạn review hơn là tìm quán. "
                    f"Mình đoán người viết đang **{label}**.\n\n"
                    f"Còn nếu bạn muốn tìm quán thì thử gõ kiểu này:",
                    suggestions=FALLBACK_TIPS)
            return self._pack(
                _pick("Mình chưa bắt được ý bạn. Thử nói cụ thể hơn, ví dụ:",
                      "Hơi khó hiểu à. Bạn thử nêu món hoặc khu vực xem, kiểu như:"),
                suggestions=FALLBACK_TIPS)

        # ---------------- SEARCH ----------------
        # Kế thừa ngữ cảnh câu trước (vd: "rẻ hơn nữa" / "gần hơn")
        q = self._inherit_context(q, text)

        # Câu nói nhắc tới CẢ món ăn lẫn đồ uống (vd "cơm gà và trà sữa gần
        # đây") -> tách thành 2 khối gợi ý riêng thay vì gộp chung 1 danh sách.
        if q.mixed:
            return self._respond_mixed(q, user_location=user_location, now=now)

        cards, relaxed = self.db.search(q, user_location=user_location, now=now)
        self.last_query = q

        if not cards:
            return self._pack(
                "Tìm hoài mà không có quán nào khớp hết mấy điều kiện đó. "
                "Bạn nới bớt một cái thử, như tăng ngân sách, mở rộng khu vực "
                "hoặc bỏ yêu cầu khẩu vị.",
                query=q, suggestions=["Mở rộng khu vực", "Tăng ngân sách",
                                      "Bỏ yêu cầu khẩu vị"])

        dish_label = (DISH_BY_KEY[q.dishes[0]]["name"] if q.dishes
                      else (q.categories[0] if q.categories else None))
        n = len(cards)
        what = dish_label.lower() if dish_label else (
            "chỗ uống / tráng miệng" if q.want_drink else "quán ăn")
        if n == 1:
            header = f"Chỉ có 1 quán {what} khớp với bạn:" if dish_label else f"Mình thấy 1 chỗ hợp nhất:"
        else:
            header = _pick(f"Có {n} quán {what} khá hợp nè:",
                           f"Mình chọn được {n} quán {what} cho bạn:",
                           f"{n} quán {what} này ổn đó:")
        if q.near_me and n > 1:
            header = header[:-1] + ", xếp theo độ hợp và độ gần:"

        notes = []
        for r in relaxed:
            notes.append("Mình " + r if r.startswith("mở rộng") else r[0].upper() + r[1:])

        return self._pack(header, cards=cards, query=q, notes=notes,
                          suggestions=self._suggest_followups(q))

    def respond_text(self, text: str, user_location=None) -> str:
        """Phiên bản trả về text thuần — dùng cho CLI."""
        res = self.respond(text, user_location=user_location)
        out = [res["reply"]]
        if res["understood"]:
            out.append("\n[Bot hiểu] " + " · ".join(res["understood"]))

        groups = res.get("groups") or ([{"label": None, "cards": res["cards"]}]
                                       if res["cards"] else [])
        for g in groups:
            if g["label"]:
                out.append(f"\n== {g['label']} ==")
            for i, c in enumerate(g["cards"], 1):
                out.append(self._format_card_text(c, i))

        for n in res["notes"]:
            out.append("\n" + n)
        if res["suggestions"]:
            out.append("\n[Gợi ý] " + " | ".join(res["suggestions"]))
        return "\n".join(out)

    def _format_card_text(self, c, i):
        line = (f"\n{i}. {c['name']} ⭐ {c['rating']} ({c['num_reviews']} đánh giá) "
                f"— phù hợp {c['match_score']}%")
        if c["distance_text"]:
            line += f"\n   📍 Cách bạn {c['distance_text']} (~{c['eta_min']} phút) — {c['address']}"
        else:
            line += f"\n   📍 {c['address']}"
        line += f"\n   💰 {c['price_text']}   🕐 {c['open_time']}–{c['close_time']}"
        line += f"   {'🟢 Đang mở' if c['is_open'] else '🔴 Đã đóng'}"
        line += f"\n   🧂 {' · '.join(c['taste_tags'][:2])}"
        if c["reasons"]:
            line += f"\n   ✅ {' · '.join(c['reasons'])}"
        if c["warnings"]:
            line += f"\n   ⚠️ {c['warnings'][0]}"
        line += f"\n   🗺️ {c['maps_url']}"
        return line

    # ------------------------------------------------------------- nội bộ
    def _pack(self, reply, cards=None, query=None, notes=None, suggestions=None,
              groups=None):
        out = {
            "reply": reply,
            "understood": query.explain() if query else [],
            "intent": query.intent if query else "CHAT",
            "cards": cards or [],
            "notes": notes or [],
            "suggestions": suggestions or [],
        }
        # `groups`: dùng khi cần hiển thị nhiều khối thẻ quán tách riêng, vd
        # "🍜 Món ăn" và "🥤 Đồ uống" — chỉ có mặt khi thật sự cần tách.
        if groups:
            out["groups"] = groups
        return out

    # -------------------------------------------------------------- tư vấn
    def _is_vague(self, q) -> bool:
        """Câu nói quá chung chung (không nêu món/khẩu vị/giá/khu vực gì cả)
        -> nên hỏi lại (tư vấn) thay vì liệt kê đại một danh sách ngẫu nhiên."""
        return not (q.dishes or q.categories or q.taste or q.price_min
                    or q.price_max or q.district or q.city or q.veg_only
                    or q.utilities or q.min_rating)

    def _start_consult(self):
        self.consult = {"stage": "type", "want_drink": None, "taste": None,
                        "price_min": None, "price_max": None}
        return self._pack(CONSULT_INTRO, suggestions=CONSULT_TYPE_CHIPS)

    def _consult_step(self, text, user_location=None, now=None):
        """Xử lý 1 bước trả lời trong buổi tư vấn. Trả về None nếu câu trả
        lời không khớp bước hiện tại (khi đó respond() sẽ huỷ tư vấn và xử
        lý câu nói như bình thường)."""
        t = strip_accents(text).lower()
        st = self.consult
        stage = st["stage"]

        # Người dùng gõ hẳn một yêu cầu mới (có món / khu vực cụ thể) chứ không
        # bấm các lựa chọn của buổi tư vấn -> bỏ tư vấn, xử lý như câu bình thường.
        if t.strip() not in _CONSULT_CHIP_KEYS:
            probe = nlu.parse(text)
            if probe.dishes or probe.categories or probe.district or probe.city:
                return None

        if stage == "type":
            if any(w in t for w in ["do uong", "thuc uong", "trang mieng",
                                    "nuoc", "giai khat", "uong"]):
                st["want_drink"] = True
            elif any(w in t for w in ["ca hai", "sao cung", "gi cung"]):
                st["want_drink"] = None
            elif any(re.search(rf"\b{w}\b", t) for w in
                     ["an no", "mon an", "no bung", "com", "bun", "pho", "an"]):
                st["want_drink"] = False
            else:
                return self._pack("Bạn chọn giúp mình một cái nha:",
                                  suggestions=CONSULT_TYPE_CHIPS)
            st["stage"] = "taste"
            return self._pack(CONSULT_TASTE_QUESTION, suggestions=CONSULT_TASTE_CHIPS)

        if stage == "taste":
            if any(w in t for w in ["dam da", "man", "dam vi"]):
                st["taste"] = {"man": "high"}
            elif any(w in t for w in ["thanh", "it dau", "nhat", "lat"]):
                st["taste"] = {"man": "low", "beo": "low"}
            elif "cay" in t:
                st["taste"] = {"cay": "high"}
            # "khẩu vị nào cũng được" -> không ràng buộc gì thêm
            st["stage"] = "budget"
            return self._pack(CONSULT_BUDGET_QUESTION, suggestions=CONSULT_BUDGET_CHIPS)

        if stage == "budget":
            if "khong gioi han" in t:
                pass
            elif "30" in t and "70" in t:
                st["price_min"], st["price_max"] = 30000, 70000
            elif "70" in t and "150" in t:
                st["price_min"], st["price_max"] = 70000, 150000
            elif "30" in t:
                st["price_max"] = 30000

            q = nlu.FoodQuery(raw=text, intent="SEARCH")
            q.want_drink = bool(st["want_drink"])
            if st["taste"]:
                q.taste = st["taste"]
            q.price_min, q.price_max = st["price_min"], st["price_max"]
            if user_location:
                q.near_me = True
                q.radius_km = 4.0

            self.consult = None
            self.last_query = q

            # "cả hai đều được" -> tư vấn cả món ăn lẫn đồ uống, tách 2 khối
            if st["want_drink"] is None:
                return self._respond_mixed_free(q, user_location=user_location,
                                                 now=now)

            cards, relaxed = self.db.search(q, user_location=user_location, now=now)
            if not cards:
                return self._pack(
                    "Mấy điều kiện này chưa ra được quán nào. Bạn nói thẳng tên món "
                    "hoặc khu vực xem, mình tìm lại.",
                    suggestions=FALLBACK_TIPS)
            header = ("Vậy thì thử mấy chỗ này, "
                      f"{'uống' if q.want_drink else 'ăn'} hợp nhất với bạn:")
            notes = [r[0].upper() + r[1:] for r in relaxed]
            return self._pack(header, cards=cards, query=q, notes=notes,
                              suggestions=self._suggest_followups(q))

        return None

    def _respond_mixed(self, q, user_location=None, now=None):
        """Câu nói nêu rõ cả món ăn lẫn đồ uống (vd "cơm gà và trà sữa") ->
        tìm riêng từng nhóm rồi trả về 2 khối thẻ quán tách biệt."""
        food_keys = [d for d in q.dishes
                    if DISH_BY_KEY[d]["category"] not in DRINK_CATEGORIES]
        drink_keys = [d for d in q.dishes
                     if DISH_BY_KEY[d]["category"] in DRINK_CATEGORIES]

        q_food = copy.deepcopy(q); q_food.dishes = food_keys; q_food.categories = []
        q_drink = copy.deepcopy(q); q_drink.dishes = drink_keys; q_drink.categories = []

        self.last_query = q
        return self._search_two_groups(q_food, q_drink, user_location, now,
                                        "Mình tách hai phần cho dễ chọn, đồ ăn một bên, đồ uống một bên:", query=q)

    def _respond_mixed_free(self, q, user_location=None, now=None):
        """Dùng khi tư vấn và người dùng chọn 'cả hai đều được' — không có
        dish cụ thể nên tách theo want_drink True/False."""
        q_food = copy.deepcopy(q); q_food.want_drink = False
        q_drink = copy.deepcopy(q); q_drink.want_drink = True
        return self._search_two_groups(
            q_food, q_drink, user_location, now,
            "Gì cũng được thì mình đưa cả hai, đồ ăn và đồ uống tách riêng:",
            query=q)

    def _search_two_groups(self, q_food, q_drink, user_location, now, header,
                           query=None):
        food_cards, relaxed_f = self.db.search(q_food, user_location=user_location,
                                                now=now)
        drink_cards, relaxed_d = self.db.search(q_drink, user_location=user_location,
                                                 now=now)
        groups = []
        if food_cards:
            groups.append({"label": "Món ăn", "cards": food_cards})
        if drink_cards:
            groups.append({"label": "Đồ uống, tráng miệng", "cards": drink_cards})

        if not groups:
            return self._pack(
                "Chưa có quán nào khớp hết. Bạn thử tăng ngân sách hoặc mở rộng khu vực.",
                suggestions=["Mở rộng khu vực", "Tăng ngân sách"])

        notes = [r[0].upper() + r[1:] for r in (relaxed_f + relaxed_d)]
        all_cards = food_cards + drink_cards
        suggestions = self._suggest_followups(q_food if food_cards else q_drink)
        return self._pack(header, cards=all_cards, query=query, notes=notes,
                          groups=groups, suggestions=suggestions)

    def _inherit_context(self, q, text):
        """Cho phép nói tiếp kiểu 'rẻ hơn nữa', 'gần hơn', 'quán khác'."""
        prev = self.last_query
        if not prev:
            return q
        t = nlu.strip_accents(text) if hasattr(nlu, "strip_accents") else text.lower()
        from food_catalog import strip_accents
        t = strip_accents(text)
        follow = any(w in t for w in ["re hon", "gan hon", "quan khac", "cai khac",
                                      "con gi nua", "khac di", "ngon hon", "rong hon"])
        if not follow:
            return q
        if not q.dishes:
            q.dishes = prev.dishes
            q.categories = prev.categories
            q.want_drink = prev.want_drink
            q.mixed = prev.mixed
        if not q.taste:
            q.taste = prev.taste
        if "re hon" in t:
            base = prev.price_max or 100000
            q.price_max = int(base * 0.7)
        if "gan hon" in t:
            q.near_me = True
            q.radius_km = max(0.6, (prev.radius_km or 3.0) * 0.5)
        if "rong hon" in t:
            q.radius_km = (prev.radius_km or 3.0) * 2
            q.near_me = True
        if not q.district:
            q.district = prev.district
        return q

    def _detail(self, text):
        for prefix in ["cho tôi biết về", "thông tin về", "chi tiết về",
                       "review về", "đánh giá về", "nói về quán"]:
            idx = text.lower().find(prefix)
            if idx >= 0:
                text = text[idx + len(prefix):]
                break
        row = self.db.find_by_name(text.strip(" ?.!,"))
        if row is None:
            return None
        return self.db.to_card(row, None, 1.0, [], [], None,
                               datetime.now().hour * 60 + datetime.now().minute)

    def _suggest_followups(self, q):
        out = []
        if q.price_max:
            out.append("Có quán nào rẻ hơn không?")
        else:
            out.append("Lọc giúp mình dưới 50k")
        if q.near_me:
            out.append("Tìm quán gần hơn nữa")
        else:
            out.append("Quán nào gần tôi nhất?")
        if not q.open_now:
            out.append("Chỉ hiện quán đang mở cửa")
        # Gợi ý "đổi món khác" CÙNG NHÓM (đồ ăn <-> đồ ăn, đồ uống <-> đồ
        # uống) — không đề nghị trà sữa khi đang tìm cơm, và ngược lại.
        want_drink = bool(getattr(q, "want_drink", False)) or any(
            DISH_BY_KEY[d]["category"] in DRINK_CATEGORIES for d in q.dishes)
        pool = [d for d in DISH_CATALOG
                if d["key"] not in q.dishes
                and (d["category"] in DRINK_CATEGORIES) == want_drink]
        if pool:
            other = random.choice(pool)
            out.append(f"Đổi sang {other['name'].lower()} thì sao?")
        return out[:4]


# ------------------------------------------------------------------- CLI
def run_cli():
    base = os.path.dirname(os.path.abspath(__file__))
    bot = FoodChatbot(os.path.join(base, "..", "data"),
                      os.path.join(base, "..", "models", "sentiment_model.joblib"))
    print("=== Chatbot Tư Vấn Ẩm Thực === (gõ 'exit' để thoát)")
    print(f"[Đã nạp {len(bot.db):,} quán ăn]\n")
    print(GREETING_REPLY)
    while True:
        try:
            msg = input("\nBạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg.lower() in ("exit", "quit", "thoát"):
            print("Bot: Hẹn gặp lại nha.")
            break
        if msg:
            print("\nBot:", bot.respond_text(msg))


if __name__ == "__main__":
    run_cli()
