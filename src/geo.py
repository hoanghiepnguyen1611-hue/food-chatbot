# -*- coding: utf-8 -*-
"""
Module địa lý: quận/huyện TP.HCM, tính khoảng cách thực tế và sinh link Google Maps.

- Khoảng cách dùng công thức Haversine (khoảng cách theo đường chim bay trên
  mặt cầu Trái Đất), sau đó nhân hệ số 1.25 để ước lượng quãng đường đi thực tế
  trong đô thị (đường không bao giờ thẳng).
- Link Google Maps dùng Maps URLs API (không cần API key):
    + Xem quán   : https://www.google.com/maps/search/?api=1&query=...
    + Chỉ đường  : https://www.google.com/maps/dir/?api=1&origin=...&destination=...
    + Nhúng iframe: https://maps.google.com/maps?q=...&output=embed
"""
import math
from urllib.parse import quote_plus

# Tâm các quận/huyện TP.HCM (lat, lng) + danh sách tên đường thật để sinh địa chỉ
DISTRICTS = {
    "Quận 1": dict(lat=10.7769, lng=106.7009, streets=[
        "Nguyễn Huệ", "Lê Lợi", "Hai Bà Trưng", "Pasteur", "Nguyễn Thị Minh Khai",
        "Cô Giang", "Đề Thám", "Bùi Viện", "Nguyễn Trãi", "Cống Quỳnh",
        "Trần Hưng Đạo", "Nguyễn Đình Chiểu", "Điện Biên Phủ", "Mạc Đĩnh Chi"]),
    "Quận 3": dict(lat=10.7800, lng=106.6850, streets=[
        "Võ Văn Tần", "Nguyễn Đình Chiểu", "Cách Mạng Tháng 8", "Lê Văn Sỹ",
        "Trần Quốc Thảo", "Bà Huyện Thanh Quan", "Nguyễn Thiện Thuật",
        "Hoàng Sa", "Kỳ Đồng", "Trương Định"]),
    "Quận 4": dict(lat=10.7590, lng=106.7050, streets=[
        "Vĩnh Khánh", "Khánh Hội", "Hoàng Diệu", "Đoàn Văn Bơ", "Tôn Đản",
        "Nguyễn Tất Thành", "Lê Quốc Hưng"]),
    "Quận 5": dict(lat=10.7540, lng=106.6670, streets=[
        "Trần Hưng Đạo", "Nguyễn Trãi", "An Dương Vương", "Hà Tôn Quyền",
        "Châu Văn Liêm", "Nguyễn Tri Phương", "Trần Phú", "Sư Vạn Hạnh"]),
    "Quận 6": dict(lat=10.7460, lng=106.6350, streets=[
        "Hậu Giang", "Minh Phụng", "Bình Phú", "Chợ Lớn", "Phạm Văn Chí",
        "Nguyễn Văn Luông"]),
    "Quận 7": dict(lat=10.7340, lng=106.7220, streets=[
        "Nguyễn Thị Thập", "Huỳnh Tấn Phát", "Nguyễn Văn Linh", "Tôn Dật Tiên",
        "Bùi Bằng Đoàn", "Phạm Thái Bường", "Trần Văn Trà", "Lâm Văn Bền"]),
    "Quận 8": dict(lat=10.7240, lng=106.6280, streets=[
        "Phạm Thế Hiển", "Tạ Quang Bửu", "Dương Bá Trạc", "Bùi Minh Trực",
        "Âu Dương Lân"]),
    "Quận 10": dict(lat=10.7730, lng=106.6670, streets=[
        "Sư Vạn Hạnh", "Ba Tháng Hai", "Cao Thắng", "Lý Thái Tổ", "Nguyễn Tri Phương",
        "Thành Thái", "Tô Hiến Thành", "Hòa Hưng"]),
    "Quận 11": dict(lat=10.7640, lng=106.6500, streets=[
        "Lạc Long Quân", "Ông Ích Khiêm", "Đường Ba Tháng Hai", "Lãnh Binh Thăng",
        "Hàn Hải Nguyên"]),
    "Quận 12": dict(lat=10.8670, lng=106.6410, streets=[
        "Nguyễn Ảnh Thủ", "Lê Văn Khương", "Tô Ký", "Hà Huy Giáp", "Quang Trung",
        "Trường Chinh"]),
    "Bình Thạnh": dict(lat=10.8110, lng=106.7090, streets=[
        "Điện Biên Phủ", "Xô Viết Nghệ Tĩnh", "Nguyễn Hữu Cảnh", "Phan Xích Long",
        "Bạch Đằng", "Đinh Bộ Lĩnh", "Ung Văn Khiêm", "Nơ Trang Long"]),
    "Phú Nhuận": dict(lat=10.7990, lng=106.6800, streets=[
        "Phan Xích Long", "Phan Đình Phùng", "Hoàng Văn Thụ", "Nguyễn Văn Trỗi",
        "Huỳnh Văn Bánh", "Thích Quảng Đức"]),
    "Tân Bình": dict(lat=10.8010, lng=106.6520, streets=[
        "Cộng Hòa", "Hoàng Văn Thụ", "Lý Thường Kiệt", "Trường Chinh",
        "Bàu Cát", "Âu Cơ", "Phạm Văn Hai", "Nguyễn Hồng Đào"]),
    "Tân Phú": dict(lat=10.7900, lng=106.6280, streets=[
        "Lũy Bán Bích", "Tân Kỳ Tân Quý", "Gò Dầu", "Thoại Ngọc Hầu",
        "Vườn Lài", "Độc Lập"]),
    "Gò Vấp": dict(lat=10.8380, lng=106.6650, streets=[
        "Quang Trung", "Nguyễn Oanh", "Phan Văn Trị", "Lê Đức Thọ",
        "Nguyễn Văn Nghi", "Phạm Văn Đồng", "Dương Quảng Hàm"]),
    "Bình Tân": dict(lat=10.7650, lng=106.6030, streets=[
        "Tên Lửa", "Vành Đai Trong", "Kinh Dương Vương", "Lê Văn Quới",
        "Mã Lò", "Số 7"]),
    "Thủ Đức": dict(lat=10.8500, lng=106.7540, streets=[
        "Võ Văn Ngân", "Kha Vạn Cân", "Đặng Văn Bi", "Lê Văn Việt",
        "Hoàng Diệu 2", "Tô Ngọc Vân", "Đỗ Xuân Hợp", "Man Thiện"]),
    "Nhà Bè": dict(lat=10.6950, lng=106.7060, streets=[
        "Nguyễn Hữu Thọ", "Lê Văn Lương", "Huỳnh Tấn Phát", "Phạm Hữu Lầu"]),
}

# ---------------------------------------------------------------------------
# KHU VỰC QUẢNG NGÃI
#
# Lưu ý hành chính: theo Nghị quyết 1677/NQ-UBTVQH15, từ 01/7/2025 thành phố
# Quảng Ngãi kết thúc hoạt động; địa bàn thành phố cũ được sắp xếp thành 5 đơn
# vị hành chính cấp xã: phường Cẩm Thành, phường Nghĩa Lộ, phường Trương Quang
# Trọng, xã Tịnh Khê và xã An Phú (xã Đông Sơn nằm liền kề, gồm cả Tịnh Hòa,
# Bình Châu cũ). Dữ liệu dưới đây dùng TÊN MỚI, kèm tên cũ trong `aliases` để
# người dùng gõ "Nghĩa Chánh", "Chánh Lộ", "Quảng Phú"... vẫn tìm được.
# ---------------------------------------------------------------------------
QUANG_NGAI_WARDS = {
    "Phường Cẩm Thành": dict(
        lat=15.1214, lng=108.8044,
        aliases=["cẩm thành", "nguyễn nghiêm", "trần hưng đạo quảng ngãi",
                 "nghĩa chánh", "chánh lộ", "trung tâm quảng ngãi"],
        streets=["Quang Trung", "Hùng Vương", "Nguyễn Nghiêm", "Phan Đình Phùng",
                 "Trần Hưng Đạo", "Nguyễn Du", "Hai Bà Trưng", "Lê Trung Đình",
                 "Nguyễn Bá Loan", "Nguyễn Tự Tân", "Phan Bội Châu", "Bà Triệu",
                 "Ngô Quyền", "Lê Lợi", "Trương Định", "Nguyễn Thụy"]),
    "Phường Nghĩa Lộ": dict(
        lat=15.1112, lng=108.7896,
        aliases=["nghĩa lộ", "lê hồng phong", "trần phú", "quảng phú"],
        streets=["Trần Phú", "Lê Hồng Phong", "Nguyễn Công Phương", "Chu Văn An",
                 "Nguyễn Trãi", "Lê Thánh Tôn", "Bùi Thị Xuân", "Võ Thị Sáu",
                 "Đinh Tiên Hoàng", "Trần Quốc Toản", "Phạm Văn Đồng",
                 "Nguyễn Chánh", "Tôn Đức Thắng"]),
    "Phường Trương Quang Trọng": dict(
        lat=15.1452, lng=108.7918,
        aliases=["trương quang trọng", "tịnh ấn", "tịnh ấn tây", "tịnh ấn đông",
                 "tịnh an", "bắc quảng ngãi"],
        streets=["Trường Chinh", "Quang Trung", "Đinh Tiên Hoàng",
                 "Nguyễn Trung Trực", "Trương Quang Trọng", "Lê Đại Hành",
                 "Hoàng Hoa Thám", "An Dương Vương", "Trần Kỳ Phong"]),
    "Xã Tịnh Khê": dict(
        lat=15.1558, lng=108.8618,
        aliases=["tịnh khê", "mỹ khê", "biển mỹ khê", "tịnh kỳ", "tịnh long",
                 "tịnh châu", "tịnh thiện", "cửa đại"],
        streets=["Mỹ Khê – Trà Khúc", "Tịnh Khê", "Đường ven biển Dung Quất – Sa Huỳnh",
                 "Tỉnh lộ 624B", "Trương Quang Giao", "Đường Mỹ Khê"]),
    "Xã An Phú": dict(
        lat=15.0988, lng=108.8296,
        aliases=["an phú", "nghĩa hà", "nghĩa dõng", "nghĩa dũng", "nam sông trà"],
        streets=["Nguyễn Công Phương", "Nghĩa Dũng", "Tỉnh lộ 623B", "An Phú",
                 "Đường Nghĩa Hà", "Trương Quang Cận"]),
    "Xã Đông Sơn": dict(
        lat=15.2086, lng=108.8452,
        aliases=["đông sơn", "tịnh hòa", "bình châu", "bình thanh", "bình hiệp"],
        streets=["Tỉnh lộ 621", "Đường ven biển Dung Quất – Sa Huỳnh",
                 "Bình Châu", "Tịnh Hòa"]),
}

# Gộp hai vùng vào một bảng tra cứu duy nhất, mỗi khu vực ghi rõ thuộc thành phố
# / tỉnh nào để chatbot lọc và hiển thị đúng.
CITY_OF = {}
for _name in DISTRICTS:
    DISTRICTS[_name].setdefault("aliases", [])
    CITY_OF[_name] = "TP.HCM"
for _name, _info in QUANG_NGAI_WARDS.items():
    DISTRICTS[_name] = _info
    CITY_OF[_name] = "Quảng Ngãi"

CITIES = {
    "TP.HCM": dict(label="TP. Hồ Chí Minh", center=(10.7725, 106.6980),
                   areas=[n for n in CITY_OF if CITY_OF[n] == "TP.HCM"]),
    "Quảng Ngãi": dict(label="Quảng Ngãi (địa bàn TP Quảng Ngãi cũ)",
                       center=(15.1214, 108.8044),
                       areas=[n for n in CITY_OF if CITY_OF[n] == "Quảng Ngãi"]),
}


CITY_ALIASES = {
    "TP.HCM": ["tphcm", "tp hcm", "ho chi minh", "sai gon", "hcm", "sg"],
    "Quảng Ngãi": ["quang ngai", "tp quang ngai", "qng", "quangngai"],
}


def find_city(text: str):
    """Nhận diện thành phố/tỉnh được nhắc trong câu."""
    from food_catalog import strip_accents
    t = strip_accents(text)
    for city, aliases in CITY_ALIASES.items():
        if any(a in t for a in aliases):
            return city
    return None


def city_of(area: str) -> str:
    """Khu vực này thuộc thành phố nào."""
    return CITY_OF.get(area, "TP.HCM")


def areas_of(city: str):
    return CITIES.get(city, {}).get("areas", [])


DISTRICT_NAMES = list(DISTRICTS.keys())

# Vị trí mặc định khi người dùng không cho phép định vị (Chợ Bến Thành, Q1)
DEFAULT_USER_LOCATION = (10.7725, 106.6980)

EARTH_RADIUS_KM = 6371.0
CITY_DETOUR_FACTOR = 1.25  # hệ số ước lượng đường đi thực tế so với đường chim bay


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    """Khoảng cách đường chim bay giữa 2 toạ độ (km)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def travel_distance_km(lat1, lng1, lat2, lng2) -> float:
    """Ước lượng quãng đường di chuyển thực tế trong đô thị (km)."""
    return haversine_km(lat1, lng1, lat2, lng2) * CITY_DETOUR_FACTOR


def format_distance(km: float) -> str:
    if km is None:
        return ""
    if km < 1:
        return f"{int(round(km * 1000 / 10) * 10)}m"
    return f"{km:.1f}km".replace(".", ",")


def estimate_minutes(km: float, speed_kmh: float = 22.0) -> int:
    """Ước lượng thời gian chạy xe máy (tốc độ trung bình nội thành ~22km/h)."""
    return max(1, int(round(km / speed_kmh * 60)))


# ------------------------------------------------------- Google Maps URLs
def maps_place_url(name: str, address: str, lat: float, lng: float) -> str:
    """Link mở Google Maps tại đúng quán (kèm toạ độ để không bị lệch)."""
    query = quote_plus(f"{name}, {address}")
    return f"https://www.google.com/maps/search/?api=1&query={query}&center={lat},{lng}"


def maps_coord_url(lat: float, lng: float) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"


def maps_directions_url(lat: float, lng: float, name: str = "",
                        origin_lat=None, origin_lng=None,
                        mode: str = "two-wheeler") -> str:
    """Link chỉ đường từ vị trí người dùng tới quán."""
    url = (f"https://www.google.com/maps/dir/?api=1"
           f"&destination={lat},{lng}&travelmode={mode}")
    if name:
        url += f"&destination_place_id=&query={quote_plus(name)}"
    if origin_lat is not None and origin_lng is not None:
        url += f"&origin={origin_lat},{origin_lng}"
    return url


def maps_embed_url(lat: float, lng: float, zoom: int = 17) -> str:
    """Link nhúng bản đồ vào iframe — KHÔNG cần API key."""
    return f"https://maps.google.com/maps?q={lat},{lng}&z={zoom}&output=embed"


def nearest_district(lat: float, lng: float):
    """
    Định vị "ngược": từ toạ độ GPS suy ra quận/phường gần nhất trong dữ liệu.

    Đây là ước lượng theo khoảng cách tới tâm quận/phường (không phải tra theo
    ranh giới hành chính chính xác) — đủ dùng để hiển thị cho người dùng biết
    "bạn đang ở gần khu vực nào" ngay khi bật định vị, không cần gõ gì cả.

    -> (tên_quận_phường, khoảng_cách_km)
    """
    best_name, best_km = None, None
    for name, info in DISTRICTS.items():
        km = haversine_km(lat, lng, info["lat"], info["lng"])
        if best_km is None or km < best_km:
            best_name, best_km = name, km
    return best_name, best_km


def find_district(text: str):
    """
    Nhận diện quận/phường/xã được nhắc trong câu.

    Có tra cả TÊN CŨ trước sáp nhập (vd "Nghĩa Chánh" -> phường Cẩm Thành),
    vì địa chỉ trên Google Maps và trong thói quen người dân vẫn dùng tên cũ.
    """
    from food_catalog import strip_accents
    import re
    t = strip_accents(text)

    candidates = []
    for name, info in DISTRICTS.items():
        for label in [name] + list(info.get("aliases", [])):
            candidates.append((strip_accents(label), name))
    candidates.sort(key=lambda x: -len(x[0]))

    for label, name in candidates:
        if re.search(r"(?<![a-z])" + re.escape(label) + r"(?![a-z])", t):
            return name

    m = re.search(r"\b(?:quan|q)\s*\.?\s*(\d{1,2})\b", t)
    if m:
        cand = f"Quận {int(m.group(1))}"
        if cand in DISTRICTS:
            return cand
    return None
