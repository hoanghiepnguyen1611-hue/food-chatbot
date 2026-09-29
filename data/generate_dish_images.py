# -*- coding: utf-8 -*-
"""
SINH ẢNH MINH HOẠ MÓN ĂN, LƯU NGAY TRONG PROJECT.

Lý do: trước đây thẻ quán trỏ tới ảnh của một website bên ngoài. Khi site đó
chậm, chặn hotlink hoặc máy không có mạng thì thẻ quán trống trơn, nhìn rất
giống bản nháp. Nay mỗi nhóm món có một ảnh SVG riêng nằm trong
`static/img/dishes/`, luôn tải được, dung lượng ~1–2KB.

Thứ tự hiển thị ảnh trên thẻ quán:
    1. photo_url  — ảnh thật của quán, nếu bạn điền vào restaurants.csv
    2. image_url  — ảnh SVG theo nhóm món (file này sinh ra)
    3. ô màu + emoji + tên quán — chỉ khi cả hai đều lỗi

Chạy: python generate_dish_images.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from food_catalog import DISH_CATALOG  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "static", "img", "dishes")

# Mỗi nhóm món một cặp màu nền, chọn theo category để cùng nhóm thì cùng tông
PALETTE = {
    "Ăn sáng": ("#F7E6C4", "#E7C48B"),
    "Bún – Phở": ("#F3DFD2", "#D9A98C"),
    "Cơm": ("#F6E7C8", "#DDBF87"),
    "Chay – Healthy": ("#DEEDDB", "#A9CFA2"),
    "Lẩu – Nướng": ("#F2D9CE", "#D79C84"),
    "Ăn vặt": ("#FBE2D2", "#EDAE86"),
    "Món nước": ("#EFE1CF", "#CDAE86"),
    "Món Việt": ("#EAE6CF", "#C3BC8C"),
    "Món Âu – Fast food": ("#F8E3CB", "#E4B37E"),
    "Món Á": ("#E4E6EF", "#AEB4CC"),
    "Đồ uống": ("#E6EAE2", "#B3C0AE"),
    "Tráng miệng": ("#F6E1E6", "#DCA9B6"),
    "Đặc sản Quảng Ngãi": ("#DDEAE8", "#9FC2BD"),
}
DEFAULT = ("#EDE8DE", "#C3BAA8")

EMOJI = {
    "xoi": "🍚", "banh_mi": "🥖", "banh_cuon": "🥟", "chao": "🥣", "banh_bao": "🥟",
    "pho": "🍜", "bun_bo": "🍜", "bun_cha": "🍢", "bun_rieu": "🦀",
    "bun_thit_nuong": "🍖", "bun_dau": "🍢", "hu_tieu": "🍜", "mi_quang": "🍜",
    "banh_canh": "🍲", "mi_cay": "🌶️", "com_tam": "🍛", "com_ga": "🍗",
    "com_van_phong": "🍱", "com_nieu": "🍚", "com_chien": "🍚", "com_chay": "🥬",
    "salad": "🥗", "lau": "🍲", "nuong": "🍖", "oc": "🦐", "bo_kho": "🍲",
    "pha_lau": "🍲", "banh_xeo": "🥞", "goi_cuon": "🌯", "banh_beo": "🍥",
    "vit_quay": "🦆", "banh_trang": "🥠", "xien_que": "🍡", "ga_ran": "🍗",
    "pizza": "🍕", "mi_y": "🍝", "burger": "🍔", "sushi": "🍣", "ramen": "🍜",
    "han_quoc": "🍲", "dimsum": "🥟", "thai": "🍤", "tra_sua": "🧋",
    "ca_phe": "☕", "che": "🍧", "kem_banh": "🍰", "sinh_to": "🥤",
    "don": "🐚", "ram_bap": "🌽", "ca_bong": "🐟", "ca_nuc": "🐠",
    "bun_ca": "🐟", "dac_san_qn": "🎁",
}

TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 320" \
width="480" height="320" role="img" aria-label="{alt}">
  <title>{alt}</title>
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
    <pattern id="p" width="56" height="56" patternUnits="userSpaceOnUse">
      <circle cx="14" cy="14" r="2.4" fill="#ffffff" opacity=".40"/>
      <circle cx="42" cy="42" r="1.6" fill="#1b2b24" opacity=".08"/>
    </pattern>
  </defs>
  <rect width="480" height="320" fill="url(#g)"/>
  <rect width="480" height="320" fill="url(#p)"/>
  <circle cx="240" cy="142" r="86" fill="#ffffff" opacity=".55"/>
  <circle cx="240" cy="142" r="86" fill="none" stroke="#1b2b24" stroke-opacity=".10" \
stroke-width="2"/>
  <text x="240" y="142" font-size="88" text-anchor="middle" dominant-baseline="central"\
>{emoji}</text>
  <rect x="0" y="252" width="480" height="68" fill="#16241E" opacity=".80"/>
  <text x="28" y="288" fill="#F6F8F4" font-size="28" font-weight="700"
        font-family="'Be Vietnam Pro',system-ui,'Segoe UI',sans-serif">{name}</text>
  <text x="452" y="288" fill="#F6F8F4" opacity=".70" font-size="16" text-anchor="end"
        font-family="'Be Vietnam Pro',system-ui,'Segoe UI',sans-serif">{category}</text>
</svg>
"""


def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    total = 0
    for d in DISH_CATALOG:
        c1, c2 = PALETTE.get(d["category"], DEFAULT)
        svg = TEMPLATE.format(
            alt=esc(f"Ảnh minh hoạ món {d['name']}"),
            c1=c1, c2=c2,
            emoji=EMOJI.get(d["key"], "🍽️"),
            name=esc(d["name"]),
            category=esc(d["category"]),
        )
        with open(os.path.join(OUT_DIR, f"{d['key']}.svg"), "w", encoding="utf-8") as f:
            f.write(svg)
        total += 1
    print(f"Đã sinh {total} ảnh minh hoạ -> static/img/dishes/")


if __name__ == "__main__":
    main()
