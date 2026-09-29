# -*- coding: utf-8 -*-
"""
TỪ ĐIỂN MÓN ĂN (Food Ontology) — trái tim của việc "hiểu yêu cầu tự nhiên".

Mỗi món ăn được mô tả bằng:
  - key         : định danh
  - name        : tên hiển thị
  - aliases     : các cách người dùng hay gọi (kể cả viết không dấu)
  - category    : nhóm món (ăn sáng, cơm, bún/phở, ăn vặt, đồ uống...)
  - price       : khoảng giá phổ biến (VND)
  - taste       : hồ sơ vị mặc định của món, thang 0..1
                  man  = độ mặn, cay = độ cay, ngot = độ ngọt, beo = độ béo/dầu mỡ
  - items       : các món cụ thể trong menu
  - hours       : khung giờ mở cửa điển hình
  - is_veg      : món chay hay không

Nhờ có hồ sơ vị (taste profile) ở MỨC MÓN + MỨC QUÁN, chatbot mới trả lời được
câu như "muốn ăn xôi nhưng không thích quá mặn" — thay vì chỉ match từ khóa.
"""
import re
import unicodedata


# ---------------------------------------------------------------- tiện ích
def strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt -> cho phép người dùng gõ 'xoi', 'bun bo' vẫn hiểu."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip()


def norm_key(text: str) -> str:
    return strip_accents(text)


# ---------------------------------------------------- các chiều vị (taste)
TASTE_DIMS = ["man", "cay", "ngot", "beo"]

TASTE_LABELS = {
    "man": "mặn",
    "cay": "cay",
    "ngot": "ngọt",
    "beo": "béo / dầu mỡ",
}


# ------------------------------------------------------- danh mục món ăn
# (price: min, max — VND) (taste: man, cay, ngot, beo)
DISH_CATALOG = [
    # ---- Ăn sáng / xôi / bánh mì ----
    dict(key="xoi", name="Xôi", category="Ăn sáng", price=(15000, 40000),
         taste=dict(man=0.62, cay=0.15, ngot=0.30, beo=0.52),
         aliases=["xôi", "xoi", "xôi mặn", "xôi gà", "xôi xéo", "xôi khúc", "xôi lạp xưởng"],
         items=["Xôi gà xé", "Xôi mặn thập cẩm", "Xôi xéo hành phi", "Xôi lạp xưởng",
                "Xôi đậu xanh", "Xôi chả lụa", "Xôi gấc"],
         hours=("05:00", "11:30")),
    dict(key="banh_mi", name="Bánh mì", category="Ăn sáng", price=(15000, 45000),
         taste=dict(man=0.58, cay=0.30, ngot=0.25, beo=0.50),
         aliases=["bánh mì", "banh mi", "bánh mỳ", "bánh mì thịt", "bánh mì chảo"],
         items=["Bánh mì thịt nguội", "Bánh mì chả cá", "Bánh mì xíu mại",
                "Bánh mì chảo", "Bánh mì heo quay", "Bánh mì trứng"],
         hours=("05:30", "21:00")),
    dict(key="banh_cuon", name="Bánh cuốn", category="Ăn sáng", price=(25000, 55000),
         taste=dict(man=0.48, cay=0.15, ngot=0.35, beo=0.35),
         aliases=["bánh cuốn", "banh cuon", "bánh ướt"],
         items=["Bánh cuốn nhân thịt", "Bánh cuốn chả lụa", "Bánh ướt lòng gà"],
         hours=("06:00", "13:00")),
    dict(key="chao", name="Cháo", category="Ăn sáng", price=(20000, 60000),
         taste=dict(man=0.45, cay=0.20, ngot=0.20, beo=0.35),
         aliases=["cháo", "chao long", "cháo lòng", "cháo gà", "cháo sườn"],
         items=["Cháo lòng", "Cháo gà", "Cháo sườn", "Cháo cá", "Cháo hải sản"],
         hours=("06:00", "22:00")),
    dict(key="banh_bao", name="Bánh bao", category="Ăn sáng", price=(12000, 30000),
         taste=dict(man=0.45, cay=0.10, ngot=0.40, beo=0.40),
         aliases=["bánh bao", "banh bao"],
         items=["Bánh bao nhân thịt", "Bánh bao trứng muối", "Bánh bao chay"],
         hours=("05:30", "20:00")),

    # ---- Phở / bún / hủ tiếu ----
    dict(key="pho", name="Phở", category="Bún – Phở", price=(35000, 90000),
         taste=dict(man=0.55, cay=0.20, ngot=0.30, beo=0.40),
         aliases=["phở", "pho", "phở bò", "phở gà", "phở tái"],
         items=["Phở tái", "Phở chín", "Phở gà", "Phở đặc biệt", "Phở bò viên"],
         hours=("05:30", "22:00")),
    dict(key="bun_bo", name="Bún bò Huế", category="Bún – Phở", price=(35000, 80000),
         taste=dict(man=0.68, cay=0.70, ngot=0.30, beo=0.55),
         aliases=["bún bò", "bun bo", "bún bò huế", "bún bò giò heo"],
         items=["Bún bò giò heo", "Bún bò tái", "Bún bò đặc biệt", "Bún bò chả cua"],
         hours=("06:00", "21:00")),
    dict(key="bun_cha", name="Bún chả", category="Bún – Phở", price=(35000, 75000),
         taste=dict(man=0.55, cay=0.25, ngot=0.50, beo=0.50),
         aliases=["bún chả", "bun cha", "bún chả hà nội"],
         items=["Bún chả Hà Nội", "Bún chả nem cua bể", "Bún chả que tre"],
         hours=("09:00", "21:00")),
    dict(key="bun_rieu", name="Bún riêu", category="Bún – Phở", price=(30000, 65000),
         taste=dict(man=0.55, cay=0.35, ngot=0.30, beo=0.40),
         aliases=["bún riêu", "bun rieu", "bún riêu cua"],
         items=["Bún riêu cua", "Bún riêu ốc", "Bún riêu giò"],
         hours=("06:00", "20:00")),
    dict(key="bun_thit_nuong", name="Bún thịt nướng", category="Bún – Phở",
         price=(30000, 65000),
         taste=dict(man=0.50, cay=0.25, ngot=0.55, beo=0.50),
         aliases=["bún thịt nướng", "bun thit nuong", "bún nem nướng"],
         items=["Bún thịt nướng", "Bún thịt nướng chả giò", "Bún nem nướng"],
         hours=("09:00", "21:00")),
    dict(key="bun_dau", name="Bún đậu mắm tôm", category="Bún – Phở",
         price=(45000, 120000),
         taste=dict(man=0.80, cay=0.35, ngot=0.25, beo=0.65),
         aliases=["bún đậu", "bun dau", "bún đậu mắm tôm"],
         items=["Bún đậu mẹt đầy đủ", "Bún đậu chả cốm", "Bún đậu thịt luộc"],
         hours=("10:00", "22:00")),
    dict(key="hu_tieu", name="Hủ tiếu", category="Bún – Phở", price=(30000, 70000),
         taste=dict(man=0.52, cay=0.20, ngot=0.45, beo=0.38),
         aliases=["hủ tiếu", "hu tieu", "hủ tiếu nam vang", "hủ tiếu gõ"],
         items=["Hủ tiếu Nam Vang", "Hủ tiếu khô", "Hủ tiếu mì", "Hủ tiếu sa tế"],
         hours=("06:00", "23:00")),
    dict(key="mi_quang", name="Mì Quảng", category="Bún – Phở", price=(35000, 70000),
         taste=dict(man=0.60, cay=0.40, ngot=0.30, beo=0.50),
         aliases=["mì quảng", "mi quang"],
         items=["Mì Quảng gà", "Mì Quảng tôm thịt", "Mì Quảng sườn non"],
         hours=("06:30", "21:00")),
    dict(key="banh_canh", name="Bánh canh", category="Bún – Phở", price=(30000, 70000),
         taste=dict(man=0.58, cay=0.30, ngot=0.35, beo=0.45),
         aliases=["bánh canh", "banh canh", "bánh canh cua", "bánh canh ghẹ"],
         items=["Bánh canh cua", "Bánh canh giò heo", "Bánh canh cá lóc"],
         hours=("07:00", "22:00")),
    dict(key="mi_cay", name="Mì cay", category="Bún – Phở", price=(45000, 90000),
         taste=dict(man=0.60, cay=0.92, ngot=0.25, beo=0.55),
         aliases=["mì cay", "mi cay", "mì cay 7 cấp độ"],
         items=["Mì cay hải sản", "Mì cay bò", "Mì cay kim chi"],
         hours=("10:00", "22:30")),

    # ---- Cơm ----
    dict(key="com_tam", name="Cơm tấm", category="Cơm", price=(30000, 75000),
         taste=dict(man=0.62, cay=0.25, ngot=0.45, beo=0.60),
         aliases=["cơm tấm", "com tam", "cơm sườn"],
         items=["Cơm tấm sườn bì chả", "Cơm tấm sườn trứng", "Cơm tấm gà nướng"],
         hours=("06:00", "23:00")),
    dict(key="com_ga", name="Cơm gà", category="Cơm", price=(35000, 85000),
         taste=dict(man=0.55, cay=0.25, ngot=0.30, beo=0.55),
         aliases=["cơm gà", "com ga", "cơm gà xối mỡ", "cơm gà hải nam"],
         items=["Cơm gà xối mỡ", "Cơm gà Hải Nam", "Cơm gà xé", "Cơm gà roti"],
         hours=("09:00", "22:00")),
    dict(key="com_van_phong", name="Cơm văn phòng", category="Cơm", price=(35000, 70000),
         taste=dict(man=0.50, cay=0.20, ngot=0.25, beo=0.40),
         aliases=["cơm văn phòng", "com van phong", "cơm trưa", "cơm bình dân", "cơm phần"],
         items=["Cơm sườn ram", "Cơm cá kho tộ", "Cơm thịt kho trứng", "Cơm gà chiên nước mắm"],
         hours=("10:00", "20:00")),
    dict(key="com_nieu", name="Cơm niêu – cơm nhà", category="Cơm", price=(60000, 180000),
         taste=dict(man=0.55, cay=0.25, ngot=0.30, beo=0.45),
         aliases=["cơm niêu", "com nieu", "cơm nhà", "quán cơm gia đình"],
         items=["Cơm niêu cá kho", "Canh chua cá lóc", "Thịt kho tàu", "Rau luộc chấm mắm"],
         hours=("10:00", "21:30")),
    dict(key="com_chien", name="Cơm chiên", category="Cơm", price=(35000, 80000),
         taste=dict(man=0.58, cay=0.20, ngot=0.30, beo=0.70),
         aliases=["cơm chiên", "com chien", "cơm rang"],
         items=["Cơm chiên dương châu", "Cơm chiên hải sản", "Cơm chiên cá mặn"],
         hours=("10:00", "22:00")),
    dict(key="com_chay", name="Cơm chay", category="Chay – Healthy", price=(25000, 70000),
         taste=dict(man=0.40, cay=0.15, ngot=0.30, beo=0.35),
         aliases=["cơm chay", "com chay", "đồ chay", "quán chay", "ăn chay"],
         items=["Cơm chay thập cẩm", "Đậu hũ kho tiêu", "Canh rong biển", "Nấm kho"],
         hours=("06:00", "20:00"), is_veg=True),
    dict(key="salad", name="Salad – Healthy", category="Chay – Healthy",
         price=(45000, 120000),
         taste=dict(man=0.28, cay=0.15, ngot=0.30, beo=0.25),
         aliases=["salad", "healthy", "eat clean", "cơm healthy", "ăn kiêng", "low carb"],
         items=["Salad ức gà", "Cơm gạo lứt ức gà", "Poke bowl cá hồi", "Salad cá ngừ"],
         hours=("08:00", "20:00")),

    # ---- Món nước / lẩu / nướng ----
    dict(key="lau", name="Lẩu", category="Lẩu – Nướng", price=(150000, 500000),
         taste=dict(man=0.60, cay=0.55, ngot=0.35, beo=0.55),
         aliases=["lẩu", "lau", "lẩu thái", "lẩu bò", "lẩu gà lá é", "lẩu cá"],
         items=["Lẩu Thái chua cay", "Lẩu bò nhúng dấm", "Lẩu gà lá é", "Lẩu cá kèo"],
         hours=("16:00", "23:30")),
    dict(key="nuong", name="Nướng – BBQ", category="Lẩu – Nướng", price=(150000, 450000),
         taste=dict(man=0.62, cay=0.35, ngot=0.50, beo=0.70),
         aliases=["nướng", "nuong", "bbq", "thịt nướng", "nướng hàn quốc", "buffet nướng"],
         items=["Ba chỉ bò nướng", "Sườn nướng BBQ", "Bạch tuộc nướng", "Nầm nướng"],
         hours=("16:00", "23:59")),
    dict(key="oc", name="Ốc – Hải sản", category="Ăn vặt", price=(50000, 250000),
         taste=dict(man=0.65, cay=0.62, ngot=0.40, beo=0.55),
         aliases=["ốc", "oc", "quán ốc", "hải sản", "sò", "nghêu"],
         items=["Ốc hương rang muối ớt", "Sò huyết me", "Nghêu hấp sả", "Càng ghẹ rang me"],
         hours=("15:00", "23:59")),
    dict(key="bo_kho", name="Bò kho", category="Món nước", price=(35000, 75000),
         taste=dict(man=0.58, cay=0.30, ngot=0.40, beo=0.50),
         aliases=["bò kho", "bo kho", "bánh mì bò kho"],
         items=["Bò kho bánh mì", "Bò kho hủ tiếu", "Bò kho nạm gân"],
         hours=("06:00", "21:00")),
    dict(key="pha_lau", name="Phá lấu", category="Ăn vặt", price=(25000, 60000),
         taste=dict(man=0.60, cay=0.35, ngot=0.35, beo=0.68),
         aliases=["phá lấu", "pha lau"],
         items=["Phá lấu bò nước dừa", "Phá lấu bánh mì", "Phá lấu mì"],
         hours=("13:00", "23:00")),

    # ---- Món Việt khác ----
    dict(key="banh_xeo", name="Bánh xèo", category="Món Việt", price=(35000, 90000),
         taste=dict(man=0.52, cay=0.25, ngot=0.40, beo=0.72),
         aliases=["bánh xèo", "banh xeo", "bánh khọt"],
         items=["Bánh xèo tôm thịt", "Bánh xèo miền Tây", "Bánh khọt"],
         hours=("10:00", "21:30")),
    dict(key="goi_cuon", name="Gỏi cuốn – Nem", category="Món Việt", price=(25000, 70000),
         taste=dict(man=0.40, cay=0.25, ngot=0.45, beo=0.30),
         aliases=["gỏi cuốn", "goi cuon", "nem nướng", "bò bía"],
         items=["Gỏi cuốn tôm thịt", "Nem nướng Nha Trang", "Bò bía"],
         hours=("09:00", "21:00")),
    dict(key="banh_beo", name="Bánh bèo – Bánh Huế", category="Món Việt",
         price=(30000, 70000),
         taste=dict(man=0.50, cay=0.35, ngot=0.35, beo=0.35),
         aliases=["bánh bèo", "banh beo", "bánh nậm", "bánh lọc", "bánh huế"],
         items=["Bánh bèo chén", "Bánh lọc", "Bánh nậm", "Bánh ít trần"],
         hours=("09:00", "21:00")),
    dict(key="vit_quay", name="Vịt quay – Heo quay", category="Món Việt",
         price=(60000, 200000),
         taste=dict(man=0.65, cay=0.20, ngot=0.40, beo=0.78),
         aliases=["vịt quay", "vit quay", "heo quay", "quay"],
         items=["Cơm vịt quay", "Heo quay bánh hỏi", "Mì vịt tiềm"],
         hours=("09:00", "21:00")),
    dict(key="banh_trang", name="Bánh tráng trộn – Ăn vặt", category="Ăn vặt",
         price=(15000, 45000),
         taste=dict(man=0.60, cay=0.65, ngot=0.40, beo=0.45),
         aliases=["bánh tráng", "banh trang", "bánh tráng trộn", "bánh tráng nướng", "ăn vặt"],
         items=["Bánh tráng trộn", "Bánh tráng nướng", "Bánh tráng cuốn bơ"],
         hours=("13:00", "22:30")),
    dict(key="xien_que", name="Xiên que – Viên chiên", category="Ăn vặt",
         price=(20000, 60000),
         taste=dict(man=0.58, cay=0.55, ngot=0.35, beo=0.72),
         aliases=["xiên que", "xien que", "viên chiên", "xiên bẩn", "cá viên chiên"],
         items=["Cá viên chiên", "Xúc xích nướng", "Bò viên chiên", "Khoai lắc"],
         hours=("14:00", "22:30")),

    # ---- Món quốc tế ----
    dict(key="ga_ran", name="Gà rán", category="Món Âu – Fast food",
         price=(45000, 150000),
         taste=dict(man=0.62, cay=0.40, ngot=0.35, beo=0.85),
         aliases=["gà rán", "ga ran", "fried chicken", "gà giòn"],
         items=["Combo gà rán", "Gà sốt cay", "Gà phô mai", "Burger gà"],
         hours=("09:00", "22:30")),
    dict(key="pizza", name="Pizza", category="Món Âu – Fast food",
         price=(90000, 350000),
         taste=dict(man=0.58, cay=0.25, ngot=0.30, beo=0.72),
         aliases=["pizza", "pizza ý"],
         items=["Pizza hải sản", "Pizza margherita", "Pizza bò BBQ"],
         hours=("10:00", "22:00")),
    dict(key="mi_y", name="Mì Ý – Món Âu", category="Món Âu – Fast food",
         price=(70000, 220000),
         taste=dict(man=0.50, cay=0.20, ngot=0.35, beo=0.60),
         aliases=["mì ý", "mi y", "pasta", "spaghetti", "món âu", "steak", "bít tết"],
         items=["Mì Ý sốt bò bằm", "Spaghetti carbonara", "Beefsteak sốt tiêu"],
         hours=("10:00", "22:00")),
    dict(key="burger", name="Burger", category="Món Âu – Fast food",
         price=(50000, 180000),
         taste=dict(man=0.60, cay=0.30, ngot=0.35, beo=0.80),
         aliases=["burger", "hamburger", "bơ gơ"],
         items=["Burger bò phô mai", "Burger gà giòn", "Khoai tây chiên"],
         hours=("09:00", "23:00")),
    dict(key="sushi", name="Sushi – Món Nhật", category="Món Á",
         price=(90000, 400000),
         taste=dict(man=0.42, cay=0.20, ngot=0.30, beo=0.35),
         aliases=["sushi", "sashimi", "món nhật", "nhật bản", "izakaya"],
         items=["Sushi cá hồi", "Sashimi thập cẩm", "Cơm cuộn California"],
         hours=("10:30", "22:00")),
    dict(key="ramen", name="Ramen – Mì Nhật", category="Món Á", price=(70000, 200000),
         taste=dict(man=0.70, cay=0.30, ngot=0.25, beo=0.62),
         aliases=["ramen", "mì nhật", "udon", "mì ramen"],
         items=["Ramen tonkotsu", "Ramen miso", "Udon bò"],
         hours=("10:30", "22:00")),
    dict(key="han_quoc", name="Món Hàn", category="Món Á", price=(70000, 250000),
         taste=dict(man=0.62, cay=0.70, ngot=0.40, beo=0.55),
         aliases=["món hàn", "hàn quốc", "tokbokki", "kimbap", "mì tương đen", "gà hàn quốc"],
         items=["Tokbokki phô mai", "Kimbap", "Mì tương đen", "Canh kimchi"],
         hours=("10:00", "22:00")),
    dict(key="dimsum", name="Dimsum – Món Hoa", category="Món Á",
         price=(50000, 200000),
         taste=dict(man=0.52, cay=0.20, ngot=0.35, beo=0.55),
         aliases=["dimsum", "há cảo", "ha cao", "xíu mại", "món hoa", "sủi cảo", "mì hoành thánh"],
         items=["Há cảo tôm", "Xíu mại", "Bánh bao xá xíu", "Mì hoành thánh"],
         hours=("07:00", "21:30")),
    dict(key="thai", name="Món Thái", category="Món Á", price=(70000, 250000),
         taste=dict(man=0.60, cay=0.75, ngot=0.45, beo=0.50),
         aliases=["món thái", "thái lan", "tom yum", "pad thai"],
         items=["Tom yum hải sản", "Pad Thai", "Gỏi xoài Thái", "Cà ri xanh"],
         hours=("10:00", "22:00")),

    # ---- Đồ uống / tráng miệng ----
    dict(key="tra_sua", name="Trà sữa", category="Đồ uống", price=(25000, 70000),
         taste=dict(man=0.10, cay=0.05, ngot=0.82, beo=0.45),
         aliases=["trà sữa", "tra sua", "milk tea", "trân châu"],
         items=["Trà sữa trân châu đường đen", "Hồng trà sữa", "Trà đào cam sả"],
         hours=("08:00", "22:30")),
    dict(key="ca_phe", name="Cà phê", category="Đồ uống", price=(20000, 80000),
         taste=dict(man=0.08, cay=0.03, ngot=0.55, beo=0.30),
         aliases=["cà phê", "ca phe", "cafe", "coffee", "quán cà phê", "cà phê muối"],
         items=["Cà phê sữa đá", "Bạc xỉu", "Cà phê muối", "Cold brew"],
         hours=("06:00", "22:30")),
    dict(key="che", name="Chè – Tráng miệng", category="Tráng miệng",
         price=(15000, 50000),
         taste=dict(man=0.05, cay=0.02, ngot=0.85, beo=0.35),
         aliases=["chè", "che", "tráng miệng", "sương sáo", "tàu hũ"],
         items=["Chè khúc bạch", "Chè thái", "Tàu hũ nước đường", "Chè bưởi"],
         hours=("10:00", "22:30")),
    dict(key="kem_banh", name="Kem – Bánh ngọt", category="Tráng miệng",
         price=(25000, 90000),
         taste=dict(man=0.08, cay=0.02, ngot=0.80, beo=0.60),
         aliases=["kem", "bánh ngọt", "tiệm bánh", "bakery", "bánh kem", "dessert"],
         items=["Kem gelato", "Bánh su kem", "Tiramisu", "Croissant"],
         hours=("09:00", "22:00")),
    dict(key="sinh_to", name="Sinh tố – Nước ép", category="Đồ uống",
         price=(20000, 60000),
         taste=dict(man=0.05, cay=0.02, ngot=0.65, beo=0.20),
         aliases=["sinh tố", "sinh to", "nước ép", "nuoc ep", "smoothie", "detox"],
         items=["Sinh tố bơ", "Nước ép cần tây", "Sinh tố dâu", "Nước ép cam"],
         hours=("07:00", "21:30")),
# ---- Đặc sản Quảng Ngãi ----
    dict(key="don", name="Don", category="Đặc sản Quảng Ngãi", price=(15000, 40000),
         taste=dict(man=0.45, cay=0.40, ngot=0.30, beo=0.22),
         aliases=["don", "cháo don", "chao don", "don quảng ngãi", "ốc don",
                  "canh don"],
         items=["Don nước bánh tráng", "Cháo don", "Don xúc bánh tráng",
                "Don trộn"],
         hours=("06:00", "21:00"), regions=["Quảng Ngãi"]),
    dict(key="ram_bap", name="Ram bắp", category="Đặc sản Quảng Ngãi",
         price=(20000, 55000),
         taste=dict(man=0.50, cay=0.35, ngot=0.40, beo=0.72),
         aliases=["ram bắp", "ram bap", "ram", "chả ram bắp"],
         items=["Ram bắp chấm mắm nêm", "Ram bắp cuốn rau sống", "Ram tôm đất"],
         hours=("09:00", "21:30"), regions=["Quảng Ngãi"]),
    dict(key="ca_bong", name="Cá bống sông Trà", category="Đặc sản Quảng Ngãi",
         price=(40000, 150000),
         taste=dict(man=0.72, cay=0.45, ngot=0.30, beo=0.40),
         aliases=["cá bống", "ca bong", "cá bống sông trà", "cá bống kho tiêu",
                  "cơm cá bống"],
         items=["Cá bống sông Trà kho tiêu", "Cơm cá bống", "Canh chua cá bống"],
         hours=("09:00", "21:00"), regions=["Quảng Ngãi"]),
    dict(key="ca_nuc", name="Cá nục cuốn bánh tráng", category="Đặc sản Quảng Ngãi",
         price=(35000, 90000),
         taste=dict(man=0.55, cay=0.45, ngot=0.25, beo=0.30),
         aliases=["cá nục", "ca nuc", "cá nục hấp", "cá nục cuốn bánh tráng",
                  "cuốn bánh tráng"],
         items=["Cá nục hấp cuốn bánh tráng", "Cá nục kho", "Gỏi cá trích"],
         hours=("09:00", "21:00"), regions=["Quảng Ngãi"]),
    dict(key="bun_ca", name="Bún cá – Bún chả cá", category="Bún – Phở",
         price=(25000, 60000),
         taste=dict(man=0.55, cay=0.48, ngot=0.32, beo=0.35),
         aliases=["bún cá", "bun ca", "bún chả cá", "bánh canh chả cá"],
         items=["Bún chả cá", "Bún cá ngừ", "Bún sứa"],
         hours=("05:30", "20:00")),
    dict(key="dac_san_qn", name="Đặc sản mang về", category="Đặc sản Quảng Ngãi",
         price=(25000, 200000),
         taste=dict(man=0.10, cay=0.05, ngot=0.80, beo=0.30),
         aliases=["đặc sản", "dac san", "kẹo gương", "mạch nha", "đường phèn",
                  "quà quảng ngãi", "mua về làm quà"],
         items=["Kẹo gương", "Mạch nha", "Đường phèn", "Cá bống sông Trà rim"],
         hours=("07:00", "21:00"), regions=["Quảng Ngãi"]),
]

# Món nào phổ biến ở vùng nào. Không khai báo = có mặt ở mọi vùng.
for _d in DISH_CATALOG:
    _d.setdefault("regions", None)


def dishes_for_region(region: str):
    return [d for d in DISH_CATALOG if d["regions"] is None or region in d["regions"]]


# ------------------------------------------------- tách nhóm ĐỒ ĂN / ĐỒ UỐNG
# Dùng để KHÔNG trộn gợi ý đồ ăn no bụng chung với đồ uống/tráng miệng trong
# cùng một danh sách khi người dùng không nêu rõ món cụ thể, hoặc để tách
# thành 2 khối riêng khi người dùng hỏi cả hai cùng lúc (vd "cơm gà và trà sữa").
DRINK_CATEGORIES = {"Đồ uống", "Tráng miệng"}

DISH_BY_KEY = {d["key"]: d for d in DISH_CATALOG}


def is_drink_dish(dish_key: str) -> bool:
    d = DISH_BY_KEY.get(dish_key)
    return bool(d) and d["category"] in DRINK_CATEGORIES


def is_drink_category(category: str) -> bool:
    return category in DRINK_CATEGORIES


FOOD_CATEGORIES = [c for c in sorted({d["category"] for d in DISH_CATALOG})
                   if c not in DRINK_CATEGORIES]

# Bảng tra cứu alias (đã bỏ dấu) -> dish key, sắp xếp alias dài trước để
# "bún bò huế" được ưu tiên hơn "bún"
ALIAS_INDEX = []
for _d in DISH_CATALOG:
    for _a in set(_d["aliases"] + [_d["name"]]):
        ALIAS_INDEX.append((strip_accents(_a), _d["key"]))
ALIAS_INDEX.sort(key=lambda x: -len(x[0]))


def find_dishes(text: str):
    """Tìm tất cả món ăn được nhắc tới trong câu (không phân biệt dấu)."""
    t = " " + strip_accents(text) + " "
    found, taken = [], []
    for alias, key in ALIAS_INDEX:
        if key in found:
            continue
        idx = t.find(" " + alias + " ")
        if idx == -1:
            # cho phép alias dính dấu câu
            if not re.search(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", t):
                continue
            idx = t.find(alias)
        if any(s <= idx < e for s, e in taken):
            continue
        taken.append((idx, idx + len(alias)))
        found.append(key)
    return found


CATEGORIES = sorted({d["category"] for d in DISH_CATALOG})
