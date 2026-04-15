# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Quang Minh  
**Vai trò:** Ingestion / Cleaning / Embed / Monitoring — Cleaning / Quality Owner (expectations.py)  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ** (ngắn hơn Day 09 vì rubric slide cá nhân ~10% — vẫn phải đủ bằng chứng)

---

> Viết **"tôi"**, đính kèm **run_id**, **tên file**, **đoạn log** hoặc **dòng CSV** thật.  
> Nếu làm phần clean/expectation: nêu **một số liệu thay đổi** (vd `quarantine_records`, `hits_forbidden`, `top1_doc_expected`) khớp bảng `metric_impact` của nhóm.  
> Lưu: `reports/individual/[ten_ban].md`

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**

- `expectations.py` (data quality rules)
- `artifacts/cleaned/*.csv`
- `artifacts/quarantine/*.csv`
- `logs/run_*.log`

Tôi phụ trách phần **Cleaning & Data Quality**, cụ thể là thiết kế và triển khai các expectation trong `expectations.py` để đảm bảo dữ liệu trước khi embed là chính xác và không chứa thông tin lỗi hoặc outdated. Tôi cũng chịu trách nhiệm format dữ liệu quarantine và đảm bảo pipeline loại bỏ các record không hợp lệ.

**Kết nối với thành viên khác:**

Output cleaned của tôi được dùng trực tiếp cho embedding và retrieval evaluation (`eval_retrieval.py`). Nếu cleaning sai, hệ thống sẽ retrieve nhầm dữ liệu (ví dụ stale policy), ảnh hưởng trực tiếp đến `hits_forbidden`.

**Bằng chứng (commit / comment trong code):**
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
WARN: expectation failed but --skip-validate → tiếp tục embed
_________________

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Một quyết định quan trọng tôi đưa ra là phân loại expectation thành hai loại: **`halt` và `warn`** trong `expectations.py`.

Các rule liên quan trực tiếp đến business correctness (ví dụ `refund_no_stale_14d_window`, `hr_leave_no_stale_10d_annual`) được set là `halt`, vì nếu dữ liệu sai vẫn được embed thì hệ thống sẽ trả lời sai cho user. Ngược lại, các rule về chất lượng phụ (ví dụ `chunk_min_length_8`, `no_future_effective_date`) được set là `warn` để pipeline vẫn chạy.

Ví dụ trong `run_id=inject-bad`:
expectation[refund_no_stale_14d_window] FAIL (halt)

Pipeline chỉ tiếp tục vì có flag `--skip-validate` (phục vụ demo). Quyết định này giúp đảm bảo **critical errors bị chặn**, trong khi vẫn giữ pipeline linh hoạt cho testing.
_________________

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

> Mô tả triệu chứng → metric/check nào phát hiện → fix.

Một anomaly quan trọng là **refund policy bị sai (14 ngày thay vì 7 ngày)** trong run:
run_id=inject-bad
Triệu chứng xuất hiện trong cleaned file:
Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc...
Expectation `refund_no_stale_14d_window` phát hiện lỗi:
violations=1

Tuy nhiên do chạy với `--skip-validate`, dữ liệu này vẫn được embed, gây risk cho retrieval.

Fix của tôi là đảm bảo cleaning step rewrite hoặc loại bỏ nội dung stale, thể hiện trong `run_id=final-clean`:
[cleaned: stale_refund_window]
Kết quả log:
expectation[refund_no_stale_14d_window] OK (halt) :: violations=0
_________________

---

## 4. Bằng chứng trước / sau (80–120 từ)

> Dán ngắn 2 dòng từ `before_after_eval.csv` hoặc tương đương; ghi rõ `run_id`.

So sánh từ `eval/after_inject_bad.csv`:
q_refund_window,...,contains_expected=yes,hits_forbidden=yes
Sau khi clean (`run_id=final-clean`):
q_refund_window,...,contains_expected=yes,hits_forbidden=no
Metric `hits_forbidden` giảm từ **yes → no**, cho thấy hệ thống không còn retrieve dữ liệu sai (14 ngày). Đồng thời `contains_expected` vẫn giữ `yes`, đảm bảo không làm mất dữ liệu đúng (7 ngày).

_________________

---

## 5. Cải tiến tiếp theo (40–80 từ)

> Nếu có thêm 2 giờ — một việc cụ thể (không chung chung).

Nếu có thêm 2 giờ, tôi sẽ triển khai **freshness enforcement ở mức halt**, tức là nếu:
freshness_check=FAIL
(thấy trong `run_final-clean.log` với `age_hours=121.9 > SLA 24h`), pipeline sẽ **chặn embed hoàn toàn**, thay vì chỉ log warning, để tránh dữ liệu outdated đi vào hệ thống production.
_________________
