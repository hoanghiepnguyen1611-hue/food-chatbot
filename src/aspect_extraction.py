# -*- coding: utf-8 -*-
"""
Trích xuất khía cạnh (Aspect-Based Sentiment Analysis - ABSA) mức đơn giản.

Cách tiếp cận: dựa trên từ điển từ khóa (lexicon-based) để xác định câu/đoạn
review đang nói về khía cạnh nào (món ăn, giá cả, phục vụ, không gian, vệ sinh),
kết hợp với từ điển cảm xúc (sentiment lexicon) để chấm điểm cực tính (+1/-1)
cho từng khía cạnh trong câu đó.

Đây là baseline dễ giải thích (explainable), phù hợp demo/báo cáo khóa luận.
Hướng nâng cấp trong thực tế: huấn luyện mô hình ABSA end-to-end (ví dụ
fine-tune PhoBERT cho multi-label aspect classification + sentiment
classification per aspect) khi có đủ dữ liệu gán nhãn.
"""
import re
from preprocess import normalize_text

ASPECT_KEYWORDS = {
    "món_ăn": ["món ăn", "đồ ăn", "hương vị", "nước dùng", "nguyên liệu",
               "khẩu vị", "thức ăn", "món", "vị"],
    "giá_cả": ["giá cả", "giá", "tiền", "khẩu phần", "phụ thu", "đắt", "rẻ"],
    "phục_vụ": ["nhân viên", "phục vụ", "thái độ", "order", "chủ quán"],
    "không_gian": ["không gian", "chỗ ngồi", "bàn ghế", "view", "trang trí",
                   "máy lạnh", "quán"],
    "vệ_sinh": ["vệ sinh", "sạch sẽ", "bẩn", "ruồi", "bếp"],
}

POSITIVE_WORDS = [
    "ngon", "tốt", "tuyệt", "hài lòng", "thích", "nhanh", "nhiệt tình",
    "thân thiện", "sạch sẽ", "hợp lý", "đẹp", "thoáng mát", "chu đáo",
    "xứng đáng", "tươi", "đậm đà", "ghiền", "dễ thương", "yên tĩnh",
]
NEGATIVE_WORDS = [
    "dở", "tệ", "chậm", "khó chịu", "nhạt", "mặn", "đắt", "bẩn", "ồn ào",
    "chật chội", "lâu", "thiếu", "mất ngon", "không tươi", "khó ăn",
    "vô lý", "ít", "bí", "quên",
]


def split_sentences(text: str):
    text = text.strip()
    parts = re.split(r"[.!?;]\s*", text)
    return [p for p in parts if p]


def score_sentiment_words(sentence_norm: str) -> int:
    score = 0
    for w in POSITIVE_WORDS:
        if w in sentence_norm:
            score += 1
    for w in NEGATIVE_WORDS:
        if w in sentence_norm:
            score -= 1
    return score


def extract_aspects(text: str) -> dict:
    """
    Trả về dict {aspect: polarity_score} cho 1 đoạn review.
    polarity_score > 0: tích cực, < 0: tiêu cực, không xuất hiện: bỏ qua.
    """
    result = {}
    for sentence in split_sentences(text):
        norm = normalize_text(sentence)
        matched_aspects = []
        for aspect, keywords in ASPECT_KEYWORDS.items():
            if any(kw in norm for kw in keywords):
                matched_aspects.append(aspect)
        if not matched_aspects:
            continue
        sent_score = score_sentiment_words(norm)
        if sent_score == 0:
            continue
        for aspect in matched_aspects:
            result[aspect] = result.get(aspect, 0) + sent_score
    return result


if __name__ == "__main__":
    sample = ("Món ăn rất ngon, đậm đà. Nhân viên phục vụ chậm chạp, thái độ "
               "khó chịu. Giá cả hợp lý. Không gian hơi ồn ào.")
    print(extract_aspects(sample))
