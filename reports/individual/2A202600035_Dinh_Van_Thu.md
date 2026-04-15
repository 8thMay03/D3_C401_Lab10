# Báo cáo cá nhân — Đinh Văn Thư

**Họ và tên:** Đinh Văn Thư  
**Vai trò:** Ingestion / Raw Owner  
**Độ dài:** ~550 từ  

---

## 1. Phần phụ trách cụ thể

Với tư cách là **Raw Owner** trong Lab 10, tôi chịu trách nhiệm kiểm soát chất lượng tại "cửa ngõ" vào của hệ thống. Công việc của tôi tập trung vào việc đảm bảo dữ liệu thô (raw data) được nạp một cách ổn định, đúng định dạng và có khả năng truy vết (lineage) xuyên suốt pipeline.

Các thành phần chính tôi đã thực hiện bao gồm:
- **`load_raw_csv()`**: Triển khai logic nạp dữ liệu từ tệp `data/raw/policy_export_dirty.csv`. Đây là lớp đầu tiên tiếp xúc với dữ liệu "bẩn", đòi hỏi các cơ chế dự phòng để tránh pipeline bị crash giữa chừng.
- **Data Contract**: Thiết lập và quản lý tệp [data_contract.yaml](file:///d:/Vin_AI/lab10/D3_C401_Lab10/contracts/data_contract.yaml), định nghĩa các ràng buộc về schema, kiểu dữ liệu và đặc biệt là các kỳ vọng về độ tươi (Freshness) của dữ liệu nguồn.
- **Quarantine Logic**: Xây dựng hàm `write_quarantine_csv()` để tách biệt các bản ghi không đạt chuẩn (ví dụ: thiếu ID, sai format ngày tháng) ra khỏi luồng chính, giúp duy trì tính ổn định cho các bước Embed và Retrieval phía sau.
- **Lineage Tracking**: Đảm bảo mọi đợt nạp dữ liệu đều được gắn mã `run_id` và lưu vết vào `manifest.json`, giúp Raw Owner có thể đối soát (audit) ngược lại từ Vector Store về đúng phiên bản file thô ban đầu.

**Bằng chứng:** Code tại `load_raw_csv`, file `contracts/data_contract.yaml` và các artifacts trong thư mục `quarantine/`.

---

## 2. Quyết định kỹ thuật: Data Contract & Quarantine Strategy

**Cấu hình Freshness SLA từ Contract:** Tôi quyết định tách biệt logic kiểm tra Freshness ra khỏi mã nguồn Python và đưa vào `data_contract.yaml` với thông số `sla_hours: 24`. 
- **Lý do:** Là Raw Owner, tôi hiểu rằng độ trễ của dữ liệu nguồn (Source Latency) là rủi ro lớn nhất đối với hệ thống RAG. Việc cấu hình qua YAML giúp các bộ phận vận hành (Ops) có thể điều chỉnh SLA linh hoạt mà không cần can thiệp vào code. Tôi cũng triển khai logic so sánh `exported_at` của bản ghi mới nhất với thời gian chạy hiện tại để phát hiện ngay lập tức nếu dữ liệu nguồn bị "stale" (cũ).

**Chiến lược Quarantine thay vì Halt:** Đối với các lỗi định dạng nhẹ (ví dụ: thiếu metadata không quan trọng), tôi chọn giải pháp "Quarantine" (cách ly) bản ghi lỗi và tiếp tục pipeline với các bản ghi sạch. Tuy nhiên, với các lỗi nghiêm trọng về tính chính xác của chính sách (như lỗi refund 14 ngày), tôi ủng hộ việc sử dụng cờ `halt` để chặn đứng pipeline, ngăn chặn việc đẩy dữ liệu sai lệch vào Vector Store (Vector Store Polluting).

---

## 3. Một sự cố / anomaly: Xử lý "Timestamp Chaos"

Trong quá trình nạp dữ liệu từ nguồn CS Helpdesk, tôi gặp sự cố nghiêm trọng khiến pipeline dừng đột ngột. 
- **Hiện tượng:** Bản ghi thứ 4 trong file CSV có định dạng timestamp không chuẩn ISO (thiếu phần giây và múi giờ 'Z'), gây lỗi `ValueError` khi parse.
- **Phân tích của Raw Owner:** Dữ liệu nguồn từ các hệ thống di sản (Legacy Systems) thường không đồng nhất. Nếu chỉ dùng thư viện chuẩn `datetime.fromisoformat()`, pipeline sẽ cực kỳ mong manh (brittle).
- **Xử lý:** Tôi đã triển khai một lớp bọc (wrapper) tiền xử lý chuỗi trước khi nạp. Hàm này sử dụng regex để chuẩn hóa mọi định dạng timestamp về một chuẩn duy nhất. Kết quả: Pipeline đã có thể nạp thành công 10/10 bản ghi thô mà không gặp lỗi dừng đột ngột, trong đó 4 bản ghi sai sót đã được đẩy vào thư mục `quarantine` theo đúng quy trình.

---

## 4. Before / after evidence (Raw Ingestion Perspective)

Kết quả thực thi mới nhất cho thấy hiệu quả của việc phân loại dữ liệu tại nguồn:

| Chỉ số | Giá trị | Ý nghĩa từ góc độ Ingestion |
| :--- | :--- | :--- |
| **raw_records** | 10 | Tổng số bản ghi được lấy từ file CSV gốc. |
| **cleaned_records** | 6 | Số bản ghi sạch, đủ điều kiện để nạp vào Vector Store. |
| **quarantine_records** | 4 | Số bản ghi bị loại bỏ do vi phạm "Data Contract". |
| **freshness_check** | `FAIL` | Cảnh báo dữ liệu đã quá 122 giờ (vượt ngưỡng SLA 24h). |

**Minh chứng Retrieval:** Nhờ việc lọc bỏ các bản ghi "nhiễu" ở bước Ingestion, câu hỏi về chính sách hoàn tiền (`q_refund_window`) đã không còn bị dẫn lái bởi dữ liệu 14 ngày cũ, mà trả về chính xác 7 ngày từ các bản ghi đã được "Cleaned".

---

## 5. Cải tiến thêm 2 giờ: Data Integrity & Hash Snapshot

Để đảm bảo tính bất biến của dữ liệu thô sau khi nạp, tôi đã triển khai thêm cơ chế **SHA-256 Fingerprinting**.
- **Thực hiện:** Ngay sau khi hàm `load_raw_csv()` hoàn tất, hệ thống sẽ tính toán mã hash cho toàn bộ nội dung file thô và lưu vào `manifest.json`.
- **Giá trị mang lại:** Điều này tạo ra một bằng chứng số không thể chối cãi. Nếu sau 1 tháng, có sự tranh chấp về việc "Tại sao chatbot trả lời sai?", Raw Owner có thể dùng mã hash này để chứng minh dữ liệu thô tại thời điểm nạp là đúng hay sai, loại trừ khả năng file CSV bị ai đó sửa đổi "vụng trộm" trên ổ đĩa.
