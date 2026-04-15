# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Phương Nam  
**Vai trò:** Embed Owner  
**Ngày nộp:** 15-04-2026  

---

## 1. Tôi phụ trách phần nào?

**File / module:**
Tôi đảm nhiệm vai trò Embed Owner, phụ trách chính hàm `cmd_embed_internal` trong file `etl_pipeline.py`. Nhiệm vụ của tôi là khởi tạo kết nối với ChromaDB, thiết kế luồng chuyển đổi dữ liệu từ `cleaned_csv` thành vector embedding bằng model `all-MiniLM-L6-v2`, đồng thời đảm bảo pipeline có thể chạy lặp lại nhiều lần mà không phát sinh dữ liệu trùng lặp thông qua cơ chế idempotency dựa trên `chunk_id`.

Ngoài ra, tôi sử dụng `eval_retrieval.py` để thu thập bằng chứng phục vụ việc đánh giá chất lượng truy vấn sau khi embedding.

**Kết nối với thành viên khác:**
Tôi đóng vai trò là điểm cuối trong pipeline. Dữ liệu đầu vào của tôi đến trực tiếp từ Cleaning Owner, và tôi chỉ thực hiện upsert vào ChromaDB khi toàn bộ Expectation từ Quality Owner đều đạt trạng thái PASS (không có cờ HALT). Điều này đảm bảo dữ liệu được đưa vào hệ thống luôn đạt tiêu chuẩn chất lượng.

**Bằng chứng (commit / comment trong code):**
Trong log của quá trình chạy `run_id=ci-smoke2`, tôi đã xác nhận quá trình embed thành công với dòng log:
`embed_upsert count=6 collection=day10_kb`

---

## 2. Quyết định kỹ thuật

Để giải quyết bài toán Idempotency khi chạy lại pipeline, tôi không sử dụng thao tác `.add()` cơ bản của ChromaDB mà đổi sang dùng `.upsert()` dựa theo `chunk_id` băm tĩnh (từ `doc_id` + `chunk_text`).

Đồng thời, quyết định kỹ thuật quan trọng nhất là chiến lược **Prune IDs** (thu dọn "mồi cũ"). Khi policy hệ thống thay đổi (ví dụ có luật bị cách ly và mất đi), hệ thống bắt buộc phải kiểm tra tất cả các IDs đang tồn tại trong VectorDB và xóa sạch các IDs không còn nằm trong file `cleaned.csv` lần chạy mới nhất. Quyết định này thiết lập nên một "Publish Boundary" rạch ròi, phòng trừ trường hợp RAG Agent Day 09 truy xuất nhầm vào context đã bị thu hồi. Thể hiện qua dòng log: `embed_prune_removed=1` khi dọn rác.

---

## 3. Sự cố / anomaly

Trong Sprint 3, tôi phát hiện triệu chứng kết quả retrieval bị ô nhiễm bởi thông tin cũ (vấn đề "14 ngày hoàn tiền"), ảnh hưởng nghiêm trọng tới RAG Output. Tracking lỗi này bằng phương pháp đối chiếu, tôi chạy file test trước pipeline: `artifacts/eval/after_inject_khanhemb.csv`. Cờ `hits_forbidden` đột ngột báo `yes`.

Tìm hiểu nguyên nhân: Khi cờ `--skip-validate` được kích hoạt trên hệ thống hỏng, pipeline đẩy thẳng bản raw lỗi vào Embed mà không qua bộ lọc. Lỗi này nếu lưu vào vector db sẽ bóp méo vĩnh viễn không gian vector của policy đó.
Giải pháp & Fix: Khi chạy lại pipeline chuẩn không skip, nhờ logic "Prune IDs" đã cài đặt, nó tự động tìm ra `chunk_id` chứa văn bản "14 ngày" cũ không còn trong cleaned data và thanh trừng nó: `col.delete(ids=drop)`.

---

## 4. Before/after

Quá trình Prune được thể hiện rõ rệt qua 2 bộ log chạy Evaluation mà tôi đảm nhiệm đánh giá:

**Trước (run_id: `ci-smoke`):**
Cờ `hits_forbidden` mắc bẫy nhận nhầm tài liệu cũ (`yes`).
`q_refund_window,Khách...,policy_refund_v4,Yêu cầu được gửi trong vòng 14 ngày làm việc kể từ thời điểm xác nhận đơn hàng.,yes,yes,,3`

**Sau (run_id: `2026-04-15T05-11Z`):**
Pipeline làm sạch mồi cũ. Cờ `hits_forbidden` trở lại an toàn (`no`).
`q_refund_window,Khách...,policy_refund_v4,Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng.,yes,no,,3`

---

## 5. Cải tiến thêm 2 giờ

Với thêm 2 giờ làm việc, tôi sẽ cập nhật thêm Metadata Filtering nâng cao lúc Embed. Tức là ánh xạ cấu trúc `doc_id` và `effective_date` làm metadata vào ChromaDB, giúp Agent Day 09 có thể truyền tham số metadata vào query (`where={"doc_id": "policy_refund_v4"}`) để tăng Precision 100% thay vì chỉ dùng K-NN vector similarity thuần túy dễ gây nhiễu chéo tài liệu.
