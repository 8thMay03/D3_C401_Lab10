# Kiến trúc pipeline — Lab Day 10

**Nhóm:** ____________________  
**Cập nhật:** 2026-04-15

---

## 1. Sơ đồ luồng

```text
data/raw/policy_export_dirty.csv
        |
        | ingest (etl_pipeline.py run)
        | - ghi log: run_id, raw_records
        v
transform/cleaning_rules.py
        |
        | clean + normalize
        | - allowlist doc_id
        | - normalize effective_date
        | - quarantine stale HR / duplicate / missing field
        | - fix refund window 14 -> 7
        |
        +--> artifacts/quarantine/quarantine_<run_id>.csv
        |
        v
artifacts/cleaned/cleaned_<run_id>.csv
        |
        | validate (quality/expectations.py)
        | - halt: stale refund, non-ISO date, empty doc_id, stale HR text
        | - warn: chunk quá ngắn
        v
embed Chroma collection `day10_kb`
        |
        | upsert theo chunk_id
        | prune vector không còn trong cleaned snapshot
        v
retrieval / Day 08-09 serving

song song:
- manifest: artifacts/manifests/manifest_<run_id>.json
- freshness: monitoring/freshness_check.py đọc latest_exported_at từ manifest
```

**Điểm quan sát chính**

- `run_id` được ghi ngay từ đầu log và đi tiếp vào metadata của vector.
- `quarantine` là biên publish rõ ràng: record bị loại sẽ không vào cleaned CSV và không được embed.
- `freshness` đo sau khi manifest được ghi, dùng `latest_exported_at` so với SLA cấu hình.

---

## 2. Ranh giới trách nhiệm

| Thành phần | Input | Output | Owner nhóm |
|------------|-------|--------|------------|
| Ingest | `data/raw/policy_export_dirty.csv` | `rows` trong memory, log `raw_records` | ____________________ |
| Transform | raw rows | `artifacts/cleaned/cleaned_<run_id>.csv`, `artifacts/quarantine/quarantine_<run_id>.csv` | ____________________ |
| Quality | cleaned rows | expectation results, quyết định halt / continue | ____________________ |
| Embed | cleaned CSV | collection Chroma `day10_kb` | ____________________ |
| Monitor | manifest JSON | trạng thái `PASS/WARN/FAIL` cho freshness | ____________________ |

---

## 3. Idempotency & rerun

Pipeline đang dùng chiến lược snapshot publish khá rõ ràng:

- `chunk_id` được sinh ổn định từ `doc_id + chunk_text + seq` bằng SHA-256 rút gọn.
- Khi embed, pipeline `upsert` theo `chunk_id` nên rerun cùng một cleaned snapshot sẽ cập nhật lại record thay vì tạo duplicate vector.
- Trước khi `upsert`, code đọc toàn bộ `ids` hiện có trong collection và `delete` các id không còn xuất hiện trong cleaned CSV hiện tại. Điều này giúp collection phản ánh đúng trạng thái publish mới nhất, tránh trường hợp vector cũ vẫn còn nằm trong top-k retrieval.
- Evidence trong repo cho thấy các run `ci-smoke`, `ci-smoke2`, `sprint1` và `2026-04-15T05-11Z` đều tạo ra cùng số `cleaned_records=6`, phù hợp với kỳ vọng rerun ổn định trên cùng một input.

Điểm cần lưu ý là `seq` phụ thuộc thứ tự record sau clean. Nếu tương lai nhóm thay đổi chiến lược sort hoặc thêm rule làm thay đổi thứ tự giữ lại record, `chunk_id` có thể đổi dù nội dung không đổi. Khi đó nên cân nhắc hash trực tiếp theo `doc_id + normalized_text` để ổn định hơn nữa.

---

## 4. Liên hệ Day 09

Lab Day 10 xử lý tầng dữ liệu trước khi retrieval/agent của Day 09 đọc vào corpus:

- `data/docs/*.txt` là canonical knowledge source ở mức tài liệu.
- `data/raw/policy_export_dirty.csv` mô phỏng lớp export trung gian từ hệ nguồn, nơi phát sinh duplicate, stale policy, sai format ngày và unknown catalog.
- Sau khi clean và validate, cleaned snapshot được embed vào Chroma collection `day10_kb`.
- Retrieval trong `eval_retrieval.py` đang truy vấn trực tiếp collection này, nên về mặt kiến trúc đây chính là lớp publish-ready mà Day 09 có thể tiêu thụ lại nếu muốn nối chung KB.

Nói ngắn gọn: Day 09 tập trung orchestration và trả lời; Day 10 đảm bảo dữ liệu đưa vào retrieval là đúng version, có quarantine, có manifest, và có log để debug khi câu trả lời sai.

---

## 5. Rủi ro đã biết

- `freshness_check` đang fail trên artifact hiện có vì `latest_exported_at=2026-04-10T08:00:00` đã vượt SLA 24 giờ. Đây là fail hợp lý cho data snapshot cũ, nhưng cần ghi rõ trong runbook để tránh hiểu nhầm là pipeline hỏng.
- Repo hiện chưa có `artifacts/eval/*.csv` được commit, nên evidence before/after retrieval cần chạy lại sau khi cài đủ dependency cho môi trường local.
- Rule fix refund đang thay thẳng chuỗi `"14 ngày làm việc"` sang `"7 ngày làm việc"`. Cách này phù hợp cho lab nhưng vẫn là hard-coded business rule.
- `allowed_doc_ids` trong cleaning chưa bao gồm `data/docs/access_control_sop.txt`, nên nếu nhóm muốn ingest thêm tài liệu này phải cập nhật đồng bộ contract và cleaning rules.
