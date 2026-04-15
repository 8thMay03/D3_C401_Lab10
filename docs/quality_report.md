# Quality report — Lab Day 10

**run_id:** `2026-04-15T05-11Z`  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước inject / baseline hiện có | Sau clean publish | Ghi chú |
|--------|----------------------------------|-------------------|---------|
| `raw_records` | 10 | 10 | Theo [manifest_2026-04-15T05-11Z.json](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/manifests/manifest_2026-04-15T05-11Z.json) |
| `cleaned_records` | 6 | 6 | Clean giữ lại 6 record hợp lệ để publish |
| `quarantine_records` | 4 | 4 | 4 record bị loại sang quarantine |
| Expectation halt? | Không | Không | Tất cả expectation trong log đều `OK`; `chunk_min_length_8` là `warn` nhưng cũng pass |

**Chi tiết quarantine hiện có**

- `duplicate_chunk_text`: 1
- `missing_effective_date`: 1
- `stale_hr_policy_effective_date`: 1
- `unknown_doc_id`: 1

Nguồn số liệu: [run_2026-04-15T05-11Z.log](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/logs/run_2026-04-15T05-11Z.log) và [quarantine_sprint1.csv](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/quarantine/quarantine_sprint1.csv).

---

## 2. Before / after retrieval

README yêu cầu có evidence retrieval cho ít nhất `q_refund_window`, và khuyến nghị thêm `q_leave_version`. Nhóm đã chạy đủ 3 trạng thái:

- clean chuẩn: [before_after_eval.csv](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/eval/before_after_eval.csv)
- inject corruption: [after_inject_bad.csv](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/eval/after_inject_bad.csv)
- clean lại để phục hồi: [after_restore_eval.csv](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/eval/after_restore_eval.csv)

**Câu hỏi then chốt: `q_refund_window`**

- Clean chuẩn:
  - `top1_doc_id=policy_refund_v4`
  - `contains_expected=yes`
  - `hits_forbidden=no`
- Sau inject `--no-refund-fix --skip-validate`:
  - `top1_doc_id=policy_refund_v4`
  - `contains_expected=yes`
  - `hits_forbidden=yes`
- Sau restore clean:
  - `top1_doc_id=policy_refund_v4`
  - `contains_expected=yes`
  - `hits_forbidden=no`

Điểm quan trọng là sau inject, top-1 preview vẫn nhìn có vẻ đúng nhưng top-k đã chứa chunk stale `14 ngày làm việc`. Đây là bằng chứng rõ cho việc chất lượng retrieval có thể suy giảm dù câu trả lời bề mặt chưa sai hẳn.

**Câu `q_leave_version`**

- Clean chuẩn:
  - `contains_expected=yes`
  - `hits_forbidden=no`
  - `top1_doc_expected=yes`
- Sau inject:
  - `contains_expected=yes`
  - `hits_forbidden=no`
  - `top1_doc_expected=yes`

Kết quả này cho thấy inject refund chỉ làm hỏng lát dữ liệu refund, còn biên quarantine cho HR stale vẫn bảo vệ tốt policy nghỉ phép 2026.

---

## 3. Freshness & monitor

Kết quả freshness trên manifest hiện có là `FAIL`.

Lý do:

- `latest_exported_at`: `2026-04-10T08:00:00`
- SLA cấu hình: `24` giờ
- Tuổi dữ liệu trong log khoảng `117` giờ tại thời điểm run

Điều này không có nghĩa clean hoặc embed bị lỗi. Nó chỉ cho thấy snapshot export đang cũ hơn SLA publish đã định trong contract. Với lab này, `FAIL` là diễn giải hợp lệ nếu nhóm muốn chứng minh observability đang bắt được dữ liệu stale.

---

## 4. Corruption inject (Sprint 3)

Kịch bản inject mà README gợi ý là:

```bash
python3 etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
python3 eval_retrieval.py --out artifacts/eval/after_inject_bad.csv
```

Ý nghĩa:

- `--no-refund-fix`: giữ nguyên chunk stale `"14 ngày làm việc"`
- `--skip-validate`: cho phép embed dù expectation halt, chỉ dùng để demo chất lượng retrieval giảm đi

Kỳ vọng khi inject:

- `q_refund_window` có nguy cơ `hits_forbidden=yes`
- Nếu inject thêm bản HR cũ và vẫn publish, `q_leave_version` có nguy cơ trả về `10 ngày phép năm` hoặc `top1_doc_expected=no`

Artifact inject đã có đầy đủ:

- [manifest_inject-bad.json](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/manifests/manifest_inject-bad.json)
- [run_inject-bad.log](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/logs/run_inject-bad.log)
- [after_inject_bad.csv](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/eval/after_inject_bad.csv)

---

## 5. Hạn chế & việc chưa làm

- Chưa có `data/grading_questions.json` trong repo hiện tại nên chưa thể sinh `artifacts/eval/grading_run.jsonl`.
- `owner_team` và `alert_channel` trong YAML contract vẫn cần nhóm điền trước khi nộp.
