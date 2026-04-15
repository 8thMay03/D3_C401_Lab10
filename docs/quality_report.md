# Quality report — Lab Day 10 (nhóm)

**run_id:** `fix` (sau khi chạy pipeline cố định SLA và clean data)  
**Ngày:** Cập nhật hôm nay

---

## 1. Tóm tắt số liệu

| Chỉ số             | Trước | Sau  | Ghi chú                                            |
| ------------------ | ----- | ---- | -------------------------------------------------- |
| raw_records        | 10    | 10   | Tổng số records từ export CSV mẫu                  |
| cleaned_records    | 6     | 6    | Số lượng records được đưa vào Vector DB            |
| quarantine_records | 4     | 4    | Các records vi phạm logic/schema bị cách ly        |
| Expectation halt?  | HALT  | PASS | Inject fail trên rule `refund_no_stale_14d_window` |

---

## 2. Before / after retrieval (bắt buộc)

> Đính kèm hoặc dẫn link tới `artifacts/eval/before_after_eval.csv` (hoặc 2 file before/after).

- File After Inject Bad: [after_inject_bad.csv](file:///k:/VIN_AI/Buoi_10/D3_C401_Lab10/artifacts/eval/after_inject_bad.csv)
- File Before After Eval (Fixed): [before_after_eval.csv](file:///k:/VIN_AI/Buoi_10/D3_C401_Lab10/artifacts/eval/before_after_eval.csv)

**Câu hỏi then chốt:** refund window (`q_refund_window`)  
**Trước (Inject Bad):**  
`hits_forbidden` = `yes`
(Document chứa chuỗi "14 ngày làm việc" thay vì "7 ngày làm việc" như chính sách mới).

**Sau (Cleaned / Fixed):**
`hits_forbidden` = `no`
(Chuỗi "14 ngày làm việc" được xử lý clean và fix lại thành "7 ngày làm việc"). Preview output: _"Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng."_

**Merit (khuyến nghị):** versioning HR — `q_leave_version` (`contains_expected`, `hits_forbidden`, cột `top1_doc_expected`)

**Trước / Sau (Nhất quán):**  
Cả trước và sau, với test `hr_leave_policy`, version cũ ("10 ngày phép năm") bị quarantine vì `effective_date` < 2026. Do đó `hits_forbidden` = `no` và `top1_doc_expected` = `yes`.
Preview output: _"Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm theo chính sách 2026."_

---

## 3. Freshness & monitor

> Kết quả `freshness_check` (PASS/WARN/FAIL) và giải thích SLA bạn chọn.

- Kết quả `freshness_check`: `FAIL` với data hiện tại (exported_at = "2026-04-10T08:00:00", age_hours > SLA 24h).
- SLA đã lựa chọn: `24 giờ`. Do dữ liệu gốc không được cập nhật kể từ ngày 10, check freshness log ra FAIL `{"reason": "freshness_sla_exceeded"}`. Đây là báo động thực cần gửi thông báo để force up pipeline export.

---

## 4. Corruption inject (Sprint 3)

> Mô tả cố ý làm hỏng dữ liệu kiểu gì (duplicate / stale / sai format) và cách phát hiện.

Cố ý không fix số ngày hoàn tiền (`--no-refund-fix`) và ép pipeline chạy (`--skip-validate`), bỏ qua halt dù Expectation thất bại.

- **Cách phát hiện**: Expectation `refund_no_stale_14d_window` báo fail ở step Validate và cờ `skipped_validate` bị gán True trong metadata Json. Sau tiếp, bước Evaluation query vector kiểm tra và phát hiện output văng ra cờ `hits_forbidden=yes` ám chỉ output trả về cho Agent Day 09 sẽ là chính sách hết hiệu lực (14 ngày).

---

## 5. Hạn chế & việc chưa làm

- Chưa triển khai PagerDuty integration trên Data Expectation HALT.
- Metadata chưa hỗ trợ phân tích incremental load (chỉ mới load all / clean wipe qua Prune).
