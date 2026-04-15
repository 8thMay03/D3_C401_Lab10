# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Bá Khánh  
**Vai trò:** Embed Owner  
**Ngày nộp:** 15-04-2026  

---

## 1. Tôi phụ trách phần nào?

**File / module:**
Tôi đóng vai trò **Embed Owner**. Nhiệm vụ chính của tôi nằm ở hàm `cmd_embed_internal` trong file `etl_pipeline.py`. Tôi chịu trách nhiệm khởi tạo kết nối với ChromaDB, thiết kế luồng đồng bộ văn bản đã được làm sạch (cleaned_csv) thành các vector embedding bằng model `all-MiniLM-L6-v2`, đồng thời đảm bảo pipeline chạy lại nhiều lần không sinh ra dữ liệu rác bằng cơ chế Idempotency dựa trên `chunk_id`. Cùng với đó, tôi dùng `eval_retrieval.py` để lấy bằng chứng đánh giá truy vấn.

**Kết nối với thành viên khác:**
Tôi là chốt chặn cuối cùng của pipeline. Tôi làm việc trực tiếp với file đầu ra của Cleaning Owner. Tôi chỉ cho phép upsert vào ChromaDB khi mọi Expectation của Quality Owner báo PASS (không có cờ HALT).

**Bằng chứng (commit / comment trong code):**
Trong log của quá trình chạy `run_id=khanhemb`, tôi đã xác nhận quá trình embed thành công với dòng log:
`embed_upsert count=6 collection=day10_kb`

---

## 2. Một quyết định kỹ thuật

Để giải quyết bài toán Idempotency khi chạy lại pipeline, tôi không sử dụng thao tác `.add()` cơ bản của ChromaDB mà đổi sang dùng `.upsert()` dựa theo `chunk_id` băm tĩnh (từ `doc_id` + `chunk_text`). 

Đồng thời, quyết định kỹ thuật quan trọng nhất là chiến lược **Prune IDs** (thu dọn "mồi cũ"). Khi policy hệ thống thay đổi (ví dụ có luật bị cách ly và mất đi), hệ thống bắt buộc phải kiểm tra tất cả các IDs đang tồn tại trong VectorDB và xóa sạch các IDs không còn nằm trong file `cleaned.csv` lần chạy mới nhất. Quyết định này thiết lập nên một "Publish Boundary" rạch ròi, phòng trừ trường hợp RAG Agent Day 09 truy xuất nhầm vào context đã bị thu hồi. Thể hiện qua dòng log: `embed_prune_removed=1` khi dọn rác.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Trong Sprint 3, tôi phát hiện triệu chứng kết quả retrieval bị ô nhiễm bởi thông tin cũ (vấn đề "14 ngày hoàn tiền"), ảnh hưởng nghiêm trọng tới RAG Output. Tracking lỗi này bằng phương pháp đối chiếu, tôi chạy file test trước pipeline: `artifacts/eval/after_inject_khanhemb.csv`. Cờ `hits_forbidden` đột ngột báo `yes`.

Tìm hiểu nguyên nhân: Khi cờ `--skip-validate` được kích hoạt trên hệ thống hỏng, pipeline đẩy thẳng bản raw lỗi vào Embed mà không qua bộ lọc. Lỗi này nếu lưu vào vector db sẽ bóp méo vĩnh viễn không gian vector của policy đó.
Giải pháp & Fix: Khi chạy lại pipeline chuẩn không skip, nhờ logic "Prune IDs" đã cài đặt, nó tự động tìm ra `chunk_id` chứa văn bản "14 ngày" cũ không còn trong cleaned data và thanh trừng nó: `col.delete(ids=drop)`.

---

## 4. Bằng chứng trước / sau

Quá trình Prune được thể hiện rõ rệt qua 2 bộ log chạy Evaluation mà tôi đảm nhiệm đánh giá:

**Trước (run_id: `khanhemb-inject`):**
Cờ `hits_forbidden` mắc bẫy nhận nhầm tài liệu cũ (`yes`).
`q_refund_window,Khách...,policy_refund_v4,Yêu cầu được gửi trong vòng 14 ngày làm việc kể từ thời điểm xác nhận đơn hàng.,yes,yes,,3`

**Sau (run_id: `khanhemb-fix`):**
Pipeline làm sạch mồi cũ. Cờ `hits_forbidden` trở lại an toàn (`no`).
`q_refund_window,Khách...,policy_refund_v4,Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng.,yes,no,,3`

---

## 5. Cải tiến tiếp theo

Với thêm 2 giờ làm việc, tôi sẽ cập nhật thêm Metadata Filtering nâng cao lúc Embed. Tức là ánh xạ cấu trúc `doc_id` và `effective_date` làm metadata vào ChromaDB, giúp Agent Day 09 có thể truyền tham số metadata vào query (`where={"doc_id": "policy_refund_v4"}`) để tăng Precision 100% thay vì chỉ dùng K-NN vector similarity thuần túy dễ gây nhiễu chéo tài liệu.
