# -*- coding: utf-8 -*-
"""
SINH TẬP KIỂM THỬ ĐỘC LẬP cho mô hình phân loại cảm xúc.

Vì sao cần file này: `reviews.csv` được sinh từ một bộ khuôn mẫu câu cố định.
Nếu chia train/test ngay trên tập đó thì hai phần gần như trùng phân phối, mô
hình chỉ cần "nhớ" khuôn mẫu là đạt độ chính xác rất cao — con số đó KHÔNG nói
lên khả năng tổng quát hóa.

File này tạo ra hai tập kiểm thử KHÔNG dùng khi huấn luyện:

  1. reviews_test.csv    — sinh tự động nhưng bằng BỘ TỪ VỰNG VÀ CẤU TRÚC CÂU
                            KHÁC hẳn tập huấn luyện, có thêm 4 kiểu nhiễu thực
                            tế: phủ định, khen-chê lẫn lộn, viết không dấu /
                            teencode, và câu rất ngắn.
  2. reviews_manual.csv  — các câu do người viết tay và tự gán nhãn, mô phỏng
                            văn phong người dùng thật. Đây là tập gần "thật"
                            nhất hiện có; khi làm khóa luận nên mở rộng tập này
                            bằng review thu thập thật rồi gán nhãn thủ công.

Nhãn được GÁN TRỰC TIẾP khi sinh câu (không suy ra từ số sao), nên đây là nhãn
tham chiếu độc lập với quy tắc `rating_to_label` dùng lúc huấn luyện.

Chạy: python generate_test_set.py
"""
import csv
import os
import random
import unicodedata

random.seed(20260917)
BASE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Bộ từ vựng KHÁC tập huấn luyện: cùng ý nghĩa nhưng diễn đạt kiểu khác
# ---------------------------------------------------------------------------
POS = [
    "ăn xong còn muốn gọi thêm phần nữa",
    "chất lượng vượt mong đợi của mình",
    "ngồi cả buổi mà vẫn thấy thoải mái",
    "đồ ăn ra nhanh, nóng hổi",
    "chủ quán nhớ mặt khách, chào hỏi thân tình",
    "tô đầy đặn, ăn no căng bụng",
    "nước chấm pha khéo, điểm cộng lớn",
    "lần thứ ba mình quay lại và vẫn ổn",
    "bạn bè mình ai ăn cũng gật gù",
    "đáng để chạy xe xa một chút",
    "rau sống tươi rói, sạch sẽ",
    "giá này mà được chừng này thì quá hời",
]
NEG = [
    "đợi gần bốn mươi phút mới có đồ ăn",
    "gọi mãi không ai ra ghi món",
    "thịt dai nhách, nhai không nổi",
    "bàn còn dính dầu mỡ của khách trước",
    "tính tiền cao hơn giá niêm yết trên menu",
    "ăn xong về bụng khó chịu cả tối",
    "phần ăn teo tóp so với ảnh quảng cáo",
    "nhân viên vừa nghe điện thoại vừa bưng bê",
    "lần trước còn được, lần này xuống dốc hẳn",
    "mùi dầu chiên đi chiên lại rất gắt",
    "chỗ để xe không có, phải gửi xa",
    "thất vọng, chắc không quay lại nữa",
]
NEU = [
    "ăn được, không có gì để chê mà cũng không có gì nổi bật",
    "tạm ổn cho một bữa trưa vội",
    "bình thường như bao quán khác trong khu",
    "được cái tiện đường, còn lại thì trung bình",
    "không dở nhưng cũng chưa tới mức muốn giới thiệu",
    "mức giá và chất lượng coi như hòa",
]

# Phủ định — chỗ mô hình dựa trên túi từ hay sai nhất
NEGATION_NEG = [
    "không ngon như lời đồn",
    "chẳng có gì đặc sắc cả",
    "không đáng đồng tiền chút nào",
    "nói thật là không hợp khẩu vị mình",
    "chưa bao giờ thấy quán nào phục vụ chậm như vậy",
    "không hiểu sao nhiều người khen",
]
NEGATION_POS = [
    "không chê vào đâu được",
    "không hề bị ngán dù ăn hết tô",
    "chẳng phải chờ lâu như mình lo",
    "không đắt như mình tưởng ban đầu",
    "không có gì để phàn nàn",
]

# Khen chê lẫn lộn -> nhãn trung tính
MIXED = [
    ("đồ ăn khá ngon", "nhưng phục vụ thì chậm"),
    ("quán sạch sẽ mát mẻ", "tiếc là giá hơi chát"),
    ("nhân viên dễ thương", "món thì chỉ ở mức tạm"),
    ("giá mềm", "bù lại chỗ ngồi hơi chật"),
    ("vị ổn", "mà lần này nêm hơi tay"),
]

SHORT_POS = ["ngon", "ok nha", "quá ổn", "10 điểm", "sẽ quay lại", "ưng"]
SHORT_NEG = ["dở", "tệ", "một sao", "không ưng", "chán", "khỏi quay lại"]
SHORT_NEU = ["cũng được", "tạm", "bình thường", "so so", "trung bình"]


def strip_accents(t):
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn").replace("đ", "d")


TEENCODE = {"không": "ko", "được": "dc", "rất": "rat", "quá": "wa", "mình": "mk",
            "nhưng": "nhg", "với": "vs", "nhiều": "nhìu", "gì": "j"}


def to_teencode(t):
    for k, v in TEENCODE.items():
        t = t.replace(k, v)
    return t


def add_typos(t, n=2):
    chars = list(t)
    for _ in range(n):
        if len(chars) < 6:
            break
        i = random.randrange(1, len(chars) - 1)
        op = random.random()
        if op < 0.4:
            chars[i] = chars[i - 1]           # gõ lặp ký tự
        elif op < 0.7:
            del chars[i]                      # thiếu ký tự
        else:
            chars[i], chars[i - 1] = chars[i - 1], chars[i]   # đảo ký tự
    return "".join(chars)


def build():
    rows = []

    def add(text, label, style):
        rows.append({"review_text": text.strip(), "label": label, "style": style})

    # 1. câu thường, từ vựng mới
    for _ in range(320):
        label = random.choices(["tích_cực", "tiêu_cực", "trung_tính"],
                               weights=[5, 3, 2])[0]
        pool = {"tích_cực": POS, "tiêu_cực": NEG, "trung_tính": NEU}[label]
        n = random.randint(1, 2)
        add(". ".join(random.sample(pool, n)).capitalize() + ".", label, "chuẩn")

    # 2. phủ định
    for _ in range(120):
        if random.random() < 0.55:
            add(random.choice(NEGATION_NEG).capitalize() + ".", "tiêu_cực", "phủ định")
        else:
            add(random.choice(NEGATION_POS).capitalize() + ".", "tích_cực", "phủ định")

    # 3. khen chê lẫn lộn
    for _ in range(90):
        a, b = random.choice(MIXED)
        add(f"{a.capitalize()}, {b}.", "trung_tính", "lẫn lộn")

    # 4. không dấu / teencode
    for _ in range(110):
        label = random.choice(["tích_cực", "tiêu_cực", "trung_tính"])
        pool = {"tích_cực": POS, "tiêu_cực": NEG, "trung_tính": NEU}[label]
        t = random.choice(pool)
        t = strip_accents(t) if random.random() < 0.5 else to_teencode(t)
        add(t, label, "không dấu/teencode")

    # 5. câu rất ngắn
    for _ in range(80):
        label = random.choice(["tích_cực", "tiêu_cực", "trung_tính"])
        pool = {"tích_cực": SHORT_POS, "tiêu_cực": SHORT_NEG,
                "trung_tính": SHORT_NEU}[label]
        add(random.choice(pool), label, "câu ngắn")

    # 6. lỗi chính tả
    for _ in range(80):
        label = random.choices(["tích_cực", "tiêu_cực", "trung_tính"],
                               weights=[4, 3, 2])[0]
        pool = {"tích_cực": POS, "tiêu_cực": NEG, "trung_tính": NEU}[label]
        add(add_typos(random.choice(pool)), label, "sai chính tả")

    return rows


# ---------------------------------------------------------------------------
# Tập viết tay: câu do người soạn, gán nhãn thủ công
# ---------------------------------------------------------------------------
MANUAL = [
    ("Quán nhỏ nằm trong hẻm nhưng đồ ăn làm rất có tâm, mình ăn hết sạch.", "tích_cực"),
    ("Mình đặt giao hàng, tới nơi đồ nguội ngắt và bị đổ nước lèo.", "tiêu_cực"),
    ("Hôm nay đông khách nên chờ hơi lâu, nhưng ăn thì vẫn ngon như mọi khi.", "tích_cực"),
    ("Ăn cũng được thôi, mình không thấy đặc biệt như review trên mạng.", "trung_tính"),
    ("Giá rẻ bất ngờ mà phần ăn thì đầy ụ, sinh viên nên ghé.", "tích_cực"),
    ("Không gian ọp ẹp, bàn ghế lung lay, ngồi ăn không yên tâm lắm.", "tiêu_cực"),
    ("Nêm hơi mặn với mình nhưng chồng mình lại thấy vừa.", "trung_tính"),
    ("Chủ quán dễ thương, mình xin thêm rau còn được cho thoải mái.", "tích_cực"),
    ("Đọc menu một đằng, tính tiền một nẻo, rất khó chịu.", "tiêu_cực"),
    ("Lần đầu tới, chắc phải ăn thêm vài lần nữa mới dám nhận xét.", "trung_tính"),
    ("Đồ ăn ngon nhưng ruồi nhiều quá, mình mất hứng hẳn.", "trung_tính"),
    ("Nước dùng ngọt tự nhiên chứ không phải ngọt bột ngọt, mình thích.", "tích_cực"),
    ("Gọi ba lần nhân viên mới mang nước ra, thái độ lại còn cau có.", "tiêu_cực"),
    ("Ổn trong tầm giá, không xuất sắc nhưng cũng chẳng có gì chê.", "trung_tính"),
    ("Ăn xong bị đau bụng, mình nghĩ đồ để lâu rồi.", "tiêu_cực"),
    ("Quán mở khuya nên đi làm về trễ vẫn có chỗ ăn, rất tiện.", "tích_cực"),
    ("Mình dặn ít cay mà bê ra vẫn cay xé lưỡi, chắc quên.", "tiêu_cực"),
    ("Nhìn thì bình thường thôi nhưng ăn vào mới thấy đáng tiền.", "tích_cực"),
    ("Đồ ăn tàm tạm, được cái chỗ để xe rộng.", "trung_tính"),
    ("Không bao giờ quay lại, phục vụ như ban ơn cho khách.", "tiêu_cực"),
    ("Ko ngon lắm nhưng dc cái rẻ.", "trung_tính"),
    ("Quan nay an ok, gia hop ly, se quay lai.", "tích_cực"),
    ("Chờ 45 phút cho một tô bún, hết chịu nổi.", "tiêu_cực"),
    ("Ngon xuất sắc luôn, nhất là phần nước chấm.", "tích_cực"),
    ("Cũng bình thường à, mình nghĩ do kỳ vọng cao quá.", "trung_tính"),
    ("Thịt hôi, mình ăn được hai miếng rồi bỏ.", "tiêu_cực"),
    ("Chỗ này hợp dẫn gia đình đi, món vừa miệng cả người lớn lẫn trẻ con.", "tích_cực"),
    ("Menu nhiều món nhưng hỏi món nào cũng hết.", "tiêu_cực"),
    ("Mình thấy ổn, không có gì để nói thêm.", "trung_tính"),
    ("Quán này đúng gu mình, vị đậm đà mà không bị gắt.", "tích_cực"),
]


def main():
    rows = build()
    out = os.path.join(BASE, "reviews_test.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["review_text", "label", "style"])
        w.writeheader()
        w.writerows(rows)

    out2 = os.path.join(BASE, "reviews_manual.csv")
    with open(out2, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["review_text", "label", "style"])
        w.writeheader()
        for text, label in MANUAL:
            w.writerow({"review_text": text, "label": label, "style": "viết tay"})

    from collections import Counter
    print(f"reviews_test.csv   : {len(rows):,} câu — {dict(Counter(r['label'] for r in rows))}")
    print(f"reviews_manual.csv : {len(MANUAL)} câu viết tay, gán nhãn thủ công")


if __name__ == "__main__":
    main()
