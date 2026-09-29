# -*- coding: utf-8 -*-
"""
Mô hình phân loại cảm xúc (Sentiment Analysis) cho review ẩm thực.

Pipeline: TF-IDF (unigram + bigram) -> Logistic Regression (3 lớp: 
tích cực / trung tính / tiêu cực), suy ra từ rating gốc (>=4: tích cực,
==3: trung tính, <=2: tiêu cực).

Đây là baseline machine learning cổ điển — nhẹ, nhanh, dễ giải thích,
không cần GPU, phù hợp môi trường không có internet để tải mô hình
pretrained. Khi có điều kiện triển khai production và có GPU, nên
thay bằng fine-tune mô hình ngôn ngữ tiếng Việt (PhoBERT, ViSoBERT...)
để tăng độ chính xác, đặc biệt với câu có phủ định/mỉa mai phức tạp.
"""
import sys
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline

from preprocess import preprocess_for_vectorizer

LABEL_MAP = {"tích_cực": 2, "trung_tính": 1, "tiêu_cực": 0}
LABEL_MAP_INV = {v: k for k, v in LABEL_MAP.items()}


def rating_to_label(rating: int) -> str:
    if rating >= 4:
        return "tích_cực"
    elif rating == 3:
        return "trung_tính"
    else:
        return "tiêu_cực"


def build_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            preprocessor=preprocess_for_vectorizer,
            ngram_range=(1, 2),
            min_df=2,
            max_features=5000,
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            C=2.0,
        )),
    ])


def train(csv_path: str, model_out: str = "../models/sentiment_model.joblib"):
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["label"] = df["rating"].apply(rating_to_label)

    X = df["review_text"]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, zero_division=0, digits=3)

    print(f"[Hold-out cùng phân phối] Accuracy = {acc:.3f}")
    print(report)
    print("LƯU Ý: đây là tập tách ra từ chính dữ liệu sinh tự động nên CÙNG PHÂN")
    print("PHỐI với tập huấn luyện. Con số này KHÔNG phản ánh khả năng tổng quát")
    print("hóa và không nên dùng để kết luận mô hình tốt. Hãy xem kết quả trên")
    print("tập kiểm thử độc lập: python src/evaluate.py")

    joblib.dump(pipeline, model_out)
    print(f"Đã lưu mô hình vào: {model_out}")
    return pipeline, acc


class SentimentAnalyzer:
    """Wrapper tiện dụng để chatbot gọi dự đoán cảm xúc cho 1 câu review mới."""

    def __init__(self, model_path: str = "../models/sentiment_model.joblib"):
        self.pipeline = joblib.load(model_path)

    def predict(self, text: str) -> dict:
        label = self.pipeline.predict([text])[0]
        proba = self.pipeline.predict_proba([text])[0]
        classes = self.pipeline.classes_
        proba_dict = {c: round(float(p), 3) for c, p in zip(classes, proba)}
        return {"label": label, "probabilities": proba_dict}


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "../data/reviews.csv"
    train(csv_path)
