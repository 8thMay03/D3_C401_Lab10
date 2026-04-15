# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyen Quoc Khanh 
**Vai trò:** Cleaning Owner  
**Ngày nộp:** 15/04/2026

---

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.  
> Nếu làm phần clean/expectation: nêu **một số liệu thay đổi** (vd `quarantine_records`, `hits_forbidden`, `top1_doc_expected`) khớp bảng `metric_impact` của nhóm.  
> Lưu: `reports/individual/[ten_ban].md`

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `transform/cleaning_rules.py`
- `quality/expectations.py`

**Kết nối với thành viên khác:**

Tôi nhận raw export từ ingestion, làm sạch rồi chuyển `cleaned_final-clean.csv` sang embed. Trong run `final-clean`, pipeline ghi nhận `raw_records=10`, `cleaned_records=6`, `quarantine_records=4`, nên downstream chỉ nhận dữ liệu đã qua kiểm soát. Tôi phối hợp chặt với Embed Owner vì bất kỳ dòng bẩn nào lọt qua sẽ làm sai retrieval ngay ở bài test `q_refund_window`.

**Bằng chứng (commit / comment trong code):**

Các rule cleaning trong `transform/cleaning_rules.py` đã bao gồm allowlist `doc_id`, chuẩn hoá `effective_date`, quarantining cho `missing_exported_at`, `contains_garbage_or_placeholders`, `non_meaningful_content`, `duplicate_chunk_text`, và fix nội dung hoàn tiền từ 14 ngày sang 7 ngày làm việc.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Tôi chọn chiến lược **quarantine thay vì warn** cho các lỗi có nguy cơ làm bẩn chỉ mục truy xuất. Với dữ liệu policy, nếu `doc_id` lạ, `exported_at` thiếu, nội dung placeholder, hoặc chunk không đủ nghĩa mà chỉ “cảnh báo”, dòng đó vẫn có thể đi tiếp sang embed và gây nhiễu vector DB. Vì vậy tôi ưu tiên chặn cứng ở cleaning, còn expectation ở `quality/expectations.py` dùng `halt` cho lỗi nghiệp vụ quan trọng như `refund_no_stale_14d_window`, `effective_date_iso_yyyy_mm_dd`, và `exported_at_not_in_future`. Quyết định này giúp pipeline có tính idempotent và ổn định hơn: dữ liệu đã sạch thì `cleaned_final-clean.csv` luôn tái tạo được, còn dữ liệu xấu luôn bị tách ra `quarantine`, không âm thầm ảnh hưởng kết quả RAG.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Lỗi rõ nhất tôi xử lý là policy hoàn tiền bị stale: trong raw có câu “14 ngày làm việc”, nhưng policy hiện hành phải là “7 ngày làm việc”. Tôi phát hiện lỗi này qua expectation `refund_no_stale_14d_window`; khi inject bản hỏng, kết quả retrieval đổi sang `hits_forbidden=yes`, tức agent vẫn bám vào nội dung cũ. Sau đó tôi sửa ở cleaning rule bằng cách normalize nội dung và thay chuỗi stale ngay tại nguồn, rồi để expectation xác nhận lại trước khi embed. Kết quả là bản `final-clean` không còn đường cho nội dung cũ lọt xuống vector DB. Số liệu thay đổi tôi dùng để chứng minh là `quarantine_records=4` trên tổng `raw_records=10`, đồng thời `hits_forbidden` của câu hỏi refund chuyển từ `yes` sang `no`.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Run tôi dùng làm mốc là `final-clean`. Dưới đây là hai dòng trực tiếp từ `artifacts/eval/before_after_eval.csv` để thấy hiệu quả của cleaning:

Trước khi fix/inject bad:  
`q_refund_window,Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi xác nhận đơn?,policy_refund_v4,Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng.,yes,yes,,3`

Sau khi clean/fix:  
`q_refund_window,Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi xác nhận đơn?,policy_refund_v4,Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng.,yes,no,,3`

Tôi cũng kiểm tra thêm dòng `q_leave_version`, và `top1_doc_expected=yes` giữ ổn định, cho thấy cleaning không làm hỏng các câu hỏi hợp lệ khác.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ thêm thống kê `quarantine_reason_counts` vào manifest và xuất thẳng vào report markdown. Như vậy mỗi run sẽ cho thấy chính xác bao nhiêu dòng bị loại vì `missing_exported_at`, `duplicate_chunk_text`, hay `contains_garbage_or_placeholders`, thay vì chỉ có tổng `quarantine_records`. Điều này sẽ giúp debug nhanh hơn khi export thực tế đổi format.
