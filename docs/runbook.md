# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

> User / agent thấy gì? (VD: trả lời “14 ngày” thay vì 7 ngày)

User phàn nàn Agent trả lời sai logic chính sách cũ, VD: bảo HR leave vẫn dùng "10 ngày phép năm" (thực tế bỏ đi, HR mới >2026), hoặc refund là "14 ngày làm việc" (thay vì 7 ngày mới).

---

## Detection

> Metric nào báo? (freshness, expectation fail, eval `hits_forbidden`)

1. Trigger Alert Expectation: `refund_no_stale_14d_window` (fail) và Pipeline HALT báo hiệu.
2. Retrieval Eval cho thấy metrics `hits_forbidden` gia tăng ở top-k list.
3. Lệnh giám sát SLA `python etl_pipeline.py freshness` báo status `FAIL`.

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/*.json` | Nhìn vào timestamp, count record, xem `skipped_validate` để check xem pipeline failed ở ingest hay check. |
| 2 | Mở `artifacts/quarantine/*.csv` | Kiểm tra nguyên nhân flag (reason), thấy raw data chứa bao nhiêu records là rác hay mismatch ISO date. |
| 3 | Mở logs `artifacts/logs/run_*.log` | Kiểm tra dòng Expectation detail, track ID cụ thể bị lỗi. |
| 4 | Chạy `python eval_retrieval.py` | Kiểm tra file `before_after_eval.csv` xem top 1 vector đang chỉ về chunk nào, expectation text nào. |

---

## Mitigation

> Rerun pipeline, rollback embed, tạm banner “data stale”, …

Tạm thời cô lập: Nếu pipeline thất bại vì bad source. Có thể roll back vector DB hoặc ngừng cron job ingest. Bật cleaning filter `apply_refund_window_fix=True` để fix 14 -> 7 days. Fix xong rerun `python etl_pipeline.py run` để embed tự động overwrite vector theo logic prune và clean source text.

---

## Prevention

> Thêm expectation, alert, owner — nối sang Day 11 nếu có guardrail.

Bắt chặt Data Contract và Expectations: `effective_date_iso_yyyy_mm_dd` và `min_one_row`.
Tiến hành tích hợp alert Slack/PagerDuty khi `should_halt=True` tới Data Quality Owner. Nối guardrail ở runtime Day 11 cho Agent - kiểm duyệt context window output không chứa hard keyword "14 ngày làm việc".
