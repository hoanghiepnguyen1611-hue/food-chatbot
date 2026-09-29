# Báo cáo đánh giá mô hình phân loại cảm xúc

Mô hình: TF-IDF (1–2 gram) + Logistic Regression, 3 lớp.

## A. Hold-out cùng phân phối với dữ liệu huấn luyện

20% tách ra từ `reviews.csv`. **Không dùng con số này để kết luận mô hình tốt**: tập này sinh từ cùng bộ khuôn mẫu câu với tập huấn luyện nên mô hình chỉ cần khớp khuôn mẫu là đạt điểm rất cao.

Accuracy: **1.000** — F1 macro: **1.000**

| Lớp | Precision | Recall | F1 | Số mẫu |
|---|---|---|---|---|
| tiêu cực | 1.000 | 1.000 | 1.000 | 259 |
| trung tính | 1.000 | 1.000 | 1.000 | 1160 |
| tích cực | 1.000 | 1.000 | 1.000 | 3555 |
| **Macro avg** | 1.000 | 1.000 | **1.000** | 4974 |
| **Weighted avg** | 1.000 | 1.000 | 1.000 | 4974 |

Ma trận nhầm lẫn:

| thực \ dự đoán | tiêu cực | trung tính | tích cực |
|---|---|---|---|
| **tiêu cực** | 259 | 0 | 0 |
| **trung tính** | 0 | 1160 | 0 |
| **tích cực** | 0 | 0 | 3555 |

## B. Tập kiểm thử độc lập (sinh bằng từ vựng khác)

Không dùng khi huấn luyện. Từ vựng, cấu trúc câu khác hẳn; có phủ định, khen–chê lẫn lộn, viết không dấu/teencode, câu ngắn và sai chính tả.

Accuracy: **0.507** — F1 macro: **0.449**

| Lớp | Precision | Recall | F1 | Số mẫu |
|---|---|---|---|---|
| tiêu cực | 0.632 | 0.399 | 0.489 | 258 |
| trung tính | 0.459 | 0.170 | 0.248 | 229 |
| tích cực | 0.478 | 0.843 | 0.610 | 313 |
| **Macro avg** | 0.523 | 0.471 | **0.449** | 800 |
| **Weighted avg** | 0.522 | 0.507 | 0.468 | 800 |

Ma trận nhầm lẫn:

| thực \ dự đoán | tiêu cực | trung tính | tích cực |
|---|---|---|---|
| **tiêu cực** | 103 | 17 | 138 |
| **trung tính** | 40 | 39 | 150 |
| **tích cực** | 20 | 29 | 264 |

Độ chính xác theo từng kiểu câu:

| Kiểu câu | Số mẫu | Accuracy |
|---|---|---|
| chuẩn | 320 | 0.647 |
| câu ngắn | 80 | 0.550 |
| không dấu/teencode | 110 | 0.445 |
| lẫn lộn | 90 | 0.433 |
| phủ định | 120 | 0.258 |
| sai chính tả | 80 | 0.450 |

## C. Tập viết tay, gán nhãn thủ công

Câu do người soạn theo văn phong người dùng thật. Tập nhỏ nên sai số thống kê lớn, chỉ mang tính tham khảo định tính.

Accuracy: **0.367** — F1 macro: **0.238**

| Lớp | Precision | Recall | F1 | Số mẫu |
|---|---|---|---|---|
| tiêu cực | 0.167 | 0.100 | 0.125 | 10 |
| trung tính | 0.000 | 0.000 | 0.000 | 9 |
| tích cực | 0.435 | 0.909 | 0.588 | 11 |
| **Macro avg** | 0.200 | 0.336 | **0.238** | 30 |
| **Weighted avg** | 0.215 | 0.367 | 0.257 | 30 |

Ma trận nhầm lẫn:

| thực \ dự đoán | tiêu cực | trung tính | tích cực |
|---|---|---|---|
| **tiêu cực** | 1 | 1 | 8 |
| **trung tính** | 4 | 0 | 5 |
| **tích cực** | 1 | 0 | 10 |

Độ chính xác theo từng kiểu câu:

| Kiểu câu | Số mẫu | Accuracy |
|---|---|---|
| viết tay | 30 | 0.367 |

## Nhận xét

- F1 macro giảm **0.551** khi chuyển từ tập cùng phân phối (A) sang tập độc lập (B). Khoảng cách này chính là phần mà tập demo đang "cho điểm" quá hào phóng.
- Nguồn lỗi tập trung ở câu phủ định và câu khen–chê lẫn lộn — đúng điểm yếu đã biết của mô hình túi từ (TF-IDF không mã hoá được phạm vi tác động của từ phủ định).
- Khi báo cáo, nên trích số liệu ở mục B và C kèm Precision/Recall/F1 theo từng lớp, không dùng riêng Accuracy ở mục A.
- Hướng cải thiện: bổ sung review thật có gán nhãn thủ công; thử fine-tune PhoBERT/ViSoBERT vốn xử lý phủ định tốt hơn nhiều so với TF-IDF.
