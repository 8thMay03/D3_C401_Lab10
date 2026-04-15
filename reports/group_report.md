# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** ___________  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| ___ | Ingestion / Raw Owner | ___ |
| ___ | Cleaning & Quality Owner | ___ |
| ___ | Embed & Idempotency Owner | ___ |
| ___ | Monitoring / Docs Owner | ___ |

**Ngày nộp:** 2026-04-15  
**Repo:** `D3_C401_Lab10`  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

Nguồn raw của nhóm là file export mô phỏng [data/raw/policy_export_dirty.csv](/Users/cinne/Documents/GitHub/D3_C401_Lab10/data/raw/policy_export_dirty.csv). File này cố ý chứa nhiều lỗi thường gặp ở lớp ingest như duplicate chunk, thiếu `effective_date`, `doc_id` lạ ngoài allowlist, một bản refund policy cũ còn ghi `14 ngày làm việc`, và một record HR 2025 mâu thuẫn với policy 2026. Pipeline được chạy qua entrypoint [etl_pipeline.py](/Users/cinne/Documents/GitHub/D3_C401_Lab10/etl_pipeline.py), đi theo chuỗi ingest -> clean -> validate -> embed -> manifest/freshness. Trong quá trình chạy, hệ thống sinh log vào `artifacts/logs/`, cleaned snapshot vào `artifacts/cleaned/`, quarantine vào `artifacts/quarantine/`, và manifest vào `artifacts/manifests/`.

Artifact chuẩn hiện có trong repo là run `sprint1` và `2026-04-15T05-11Z`. Cả hai đều ghi nhận `raw_records=10`, `cleaned_records=6`, `quarantine_records=4`, cho thấy pipeline ổn định khi rerun cùng một input. `run_id` được ghi ngay đầu log, ví dụ trong [run_sprint1.log](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/logs/run_sprint1.log) có dòng `run_id=sprint1`. Nhờ vậy nhóm có thể truy vết từ câu trả lời retrieval sai quay lại đúng snapshot dữ liệu đã publish.

**Tóm tắt luồng:**

`data/raw/policy_export_dirty.csv` -> `transform/cleaning_rules.py` -> `quality/expectations.py` -> Chroma collection `day10_kb` -> `artifacts/manifests/manifest_<run_id>.json` -> `monitoring/freshness_check.py`

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

```bash
.venv/bin/python etl_pipeline.py run --run-id sprint1
```

---

## 2. Cleaning & expectation (150–200 từ)

Pipeline clean hiện xử lý đầy đủ các lỗi chính trong raw export. Các rule baseline đang hoạt động gồm: allowlist `doc_id`, chuẩn hóa `effective_date`, quarantine HR policy cũ có ngày hiệu lực trước `2026-01-01`, loại record thiếu trường bắt buộc, loại duplicate theo normalized `chunk_text`, và sửa chunk refund stale từ `14 ngày làm việc` sang `7 ngày làm việc`. Trên run `sprint1`, 4 record bị đưa sang quarantine với đúng 4 loại lỗi khác nhau: duplicate, missing effective date, stale HR policy, và unknown doc id.

Expectation suite hiện có 6 kiểm tra. Các expectation mức `halt` là `min_one_row`, `no_empty_doc_id`, `refund_no_stale_14d_window`, `effective_date_iso_yyyy_mm_dd`, và `hr_leave_no_stale_10d_annual`. Expectation mức `warn` là `chunk_min_length_8`. Ở artifact chuẩn hiện có, toàn bộ expectation đều pass nên pipeline tiếp tục embed và ghi manifest. Cách phân tầng `warn` và `halt` giúp nhóm phân biệt lỗi có thể cho chạy tiếp với lỗi ảnh hưởng trực tiếp đến correctness của retrieval.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| `duplicate_chunk_text` quarantine | Raw có 2 chunk refund trùng nhau | Quarantine tăng thêm 1 record, cleaned chỉ giữ 1 bản | [quarantine_sprint1.csv](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/quarantine/quarantine_sprint1.csv) |
| `stale_hr_policy_effective_date` quarantine | Raw có 1 bản HR 2025 ghi `10 ngày phép năm` | Record bị loại khỏi cleaned, tránh publish version cũ | [quarantine_sprint1.csv](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/quarantine/quarantine_sprint1.csv) |
| `refund_no_stale_14d_window` halt | Raw có 1 chunk chứa `14 ngày làm việc` | Sau clean, `violations=0` trong log chuẩn | [run_sprint1.log](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/logs/run_sprint1.log) |
| `effective_date_iso_yyyy_mm_dd` halt | Raw có ngày dạng `01/02/2026` | Sau clean, `non_iso_rows=0` | [run_sprint1.log](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/logs/run_sprint1.log) |

**Rule chính (baseline + mở rộng):**

- Allowlist `doc_id`
- Chuẩn hóa `effective_date` về `YYYY-MM-DD`
- Quarantine record HR stale trước `2026-01-01`
- Quarantine record thiếu `effective_date` hoặc `chunk_text`
- Dedupe theo normalized text
- Rewrite refund stale `14 -> 7`

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

Kịch bản fail dự kiến của nhóm là chạy inject với `--no-refund-fix --skip-validate`. Khi đó expectation `refund_no_stale_14d_window` sẽ fail vì cleaned snapshot vẫn còn chunk cũ `14 ngày làm việc`. Với run production, cách xử lý là bỏ flag inject, chạy lại pipeline chuẩn để expectation trở về `OK` rồi mới publish vào collection.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

Mục tiêu chính của phần này là chứng minh chất lượng retrieval thay đổi theo chất lượng dữ liệu. Kịch bản inject của nhóm bám README: chạy pipeline với `--no-refund-fix --skip-validate` để cố tình embed chunk refund stale vào collection. Khi đó về mặt kỳ vọng, câu `q_refund_window` sẽ có nguy cơ trả về top-k chứa `14 ngày làm việc`, tức `hits_forbidden=yes`. Tương tự, nếu một bản HR cũ bị lọt qua publish boundary thì câu `q_leave_version` có thể chứa `10 ngày phép năm` hoặc `top1_doc_expected=no`.

**Kịch bản inject:**

```bash
.venv/bin/python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate
.venv/bin/python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv
```

**Kết quả định lượng (từ CSV / bảng):**

Nhóm đã chạy đủ 3 trạng thái và sinh được artifact thật:

- [before_after_eval.csv](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/eval/before_after_eval.csv)
- [after_inject_bad.csv](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/eval/after_inject_bad.csv)
- [after_restore_eval.csv](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/eval/after_restore_eval.csv)

Kết quả rõ nhất nằm ở câu `q_refund_window`. Ở run clean chuẩn, dòng CSV cho thấy `contains_expected=yes` và `hits_forbidden=no`. Sau khi inject bằng `--no-refund-fix --skip-validate`, cùng câu này chuyển thành `contains_expected=yes` nhưng `hits_forbidden=yes`. Điều đó nghĩa là top-k retrieval đã lẫn chunk stale `14 ngày làm việc`, dù top-1 preview vẫn nhìn có vẻ đúng. Sau khi chạy lại pipeline chuẩn ở `clean-restored`, chỉ số trở về `hits_forbidden=no`, xác nhận publish boundary và prune index đang hoạt động đúng.

Với câu `q_leave_version`, cả run chuẩn lẫn run inject đều cho `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`. Điều này chứng minh biên quarantine cho HR stale đang bảo vệ tốt knowledge base: inject ở refund làm hỏng refund retrieval, nhưng không kéo theo regression ở policy nghỉ phép.

---

## 4. Freshness & monitoring (100–150 từ)

Nhóm dùng freshness SLA mặc định `24 giờ` theo [contracts/data_contract.yaml](/Users/cinne/Documents/GitHub/D3_C401_Lab10/contracts/data_contract.yaml), đo tại boundary `publish`. Trên [manifest_sprint1.json](/Users/cinne/Documents/GitHub/D3_C401_Lab10/artifacts/manifests/manifest_sprint1.json), `latest_exported_at` là `2026-04-10T08:00:00`, trong khi thời điểm run ở log muộn hơn khoảng 117 giờ, nên `freshness_check=FAIL`. Đây là một kết quả hợp lý chứ không phải lỗi code, vì snapshot nguồn đang cũ hơn SLA đã cam kết.

Ý nghĩa ba mức trạng thái là: `PASS` khi tuổi dữ liệu không vượt SLA; `WARN` khi manifest thiếu timestamp hoặc không parse được; `FAIL` khi dữ liệu quá hạn. Việc có freshness check giúp nhóm tách bạch hai loại lỗi: pipeline có thể chạy thành công về mặt kỹ thuật nhưng vẫn không an toàn để publish nếu dữ liệu đã stale.

---

## 5. Liên hệ Day 09 (50–100 từ)

Có. Day 10 bổ sung lớp kiểm soát dữ liệu trước khi retrieval của Day 09 sử dụng corpus. Collection hiện dùng là `day10_kb`, tách riêng để quan sát rõ ảnh hưởng của clean, quarantine và freshness lên retrieval. Tuy nhiên về mặt kiến trúc, collection này hoàn toàn có thể được Day 09 dùng lại như published snapshot cho agent sau khi pipeline pass expectation.

---

## 6. Rủi ro còn lại & việc chưa làm

- Đã có artifact eval thật cho before/inject/restore, nhưng repo vẫn thiếu `data/grading_questions.json` nên chưa sinh được `artifacts/eval/grading_run.jsonl`.
- Rule refund hiện vẫn hard-code thay chuỗi `14 ngày làm việc` sang `7 ngày làm việc`; nếu mở rộng production nên đọc cutoff/rule từ contract hoặc env.
- `owner_team` và `alert_channel` trong YAML contract vẫn là placeholder, cần điền trước khi nộp chính thức.
