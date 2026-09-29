# -*- coding: utf-8 -*-
"""
Bộ máy gợi ý (Recommender) — tổng hợp kết quả phân tích cảm xúc + khía cạnh
trên toàn bộ review để xếp hạng quán ăn theo:
  - Điểm hài lòng tổng thể (dựa trên tỉ lệ review tích cực)
  - Điểm từng khía cạnh: món ăn, giá cả, phục vụ, không gian, vệ sinh
  - Lọc theo khu vực (area) / loại món (cuisine)

Đây là phần "biến phân tích NLP thành tri thức có thể truy vấn được"
để chatbot sử dụng khi trả lời người dùng.
"""
import pandas as pd
from aspect_extraction import extract_aspects
from sentiment_model import rating_to_label


class RestaurantKnowledgeBase:
    def __init__(self, csv_path: str):
        self.df = pd.read_csv(csv_path, encoding="utf-8-sig")
        self._build_knowledge_base()

    def _build_knowledge_base(self):
        # Gán nhãn cảm xúc dựa trên rating (đóng vai trò nhãn "vàng" ground-truth
        # cho demo; trong thực tế đây chính là đầu ra của sentiment_model trên
        # review MỚI không có rating kèm theo, ví dụ review từ mạng xã hội).
        self.df["sentiment_label"] = self.df["rating"].apply(rating_to_label)

        # Trích xuất khía cạnh cho từng review
        aspect_rows = []
        for text in self.df["review_text"]:
            aspect_rows.append(extract_aspects(text))
        aspect_df = pd.DataFrame(aspect_rows).fillna(0)
        self.aspect_columns = list(aspect_df.columns)
        self.df = pd.concat([self.df.reset_index(drop=True),
                              aspect_df.reset_index(drop=True)], axis=1)

        # Tổng hợp theo quán
        agg_dict = {
            "rating": "mean",
            "review_id": "count",
        }
        summary = self.df.groupby(
            ["restaurant_id", "restaurant_name", "area", "cuisine"]
        ).agg(agg_dict).reset_index()
        summary = summary.rename(columns={"rating": "avg_rating",
                                           "review_id": "num_reviews"})

        # % review tích cực
        pos_ratio = (
            self.df.groupby("restaurant_id")["sentiment_label"]
            .apply(lambda s: (s == "tích_cực").mean())
            .reset_index(name="positive_ratio")
        )
        summary = summary.merge(pos_ratio, on="restaurant_id")

        # Điểm trung bình từng khía cạnh
        for col in self.aspect_columns:
            aspect_avg = self.df.groupby("restaurant_id")[col].mean().reset_index()
            aspect_avg = aspect_avg.rename(columns={col: f"aspect_{col}"})
            summary = summary.merge(aspect_avg, on="restaurant_id", how="left")

        summary = summary.fillna(0)
        self.summary = summary.sort_values("avg_rating", ascending=False).reset_index(drop=True)

    # ---------- API truy vấn dùng cho chatbot ----------

    def top_restaurants(self, n=5, area=None, cuisine=None):
        df = self.summary.copy()
        if area:
            df = df[df["area"].str.contains(area, case=False, na=False)]
        if cuisine:
            df = df[df["cuisine"].str.contains(cuisine, case=False, na=False)]
        return df.sort_values("avg_rating", ascending=False).head(n)

    def best_for_aspect(self, aspect: str, n=5, area=None, cuisine=None):
        col = f"aspect_{aspect}"
        if col not in self.summary.columns:
            return pd.DataFrame()
        df = self.summary.copy()
        if area:
            df = df[df["area"].str.contains(area, case=False, na=False)]
        if cuisine:
            df = df[df["cuisine"].str.contains(cuisine, case=False, na=False)]
        return df.sort_values(col, ascending=False).head(n)

    def restaurant_detail(self, name_query: str):
        df = self.summary[
            self.summary["restaurant_name"].str.contains(name_query, case=False, na=False)
        ]
        return df

    def sample_reviews(self, restaurant_id: str, sentiment: str = None, n=3):
        df = self.df[self.df["restaurant_id"] == restaurant_id]
        if sentiment:
            df = df[df["sentiment_label"] == sentiment]
        return df["review_text"].head(n).tolist()


    # ---------- Xuất tri thức NLP ra file để chatbot nạp nhanh ----------
    def export_stats(self, out_path: str):
        """
        Chắt lọc kết quả phân tích NLP của toàn bộ review thành 1 bảng nhỏ gọn
        theo từng quán (tỉ lệ review tích cực, điểm từng khía cạnh, câu review
        tiêu biểu). Chatbot chỉ cần nạp file này -> khởi động tức thì thay vì
        phân tích lại hàng nghìn review mỗi lần chạy.
        """
        cols = ["restaurant_id", "positive_ratio"] + \
               [f"aspect_{c}" for c in self.aspect_columns
                if f"aspect_{c}" in self.summary.columns]
        stats = self.summary[cols].copy()

        quotes_pos, quotes_neg = [], []
        for rid in stats["restaurant_id"]:
            p = self.sample_reviews(rid, "tích_cực", 1)
            n = self.sample_reviews(rid, "tiêu_cực", 1)
            quotes_pos.append(p[0] if p else None)
            quotes_neg.append(n[0] if n else None)
        stats["quote_pos"] = quotes_pos
        stats["quote_neg"] = quotes_neg

        stats.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"Đã xuất tri thức NLP của {len(stats):,} quán -> {out_path}")
        return stats

    def list_areas(self):
        return sorted(self.summary["area"].unique().tolist())

    def list_cuisines(self):
        return sorted(self.summary["cuisine"].unique().tolist())


if __name__ == "__main__":
    kb = RestaurantKnowledgeBase("../data/reviews.csv")
    print("=== Top 5 quán ăn tổng thể ===")
    print(kb.top_restaurants(5)[["restaurant_name", "area", "cuisine",
                                  "avg_rating", "positive_ratio"]])

    print("\n=== Top quán phục vụ tốt nhất ===")
    print(kb.best_for_aspect("phục_vụ", 3)[["restaurant_name", "aspect_phục_vụ"]])

    print("\n=== Khu vực có trong dữ liệu ===")
    print(kb.list_areas())
