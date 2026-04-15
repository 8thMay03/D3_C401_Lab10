# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Bá Khánh  
**Vai trò:** Embed Owner  
**Ngày nộp:** 15-04-2026  

---

## 1. Tôi phụ trách phần nào?

**Nhiệm vụ chính:**
Trong dự án này, tôi là **Embed Owner**, focus chính vào hàm `cmd_embed_internal` trong file `etl_pipeline.py`. Công việc của tôi là nhận dữ liệu đã được làm sạch (từ file `cleaned.csv`), sau đó dùng model `all-MiniLM-L6-v2` để chuyển đổi các đoạn text này thành vector và lưu vào ChromaDB. Ngoài ra, tôi cũng phụ trách phần đánh giá chất lượng truy xuất bằng script `eval_retrieval.py`.

**Cách phối hợp với team:**
tôi làm việc trực tiếp với kết quả đầu ra từ bạn Cleaning Owner. Tôi chỉ cho phép hệ thống ghi dữ liệu vào vector database khi tất cả các bài test (Expectation) của phần Quality đều đã báo PASS hoàn toàn, không có bất kỳ cảnh báo HALT nào cản đường.

**Bằng chứng thực thi:**
Khi chạy thử với `run_id=official_fix`, log trả về đã xác nhận luồng embed hoạt động trơn tru:
`embed_upsert count=6 collection=day10_kb`

---

## 2. Một quyết định kỹ thuật đáng chú ý

Thay vì dùng hàm `.add()` mặc định của ChromaDB, tôi quyết định chuyển sang dùng `.upsert()` kết hợp với việc băm tĩnh `chunk_id` (ghép từ `doc_id` và `chunk_text`). Việc này giúp giải quyết triệt để bài toán Idempotency, nghĩa là dù pipeline có chạy đi chạy lại bao nhiêu lần thì dữ liệu cũng không bị rác hay đúp lại.

Tuy nhiên, quyết định làm tôi tâm đắc nhất là cơ chế **Prune IDs** (dọn dẹp dữ liệu cũ). Khi hệ thống cập nhật một chính sách mới (ví dụ một luật cũ bị loại bỏ), ChromaDB bắt buộc phải rà soát lại toàn bộ ID nó đang giữ và xóa sạch các ID không còn xuất hiện trong file `cleaned.csv` mới nhất. Điều này tạo ra một "màng lọc" an toàn, đảm bảo RAG Agent ở các lab trước không lấy nhầm các thông tin đã out-date. Các bạn có thể thấy cơ chế này hoạt động qua dòng log đi dọn rác: `embed_prune_removed=1`.

---

## 3. Quá trình fix một lỗi cụ thể

Ở Sprint 3, tôi gặp phải một lỗi khá nghiêm trọng: kết quả retrieval bị lẫn lộn thông tin cũ (cụ thể là cái lỗi "14 ngày hoàn tiền" bị out-date), làm sai luôn đầu ra của RAG. Tôi chạy đối chiếu qua file test `artifacts/eval/after_inject_bad.csv` thì thấy cờ `hits_forbidden` chuyển đỏ sang trạng thái `yes` cái rụp.

Sau khi debug thì tôi tìm ra nguyên nhân là do lúc kích hoạt cờ `--skip-validate` trên hệ thống hỏng, pipeline xả thẳng dữ liệu raw lỗi, chưa qua kiểm duyệt vào quá trình Embed. Đống dữ liệu bẩn này nếu lọt vào Vector DB sẽ làm sai lệch không gian vector của chính sách đó mãi mãi.

**Cách tôi sửa:** Khi tôi chạy lại pipeline chuẩn (với `run-id=official_fix`) và không truyền cờ skip nữa, cơ chế "Prune IDs" đã phát huy sức mạnh. Nó tự động quét, tóm cổ ngay được cái `chunk_id` chứa nội dung "14 ngày" tàn dư (do không có mặt trong file `cleaned_csv` xịn) và xóa thẳng tay thông qua lệnh `col.delete(ids=drop)`.

---

## 4. Bằng chứng trước / sau khi fix lỗi

Các bạn có thể thấy rõ độ hiệu quả của cơ chế Prune qua 2 bộ log đánh giá:

**Trước khi fix (run_id: `inject-bad`):**
Cờ `hits_forbidden` dính bẫy vì nạp nhầm policy cũ (`yes`).
`q_refund_window,Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi xác nhận đơn?,policy_refund_v4,Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng.,yes,yes,,3`

**Sau khi fix (run_id: `official_fix` - ghi vào `before_after_eval.csv`):**
Pipeline đã dọn sạch sẽ đống dữ liệu thừa đó. Cờ `hits_forbidden` trở lại trạng thái an toàn (`no`).
`q_refund_window,Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi xác nhận đơn?,policy_refund_v4,Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng.,yes,no,,3`

---

## 5. Nếu có thêm thời gian

Nếu còn dư thêm 2 tiếng ngồi code, tôi chắc chắn sẽ áp thêm kỹ thuật Metadata Filtering nâng cao vào Embed. Thay vì chỉ nạp vector chay, tôi sẽ gắn thêm `doc_id` và `effective_date` làm metadata trực tiếp trên ChromaDB. Truyền tham số vậy thì sau này Agent bên Lab 09 chỉ cần đẩy thêm điều kiện `where={"doc_id": "policy_refund_v4"}` vào query là độ chính xác (Precision) vọt lên 100%, chấm dứt hoàn toàn tình trạng bị nhiễu do tìm theo k-NN thuần túy.
