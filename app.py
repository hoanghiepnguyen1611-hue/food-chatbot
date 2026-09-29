# -*- coding: utf-8 -*-
"""
Máy chủ web cho Chatbot tư vấn ẩm thực.

    python app.py      ->  http://localhost:5000

API:
    POST /api/chat          {message, location:[lat,lng]}  -> {reply, understood, cards, ...}
    GET  /api/restaurant/<id>                              -> chi tiết 1 quán
    GET  /api/stats                                        -> thống kê dữ liệu
    GET  /api/locate?lat=..&lng=..                         -> định vị ngược (quận/phường gần nhất)
"""
import os
import sys

from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

from chatbot import FoodChatbot  # noqa: E402
from geo import nearest_district  # noqa: E402

DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_PATH = os.path.join(BASE_DIR, "models", "sentiment_model.joblib")

app = Flask(__name__, template_folder="templates")
bot = FoodChatbot(DATA_DIR, MODEL_PATH)


def _parse_location(loc):
    if isinstance(loc, (list, tuple)) and len(loc) == 2:
        try:
            return (float(loc[0]), float(loc[1]))
        except (TypeError, ValueError):
            return None
    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/chat")
def api_chat():
    data = request.get_json(force=True, silent=True) or {}
    message = (data.get("message") or "").strip()
    user_location = _parse_location(data.get("location"))
    result = bot.respond(message, user_location=user_location)
    # Kèm theo tên khu vực gần nhất khi có vị trí GPS, để giao diện hiển thị
    # "📍 Gần ..." mà không cần gọi thêm request riêng.
    if user_location:
        area, dist_km = nearest_district(*user_location)
        if area:
            result["user_area"] = area
            result["user_area_distance_km"] = round(dist_km, 2)
    return jsonify(result)


@app.get("/api/locate")
def api_locate():
    """Định vị ngược: từ toạ độ GPS suy ra quận/phường gần nhất, để hiển thị
    ngay khi người dùng vừa bật định vị (trước khi họ gõ tin nhắn nào)."""
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    if lat is None or lng is None:
        return jsonify({"error": "Thiếu toạ độ lat/lng"}), 400
    area, dist_km = nearest_district(lat, lng)
    return jsonify({"area": area, "distance_km": round(dist_km, 2) if dist_km is not None else None})


@app.get("/api/restaurant/<rid>")
def api_restaurant(rid):
    from datetime import datetime
    row = bot.db.get(rid)
    if row is None:
        return jsonify({"error": "Không tìm thấy quán"}), 404
    now = datetime.now()
    return jsonify(bot.db.to_card(row, None, 1.0, [], [], None,
                                  now.hour * 60 + now.minute))


@app.get("/api/stats")
def api_stats():
    df = bot.db.df
    return jsonify({
        "restaurants": int(len(df)),
        "dishes": int(df["dish_name"].nunique()),
        "districts": int(df["district"].nunique()),
        "avg_rating": round(float(df["rating"].mean()), 2),
    })


if __name__ == "__main__":
    print(f"Đã nạp {len(bot.db):,} quán ăn. Mở http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
