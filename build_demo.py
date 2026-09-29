# -*- coding: utf-8 -*-
"""
Đóng gói một bản DEMO TĨNH: nhúng dữ liệu quán ăn + bộ máy tìm kiếm rút gọn
(viết bằng JavaScript) vào một file HTML duy nhất, chạy được offline, không
cần máy chủ — tiện để gửi cho người khác xem hoặc mở trên điện thoại.

Bản chạy thật (python app.py) vẫn dùng toàn bộ mã Python ở thư mục src/.

Chạy: python build_demo.py   ->   demo.html
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "src"))

import pandas as pd  # noqa: E402
from food_catalog import DISH_CATALOG  # noqa: E402
from geo import CITY_OF, DISTRICTS  # noqa: E402

FIELDS = ["restaurant_id", "name", "city", "dish_key", "dish_name", "category", "address",
          "district", "lat", "lng", "price_min", "price_max", "rating",
          "num_reviews", "taste_man", "taste_cay", "taste_ngot", "taste_beo",
          "taste_tags", "adjustable", "open_time", "close_time", "menu",
          "utilities", "is_veg", "phone", "emoji", "photo_url"]


def main():
    df = pd.read_csv(os.path.join(BASE, "data", "restaurants.csv"), encoding="utf-8-sig")
    df["adjustable"] = df["adjustable"].fillna("")
    records = df[FIELDS].to_dict("records")
    for r in records:
        r["lat"] = round(float(r["lat"]), 5)
        r["lng"] = round(float(r["lng"]), 5)
        for k in ("taste_man", "taste_cay", "taste_ngot", "taste_beo"):
            r[k] = round(float(r[k]), 2)
        r["photo_url"] = r.get("photo_url") or ""
        # bản demo nhúng thẳng ảnh SVG (dạng data URI) nên mở offline vẫn có ảnh
        r["image_url"] = ""

    # nhúng ảnh SVG của từng nhóm món, dùng chung cho mọi quán cùng món
    img_dir = os.path.join(BASE, "static", "img", "dishes")
    images = {}
    if os.path.isdir(img_dir):
        for fn in os.listdir(img_dir):
            if fn.endswith(".svg"):
                images[fn[:-4]] = open(os.path.join(img_dir, fn), encoding="utf-8").read()

    payload = {
        "restaurants": records,
        "images": images,
        "dishes": [{"key": d["key"], "name": d["name"], "aliases": d["aliases"]}
                   for d in DISH_CATALOG],
        "districts": [{"name": n, "city": CITY_OF.get(n, "TP.HCM"),
                       "aliases": DISTRICTS[n].get("aliases", [])} for n in DISTRICTS],
    }

    html = open(os.path.join(BASE, "templates", "index.html"), encoding="utf-8").read()
    html = html.replace(
        "const EMBEDDED = null; /*__EMBEDDED_DATA__*/",
        "const EMBEDDED = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";")

    out = os.path.join(BASE, "demo.html")
    open(out, "w", encoding="utf-8").write(html)
    print(f"Đã tạo {out} ({os.path.getsize(out)/1024/1024:.2f} MB, "
          f"{len(records):,} quán nhúng sẵn)")


if __name__ == "__main__":
    main()
