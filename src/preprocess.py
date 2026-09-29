# -*- coding: utf-8 -*-
"""
Tiền xử lý văn bản tiếng Việt cho bài toán phân tích đánh giá ẩm thực.

Ghi chú kỹ thuật:
- Bản demo này dùng tokenizer dựa trên regex (không phụ thuộc thư viện ngoài,
  chạy được offline). Khi triển khai thực tế, nên thay bằng các thư viện
  NLP tiếng Việt chuyên dụng để tách từ ghép chính xác hơn, ví dụ:
    + underthesea (word_tokenize, pos_tag)
    + pyvi (ViTokenizer)
    + VnCoreNLP
  và có thể dùng embedding PhoBERT (VinAI) thay cho TF-IDF để tăng độ chính xác.
"""
import re
import unicodedata

# Danh sách stopword tiếng Việt rút gọn (mở rộng thêm tùy nhu cầu thực tế)
VIETNAMESE_STOPWORDS = set("""
là và có của cho ở tại rất khá thì mà nên đã đang sẽ
này kia đó các những một hai ba bị được ra vào
với như từ để trên dưới trong ngoài
tôi bạn chúng_tôi mình nó họ
nhưng nếu vì bởi_vì do
a_b khi lúc luôn cũng
""".split())

# Từ ghép quan trọng cần giữ nguyên (ghép bằng "_") để không bị tách nhầm,
# giúp mô hình học đúng ngữ nghĩa của cụm từ 2-3 âm tiết phổ biến trong ẩm thực.
COMMON_PHRASES = [
    "nhân viên", "phục vụ", "không gian", "món ăn", "đồ ăn", "giá cả",
    "chất lượng", "nước dùng", "nguyên liệu", "vệ sinh", "chỗ ngồi",
    "thái độ", "khẩu phần", "trình bày",
]


def normalize_text(text: str) -> str:
    """Chuẩn hóa unicode, chữ thường, loại ký tự thừa."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = re.sub(r"[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễ"
                  r"ìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def merge_common_phrases(text: str) -> str:
    """Ghép các cụm từ phổ biến thành 1 token bằng dấu gạch dưới."""
    for phrase in COMMON_PHRASES:
        text = text.replace(phrase, phrase.replace(" ", "_"))
    return text


def tokenize(text: str, remove_stopwords: bool = True):
    """Tách từ đơn giản theo khoảng trắng sau khi đã ghép cụm từ phổ biến."""
    text = normalize_text(text)
    text = merge_common_phrases(text)
    tokens = text.split()
    if remove_stopwords:
        tokens = [t for t in tokens if t not in VIETNAMESE_STOPWORDS and len(t) > 1]
    return tokens


def preprocess_for_vectorizer(text: str) -> str:
    """Trả về chuỗi đã xử lý, sẵn sàng đưa vào TfidfVectorizer."""
    return " ".join(tokenize(text))


if __name__ == "__main__":
    sample = "Món ăn rất ngon, nhân viên phục vụ nhiệt tình nhưng giá hơi đắt."
    print("Gốc :", sample)
    print("Xử lý:", preprocess_for_vectorizer(sample))
