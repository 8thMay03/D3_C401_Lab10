# Quality report — Lab Day 10 (nhóm)

**run_id (bản lỗi):** `inject_bad`  
**Ngày:** (Điền ngày hôm nay, ví dụ: 2026-04-15)

---

## 1. Tóm tắt số liệu
*(Bạn điền số liệu từ log lúc chạy ETL pipeline vào bảng này)*

| Chỉ số | Trước (clean_run) | Sau (inject_bad) | Ghi chú / Giải thích |
|--------|-------|-----|---------|
| raw_records | | | (Bình thường là giống nhau) |
| cleaned_records | | | |
| quarantine_records | | | |
| Expectation halt? | Không (OK) | Có (Do bị skip_validate) | Bản lỗi chạy bị fail Expectation `refund_no_stale_14d_window` |

---

## 2. Before / after retrieval (bắt buộc)

> Đính kèm hoặc báo cáo dựa trên 2 file: `artifacts/eval/before_eval_clean.csv` và `artifacts/eval/after_eval_bad.csv`.

**Câu hỏi then chốt:** refund window (`q_refund_window`)  
**Trước (Sạch):** `hits_forbidden=no` (Hệ thống RAG hoàn toàn không gọi nhầm chính sách 14 ngày làm việc cũ. Dữ liệu mâu thuẫn đã được Fix và Filter triệt để khỏi VectorDB).
**Sau (Lỗi):** `hits_forbidden=yes` (Trong Top-3 chunk văn bản nạp vào cho chatbot sinh ra câu trả lời, vẫn còn chứa văn bản lỗi thời "14 ngày làm việc". Chatbot sẽ rất dễ bị ảo giác và bồi thường sai quy định cho khách hàng!)

**Merit (khuyến nghị nâng cao):** versioning HR — `q_leave_version` (`contains_expected`, `hits_forbidden`, cột `top1_doc_expected`)

**Trước (Sạch):**  
**Sau (Lỗi):** 

---

## 3. Freshness & monitor
*(Kết quả khi bạn chạy `python etl_pipeline.py freshness --manifest [tên-file]` của Sprint 4)*
> (Điền PASS/WARN/FAIL vào đây và tại sao)

---

## 4. Corruption inject (Sprint 3)
Chúng tôi đã sử dụng lệnh `--no-refund-fix --skip-validate` để ép pipeline:
- **Ngưng sửa lỗi Refund Window**: Cho phép chính sách hoàn tiền cũ (14 ngày làm việc) lọt vào Cleaned Data.
- **Vượt rào Data Quality**: Bỏ qua chốt chặn Expectation Halt để đẩy cả dữ liệu sai vào Vector Database (ChromaDB) để có thể thử nghiệm hậu quả của RAG.

---

## 5. Hạn chế & việc chưa làm
- (Các bạn có thể tự điền nếu có, ví dụ: chưa thử nghiệm nhiều bộ dữ liệu lớn hơn...)
