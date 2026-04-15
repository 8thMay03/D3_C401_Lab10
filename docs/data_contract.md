# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| Hệ thống HR (DB) | CSV Export tự động | Thiếu/sai định dạng ngày hiệu lực (effective_date) | `missing_effective_date` / `non_iso_rows` cao |
| CS Helpdesk (KB) | Đẩy file nội bộ (CSV) | Chứa version tài liệu cũ dẫn đến chính sách bị lệch | `stale_hr_policy` / Expectation halt |
| Hệ thống IT | Manual Export | Trùng lặp chunk text, ID tài liệu lạ | `duplicate_chunk_text` / `unknown_doc_id` tăng |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | … |
| doc_id | string | Có | … |
| chunk_text | string | Có | … |
| effective_date | date | Có | … |
| exported_at | datetime | Có | … |

---

## 3. Quy tắc quarantine vs drop

> Record bị flag đi đâu? Ai approve merge lại?

---

## 4. Phiên bản & canonical

> Source of truth cho policy refund: file nào / version nào?
