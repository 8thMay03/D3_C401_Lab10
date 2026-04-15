# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| policy_refund_v4 | API Export (CSV) | Chứa số liệu cũ (14 ngày làm việc) | Expectation `refund_no_stale_14d_window` |
| hr_leave_policy | API Export (CSV) | Effective date cũ (<2026) | Expectation `hr_leave_no_stale_10d_annual` |
| it_helpdesk_faq | API Export (CSV) | Chứa ký tự rác, lỗi mã hóa | Rule `contains_garbage_or_placeholders` |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | Hash ổn định từ doc_id, text và seq |
| doc_id | string | Có | Khóa logic từ hệ nguồn (vd policy_refund_v4) |
| chunk_text | string | Có | Nội dung chunk đã được loại bỏ ký tự rác |
| effective_date | date | Có | Ngày hiệu lực, chuẩn hóa YYYY-MM-DD |
| exported_at | datetime | Có | Dùng để đo lường freshness SLA |

---

## 3. Quy tắc quarantine vs drop

> Record bị flag đi đâu? Ai approve merge lại?

Record vi phạm luật (như chứa ký tự lạ, date không hợp lệ, chính sách stale) sẽ bị đưa vào `artifacts/quarantine/quarantine_<run-id>.csv` với cột `reason` chỉ định rõ lý do.
Các bản ghi này không được tự động merge. Chủ sở hữu (Quality Owner) sẽ xem xét, báo cáo đội ngũ upstream (Ingestion) để fix từ hệ thống gốc. Sau đó, chạy lại pipeline một cách tự động (idempotent).

---

## 4. Phiên bản & canonical

> Source of truth cho policy refund: file nào / version nào?

Source of truth là các file nguyên bản nằm ở `data/docs/` (ví dụ: `data/docs/policy_refund_v4.txt`). Bất kỳ khi nào có bất đồng versioning (HR policy >= 2026-01-01), rule và expectation chặn và ưu tiên version mới hơn.
