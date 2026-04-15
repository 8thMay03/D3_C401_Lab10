# Runbook — Lab Day 10

---

## 1. Symptom

Các triệu chứng chính mà user hoặc agent có thể gặp:

- Trả lời sai version chính sách, ví dụ trả về `14 ngày làm việc` thay vì `7 ngày làm việc`.
- Trả lời nhầm policy HR cũ `10 ngày phép năm` thay vì bản 2026 là `12 ngày phép năm`.
- Retrieval không sai hẳn top-1 nhưng trong top-k vẫn còn chunk stale, làm `hits_forbidden=yes`.
- Pipeline chạy xong nhưng dữ liệu vẫn bị xem là quá cũ vì `freshness_check=FAIL`.
- Số lượng record publish giảm bất thường, hoặc quarantine tăng đột ngột.

---

## 2. Detection

Các tín hiệu phát hiện nên kiểm tra theo thứ tự:

- Log pipeline trong `artifacts/logs/run_<run_id>.log`
  - bắt buộc có `run_id`, `raw_records`, `cleaned_records`, `quarantine_records`
  - expectation fail mức `halt` sẽ hiện `PIPELINE_HALT`
- Manifest trong `artifacts/manifests/manifest_<run_id>.json`
  - kiểm tra `latest_exported_at`
  - kiểm tra `no_refund_fix` và `skipped_validate`
- Quarantine CSV trong `artifacts/quarantine/`
  - xem distribution theo cột `reason`
- Eval retrieval trong `artifacts/eval/*.csv`
  - đặc biệt theo dõi `contains_expected`, `hits_forbidden`, `top1_doc_expected`

Ưu tiên debug theo đúng README:

```text
Freshness / version -> Volume & errors -> Schema & contract -> Lineage / run_id -> model / prompt
```

---

## 3. Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Mở manifest mới nhất: `cat artifacts/manifests/manifest_<run_id>.json` | Xác nhận đúng raw path, đúng run_id, `cleaned_records` và `quarantine_records` khớp log |
| 2 | Mở log run: `cat artifacts/logs/run_<run_id>.log` | Thấy toàn bộ expectation `OK` hoặc biết chính xác expectation nào fail |
| 3 | So sánh quarantine: `reason` nào tăng | Xác định lỗi đến từ duplicate, stale HR, missing date hay unknown doc |
| 4 | Nếu lỗi retrieval, chạy `python3 eval_retrieval.py --out artifacts/eval/before_after_eval.csv` | Xem câu nào bị `hits_forbidden=yes` hoặc `contains_expected=no` |
| 5 | Nếu lỗi freshness, chạy `python3 etl_pipeline.py freshness --manifest artifacts/manifests/manifest_<run_id>.json` | Phân biệt lỗi do snapshot cũ hay do manifest thiếu timestamp |

**Ví dụ diagnosis trên artifact hiện có**

- `run_sprint1.log` cho thấy pipeline chuẩn pass expectation và publish `cleaned_records=6`.
- Tuy nhiên `freshness_check=FAIL` vì `latest_exported_at` là `2026-04-10T08:00:00`, cũ hơn SLA 24 giờ.
- `quarantine_sprint1.csv` cho thấy 4 record bị loại với các lý do: duplicate, missing date, stale HR, unknown doc.

---

## 4. Mitigation

### Case A: refund answer bị stale

- Chạy pipeline chuẩn, không dùng `--no-refund-fix`.
- Không dùng `--skip-validate` trong run production.
- Xác nhận log có `expectation[refund_no_stale_14d_window] OK`.

### Case B: HR leave policy bị nhầm version

- Kiểm tra raw export có record `effective_date < 2026-01-01` hay không.
- Đảm bảo record cũ vào quarantine với `reason=stale_hr_policy_effective_date`.
- Rerun pipeline để publish snapshot mới và prune vector cũ khỏi collection.

### Case C: freshness fail

- Nếu đây là snapshot lab cũ: ghi chú rõ trong report rằng FAIL là expected theo SLA.
- Nếu đây là production-like run: cập nhật nguồn export, hoặc điều chỉnh `FRESHNESS_SLA_HOURS` cho đúng boundary đã thống nhất.

### Case D: eval retrieval xấu sau inject

- Rerun pipeline chuẩn:

```bash
python3 etl_pipeline.py run --run-id rerun-clean
python3 eval_retrieval.py --out artifacts/eval/before_after_eval.csv
```

- So sánh lại với file inject để chứng minh retrieval đã hồi phục.

---

## 5. Prevention

- Không publish trực tiếp từ raw export vào vector DB; luôn đi qua clean -> validate -> manifest.
- Giữ `halt` cho các expectation liên quan version correctness:
  - stale refund window
  - non-ISO effective date
  - stale HR annual leave text
- Theo dõi `quarantine_records` và top `reason` để phát hiện drift sớm.
- Ghi `run_id` vào mọi artifact để truy vết từ câu trả lời sai về đúng snapshot đã publish.
- Đồng bộ mọi thay đổi business rule vào cả 3 nơi:
  - [contracts/data_contract.yaml](/Users/cinne/Documents/GitHub/D3_C401_Lab10/contracts/data_contract.yaml)
  - [docs/data_contract.md](/Users/cinne/Documents/GitHub/D3_C401_Lab10/docs/data_contract.md)
  - [transform/cleaning_rules.py](/Users/cinne/Documents/GitHub/D3_C401_Lab10/transform/cleaning_rules.py)
