# -*- coding: utf-8 -*-
"""
ĐÁNH GIÁ MÔ HÌNH PHÂN LOẠI CẢM XÚC — báo cáo đầy đủ, không chỉ Accuracy.

Script chạy mô hình đã huấn luyện trên BA tập khác nhau để thấy rõ khoảng cách
giữa "thuộc bài" và "hiểu bài":

  A. Hold-out cùng phân phối  — 20% tách từ reviews.csv. Con số ở đây CAO là
     chuyện đương nhiên vì cùng khuôn mẫu sinh dữ liệu, KHÔNG dùng để kết luận
     mô hình tốt.
  B. Tập kiểm thử độc lập     — reviews_test.csv: từ vựng và cấu trúc câu khác
     hẳn, có phủ định, khen-chê lẫn lộn, viết không dấu, sai chính tả.
  C. Tập viết tay             — reviews_manual.csv: câu người viết, gán nhãn
     thủ công. Gần văn phong thật nhất.

Kết quả ghi ra `models/evaluation_report.md` để đưa thẳng vào báo cáo.

Chạy: python src/evaluate.py
"""
import os
import sys

import joblib
import pandas as pd
from sklearn.metrics import (classification_report, confusion_matrix,
                             precision_recall_fscore_support)
from sklearn.model_selection import train_test_split

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "src"))

from sentiment_model import rating_to_label  # noqa: E402

LABELS = ["tiêu_cực", "trung_tính", "tích_cực"]


def _metrics(y_true, y_pred):
    p, r, f, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=LABELS, zero_division=0)
    macro = precision_recall_fscore_support(
        y_true, y_pred, labels=LABELS, average="macro", zero_division=0)
    weighted = precision_recall_fscore_support(
        y_true, y_pred, labels=LABELS, average="weighted", zero_division=0)
    acc = (pd.Series(y_true).values == pd.Series(y_pred).values).mean()
    return dict(per_class=list(zip(LABELS, p, r, f)), macro=macro[:3],
                weighted=weighted[:3], accuracy=acc)


def _md_table(m, y_true):
    counts = pd.Series(y_true).value_counts()
    lines = ["| Lớp | Precision | Recall | F1 | Số mẫu |",
             "|---|---|---|---|---|"]
    for label, p, r, f in m["per_class"]:
        lines.append(f"| {label.replace('_', ' ')} | {p:.3f} | {r:.3f} | {f:.3f} "
                     f"| {int(counts.get(label, 0))} |")
    mp, mr, mf = m["macro"]
    wp, wr, wf = m["weighted"]
    lines.append(f"| **Macro avg** | {mp:.3f} | {mr:.3f} | **{mf:.3f}** | {len(y_true)} |")
    lines.append(f"| **Weighted avg** | {wp:.3f} | {wr:.3f} | {wf:.3f} | {len(y_true)} |")
    return "\n".join(lines)


def _md_confusion(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred, labels=LABELS)
    head = "| thực \\ dự đoán | " + " | ".join(l.replace("_", " ") for l in LABELS) + " |"
    sep = "|---" * (len(LABELS) + 1) + "|"
    rows = [head, sep]
    for i, label in enumerate(LABELS):
        rows.append(f"| **{label.replace('_', ' ')}** | " +
                    " | ".join(str(v) for v in cm[i]) + " |")
    return "\n".join(rows)


def evaluate():
    model_path = os.path.join(BASE, "models", "sentiment_model.joblib")
    if not os.path.exists(model_path):
        print("Chưa có mô hình. Chạy `python train.py` trước.")
        return
    pipe = joblib.load(model_path)

    out = ["# Báo cáo đánh giá mô hình phân loại cảm xúc", "",
           "Mô hình: TF-IDF (1–2 gram) + Logistic Regression, 3 lớp.", ""]

    # ---------------- A. hold-out cùng phân phối ----------------
    df = pd.read_csv(os.path.join(BASE, "data", "reviews.csv"), encoding="utf-8-sig")
    df["label"] = df["rating"].apply(rating_to_label)
    _, X_test, _, y_test = train_test_split(
        df["review_text"], df["label"], test_size=0.2, random_state=42,
        stratify=df["label"])
    yp = pipe.predict(X_test)
    mA = _metrics(list(y_test), list(yp))

    out += ["## A. Hold-out cùng phân phối với dữ liệu huấn luyện", "",
            "20% tách ra từ `reviews.csv`. **Không dùng con số này để kết luận mô "
            "hình tốt**: tập này sinh từ cùng bộ khuôn mẫu câu với tập huấn luyện "
            "nên mô hình chỉ cần khớp khuôn mẫu là đạt điểm rất cao.", "",
            f"Accuracy: **{mA['accuracy']:.3f}** — F1 macro: **{mA['macro'][2]:.3f}**",
            "", _md_table(mA, list(y_test)), "",
            "Ma trận nhầm lẫn:", "", _md_confusion(list(y_test), list(yp)), ""]

    results = {"A": mA}

    # ---------------- B & C. tập độc lập ----------------
    for key, fname, title, note in [
        ("B", "reviews_test.csv", "B. Tập kiểm thử độc lập (sinh bằng từ vựng khác)",
         "Không dùng khi huấn luyện. Từ vựng, cấu trúc câu khác hẳn; có phủ định, "
         "khen–chê lẫn lộn, viết không dấu/teencode, câu ngắn và sai chính tả."),
        ("C", "reviews_manual.csv", "C. Tập viết tay, gán nhãn thủ công",
         "Câu do người soạn theo văn phong người dùng thật. Tập nhỏ nên sai số "
         "thống kê lớn, chỉ mang tính tham khảo định tính."),
    ]:
        path = os.path.join(BASE, "data", fname)
        if not os.path.exists(path):
            out += [f"## {title}", "", f"_Chưa có `{fname}`. "
                    f"Chạy `python data/generate_test_set.py` để tạo._", ""]
            continue
        t = pd.read_csv(path, encoding="utf-8-sig")
        yp = pipe.predict(t["review_text"])
        m = _metrics(list(t["label"]), list(yp))
        results[key] = m

        out += [f"## {title}", "", note, "",
                f"Accuracy: **{m['accuracy']:.3f}** — F1 macro: **{m['macro'][2]:.3f}**",
                "", _md_table(m, list(t["label"])), "",
                "Ma trận nhầm lẫn:", "", _md_confusion(list(t["label"]), list(yp)), ""]

        if "style" in t.columns:
            t = t.assign(pred=yp)
            out += ["Độ chính xác theo từng kiểu câu:", "",
                    "| Kiểu câu | Số mẫu | Accuracy |", "|---|---|---|"]
            for style, g in t.groupby("style"):
                out.append(f"| {style} | {len(g)} | {(g['label'] == g['pred']).mean():.3f} |")
            out.append("")

    # ---------------- kết luận ----------------
    out += ["## Nhận xét", ""]
    if "B" in results:
        gap = results["A"]["macro"][2] - results["B"]["macro"][2]
        out += [f"- F1 macro giảm **{gap:.3f}** khi chuyển từ tập cùng phân phối (A) "
                f"sang tập độc lập (B). Khoảng cách này chính là phần mà tập demo "
                f"đang \"cho điểm\" quá hào phóng.",
                "- Nguồn lỗi tập trung ở câu phủ định và câu khen–chê lẫn lộn — đúng "
                "điểm yếu đã biết của mô hình túi từ (TF-IDF không mã hoá được phạm "
                "vi tác động của từ phủ định).",
                "- Khi báo cáo, nên trích số liệu ở mục B và C kèm Precision/Recall/F1 "
                "theo từng lớp, không dùng riêng Accuracy ở mục A.",
                "- Hướng cải thiện: bổ sung review thật có gán nhãn thủ công; thử "
                "fine-tune PhoBERT/ViSoBERT vốn xử lý phủ định tốt hơn nhiều so với "
                "TF-IDF.", ""]

    report_path = os.path.join(BASE, "models", "evaluation_report.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    # in gọn ra màn hình
    for key, name in [("A", "Hold-out cùng phân phối"),
                      ("B", "Tập độc lập"), ("C", "Tập viết tay")]:
        if key in results:
            m = results[key]
            print(f"{name:26s} acc={m['accuracy']:.3f}  F1-macro={m['macro'][2]:.3f}")
    print(f"\nBáo cáo chi tiết: {report_path}")
    return results


if __name__ == "__main__":
    evaluate()
