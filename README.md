# Chatbot Tư Vấn Ẩm Thực

Chatbot tìm quán ăn hiểu được yêu cầu nói tự nhiên bằng tiếng Việt, tra cứu trên
cơ sở dữ liệu **2.485 quán** ở hai địa bàn (TP.HCM và Quảng Ngãi), xếp hạng theo
độ phù hợp và **giải thích vì sao từng quán được gợi ý**.

> *“Tôi muốn ăn xôi nhưng không thích quá mặn, giá dưới 30k, gần đây”*
> → bot tách được **món = xôi**, **khẩu vị = ít mặn**, **ngân sách = dưới 30k**,
> **vị trí = quanh bạn**, rồi xếp hạng theo mức khớp của cả bốn tiêu chí.

> ⚠️ **Dữ liệu quán trong repo này là dữ liệu MÔ PHỎNG** (`data_source = simulated`),
> dùng để chạy thử hệ thống. Tên quán, địa chỉ, toạ độ đều do máy sinh ra và
> **không phải quán có thật**. Xem mục 6 để biết cách nạp dữ liệu quán thật.

---

## 1. Hiểu yêu cầu ăn uống tự nhiên (`src/nlu.py`)

Bản đầu chỉ so khớp từ khóa, nên câu “xôi **không quá mặn**” lại trả về đúng
những quán mặn nhất. Bản này chuyển câu nói thành một *bản yêu cầu có cấu trúc*
(`FoodQuery`) rồi mới đi tìm.

| Người dùng nói | Bot hiểu thành |
|---|---|
| “xôi không thích quá mặn” | `dishes=[xoi]`, `taste={man: low}` |
| “bún bò **thật cay**” | `taste={cay: high}` |
| “trà sữa **ít đường**” | `taste={ngot: low}` |
| “dưới 30k” / “tầm 300k” / “từ 20k đến 40k” | `price_max`, `price_min` |
| “gần đây” / “trong vòng 1km” / “đi bộ được” | `near_me`, `radius_km` |
| “ở Quận 3”, “q7”, “Nghĩa Chánh”, “gần biển Mỹ Khê” | `district`, `city` |
| “đang mở cửa” / “ăn khuya” | `open_now`, `at_hour` |
| “trên 4 sao” / “ngon nhất” | `min_rating` |
| “đi nhóm đông, có máy lạnh” | `utilities` |
| “top 3 quán” | `limit` |

Bốn kỹ thuật chính:

1. **Từ điển món ăn có hồ sơ vị** (`src/food_catalog.py`) — 53 nhóm món, mỗi
   nhóm có alias (“bún bò”, “bun bo”, “bún bò huế”) và hồ sơ vị mặc định
   (mặn / cay / ngọt / béo, thang 0–1).
2. **Xử lý phủ định và mức độ** — với mỗi từ chỉ vị, bot soi cửa sổ ngữ cảnh
   ~30 ký tự xung quanh để tìm dấu hiệu giảm (*không, đừng, ít, giảm, bớt,
   kiêng, sợ, tránh*), vừa (*vừa ăn, vừa phải*) hay tăng (*thật, cực, siêu,
   nhiều*). Đây là chỗ mà tìm kiếm từ khóa thất bại.
3. **Quét hai lượt có dấu / không dấu** — vừa chính xác (“nhạt” ≠ “nhất”), vừa
   chấp nhận người dùng gõ tắt không dấu (“khong qua man”).
4. **Chuẩn hóa tiền Việt** — “30k”, “30 nghìn”, “30.000đ” đều thành `30000`,
   đồng thời loại số không phải tiền (“4 **sao**”, “3 **quán**”, “1**km**”).

### Giải thích vì sao quán được gợi ý

Mỗi thẻ quán kèm một câu lý do dựng từ chính các thành phần điểm số:

> *Gợi ý vì đúng món xôi, vị vừa không quá mặn, giá từ 17k nằm trong ngân sách,
> cách bạn 3,5km.*

Nếu quán lệch tiêu chí, bot nói thẳng thay vì giấu: *“Vị mặn khá đậm, nhưng quán
nhận yêu cầu giảm mặn”*, *“Giá khởi điểm 60k, cao hơn ngân sách bạn nêu”*.

---

## 2. Dữ liệu quán ăn

| | TP.HCM | Quảng Ngãi | Tổng |
|---|---|---|---|
| Số quán | 1.765 | 720 | **2.485** |
| Khu vực | 18 quận/huyện | 6 phường/xã | 24 |
| Nhóm món | 48 | 53 | 53 |
| Review | — | — | **24.866** |

### Về địa bàn Quảng Ngãi

Theo **Nghị quyết 1677/NQ-UBTVQH15**, từ **01/7/2025** thành phố Quảng Ngãi kết
thúc hoạt động; địa bàn thành phố cũ được sắp xếp thành 5 đơn vị hành chính cấp
xã. Dữ liệu dùng đúng tên hiện hành, đồng thời giữ tên cũ trong `aliases` để
người dùng gõ tên quen vẫn tìm được:

| Đơn vị hiện nay | Gồm các phường/xã trước sắp xếp | Số quán |
|---|---|---|
| Phường Cẩm Thành | Nguyễn Nghiêm, Trần Hưng Đạo, Nghĩa Chánh, Chánh Lộ | 220 |
| Phường Nghĩa Lộ | Lê Hồng Phong, Trần Phú, Quảng Phú, Nghĩa Lộ | 186 |
| Phường Trương Quang Trọng | Trương Quang Trọng, Tịnh Ấn Tây, Tịnh Ấn Đông, Tịnh An | 127 |
| Xã Tịnh Khê | Tịnh Kỳ, Tịnh Châu, Tịnh Long, Tịnh Thiện, Tịnh Khê | 88 |
| Xã An Phú | Nghĩa Hà, Nghĩa Dõng, Nghĩa Dũng, An Phú | 65 |
| Xã Đông Sơn (liền kề) | Tịnh Hòa, Bình Châu, Bình Thanh, Bình Hiệp, Bình Tân Phú | 34 |

Có thêm 6 nhóm món đặc trưng địa phương: **don / cháo don**, **ram bắp**,
**cá bống sông Trà**, **cá nục hấp cuốn bánh tráng**, **bún chả cá**, và
**đặc sản mang về** (kẹo gương, mạch nha, đường phèn). Mặt bằng giá ở Quảng Ngãi
được đặt thấp hơn TP.HCM khoảng 15%.

Chatbot tự chọn địa bàn theo vị trí GPS của người dùng, hoặc theo khu vực được
nhắc trong câu, nên kết quả không bị lẫn giữa hai tỉnh thành.

Mỗi quán có 30 trường: tên, địa chỉ, khu vực, **toạ độ lat/lng**, món chính,
menu, khoảng giá, đánh giá sao, số lượt đánh giá, **đặc điểm vị** (mặn/cay/ngọt/béo
kèm nhãn chữ), khả năng điều chỉnh vị theo yêu cầu, giờ mở–đóng cửa, tiện ích,
số điện thoại, ảnh, và **`data_source`** ghi rõ nguồn gốc dữ liệu.

---

## 3. Ảnh quán ăn

Trước đây thẻ quán trỏ tới ảnh của một website bên ngoài; khi site đó chặn
hotlink hoặc máy không có mạng thì thẻ trống trơn, nhìn rất giống bản nháp.

Nay ảnh **nằm trong project**: `data/generate_dish_images.py` sinh 53 file SVG
(~2KB/file) vào `static/img/dishes/`, mỗi nhóm món một ảnh có màu nền theo nhóm,
biểu tượng món và tên món in trên ảnh.

Thứ tự hiển thị:

```
1. photo_url  → ảnh thật của quán (cột photo_url trong restaurants.csv)
        ↓ lỗi
2. image_url  → ảnh SVG theo nhóm món, nằm trong project
        ↓ lỗi
3. ô màu + biểu tượng + tên món
```

Mọi ảnh đều có thuộc tính `alt` dạng *“Ảnh minh hoạ món Xôi — Xôi Cô Tấm”*, nên
khi ảnh lỗi hoặc dùng trình đọc màn hình vẫn biết đó là quán nào. Muốn dùng ảnh
thật, chỉ cần điền URL vào cột `photo_url`; không phải sửa code.

---

## 4. Giao diện (`templates/index.html`)

- Thẻ quán dạng “vé” có ảnh, số thứ tự hạng, sao, khoảng cách, thời gian chạy xe
  ước tính, khoảng giá và trạng thái đang mở / đã đóng.
- **Thanh đo khẩu vị** (mặn / cay / ngọt / béo) vẽ bằng 5 vạch cho từng quán.
- Khối **“Mình hiểu yêu cầu của bạn là…”** hiển thị đúng những gì bot bóc tách
  được — người dùng biết bot hiểu sai chỗ nào để nói lại.
- Câu **“Gợi ý vì…”** trên từng thẻ.
- Bốn nút: **Xem bản đồ** (bản đồ nhúng ngay trong thẻ), **Xem quán**,
  **Chỉ đường**, **Gọi**.
- Chạy tốt trên điện thoại, tự đổi màu theo chế độ sáng/tối.

### Tích hợp Google Maps (`src/geo.py`)

Dùng **Maps URLs API**, không cần API key:

| Chức năng | URL |
|---|---|
| Xem quán | `…/maps/search/?api=1&query=<tên+địa chỉ>&center=<lat>,<lng>` |
| Chỉ đường | `…/maps/dir/?api=1&origin=<vị trí bạn>&destination=<lat>,<lng>&travelmode=two-wheeler` |
| Bản đồ nhúng | `https://maps.google.com/maps?q=<lat>,<lng>&z=17&output=embed` |

Khoảng cách tính bằng **Haversine** rồi nhân 1.25 để ước lượng quãng đường đi
thực tế trong đô thị; thời gian ước tính theo tốc độ xe máy nội thành ~22 km/h.

---

## 5. Đánh giá mô hình cảm xúc — đọc kỹ mục này trước khi báo cáo

> **Lưu ý:** Bộ dữ liệu hiện tại chủ yếu được sinh tự động nhằm phục vụ mục đích
> thử nghiệm và demo. Vì dữ liệu có cấu trúc tương đối đồng nhất với dữ liệu
> huấn luyện, kết quả đánh giá có thể cao hơn thực tế. Để đánh giá khả năng tổng
> quát hóa của mô hình, cần thay thế/bổ sung bằng dữ liệu review thực tế và tập
> kiểm thử độc lập.

Để không rơi vào bẫy “mô hình đạt 100%”, `src/evaluate.py` chạy mô hình trên
**ba tập khác nhau** và xuất báo cáo đầy đủ Precision / Recall / F1 theo từng
lớp vào `models/evaluation_report.md`:

| Tập | Mô tả | Accuracy | F1 macro |
|---|---|---|---|
| **A.** Hold-out cùng phân phối | 20% tách từ `reviews.csv`, cùng khuôn mẫu câu với tập huấn luyện | 1.000 | 1.000 |
| **B.** Kiểm thử độc lập | `reviews_test.csv` — 800 câu, từ vựng và cấu trúc khác hẳn, có phủ định, khen–chê lẫn lộn, viết không dấu/teencode, câu ngắn, sai chính tả | **0.507** | **0.449** |
| **C.** Viết tay, gán nhãn thủ công | `reviews_manual.csv` — 30 câu người soạn theo văn phong thật | **0.367** | **0.238** |

**Con số ở mục A là 1.000 không phải vì mô hình giỏi, mà vì tập test cùng khuôn
mẫu sinh dữ liệu với tập train.** Khi trình bày, hãy dùng số liệu ở mục B và C.

Bóc tách lỗi trên tập B cho thấy điểm yếu rất cụ thể:

| Kiểu câu | Số mẫu | Accuracy |
|---|---|---|
| Câu chuẩn | 320 | 0.647 |
| Câu ngắn | 80 | 0.550 |
| Sai chính tả | 80 | 0.450 |
| Viết không dấu / teencode | 110 | 0.445 |
| Khen–chê lẫn lộn | 90 | 0.433 |
| **Phủ định** | 120 | **0.258** |

Câu phủ định (“không ngon như lời đồn”, “chẳng có gì đặc sắc”) là chỗ mô hình
sai nhiều nhất — đúng như dự đoán, vì TF-IDF là mô hình túi từ, không mã hoá
được phạm vi tác động của từ phủ định. Đây là lập luận tốt để đề xuất nâng cấp
sang PhoBERT/ViSoBERT trong báo cáo.

**Việc nên làm tiếp:** thu thập review thật (Google Maps, Foody, ShopeeFood),
gán nhãn thủ công ít nhất 500–1.000 câu, rồi chạy lại `src/evaluate.py`. Thêm
câu vào danh sách `MANUAL` trong `data/generate_test_set.py` là cách nhanh nhất
để mở rộng tập C.

---

## 6. Nạp dữ liệu quán thật

`data/import_places.py` gọi **Google Places API (New)** và ghi ra
`restaurants_real.csv` đúng định dạng chatbot đang dùng, với
`data_source = google_places`:

```bash
export GOOGLE_MAPS_API_KEY="..."
pip install requests
python data/import_places.py --city "Quảng Ngãi" --max-per-query 60
```

Script quét theo tâm từng phường/xã và theo từ khoá của từng nhóm món để phủ
đều địa bàn, thay vì dồn hết vào trung tâm.

Ba điểm cần biết trước khi chạy:

- Places API **tính phí theo lượt gọi**; xem bảng giá trước khi quét rộng.
- Mỗi truy vấn Text Search chỉ trả tối đa 60 kết quả, nên phải chia nhỏ theo
  từ khoá và theo ô lưới toạ độ — script đã làm sẵn.
- Điều khoản của Google **không cho lưu trữ dài hạn** phần lớn dữ liệu Places
  (trừ `place_id`). Dùng cho khoá luận/demo thì được, triển khai thật cần đọc
  kỹ Google Maps Platform Terms of Service.
- Google **không cung cấp độ mặn / độ cay**. Script điền hồ sơ vị bằng giá trị
  mặc định của nhóm món và đánh dấu `taste_source = dish_default`. Muốn có hồ sơ
  vị riêng từng quán, phải chạy mô hình ABSA trên chính review lấy về.

---

## 7. Cài đặt & chạy

```bash
pip install -r requirements.txt

# Sinh dữ liệu + ảnh + tập kiểm thử + huấn luyện + đánh giá (chạy 1 lần)
python train.py

python app.py            # giao diện web: http://localhost:5000
python src/chatbot.py    # bản dòng lệnh
python src/evaluate.py   # chạy lại đánh giá mô hình
python build_demo.py     # đóng gói demo.html chạy offline, 1 file
```

Thử các câu:

```
Tôi muốn ăn xôi không quá mặn, giá dưới 30k, gần tôi
muốn ăn don không quá mặn ở Quảng Ngãi
ram bắp ngon ở phường Cẩm Thành
cá bống sông Trà kho tiêu, trên 4 sao
bún bò thật cay ở Quận 1
quán lẩu đi nhóm đông, có máy lạnh, tầm 300k ở Bình Thạnh
cơm trưa bình dân đang mở cửa gần đây
```

---

## 8. Kiến trúc

```
        Câu nói tự nhiên của người dùng
                    │
                    ▼
        ┌───────────────────────────┐
        │  NLU  (src/nlu.py)        │  món · khẩu vị · giá · vị trí · giờ
        │  slot filling + phủ định  │  -> FoodQuery
        └─────────────┬─────────────┘
                      ▼
        ┌───────────────────────────┐      ┌──────────────────────────┐
        │ Tìm kiếm đa tiêu chí       │◄────┤ restaurants.csv (2.485)  │
        │ (src/restaurant_db.py)     │     │ review_stats.csv         │
        │ xếp hạng + sinh lý do      │     └──────────────────────────┘
        └─────────────┬─────────────┘                  ▲
                      ▼                                │
        ┌───────────────────────────┐      ┌───────────┴──────────────┐
        │ Chatbot (src/chatbot.py)  │      │ Pipeline NLP (offline)    │
        │ phản hồi + thẻ quán       │      │ sentiment_model.py        │
        └─────────────┬─────────────┘      │ aspect_extraction.py      │
                      ▼                    │ recommender.py            │
        ┌───────────────────────────┐      │ evaluate.py  ← đánh giá   │
        │ Web (app.py + templates)  │      └───────────────────────────┘
        └───────────────────────────┘
```

**Công thức xếp hạng** — trung bình có trọng số, chỉ tính tiêu chí người dùng nêu:

| Tiêu chí | Trọng số | Cách chấm |
|---|---|---|
| Khẩu vị | **0.45** | dải chấp nhận: “ít mặn” đạt điểm tối đa khi độ mặn ≤ 0.42, về 0 ở 0.80 |
| Khoảng cách | 0.24 | suy giảm theo `exp(-km / bán kính)` |
| Đánh giá | 0.22 | sao kết hợp độ tin cậy theo số lượt đánh giá |
| Giá | 0.16 | mức chồng lấn giữa khoảng giá quán và ngân sách |
| Tiện ích | 0.08 | tỉ lệ tiện ích khớp |

---

## 9. Cấu trúc thư mục

```
food_chatbot/
├── data/
│   ├── generate_restaurants.py   # sinh quán mô phỏng cho TP.HCM + Quảng Ngãi
│   ├── generate_sample_data.py   # sinh review nhất quán với hồ sơ vị của quán
│   ├── generate_test_set.py      # tập kiểm thử ĐỘC LẬP + tập viết tay  ★
│   ├── generate_dish_images.py   # ảnh SVG từng nhóm món, lưu trong project  ★
│   ├── import_places.py          # nhập quán THẬT từ Google Places API  ★
│   ├── restaurants.csv           # 2.485 quán (data_source = simulated)
│   ├── reviews.csv               # 24.866 review
│   ├── reviews_test.csv          # 800 câu kiểm thử độc lập
│   ├── reviews_manual.csv        # 30 câu viết tay, gán nhãn thủ công
│   └── review_stats.csv          # tri thức NLP đã chắt lọc theo từng quán
├── src/
│   ├── food_catalog.py           # 53 nhóm món + hồ sơ vị + đặc sản Quảng Ngãi
│   ├── geo.py                    # khu vực 2 tỉnh thành, Haversine, Google Maps
│   ├── nlu.py                    # hiểu yêu cầu tự nhiên
│   ├── restaurant_db.py          # tìm kiếm, xếp hạng, sinh câu giải thích
│   ├── chatbot.py                # điều phối hội thoại, trả JSON có thẻ quán
│   ├── evaluate.py               # đánh giá Precision/Recall/F1 trên 3 tập  ★
│   ├── preprocess.py             # tiền xử lý tiếng Việt
│   ├── aspect_extraction.py      # ABSA theo từ điển
│   ├── sentiment_model.py        # TF-IDF + Logistic Regression
│   └── recommender.py            # tổng hợp tri thức từ review
├── static/img/dishes/            # 53 ảnh SVG minh hoạ món ăn  ★
├── models/evaluation_report.md   # báo cáo đánh giá đầy đủ  ★
├── templates/index.html          # giao diện chat + thẻ quán
├── app.py · train.py · build_demo.py · requirements.txt
```

---

## 10. Hướng phát triển

| Thành phần | Bản này | Nâng cấp đề xuất |
|---|---|---|
| Dữ liệu quán | Mô phỏng 2.485 quán | Google Places API (`import_places.py`), Foody, ShopeeFood |
| Dữ liệu review | Sinh tự động theo khuôn mẫu | Crawl review thật + gán nhãn thủ công 500–1.000 câu |
| Đánh giá mô hình | 3 tập, P/R/F1, bóc tách theo kiểu câu | Kiểm định chéo k-fold; khảo sát mức hài lòng người dùng |
| Phân loại cảm xúc | TF-IDF + Logistic Regression (yếu ở phủ định) | Fine-tune PhoBERT / ViSoBERT |
| Hồ sơ vị của quán | Gán khi sinh dữ liệu | Học từ review thật bằng mô hình ABSA |
| NLU | Slot filling bằng luật | Joint Intent + Slot Filling (JointBERT) hoặc LLM trả JSON |
| Tách từ | Regex + ghép cụm từ | `underthesea` / `pyvi` / VnCoreNLP |
| Ảnh quán | SVG theo nhóm món | Google Place Photo API, lưu cache trong project |
| Khoảng cách | Haversine × 1.25 | Google Distance Matrix API (đường đi thật, có kẹt xe) |
| Giao diện | Web Flask | Zalo OA / Messenger / ứng dụng di động |
