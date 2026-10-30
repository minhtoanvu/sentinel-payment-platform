# Architecture Decision Records (ADR) — Log

Định dạng: Bối cảnh → Quyết định → Phương án đã loại → Hệ quả → Trạng thái. Khi một quyết định thay đổi, **không xóa**; thêm ADR mới với trạng thái `Supersedes ADR-xxx`. Trong phỏng vấn, đây là tài liệu để giải thích *vì sao*, không chỉ *cái gì*.

---

## ADR-001 — Modular monolith + worker, không microservices
- **Trạng thái:** Accepted (v0.1)
- **Bối cảnh:** Một người thực hiện, tài nguyên máy hạn chế, cần chứng minh tư duy kiến trúc mà không tăng chi phí vận hành.
- **Quyết định:** Một ứng dụng FastAPI chia package rõ ràng (`payment_lab`, `sentinelqa`), thêm worker cho tác vụ nền (status query, chạy test, agent). Một PostgreSQL với hai schema.
- **Đã loại:** Microservices (phức tạp triển khai, không mang lại bằng chứng năng lực tương xứng); serverless (khó tái lập local).
- **Hệ quả:** Triển khai đơn giản, debug dễ; phải giữ kỷ luật ranh giới module (SentinelQA chỉ gọi Payment Lab qua API công khai). Có thể tách worker sau.

## ADR-002 — Lưu tiền bằng số nguyên minor unit
- **Trạng thái:** Accepted
- **Bối cảnh:** Số thực gây sai số làm tròn; VND không có phần thập phân còn USD có 2 chữ số.
- **Quyết định:** `amount BIGINT` theo minor unit + `currency`; bảng exponent theo ISO 4217; API nhận/trả số nguyên; không dùng FLOAT/DOUBLE.
- **Đã loại:** `NUMERIC(18,2)` cho mọi currency (dễ nhầm với VND); số thực.
- **Hệ quả:** Phải chuyển đổi khi hiển thị; đơn giản hóa so sánh trong đối soát; seeded defect BUG-009 mô phỏng lỗi dùng số thực.

## ADR-003 — PostgreSQL là nguồn sự thật, ràng buộc DB là chốt chặn cuối
- **Trạng thái:** Accepted
- **Bối cảnh:** Các bất biến về tiền phải đúng dưới concurrency.
- **Quyết định:** Dùng UNIQUE, partial UNIQUE, CHECK và khóa dòng (`SELECT … FOR UPDATE`) ở DB; tầng domain kiểm tra trước để trả lỗi có nghĩa.
- **Đã loại:** Chỉ kiểm tra ở tầng ứng dụng (race condition); distributed lock bên ngoài (thêm thành phần).
- **Hệ quả:** Thiết kế migration cẩn thận; test concurrency bắt buộc; một số seeded defect cố ý bỏ qua kiểm tra ứng dụng nhưng không tắt constraint.

## ADR-004 — Idempotency lưu trong DB, cùng transaction với resource
- **Trạng thái:** Accepted
- **Bối cảnh:** Retry và double-submit là nguyên nhân chính của giao dịch trùng.
- **Quyết định:** Bảng `idempotency_keys` UNIQUE `(merchant_id, endpoint, key)`; lưu `request_hash` và response đã commit; trạng thái IN_FLIGHT/COMPLETED; TTL 24 giờ.
- **Đã loại:** Redis (thêm hạ tầng, khó đảm bảo atomic với DB).
- **Hệ quả:** Tải ghi thêm trên DB; cần job dọn key hết hạn; ngữ nghĩa 409/422 phải ghi rõ trong API.

## ADR-005 — Timeout là trạng thái UNKNOWN, không phải FAILED
- **Trạng thái:** Accepted
- **Bối cảnh:** Timeout không cho biết provider đã xử lý hay chưa.
- **Quyết định:** Thêm trạng thái UNKNOWN + status query có backoff + cờ `needs_review`; đối soát là lưới an toàn cuối.
- **Đã loại:** Coi là FAILED và cho retry (dễ double charge); coi là SUCCEEDED (có thể sai).
- **Hệ quả:** Giao diện và báo cáo phải hiển thị trạng thái trung gian; thêm worker; có thể có tình huống kết quả đến muộn mâu thuẫn terminal → anomaly `STATE_CONFLICT`.

## ADR-006 — Release gate dựa trên quy tắc xác định; LLM chỉ tham khảo
- **Trạng thái:** Accepted
- **Bối cảnh:** Quyết định phát hành cần giải thích được, tái lập được và kiểm thử được.
- **Quyết định:** Rule set có phiên bản, đầu vào là tín hiệu đo được; mỗi quyết định lưu rule IDs, snapshot, ngưỡng. LLM có thể tạo giải thích tham khảo nhưng không là căn cứ duy nhất để PASS/BLOCK.
- **Đã loại:** Mô hình điểm rủi ro hộp đen; để LLM tự quyết.
- **Hệ quả:** Cần dữ liệu thật để đặt ngưỡng; có thể thử scoring model ở giai đoạn sau, đánh giá riêng.

## ADR-007 — Đầu ra của LLM là dữ liệu không tin cậy
- **Trạng thái:** Accepted
- **Bối cảnh:** Prompt injection và hallucination.
- **Quyết định:** Mọi output qua schema validation; tool allow-list; giới hạn bước/thời gian/chi phí; test AI sinh chạy trong sandbox; agent không có quyền approve.
- **Đã loại:** Cho agent chạy shell tùy ý; tự động merge test do AI sinh.
- **Hệ quả:** Phải xây sandbox và trace; tốc độ chậm hơn nhưng an toàn và đo được.

## ADR-008 — Seeded defects bằng feature flag trong Payment Lab
- **Trạng thái:** Accepted
- **Bối cảnh:** Cần ground truth để đo hiệu quả test và AI.
- **Quyết định:** 18 cờ `PL_DEFECT_BUG_xxx`; mỗi cờ bật hành vi lỗi xác định; mặc định tắt; danh mục ở test-scenarios.md; held-out set không dùng để tinh chỉnh prompt.
- **Đã loại:** Chỉ dùng mutation tự động (không kiểm soát được nghiệp vụ); lỗi ngẫu nhiên.
- **Hệ quả:** Có thể đo detection rate; phải đảm bảo cờ lỗi không lọt vào bản demo công khai trừ khi được chủ đích bật.

## ADR-009 — Playwright + pytest là bộ thực thi chính; Selenium là tùy chọn
- **Trạng thái:** Accepted (có thể xem lại)
- **Bối cảnh:** Cần trace, fixture tốt, chạy ổn định trong CI.
- **Quyết định:** Playwright (Python) với pytest; chỉ thêm Selenium khi luồng Playwright đã ổn để chứng minh tương thích nhiều công cụ.
- **Hệ quả:** Page Object Model dùng chung; nếu thêm Selenium cần lớp trừu tượng nhỏ.

## ADR-010 — Dữ liệu tổng hợp, không PII và không dữ liệu thẻ thật
- **Trạng thái:** Accepted
- **Quyết định:** Mọi dữ liệu sinh bằng seed; payment method là token giả lập; không PAN; không tuyên bố tuân thủ PCI DSS.
- **Hệ quả:** An toàn khi công khai; dataset đánh giá cần kiểm tra trước khi publish.

## Mẫu ADR mới

```
## ADR-0xx — Tiêu đề
- Trạng thái: Proposed | Accepted | Superseded by ADR-0yy
- Bối cảnh:
- Quyết định:
- Đã loại (và lý do):
- Hệ quả (tốt, xấu, rủi ro):
- Bằng chứng/đối chiếu (nguồn tài liệu, thử nghiệm):
```
