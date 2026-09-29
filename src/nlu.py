# -*- coding: utf-8 -*-
"""
NLU — HIỂU YÊU CẦU ĂN UỐNG TỰ NHIÊN
====================================

Đây là nâng cấp cốt lõi so với bản cũ (chỉ match từ khóa). Module này biến
một câu nói tự nhiên thành một BẢN YÊU CẦU CÓ CẤU TRÚC (structured query).

Ví dụ:
    "Tôi muốn ăn xôi, nhưng không thích quá mặn, tìm quán gần đây, dưới 30k"
    ->  FoodQuery(
            dishes      = ["xoi"],
            taste       = {"man": "low"},          # <- hiểu được PHỦ ĐỊNH
            price_max   = 30000,
            near_me     = True, radius_km = 3.0,
        )

Kỹ thuật sử dụng:
  1. Chuẩn hoá + bỏ dấu  -> người dùng gõ "xoi khong qua man" vẫn hiểu.
  2. Slot filling bằng từ điển + luật (rule-based slot filling).
  3. XỬ LÝ PHỦ ĐỊNH & LƯỢNG HOÁ (negation / intensity scope): với mỗi từ chỉ
     vị (mặn, cay, ngọt, béo) ta soi cửa sổ ngữ cảnh ~30 ký tự phía trước và
     sau nó để tìm các dấu hiệu "không / đừng / ít / giảm / bớt / kiêng / sợ"
     (giảm) hay "nhiều / thật / cực / siêu" (tăng), từ đó suy ra người dùng
     MUỐN vị đó THẤP, VỪA hay CAO. Đây chính là điểm mà tìm kiếm từ khóa
     thất bại: "không quá mặn" nếu chỉ match từ khóa sẽ ra toàn quán mặn.
  4. Chuẩn hoá đơn vị tiền Việt: "30k", "30 nghìn", "30.000đ" -> 30000.

Hướng nâng cấp thực tế: thay lớp luật này bằng mô hình Joint Intent
Classification + Slot Filling (fine-tune PhoBERT theo kiểu JointBERT), hoặc
gọi LLM với output JSON schema. Cấu trúc FoodQuery bên dưới giữ nguyên nên
phần còn lại của hệ thống không phải sửa.
"""
import re
from dataclasses import dataclass, field

from food_catalog import find_dishes, strip_accents, DISH_BY_KEY, DRINK_CATEGORIES
from geo import find_city, find_district

# ------------------------------------------------------------------ 1. Vị
# Từ khoá chỉ từng chiều vị. "high" = từ mô tả vị ở mức cao,
# "low" = từ vốn đã mang nghĩa mức thấp (nhạt, thanh đạm...)
TASTE_TERMS = {
    "man": {"high": ["mặn", "đậm đà", "đậm vị", "mặn mà", "nước mắm", "muối"],
            "low": ["nhạt", "lạt", "thanh vị"]},
    "cay": {"high": ["cay", "ớt", "tê lưỡi", "xé lưỡi"],
            "low": ["không cay"]},
    "ngot": {"high": ["ngọt", "đường"],
             "low": ["ít đường", "không đường", "ít ngọt"]},
    "beo": {"high": ["béo", "dầu mỡ", "ngấy", "ngán", "mỡ màng", "chiên ngập dầu"],
            "low": ["thanh đạm", "ít dầu", "healthy", "eat clean", "nhẹ bụng"]},
}

# Bản KHÔNG DẤU: chỉ giữ những từ không bị đụng nghĩa khi bỏ dấu.
# (loại "nhat" vì trùng "nhất", "duong" trùng "đường phố", "ngan" trùng "ngàn",
#  "ngay" trùng "ngay", "ot" quá ngắn dễ trùng)
TASTE_TERMS_NO_ACCENT = {
    "man": {"high": ["man", "dam da", "dam vi"], "low": ["thanh vi"]},
    "cay": {"high": ["cay"], "low": ["khong cay"]},
    "ngot": {"high": ["ngot"], "low": ["it duong", "khong duong", "it ngot"]},
    "beo": {"high": ["beo", "dau mo"],
            "low": ["thanh dam", "it dau", "healthy", "eat clean"]},
}

# dấu hiệu GIẢM (muốn vị thấp)
REDUCERS = ["khong thich", "khong an duoc", "khong an", "khong qua", "khong",
            "dung qua", "dung", "it", "giam", "bot", "han che", "kieng", "so",
            "ngai", "tranh", "hoi it", "khong duoc", "chang", "ko ", "k "]
# dấu hiệu VỪA
MIDS = ["vua an", "vua phai", "vua mieng", "vua vua", "vua du", "canh bang", "vua"]
# dấu hiệu TĂNG (muốn vị cao)
AMPLIFIERS = ["that", "cuc", "sieu", "rat", "nhieu", "dam", "ghien", "chay nuoc mat",
              "cang cang", "ki", "thich"]

TASTE_DIR_LABEL = {
    "man": {"low": "ít mặn / vị vừa", "mid": "vị mặn vừa phải", "high": "đậm đà, mặn"},
    "cay": {"low": "không cay / ít cay", "mid": "cay vừa", "high": "cay nhiều"},
    "ngot": {"low": "ít ngọt", "mid": "ngọt vừa", "high": "ngọt đậm"},
    "beo": {"low": "ít dầu mỡ, thanh đạm", "mid": "béo vừa", "high": "béo ngậy"},
}

# ------------------------------------------------------------- 2. Khoảng cách
NEAR_ME_PATTERNS = ["gan day", "gan toi", "gan cho toi", "gan nha", "quanh day",
                    "xung quanh", "gan nhat", "gan minh", "near me", "o day",
                    "khu vuc nay", "loanh quanh", "gan ben nay", "gan vi tri"]

# ---------------------------------------------------------------- 3. Tiện ích
UTILITY_PATTERNS = {
    "Máy lạnh": ["may lanh", "dieu hoa", "mat me"],
    "Chỗ đậu xe hơi": ["dau xe", "do xe hoi", "gui xe", "cho de xe"],
    "Giao hàng": ["giao hang", "ship", "dat ve", "mang ve", "delivery"],
    "Nhận đặt bàn": ["dat ban", "dat cho"],
    "Wifi mạnh": ["wifi", "lam viec", "laptop", "hoc bai", "ngoi lau"],
    "Có phòng riêng": ["phong rieng", "phong vip", "tiep khach"],
    "View đẹp": ["view dep", "song ao", "chup anh", "hen ho", "lang man", "dep"],
    "Mở khuya": ["mo khuya", "an khuya", "ban dem", "dem khuya", "khuya"],
    "Phù hợp nhóm đông": ["nhom dong", "di dong", "lien hoan", "tiec", "ca nhom",
                          "ban be", "team"],
    "Phù hợp gia đình": ["gia dinh", "ca nha", "tre em", "bo me", "con nho"],
    "Bình dân": ["binh dan", "via he", "le duong", "quan coc"],
}

# ---------------------------------------------------------------- 4. Khung giờ
MEAL_TIMES = {
    "sáng": (7, 0, ["an sang", "bua sang", "buoi sang", "sang nay", "sang som"]),
    "trưa": (12, 0, ["an trua", "bua trua", "buoi trua", "trua nay"]),
    "chiều": (16, 0, ["buoi chieu", "chieu nay", "xe chieu"]),
    "tối": (19, 0, ["an toi", "bua toi", "buoi toi", "toi nay"]),
    "khuya": (23, 0, ["an khuya", "dem khuya", "nua dem", "khuya"]),
}

OPEN_NOW_PATTERNS = ["dang mo", "mo cua", "gio nay", "bay gio", "luc nay",
                     "hien tai", "con mo", "mo khong", "mo hem"]

# ------------------------------------------------------- 4b. Đồ ăn / đồ uống
# Câu KHÔNG nêu tên món/nhóm món cụ thể nhưng vẫn cho biết người dùng đang
# muốn "uống" chứ không phải "ăn no bụng" -> để KHÔNG lẫn quán trà sữa/cà phê
# vào danh sách gợi ý cơm/bún/phở khi người dùng chỉ nói chung chung.
DRINK_INTENT_PATTERNS = ["uong gi", "do uong", "thuc uong", "giai khat",
                         "khat nuoc", "nuoc uong", "an trang mieng",
                         "trang mieng gi", "giai nhiet", "tim quan nuoc",
                         "quan nuoc"]

# Các câu thể hiện người dùng CHƯA BIẾT muốn ăn gì -> nên hỏi lại (tư vấn)
# thay vì liệt kê đại một danh sách ngẫu nhiên.
CONSULT_PATTERNS = ["tu van", "chua biet an gi", "khong biet an gi",
                    "khong biet uong gi", "goi y giup", "chua biet uong gi",
                    "doi qua ma chua biet an gi", "an gi day", "an gi bay gio"]

# ---------------------------------------------------------------- 5. Ý định
GREETING_PATTERNS = ["xin chao", "chao ban", "chao bot", "hello", "hi ", "alo", "hey"]
THANKS_PATTERNS = ["cam on", "thanks", "thank you", "tks", "cam on ban"]
HELP_PATTERNS = ["ban lam duoc gi", "huong dan", "giup gi", "co the lam gi",
                 "cach dung", "help"]
DETAIL_PATTERNS = ["thong tin ve", "chi tiet ve", "review ve", "danh gia ve",
                   "cho toi biet ve", "noi ve quan", "quan nay the nao"]


# ============================================================ cấu trúc kết quả
@dataclass
class FoodQuery:
    raw: str = ""
    intent: str = "SEARCH"
    dishes: list = field(default_factory=list)       # danh sách dish_key
    categories: list = field(default_factory=list)
    keywords: list = field(default_factory=list)     # từ khoá tự do còn lại
    taste: dict = field(default_factory=dict)        # {"man": "low"|"mid"|"high"}
    price_min: int = None
    price_max: int = None
    price_level: str = None                          # "rẻ" | "sang"
    district: str = None
    city: str = None
    near_me: bool = False
    radius_km: float = None
    min_rating: float = None
    open_now: bool = False
    at_hour: int = None
    meal: str = None
    veg_only: bool = False
    utilities: list = field(default_factory=list)
    limit: int = 5
    restaurant_name: str = None
    # muốn đồ uống/tráng miệng thay vì đồ ăn no bụng -> dùng để KHÔNG trộn 2
    # nhóm này vào chung một danh sách gợi ý
    want_drink: bool = False
    # câu nói nhắc tới CẢ món ăn lẫn đồ uống cùng lúc (vd "cơm gà và trà sữa")
    # -> nên tách thành 2 khối gợi ý riêng thay vì gộp chung
    mixed: bool = False

    # ------- diễn giải lại cho người dùng thấy bot đã hiểu gì -------
    def explain(self) -> list:
        out = []
        if self.dishes:
            out.append("🍜 Món: " + ", ".join(DISH_BY_KEY[d]["name"] for d in self.dishes))
        elif self.categories:
            out.append("🍜 Nhóm món: " + ", ".join(self.categories))
        for dim, direction in self.taste.items():
            out.append("🧂 Khẩu vị: " + TASTE_DIR_LABEL[dim][direction])
        if self.veg_only:
            out.append("🥬 Ưu tiên: món chay / healthy")
        if self.want_drink and not self.dishes and not self.categories:
            out.append("🥤 Nhóm: đồ uống / tráng miệng")
        if self.price_max and self.price_min:
            out.append(f"💰 Giá: {self.price_min // 1000}k – {self.price_max // 1000}k")
        elif self.price_max:
            out.append(f"💰 Giá: dưới {self.price_max // 1000}k")
        elif self.price_min:
            out.append(f"💰 Giá: trên {self.price_min // 1000}k")
        elif self.price_level:
            out.append(f"💰 Phân khúc: {self.price_level}")
        if self.near_me:
            r = f" (trong {self.radius_km:g}km)" if self.radius_km else ""
            out.append(f"📍 Vị trí: gần bạn{r}")
        if self.district:
            out.append(f"📍 Khu vực: {self.district}")
        elif self.city:
            out.append(f"📍 Thành phố: {self.city}")
        if self.min_rating:
            out.append(f"⭐ Đánh giá: từ {self.min_rating} sao")
        if self.open_now:
            out.append("🕐 Đang mở cửa")
        elif self.meal:
            out.append(f"🕐 Bữa: {self.meal}")
        if self.utilities:
            out.append("✨ Tiện ích: " + ", ".join(self.utilities))
        return out


# =================================================================== tiện ích
# Danh từ đứng sau con số chứng tỏ ĐÓ KHÔNG PHẢI TIỀN ("4 sao", "3 quán", "1km")
NOT_MONEY_AFTER = re.compile(
    r"^\s*(sao|quan|cho|noi|nguoi|km|met|m\b|phut|gio|h\b|mon|cap do|cap|ly|phan|"
    r"tuoi|thang|nam|ngay|lan|suat|dia diem|tiem|diem)", re.I)
# Từ báo hiệu con số phía sau là GIÁ TIỀN
MONEY_CUES = re.compile(
    r"(gia|duoi|tren|khoang|tam|chi|budget|ngan sach|bao nhieu|tu|den|toi da|"
    r"it nhat|gioi han|quanh|do)\s*$", re.I)


def _parse_money_tokens(t: str):
    """
    Tìm mọi SỐ TIỀN trong câu -> [(giá_trị_vnd, vị_trí_đầu, vị_trí_cuối)].

    Quy tắc chống nhận nhầm:
      - Có đơn vị tiền (k / nghìn / ngàn / triệu / đ / vnd)  -> chắc chắn là tiền.
      - Không có đơn vị -> phải có từ báo hiệu giá đứng trước ("giá", "dưới",
        "khoảng"...) VÀ không được theo sau bởi danh từ khác ("sao", "quán", "km").
    """
    out = []
    pattern = re.compile(
        r"(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*"
        r"(k\b|nghin|ngan|ngin|trieu|tr\b|dong|vnd|vnđ|đ)?", re.I)
    for m in pattern.finditer(t):
        num_raw, unit = m.group(1), (m.group(2) or "").strip().lower()
        after = t[m.end():m.end() + 12]
        before = t[max(0, m.start() - 26):m.start()]

        if not unit:
            if NOT_MONEY_AFTER.match(after):
                continue
            if not MONEY_CUES.search(before):
                continue

        if re.match(r"^\d{1,3}([.,]\d{3})+$", num_raw):      # 30.000
            value = float(num_raw.replace(".", "").replace(",", ""))
        else:
            value = float(num_raw.replace(",", "."))

        if unit in ("k", "nghin", "ngan", "ngin"):
            value *= 1000
        elif unit in ("trieu", "tr"):
            value *= 1_000_000
        elif value < 1000:                                    # "khoảng 30" = 30k
            value *= 1000

        if value < 3000 or value > 5_000_000:
            continue
        out.append((int(value), m.start(), m.end()))
    return out


def _has_phrase_fwd(t, p):
    return _has_phrase(t, p)


def _window_before(t: str, pos: int, size: int = 32) -> str:
    return t[max(0, pos - size):pos]


def _detect_direction(prefix: str, suffix: str, term_is_low: bool) -> str:
    """Suy ra người dùng muốn vị đó THẤP / VỪA / CAO từ ngữ cảnh xung quanh."""
    has_reducer = any(r.strip() and r in prefix for r in REDUCERS)
    has_mid = any(m in prefix for m in MIDS)
    has_amp = any(a.strip() and a in prefix for a in AMPLIFIERS)
    # "mặn quá", "cay quá" đứng sau -> lời than phiền -> muốn giảm
    complains = bool(re.match(r"^\s*(qua|lam|ghe|kinh)\b", suffix))

    if term_is_low:
        # "nhạt", "thanh đạm": bản thân đã nghĩa thấp; phủ định thì đảo lại
        return "high" if has_reducer else "low"
    if has_reducer:
        return "low"
    if has_mid:
        return "mid"
    if complains and not has_amp:
        return "low"
    if has_amp:
        return "high"
    return "high"   # "muốn ăn cay" -> thích cay


def _scan_taste(text: str, table: dict, result: dict):
    for dim, groups in table.items():
        for is_low, terms in ((False, groups["high"]), (True, groups["low"])):
            for term in terms:
                for m in re.finditer(r"(?<![\w])" + re.escape(term) + r"(?![\w])", text):
                    prefix = strip_accents(_window_before(text, m.start()))
                    suffix = strip_accents(text[m.end():m.end() + 14])
                    direction = _detect_direction(prefix, suffix, is_low)
                    # ưu tiên giữ ràng buộc cụ thể hơn ("low"/"mid" > "high")
                    if dim not in result or result[dim] == "high":
                        result[dim] = direction


def parse_taste(raw_text: str, stripped: str) -> dict:
    """
    Trích ràng buộc khẩu vị, CÓ XỬ LÝ PHỦ ĐỊNH.

    Chạy 2 lượt:
      - Lượt 1 trên văn bản CÒN DẤU  -> chính xác ("nhạt" != "nhất").
      - Lượt 2 trên văn bản BỎ DẤU   -> bắt được người gõ tắt ("khong qua man"),
        chỉ dùng tập từ an toàn, không gây nhập nhằng.
    """
    result = {}
    _scan_taste(" " + raw_text.lower() + " ", TASTE_TERMS, result)
    _scan_taste(stripped, TASTE_TERMS_NO_ACCENT, result)
    return result


def parse_price(t: str) -> tuple:
    """-> (price_min, price_max, price_level)"""
    money = _parse_money_tokens(t)
    price_min = price_max = None
    level = None

    if any(_has_phrase(t, w) for w in ["binh dan", "gia re", "re thoi", "sinh vien",
                                       "tiet kiem", "gia mem", "re", "it tien",
                                       "gia hoc sinh"]):
        level = "bình dân"
    if any(_has_phrase(t, w) for w in ["sang trong", "sang chanh", "cao cap",
                                       "fine dining", "sang xin", "xin so"]):
        level = "cao cấp"

    if money:
        # khoảng "từ X đến Y" / "X - Y"
        if len(money) >= 2:
            seg = t[money[0][2]:money[1][1]]
            if re.search(r"(den|toi|->|-|~|đến)", seg) and money[0][0] < money[1][0]:
                return money[0][0], money[1][0], level

        value, start, end = money[0]
        before = _window_before(t, start, 26)
        after = t[end:end + 12]
        if re.search(r"(duoi|<|khong qua|toi da|it hon|be hon|nho hon|trong tam|"
                     r"khoang duoi|max)", before):
            price_max = value
        elif re.search(r"(tren|>|tu|it nhat|hon)\s*$", before):
            price_min = value
        elif re.search(r"(tro xuong|do xuong|la duoc|do lai)", after):
            price_max = value
        elif re.search(r"(khoang|tam|co|gia|chi|quanh|độ|do)\s*$", before):
            price_min = int(value * 0.6)
            price_max = int(value * 1.25)
        else:
            price_max = value
    return price_min, price_max, level


def parse_distance(t: str):
    """-> (near_me: bool, radius_km: float|None)"""
    near = any(_has_phrase(t, p) for p in NEAR_ME_PATTERNS)
    radius = None
    m = re.search(r"(?:trong vong|trong ban kinh|duoi|cach|ban kinh|khong qua)\s*"
                  r"(\d+(?:[.,]\d+)?)\s*(km|m|met|phut)", t)
    if m:
        val = float(m.group(1).replace(",", "."))
        unit = m.group(2)
        if unit in ("m", "met"):
            radius = val / 1000
        elif unit == "phut":
            radius = val * 22 / 60          # ~22km/h trong nội thành
        else:
            radius = val
        near = True
    if any(_has_phrase(t, w) for w in ["di bo", "cuoc bo", "walk"]):
        near, radius = True, min(radius or 1.0, 1.0)
    return near, radius


def parse_rating(t: str):
    m = re.search(r"(?:tren|từ|tu|>=|>|it nhat)\s*(\d(?:[.,]\d)?)\s*sao", t)
    if m:
        return float(m.group(1).replace(",", "."))
    m = re.search(r"(\d(?:[.,]\d)?)\s*sao\s*(?:tro len|do len)", t)
    if m:
        return float(m.group(1).replace(",", "."))
    if any(_has_phrase(t, w) for w in ["danh gia cao", "review tot", "duoc khen",
                                       "nhieu nguoi khen", "uy tin", "ngon nhat",
                                       "tot nhat", "top", "noi tieng", "ngon"]):
        return 4.2
    return None


def parse_limit(t: str) -> int:
    m = re.search(r"(?:top|cho toi|goi y|tim|liet ke|khoang)?\s*(\d{1,2})\s*"
                  r"(?:quan|cho|noi|dia diem|tiem)", t)
    if m:
        return max(1, min(20, int(m.group(1))))
    m = re.search(r"top\s*(\d{1,2})", t)
    if m:
        return max(1, min(20, int(m.group(1))))
    if any(_has_phrase(t, w) for w in ["nhieu quan", "danh sach", "tat ca"]):
        return 12
    return 5


def _has_phrase(t: str, phrase: str) -> bool:
    """Khớp theo ranh giới từ: 'gan toi' KHÔNG được tính là chứa 'an toi'."""
    return re.search(r"(?<![\w])" + re.escape(phrase) + r"(?![\w])", t) is not None


def parse_time(t: str):
    """-> (open_now, at_hour, meal_label)"""
    open_now = any(_has_phrase(t, p) for p in OPEN_NOW_PATTERNS)
    for label, (hour, _minute, pats) in MEAL_TIMES.items():
        if any(_has_phrase(t, p) for p in pats):
            return open_now, hour, label
    return open_now, None, None


def parse_utilities(t: str) -> list:
    out = []
    for util, pats in UTILITY_PATTERNS.items():
        if any(_has_phrase(t, p) for p in pats):
            out.append(util)
    return out


def detect_intent(t: str, q) -> str:
    if any(_has_phrase(t, p.strip()) for p in THANKS_PATTERNS) and len(t) < 30:
        return "THANKS"
    if any(p in t for p in HELP_PATTERNS):
        return "HELP"
    if any(_has_phrase(t, p.strip()) for p in GREETING_PATTERNS) and len(t) < 25:
        return "GREETING"
    if any(p in t for p in DETAIL_PATTERNS):
        return "DETAIL"
    if (q.dishes or q.categories or q.taste or q.price_max or q.price_min
            or q.district or q.city or q.near_me or q.utilities or q.veg_only
            or q.min_rating):
        return "SEARCH"
    if any(_has_phrase(t, w) for w in ["an gi", "goi y", "de xuat", "doi an",
                                       "doi bung", "them an", "muon an", "tim quan",
                                       "quan nao", "cho nao", "o dau", "an trua",
                                       "an sang", "an toi"] + CONSULT_PATTERNS):
        return "SEARCH"
    return "FALLBACK"


def parse(text: str, user_location=None) -> FoodQuery:
    """Hàm chính: câu nói tự nhiên -> FoodQuery có cấu trúc."""
    q = FoodQuery(raw=text)
    t = " " + strip_accents(text) + " "

    q.dishes = find_dishes(text)
    q.taste = parse_taste(text, t)
    q.price_min, q.price_max, q.price_level = parse_price(t)
    q.district = find_district(text)
    q.city = find_city(text)
    q.near_me, q.radius_km = parse_distance(t)
    q.min_rating = parse_rating(t)
    q.limit = parse_limit(t)
    q.open_now, q.at_hour, q.meal = parse_time(t)
    q.utilities = parse_utilities(t)
    q.veg_only = any(_has_phrase(t, w) for w in
                     ["an chay", "do chay", "quan chay", "thuan chay", "vegetarian",
                      "vegan", "eat clean", "giam can", "an kieng", "healthy"])

    # nếu chưa bắt được món nhưng có nhóm món
    if not q.dishes:
        from food_catalog import DISH_CATALOG
        for cat in {d["category"] for d in DISH_CATALOG}:
            if strip_accents(cat) in t:
                q.categories.append(cat)

    # phân khúc giá -> ràng buộc mềm
    if q.price_level == "bình dân" and not q.price_max:
        q.price_max = 60000
    if q.price_level == "cao cấp" and not q.price_min:
        q.price_min = 150000

    # ---- tách nhóm đồ ăn no bụng / đồ uống - tráng miệng ----
    dish_cats = {DISH_BY_KEY[d]["category"] for d in q.dishes if d in DISH_BY_KEY}
    has_drink_dish = any(c in DRINK_CATEGORIES for c in dish_cats)
    has_food_dish = any(c not in DRINK_CATEGORIES for c in dish_cats)
    # người dùng nhắc tới CẢ món ăn lẫn đồ uống trong cùng 1 câu (vd "cơm gà
    # và trà sữa") -> nên tách thành 2 khối riêng khi trả kết quả
    q.mixed = has_drink_dish and has_food_dish

    if has_drink_dish and not has_food_dish:
        q.want_drink = True
    elif q.categories and all(c in DRINK_CATEGORIES for c in q.categories):
        q.want_drink = True
    elif not q.dishes and not q.categories and any(
            _has_phrase(t, w) for w in DRINK_INTENT_PATTERNS):
        q.want_drink = True

    # nói "gần" mà không nêu bán kính -> mặc định 3km
    if q.near_me and not q.radius_km:
        q.radius_km = 3.0
    # không nói gì về vị trí nhưng có vị trí GPS -> vẫn ưu tiên gần
    if not q.near_me and not q.district and user_location:
        q.radius_km = q.radius_km or None

    q.intent = detect_intent(t, q)
    return q


# ------------------------------------------------------------------ demo CLI
if __name__ == "__main__":
    tests = [
        "Tôi muốn ăn xôi, nhưng không thích quá mặn, tìm quán gần đây.",
        "Tôi muốn ăn xôi không quá mặn, giá dưới 30k, gần tôi.",
        "tìm quán bún bò thật cay ở quận 1 trên 4 sao",
        "com trua binh dan gan day dang mo cua",
        "quán lẩu cho nhóm đông người, có máy lạnh, tầm 300k ở Bình Thạnh",
        "muốn ăn gì đó healthy ít dầu mỡ, dưới 80k",
        "trà sữa ít đường gần tôi trong vòng 1km",
        "top 3 quán phở ngon nhất quận 3",
    ]
    for s in tests:
        q = parse(s)
        print("\n>>", s)
        print("   intent:", q.intent)
        for line in q.explain():
            print("   ", line)
