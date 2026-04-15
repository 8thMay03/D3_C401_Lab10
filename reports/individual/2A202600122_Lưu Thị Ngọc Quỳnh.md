# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Lưu Thị Ngọc Quỳnh  
**Vai trò:** Monitoring  
**Ngày nộp:** 15 - 04 - 2026 
**Độ dài yêu cầu:** **400–650 từ** (ngắn hơn Day 09 vì rubric slide cá nhân ~10% — vẫn phải đủ bằng chứng)

---

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.  
> Nếu làm phần clean/expectation: nêu **một số liệu thay đổi** (vd `quarantine_records`, `hits_forbidden`, `top1_doc_expected`) khớp bảng `metric_impact` của nhóm.  
> Lưu: `reports/individual/[ten_ban].md`

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `monitoring/freshness_check.py`
- `docs/quality_report.md`
- phần log/manifest trong `etl_pipeline.py`

**Kết nối với thành viên khác:**

Tôi phụ trách một phần nhỏ ở khâu monitoring, chủ yếu là kiểm tra log và manifest sau khi pipeline chạy xong để xem dữ liệu có còn đủ mới và có dấu hiệu bất thường hay không. Tôi đọc `artifacts/manifests/manifest_2026-04-15T05-11Z.json`, đối chiếu `artifacts/logs/run_2026-04-15T05-11Z.log` và xem thêm `artifacts/eval/before_after_eval.csv` để ghi lại kết quả freshness và before/after. Phần này hỗ trợ cho các bạn làm Cleaning và Embed, chứ tôi không trực tiếp xử lý toàn bộ pipeline.

**Bằng chứng (commit / comment trong code):**

Trong log run tốt `run_id=2026-04-15T05-11Z`, tôi dùng các dòng:
`manifest_written=artifacts/manifests/manifest_2026-04-15T05-11Z.json`
và
`freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 117.218, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}`
để làm bằng chứng phần monitor tôi theo dõi có hoạt động đúng.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

> VD: chọn halt vs warn, chiến lược idempotency, cách đo freshness, format quarantine.

Phần quyết định kỹ thuật mà tôi hiểu và theo dõi rõ nhất là check freshness nên được tách riêng khỏi expectation. Tôi không để freshness làm dừng pipeline, mà chỉ dùng nó như một tín hiệu cảnh báo qua `check_manifest_freshness(...)` trong `monitoring/freshness_check.py`. Lý do là có trường hợp dữ liệu vẫn sạch và chạy được, nhưng file export đã cũ hơn SLA nên cần báo cho nhóm biết. Với `manifest_2026-04-15T05-11Z.json`, trường `latest_exported_at` là `2026-04-10T08:00:00`; so với SLA `24 giờ`, hệ thống trả `FAIL` vì `age_hours=117.218`. Theo tôi, cách này dễ theo dõi hơn và giúp nhóm phân biệt lỗi dữ liệu với lỗi độ mới.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

> Mô tả triệu chứng → metric/check nào phát hiện → fix.

Anomaly tôi theo dõi rõ nhất là case inject corruption cho policy hoàn tiền. Ở run `inject-bad`, log `artifacts/logs/run_inject-bad.log` ghi:
`expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`
nhưng vì chạy với `--skip-validate`, pipeline vẫn tiếp tục embed. Tôi dùng thêm `artifacts/eval/after_eval_bad.csv` để xác nhận hậu quả ở tầng retrieval: dòng `q_refund_window` có `hits_forbidden=yes`. Sau khi chạy lại pipeline chuẩn, expectation này trở về `OK` trong `run_2026-04-15T05-11Z.log`, còn `before_after_eval.csv` chuyển `hits_forbidden` từ `yes` sang `no`. Phần tôi làm chủ yếu là đọc các dấu hiệu này và ghi lại để nhóm dễ giải thích trong report.

---

## 4. Bằng chứng trước / sau (80–120 từ)

> Dán ngắn 2 dòng từ `before_after_eval.csv` hoặc tương đương; ghi rõ `run_id`.

Tôi dùng đúng câu hỏi `q_refund_window` để chứng minh before/after:

**Trước, run_id: `inject-bad`**  
Từ `artifacts/eval/after_eval_bad.csv`:
`q_refund_window,Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi xác nhận đơn?,policy_refund_v4,...,yes,yes,,3`

**Sau, run_id: `2026-04-15T05-11Z`**  
Từ `artifacts/eval/before_after_eval.csv`:
`q_refund_window,Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi xác nhận đơn?,policy_refund_v4,...,yes,no,,3`

Điểm thay đổi tôi theo dõi là `hits_forbidden`: từ `yes` xuống `no`. Với monitor, đây là tín hiệu quan trọng hơn chỉ nhìn `contains_expected`, vì nó phát hiện việc index còn lưu context đã hết hiệu lực.

---

## 5. Cải tiến tiếp theo (40–80 từ)

> Nếu có thêm 2 giờ — một việc cụ thể (không chung chung).

Nếu có thêm 2 giờ, tôi sẽ làm thêm một alert đơn giản cho trường hợp `freshness_check=FAIL`, ví dụ ghi rõ `run_id` và file manifest cần kiểm tra. Như vậy lúc có dữ liệu stale thì nhóm đỡ phải mở log thủ công để tìm lại.
