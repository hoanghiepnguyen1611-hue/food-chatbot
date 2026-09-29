# -*- coding: utf-8 -*-
"""
Script tổng hợp: sinh dữ liệu mẫu (nếu chưa có) -> huấn luyện mô hình sentiment
-> lưu mô hình vào models/.

Chạy: python train.py
"""
import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SRC_DIR = os.path.join(BASE_DIR, "src")
MODELS_DIR = os.path.join(BASE_DIR, "models")
CSV_PATH = os.path.join(DATA_DIR, "reviews.csv")

sys.path.insert(0, SRC_DIR)


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)

    rest_path = os.path.join(DATA_DIR, "restaurants.csv")
    if not os.path.exists(rest_path):
        print("[1/6] Sinh cơ sở dữ liệu quán ăn...")
        subprocess.run([sys.executable, os.path.join(DATA_DIR, "generate_restaurants.py")],
                       cwd=DATA_DIR, check=True)
    else:
        print(f"[1/6] Đã có dữ liệu quán ăn: {rest_path}")

    if not os.path.exists(CSV_PATH):
        print("[2/6] Sinh dữ liệu đánh giá...")
        subprocess.run([sys.executable, os.path.join(DATA_DIR, "generate_sample_data.py")],
                       cwd=DATA_DIR, check=True)
    else:
        print(f"[2/6] Đã có dữ liệu đánh giá: {CSV_PATH}")

    print("\n[3/6] Sinh tập kiểm thử độc lập + ảnh minh hoạ món ăn...")
    subprocess.run([sys.executable, os.path.join(DATA_DIR, "generate_test_set.py")],
                   cwd=DATA_DIR, check=True)
    subprocess.run([sys.executable, os.path.join(DATA_DIR, "generate_dish_images.py")],
                   cwd=DATA_DIR, check=True)

    print("\n[4/6] Huấn luyện mô hình phân loại cảm xúc...")
    from sentiment_model import train  # import sau khi sys.path đã có SRC_DIR
    model_out = os.path.join(MODELS_DIR, "sentiment_model.joblib")
    train(CSV_PATH, model_out)

    print("\n[5/6] Đánh giá mô hình trên tập độc lập (Precision/Recall/F1)...")
    from evaluate import evaluate
    evaluate()

    # Chắt lọc kết quả phân tích NLP theo từng quán -> chatbot khởi động tức thì
    print("\n[6/6] Tổng hợp tri thức NLP theo từng quán...")
    from recommender import RestaurantKnowledgeBase
    kb = RestaurantKnowledgeBase(CSV_PATH)
    kb.export_stats(os.path.join(DATA_DIR, "review_stats.csv"))

    print("\nHoàn tất! Bạn có thể:")
    print("  - Chạy chatbot dòng lệnh:  python src/chatbot.py")
    print("  - Chạy giao diện web:      python app.py  (rồi mở http://localhost:5000)")


if __name__ == "__main__":
    main()
