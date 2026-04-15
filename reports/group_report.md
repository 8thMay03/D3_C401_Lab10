# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Nhóm Day 10  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Đinh Văn Thư + Lưu Quang Lực | Ingestion / Raw Owner | ___ |
| Lý Quốc Anh + Nguyễn Quốc Khánh | Cleaning & Quality Owner | ___ |
| Nguyễn Bá Khánh - Nguyễn Phương Nam | Embed & Idempotency Owner | ___ |
| Lưu Thị Ngọc Quỳnh + Nguyễn Quang Minh | Monitoring / Docs Owner | ___ |

**Ngày nộp:** 15-04-2026  
**Repo:** https://github.com/8thMay03/D3_C401_Lab10.git  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

> Nguồn raw là gì (CSV mẫu / export thật)? Chuỗi lệnh chạy end-to-end? `run_id` lấy ở đâu trong log?

**Tóm tắt luồng:**

Nguồn dữ liệu raw của nhóm là tệp CSV mẫu (giả định xuất khẩu - export - từ cơ sở dữ liệu nội bộ của doanh nghiệp). Pipeline được thiết kế để chạy một chu trình ETL (Extract - Transform - Load) end-to-end hoàn chỉnh. Khởi đầu từ bước Ingestion, hệ thống đọc dữ liệu thô và đẩy qua cho phân hệ Cleaning & Quality làm sạch toàn bộ các thẻ HTML, chuẩn hóa bộ ký tự, đồng thời thanh lọc các luật hết hạn bằng cơ chế Expectation. Các tài liệu nào vi phạm quy tắc Expectation sẽ bị cô lập hoàn toàn sang tệp Quarantine để dev giám định từ đó bảo vệ Data Quality. Cuối cùng, cụm Embed & Idempotency sẽ nhận dữ liệu sạch, sử dụng model `all-MiniLM-L6-v2` để sinh vector và upsert thẳng vào kho ChromaDB. Luồng này vận hành ổn định qua nhiều lần chạy nhờ vào cỡ `chunk_id` băm tĩnh, không sinh ra các đoạn dữ liệu đúp rác. `run_id` được ghi nhận ở dòng đầu tiên ngay khi chạy terminal log.

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

`python etl_pipeline.py run --run-id official_fix`

---

## 2. Cleaning & expectation (150–200 từ)

> Baseline đã có nhiều rule (allowlist, ngày ISO, HR stale, refund, dedupe…). Nhóm thêm **≥3 rule mới** + **≥2 expectation mới**. Khai báo expectation nào **halt**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| `refund_no_stale_14d_window` | Không lỗi (0 violations) | Phát hiện 1 violation (HALT) | Log terminal của luồng `inject-bad` |
| `hr_leave_no_stale_10d_annual` | Không lỗi (0 violations) | 0 violations (trạng thái HALT)| Log pipeline trả về `OK (halt)` |
| `effective_date_iso_yyyy_mm_dd` | Format chuẩn ISO (0 lỗi) | 0 violations (trạng thái HALT)| Ghi nhận từ `cleaned_official_fix.csv` |
| `exported_at_not_in_future` | Khớp biểu mẫu (0 lỗi) | Phát hiện 1 violation (HALT)| Ghi nhận log khi chạy với raw data `policy_export_dirty_fail_exported_at.csv` |

**Rule chính (baseline + mở rộng):**

- Baseline: Làm sạch các format HTML bằng biểu thức chính quy, xóa các dấu câu không cần thiết và những khoảng trắng thừa. Bỏ qua các văn bản nằm trong blacklist.
- `refund_no_stale_14d_window`: Rào chắn chặn hoàn toàn luật "Hoàn tiền 14 ngày" cũ kĩ (Cờ HALT).
- `hr_leave_no_stale_10d_annual`: Loại ngay luật "Ngày phép theo cơ chế cũ: 10 ngày" (Cờ HALT).
- `effective_date_iso_yyyy_mm_dd`: Force dữ liệu ngày tháng bắt buộc theo định dạng năm/tháng/ngày - chuẩn ISO (Cờ HALT).
- `exported_at_not_in_future`: Chặn ngay tập dữ liệu khai khống thời gian ở tương lai đối với trường xuất metadata (Cờ HALT).
- Cảnh báo (WARN) đối với `no_future_effective_date` khi bắt gặp các luật chưa có hiệu lực.

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

Khi nhóm tiến hành nạp dữ liệu từ tệp chứa lỗi `policy_export_dirty_fail_exported_at.csv`, phân hệ quality bắt quả tang tài liệu bị khai khống thời gian và expectation `exported_at_not_in_future` tức khắc báo `FAIL (halt) :: violations=1`. Module sau đó tự động cô lập, vứt luật hỏng vào file quarantine tương ứng thay vì đẩy vào ChromaDB như bình thường.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

Trong Sprint 3, chúng mình chủ động giả lập một hành vi ô nhiễm dữ liệu hệ thống thông qua lệnh test: 
`python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`
Việc tắt thiết bị rà soát qua cờ `--skip-validate` đã kích hoạt lọt một chính sách hoàn tiền 14 ngày (đã quá hạn) vượt tuyến xả thẳng vào trong cụm vector lưu trữ. Kịch bản này phản ánh hoàn hảo việc một chuyên viên update policy chèn nhầm rules cũ mà thiếu vắng chốt chặn quality.

**Kết quả định lượng (từ CSV / bảng):**

- **Trước khi fix (trạng thái ô nhiễm):** Kết quả truy xuất trên pipeline cũ cho thấy câu hỏi "Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền..." đã móc trúng cái luật hoàn tiền 14 ngày cũ. Quan sát log tại `artifacts/eval/after_inject_bad.csv` chúng mình thấy cờ `hits_forbidden` đã đỏ lịm nhảy sang `yes`. Agent LLM lấy cái document này thì chắc chắn sẽ trả lời sai cho khách.
- **Sau khi fix (chạy official_fix):** Chúng mình rà soát tổng hợp, mở chốt chặn rào chắn Quality (Validate) lên và thiết lập cơ chế **Prune IDs**. Bộ dò đường sẽ tìm lại trong ChromaDB và lập tức thủ tiêu những vector có `chunk_id` liên kết nguồn cội tới "14 ngày". Quá trình rà soát ở `artifacts/eval/before_after_eval.csv` khẳng định agent đã lấy chuẩn nội dung mới cứng "7 ngày", cờ `hits_forbidden` khôi phục vạch an toàn (`no`).

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

Bên cạnh luồng xử lý core, hệ thống không quên bố trí lính canh `Freshness` đọc các manifest timestamp thông qua lệnh `python etl_pipeline.py freshness`. Mục tiêu thiết lập cho độ trễ (SLA) lấy dữ liệu source chỉ ở mức 24 giờ.
Ngay khi vận hành, monitor đã nhả alert trạng thái `FAIL` rạch ròi: `{"age_hours": 121.876, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}` do thời điểm xuất lô dữ liệu gần nhất đã thuộc về ngày 10/4/2026. Bằng thông báo kịp thời từ cờ FAIL, kỹ sư lập tức hình dung được tình trạng ứ đọng dữ liệu và sẽ yêu cầu Data Warehouse phải push luồng dump mới ngay nhằm đảm bảo tính current của Agent.

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

Data của pipeline Lab 10 đóng vai trò cốt yếu để cung cấp Knowledge Base cho hệ sinh thái Multi-agent Day 09. Tụi mình thiết lập cụm data này trỏ tới một phân vùng độc lập mang tên `day10_kb`. Khâu Quality Gate đóng vai trò che chắn, bảo vệ các Agent Day 09 miễn nhiễm hoàn toàn với những rủi ro luật lệ hết date, loại bỏ tỷ lệ sinh ra Hallucination trong quy trình gen output mà vẫn đảm bảo tốc độ retrieval.

---

## 6. Rủi ro còn lại & việc chưa làm

- Bộ expectation còn cứng nhắc và bị bó buộc mạnh bởi tính pattern của Regex. Nếu team nghiệp vụ thay đổi cách hành văn, toàn bộ flow Quality có thể bị trượt.
- Chưa ứng dụng thành hình hoàn thiện chu trình lọc linh động (Metadata filtering). Nếu 1 truy vấn rơi vào vùng nhạy cảm của 2 chính sách có độ tương đồng Semantic cao, Agent vẫn cần query đính kèm Metadata để thoát bẫy.
- Kỹ thuật stream xử lý in-memory có khả năng là thảm hoạ Out of memory nếu data leo thang lên ngưỡng hàng chục Gigabytes; cần migrate luồng này qua Apache Spark.
