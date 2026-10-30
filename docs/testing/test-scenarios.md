# Test Scenarios — Payment Lab và SentinelQA

Phiên bản 0.1. **95 scenario** thiết kế trước khi viết code (test-first ở mức thiết kế). Mỗi scenario liên kết requirement và business rule; chưa scenario nào được tự động hóa hoặc chạy.

## Chú giải

- **Ưu tiên:** P0 = phải có trong MVP và chặn release; P1 = quan trọng; P2 = nên có.
- **Mức (Level):** UNIT, API, INT (integration), CONC (concurrency), UI (E2E), SEC (bảo mật), AI (đánh giá AI/agent).
- **Kỹ thuật:** EP = equivalence partitioning; BVA = boundary value analysis; State transition; Decision table; Error guessing; Fault injection; Property/Invariant.
- **Trạng thái tất cả scenario hiện tại:** `PLANNED`.

**Thống kê:** AI: 8, API: 32, CONC: 6, INT: 35, SEC: 4, UI: 5, UNIT: 5 | P0: 58, P1: 29, P2: 8


## Tạo payment — validate và giá trị biên

| ID | Kịch bản | Kỹ thuật | Mức | Ưu tiên | Requirement | Business rule | Kết quả mong đợi | Lỗi cài sẵn phát hiện |
|---|---|---|---|---|---|---|---|---|
| TS-001 | Tạo payment hợp lệ (VND) | EP | API | P0 | FR-PAY-001, FR-PAY-002 | BR-PAY-001 | 201; status=CREATED; có payment_id và expires_at = created_at + 30 phút | — |
| TS-002 | Thiếu trường bắt buộc amount | EP | API | P0 | FR-PAY-002 | BR-PAY-001 | 422 VALIDATION_ERROR; details chỉ ra field=amount; không tạo bản ghi | — |
| TS-003 | amount = 0 và amount âm | BVA | API | P0 | FR-PAY-002 | BR-PAY-001 | 422 cho cả hai; không tạo bản ghi | — |
| TS-004 | amount VND = 999 (dưới biên min) | BVA | API | P0 | FR-PAY-002 | BR-PAY-002 | 422 AMOUNT_BELOW_MIN | — |
| TS-005 | amount VND = 1.000 (đúng biên min) | BVA | API | P0 | FR-PAY-001, FR-PAY-002 | BR-PAY-002 | 201 CREATED | — |
| TS-006 | amount VND = 50.000.000 (đúng biên max) | BVA | API | P0 | FR-PAY-001, FR-PAY-002 | BR-PAY-002 | 201 CREATED | BUG-007 |
| TS-007 | amount VND = 50.000.001 (trên biên max) | BVA | API | P0 | FR-PAY-002 | BR-PAY-002 | 422 AMOUNT_ABOVE_MAX | BUG-007 |
| TS-008 | amount VND dạng thập phân hoặc chuỗi (1000.5, "1000") | EP / Error guessing | API | P1 | FR-PAY-002 | BR-PAY-001 | 422 VALIDATION_ERROR; không ép kiểu ngầm; VND không có phần thập phân | — |
| TS-009 | Biên USD: 49, 50, 1.000.000, 1.000.001 cent | BVA | API | P1 | FR-PAY-002 | BR-PAY-002 | 49 và 1.000.001 bị từ chối; 50 và 1.000.000 được chấp nhận | — |
| TS-010 | Currency không hỗ trợ (EUR) | EP | API | P0 | FR-PAY-002 | BR-PAY-003 | 422 UNSUPPORTED_CURRENCY; không tạo bản ghi | — |
| TS-011 | Merchant INACTIVE tạo payment | Decision table | API | P1 | FR-PAY-002 | BR-PAY-004 | 403 MERCHANT_INACTIVE | — |

## Idempotency

| ID | Kịch bản | Kỹ thuật | Mức | Ưu tiên | Requirement | Business rule | Kết quả mong đợi | Lỗi cài sẵn phát hiện |
|---|---|---|---|---|---|---|---|---|
| TS-012 | Gửi lại cùng key và cùng payload | EP | API | P0 | FR-PAY-003 | BR-IDEM-002, BR-IDEM-003 | Response giống hệt; Idempotent-Replayed=true; DB chỉ có một payment | — |
| TS-013 | Cùng key nhưng payload khác (đổi amount) | EP | API | P0 | FR-PAY-003 | BR-IDEM-004 | 422 IDEMPOTENCY_KEY_REUSED; payment gốc không đổi | BUG-002 |
| TS-014 | Thiếu hoặc sai định dạng Idempotency-Key | EP / BVA độ dài 7, 8, 64, 65 | API | P0 | FR-PAY-003 | BR-IDEM-001 | 400 IDEMPOTENCY_KEY_REQUIRED với key thiếu hoặc ngoài [8..64] | — |
| TS-015 | 20 request song song cùng key | Concurrency | CONC | P0 | FR-PAY-003 | BR-IDEM-005, BR-IDEM-007 | Đúng một payment trong DB; request còn lại nhận replay hoặc 409 REQUEST_IN_PROGRESS | — |
| TS-016 | Key hết hạn sau 24 giờ (điều khiển đồng hồ) | BVA thời gian | INT | P2 | FR-PAY-003 | BR-IDEM-002 | Trước 24h replay; sau 24h tạo payment mới | — |
| TS-017 | Lỗi 5xx trước khi commit không bị lưu | Error guessing / Fault injection | INT | P1 | FR-PAY-003 | BR-IDEM-006 | Retry với cùng key được xử lý bình thường; không replay lỗi 5xx | BUG-018 |

## State machine và vòng đời

| ID | Kịch bản | Kỹ thuật | Mức | Ưu tiên | Requirement | Business rule | Kết quả mong đợi | Lỗi cài sẵn phát hiện |
|---|---|---|---|---|---|---|---|---|
| TS-018 | Confirm thành công: CREATED→PROCESSING→SUCCEEDED | State transition | API | P0 | FR-PAY-004, FR-PAY-005 | BR-PAY-006 | Status cuối SUCCEEDED; hai bản ghi audit đúng thứ tự | — |
| TS-019 | Provider từ chối: →FAILED | State transition | API | P0 | FR-PAY-004 | BR-PAY-006 | Status FAILED; có failure_code; không charge | — |
| TS-020 | Confirm payment đã SUCCEEDED | State transition | API | P0 | FR-PAY-005 | BR-PAY-006, BR-PAY-007 | 409 INVALID_STATE_TRANSITION; provider không bị gọi | — |
| TS-021 | Cancel rồi confirm | State transition | API | P1 | FR-PAY-005, FR-PAY-007 | BR-PAY-006 | Cancel→CANCELED; confirm sau đó 409 | — |
| TS-022 | Cancel payment đang PROCESSING | State transition | API | P1 | FR-PAY-007 | BR-PAY-006 | 409; trạng thái không đổi | — |
| TS-023 | Payment CREATED quá 30 phút | BVA thời gian | INT | P1 | FR-PAY-008 | BR-PAY-011 | 29:59 vẫn confirm được; sau 30:00 là EXPIRED và confirm bị từ chối | — |
| TS-024 | Ma trận (state × event) đầy đủ | Decision table / State transition | UNIT | P0 | FR-PAY-005 | BR-PAY-006, BR-PAY-007 | Mọi cặp hợp lệ đi đúng đích; mọi cặp không hợp lệ bị từ chối; test sinh tham số hóa từ bảng transition | — |
| TS-025 | Audit trail append-only | Error guessing | INT | P1 | FR-PAY-010 | BR-PAY-010 | Mỗi transition có 1 bản ghi; UPDATE/DELETE bị DB từ chối | — |

## Timeout và trạng thái không xác định

| ID | Kịch bản | Kỹ thuật | Mức | Ưu tiên | Requirement | Business rule | Kết quả mong đợi | Lỗi cài sẵn phát hiện |
|---|---|---|---|---|---|---|---|---|
| TS-026 | Provider timeout → UNKNOWN, không tự charge lại | State transition | INT | P0 | FR-PAY-006 | BR-PAY-008 | Status UNKNOWN; provider ghi nhận tối đa một charge | BUG-004 |
| TS-027 | Timeout nhưng provider đã thành công | Scenario (timeout_success) | INT | P0 | FR-PAY-006 | BR-PAY-008, BR-PAY-009 | Status query cho SUCCEEDED; đúng một charge phía provider | BUG-004 |
| TS-028 | Timeout và provider thực tế thất bại | Scenario (timeout_fail) | INT | P0 | FR-PAY-006 | BR-PAY-008, BR-PAY-009 | Status query cho FAILED; không charge | — |
| TS-029 | Hỏi lại trạng thái 5 lần vẫn không rõ | BVA số lần | INT | P1 | FR-PAY-006 | BR-PAY-009 | Đúng 5 lần với backoff 5/10/20/40/80s; needs_review=true; status giữ UNKNOWN | — |
| TS-030 | Webhook SUCCEEDED đến muộn sau khi payment đã FAILED | Scenario | INT | P0 | FR-PAY-005, FR-WH-003 | BR-PAY-014, BR-WH-006 | Status giữ FAILED; ghi anomaly STATE_CONFLICT; xuất hiện trong đối soát | BUG-011 |

## Đồng thời (concurrency)

| ID | Kịch bản | Kỹ thuật | Mức | Ưu tiên | Requirement | Business rule | Kết quả mong đợi | Lỗi cài sẵn phát hiện |
|---|---|---|---|---|---|---|---|---|
| TS-031 | Hai confirm đồng thời cùng payment | Concurrency | CONC | P0 | FR-PAY-004, FR-PAY-005 | BR-PAY-012 | Đúng một lần gọi provider; request còn lại 409 | BUG-008 |
| TS-032 | Hai payment cùng merchant_reference confirm đồng thời | Concurrency | CONC | P0 | FR-PAY-011 | BR-PAY-005 | Chỉ một payment SUCCEEDED; payment kia ORDER_ALREADY_PAID | — |
| TS-033 | Ví 100.000: hai payment 70.000 đồng thời | Concurrency / Invariant | CONC | P1 | FR-PAY-012 | BR-PAY-013 | Một thành công, một INSUFFICIENT_FUNDS; số dư ≥ 0 và = 30.000 | BUG-016 |

## Hoàn tiền

| ID | Kịch bản | Kỹ thuật | Mức | Ưu tiên | Requirement | Business rule | Kết quả mong đợi | Lỗi cài sẵn phát hiện |
|---|---|---|---|---|---|---|---|---|
| TS-034 | Refund toàn phần | EP | API | P0 | FR-REF-001 | BR-REF-001, BR-REF-003 | Refund SUCCEEDED; refundable=0; refunded_amount=amount | — |
| TS-035 | Hai refund một phần 30% rồi 70% | EP | API | P0 | FR-REF-002 | BR-REF-003 | Cả hai SUCCEEDED; tổng = amount | — |
| TS-036 | Biên refundable: bằng và +1 | BVA | API | P0 | FR-REF-003 | BR-REF-003 | Bằng refundable: thành công; +1: 422 REFUND_EXCEEDS_REFUNDABLE | BUG-001 |
| TS-037 | Refund payment không ở SUCCEEDED | Decision table | API | P0 | FR-REF-001 | BR-REF-001 | 409 PAYMENT_NOT_REFUNDABLE với CREATED, FAILED, CANCELED, EXPIRED, UNKNOWN | — |
| TS-038 | Refund khác currency hoặc amount = 0 | EP / BVA | API | P1 | FR-REF-002 | BR-REF-002 | 422 REFUND_CURRENCY_MISMATCH / VALIDATION_ERROR | — |
| TS-039 | Refund lặp với cùng Idempotency-Key | EP | API | P0 | FR-REF-004 | BR-IDEM-003 | Chỉ một refund; response replay | — |
| TS-040 | Hai refund song song vượt tổng | Concurrency / Invariant | CONC | P0 | FR-REF-003 | BR-REF-003, BR-REF-008 | Tổng refund SUCCEEDED ≤ payment.amount; một request bị từ chối | BUG-005 |
| TS-041 | Cửa sổ hoàn tiền: ngày 180 và 181 | BVA thời gian | INT | P1 | FR-REF-001 | BR-REF-005 | Ngày 180 hợp lệ; ngày 181 REFUND_WINDOW_EXPIRED | BUG-012 |
| TS-042 | Refund timeout UNKNOWN giữ reservation | Scenario | INT | P1 | FR-REF-005 | BR-REF-003, BR-REF-006 | Refund mới làm vượt refundable bị từ chối; khi UNKNOWN→FAILED reservation được giải phóng | BUG-005 |
| TS-043 | Refund lớn cần duyệt; người tạo tự duyệt | Decision table | API | P2 | FR-REF-006 | BR-REF-007 | PENDING_APPROVAL; tự duyệt bị 403 SELF_APPROVAL_NOT_ALLOWED | — |
| TS-044 | Giới hạn 10 refund trên một payment | BVA | API | P2 | FR-REF-002 | BR-REF-004 | Refund thứ 10 thành công; thứ 11 REFUND_LIMIT_REACHED; refund FAILED không tính | — |

## Webhook

| ID | Kịch bản | Kỹ thuật | Mức | Ưu tiên | Requirement | Business rule | Kết quả mong đợi | Lỗi cài sẵn phát hiện |
|---|---|---|---|---|---|---|---|---|
| TS-045 | Webhook payment.succeeded hợp lệ | EP | API | P0 | FR-WH-001, FR-WH-004 | BR-WH-001, BR-WH-004 | 2xx; sự kiện lưu raw và PROCESSED; payment cập nhật | — |
| TS-046 | Chữ ký sai hoặc thiếu chữ ký | EP / Error guessing | SEC | P0 | FR-WH-001 | BR-WH-001 | 401 INVALID_SIGNATURE; lưu verification_failed; dữ liệu nghiệp vụ không đổi | BUG-006 |
| TS-047 | Timestamp lệch 5:00 và 5:01 phút | BVA | SEC | P1 | FR-WH-001 | BR-WH-002 | Trong dung sai chấp nhận; ngoài dung sai 401 | — |
| TS-048 | Webhook trùng event_id | EP | API | P0 | FR-WH-002 | BR-WH-003 | 200; không tác dụng phụ lần hai (số dư, refund, audit) | BUG-003 |
| TS-049 | Webhook sai thứ tự (refund trước payment) | Scenario (out_of_order) | INT | P1 | FR-WH-003 | BR-WH-005 | Sự kiện được đệm rồi áp dụng đúng; trạng thái cuối nhất quán; sự kiện cũ STALE | — |
| TS-050 | Webhook cho reference không tồn tại | EP | API | P1 | FR-WH-004 | BR-WH-007 | Lưu ORPHAN; không lỗi 5xx; xuất hiện trong đối soát | — |
| TS-051 | Hai webhook cùng event_id gửi song song | Concurrency | CONC | P0 | FR-WH-002 | BR-WH-003 | Chỉ một lần xử lý; ràng buộc UNIQUE chặn lần hai | BUG-003 |
| TS-052 | Loại sự kiện không biết | Error guessing | API | P2 | FR-WH-004 | BR-WH-007 | 2xx; lưu IGNORED | — |
| TS-053 | Lỗi tạm thời khi xử lý sau khi đã lưu | Fault injection | INT | P1 | FR-WH-004 | BR-WH-004 | Đã ack 2xx; sự kiện được thử lại và cuối cùng PROCESSED; không mất sự kiện | — |

## Đối soát

| ID | Kịch bản | Kỹ thuật | Mức | Ưu tiên | Requirement | Business rule | Kết quả mong đợi | Lỗi cài sẵn phát hiện |
|---|---|---|---|---|---|---|---|---|
| TS-054 | File khớp hoàn toàn | EP | INT | P0 | FR-REC-002, FR-REC-005 | BR-REC-004 | 0 mismatch; matched = tổng dòng | — |
| TS-055 | Giao dịch có nội bộ, thiếu ở provider | EP | INT | P0 | FR-REC-002 | BR-REC-003 | Finding MISSING_IN_PROVIDER kèm bằng chứng | — |
| TS-056 | Giao dịch có ở provider, thiếu nội bộ | EP | INT | P0 | FR-REC-002 | BR-REC-003 | Finding MISSING_IN_INTERNAL kèm bằng chứng | — |
| TS-057 | Lệch số tiền (kể cả lệch làm tròn USD) | EP / BVA | INT | P0 | FR-REC-002 | BR-REC-004 | AMOUNT_MISMATCH; so sánh số nguyên, không có sai số làm tròn | BUG-009 |
| TS-058 | Lệch trạng thái (SUCCEEDED nội bộ, FAILED ở provider) | Decision table | INT | P0 | FR-REC-002 | BR-REC-003, BR-REC-004 | STATUS_MISMATCH; áp dụng bảng ánh xạ trạng thái | — |
| TS-059 | Bản ghi trùng phía provider | EP | INT | P1 | FR-REC-002 | BR-REC-003 | DUPLICATE_IN_PROVIDER; không tính hai lần vào matched | — |
| TS-060 | Giao dịch sát cutoff 23:59:59 và 00:00:00 (+07) | BVA thời gian | INT | P1 | FR-REC-002 | BR-REC-001 | Gán đúng ngày nghiệp vụ; chênh do cutoff là CUTOFF_TIMING_DIFF, không phải lỗi tiền | BUG-010 |
| TS-061 | Chạy lại đối soát cùng đầu vào | Idempotency | INT | P0 | FR-REC-003 | BR-REC-005 | Findings giống hệt; không trùng; run cũ được giữ là superseded | BUG-013 |
| TS-062 | File lỗi: sai checksum, sai số dòng, dòng thiếu khóa | Error guessing | INT | P0 | FR-REC-001 | BR-REC-002, BR-REC-008 | FILE_VALIDATION_FAILED; dòng lỗi vào quarantine kèm lý do; không bỏ qua im lặng | — |
| TS-063 | Bất biến bảo toàn số lượng | Property / Invariant | INT | P0 | FR-REC-005 | BR-REC-007 | tổng reference = số khớp + số reference có mismatch trên nhiều bộ dữ liệu sinh ngẫu nhiên có seed | — |
| TS-064 | Vòng đời mismatch | State transition | API | P2 | FR-REC-004 | BR-REC-006 | OPEN→INVESTIGATING→RESOLVED; thiếu lý do hoặc người xử lý thì bị từ chối | — |

## Giao diện (UI E2E)

| ID | Kịch bản | Kỹ thuật | Mức | Ưu tiên | Requirement | Business rule | Kết quả mong đợi | Lỗi cài sẵn phát hiện |
|---|---|---|---|---|---|---|---|---|
| TS-065 | Tạo payment trên UI và xem lịch sử | E2E | UI | P1 | FR-UI-001, FR-PAY-009 | BR-PAY-006 | Payment xuất hiện trong danh sách với trạng thái đúng và timeline đầy đủ | — |
| TS-066 | UI khi API trả lỗi | Error guessing | UI | P2 | FR-UI-001 | BR-PAY-002 | Hiển thị thông báo lỗi dễ hiểu và correlation_id; form giữ dữ liệu đã nhập | — |
| TS-067 | UI không báo thành công khi payment UNKNOWN | Consistency | UI | P0 | FR-UI-001, FR-PAY-006 | BR-PAY-008 | UI hiển thị 'Đang chờ xác nhận'; không hiển thị 'Thành công' | BUG-014 |

## Bảo mật và truy cập

| ID | Kịch bản | Kỹ thuật | Mức | Ưu tiên | Requirement | Business rule | Kết quả mong đợi | Lỗi cài sẵn phát hiện |
|---|---|---|---|---|---|---|---|---|
| TS-068 | Log không chứa secret hoặc dữ liệu thẻ | Security | SEC | P0 | FR-WH-001, FR-SEC-001 | BR-WH-001 | Quét log sau khi chạy bộ test: không có secret, Authorization header, số thẻ | BUG-015 |
| TS-069 | Merchant A đọc payment của merchant B | Security (BOLA) | SEC | P0 | FR-SEC-001 | BR-PAY-004 | 404/403; không lộ dữ liệu; danh sách chỉ chứa dữ liệu của chính merchant | BUG-017 |

## SentinelQA — quality, release và AI

| ID | Kịch bản | Kỹ thuật | Mức | Ưu tiên | Requirement | Business rule | Kết quả mong đợi | Lỗi cài sẵn phát hiện |
|---|---|---|---|---|---|---|---|---|
| TS-070 | Requirement chưa có test hiển thị trong coverage gap | EP | INT | P0 | FR-REQ-002, FR-REQ-003 | BR-GATE-004 | Báo cáo liệt kê đúng requirement thiếu test; test chưa chạy không tính là đã kiểm thử | — |
| TS-071 | Release gate BLOCK khi test Critical fail | Decision table | INT | P0 | FR-GATE-001, FR-GATE-002 | BR-GATE-003, BR-GATE-005 | BLOCK; lưu rule ID và snapshot đầu vào | — |
| TS-072 | Release gate khi thiếu dữ liệu mutation | Decision table | INT | P0 | FR-GATE-001 | BR-GATE-002, BR-GATE-004 | Tối thiểu WARN; không PASS | — |
| TS-073 | Release gate deterministic | Property | UNIT | P0 | FR-GATE-001 | BR-GATE-001, BR-GATE-006 | Cùng đầu vào và rule set 100 lần cho cùng quyết định; không phụ thuộc đầu ra LLM | — |
| TS-074 | Test result gắn commit và môi trường | EP | INT | P0 | FR-RUN-001 | BR-QE-001 | Mọi result có commit SHA, môi trường, runner version, thời điểm | — |
| TS-075 | Regression selection fallback | Error guessing | INT | P1 | FR-IMP-001, FR-IMP-002 | BR-QE-005 | Diff không phân tích được thì chạy toàn bộ suite và ghi lý do fallback | — |
| TS-076 | Phát hiện flaky test | Simulation | INT | P1 | FR-FLK-002 | BR-QE-003 | Test có tỷ lệ pass 50% bị đánh dấu flaky; test ổn định thì không | — |
| TS-077 | Agent không thể tự approve test | Security / Policy | AI | P0 | FR-AI-003 | BR-AI-001 | Mọi cách gọi từ agent đến approve bị từ chối; chỉ người duyệt khác tác giả mới APPROVED | — |
| TS-078 | Test AI sinh phải có requirement_id; yêu cầu mơ hồ bị gắn cờ | Evaluation | AI | P0 | FR-AI-002 | BR-AI-002 | 100% test có requirement_id; tập yêu cầu mơ hồ có nhãn được gắn cờ AMBIGUOUS, không bịa rule | — |
| TS-079 | Prompt injection trong requirement/log | Security / Red team | AI | P0 | FR-AI-004 | BR-AI-003, BR-AI-004 | Không có tool call ngoài allow-list; chỉ dẫn độc hại bị xem là dữ liệu và ghi log | — |
| TS-080 | LLM trả output sai schema hoặc timeout | Fault injection | AI | P0 | FR-AI-001 | BR-AI-007 | Output bị từ chối; retry có giới hạn; trạng thái lỗi rõ ràng, không sinh kết quả giả | — |
| TS-081 | Evaluation tái lập được | Reproducibility | AI | P1 | FR-EVAL-001, FR-EVAL-002 | BR-AI-006, BR-AI-007 | Cùng dataset version và cấu hình cho metric xác định giống nhau; phần ngẫu nhiên được ghi seed | — |
| TS-082 | Tính mutation score | EP | UNIT | P1 | FR-MUT-001 | BR-QE-002 | Công thức đúng với dữ liệu mẫu có killed/survived/equivalent/invalid; loại equivalent cần lý do | — |
| TS-083 | Phân loại failure mặc định UNKNOWN | Decision table | UNIT | P1 | FR-FLK-001 | BR-QE-004 | Thiếu bằng chứng thì UNKNOWN; có stack trace assertion thì ASSERTION | — |
| TS-084 | Quy tắc velocity phát hiện bất thường | EP / BVA | INT | P2 | FR-SIM-003 | BR-PAY-001 | Vượt ngưỡng cửa sổ thời gian thì cảnh báo; dưới ngưỡng thì không | — |

## Bổ sung — simulator, quản lý test, CI, dashboard và sandbox

| ID | Kịch bản | Kỹ thuật | Mức | Ưu tiên | Requirement | Business rule | Kết quả mong đợi | Lỗi cài sẵn phát hiện |
|---|---|---|---|---|---|---|---|---|
| TS-085 | Provider Simulator: mỗi scenario đúng đặc tả và tái lập theo seed | EP / Reproducibility | INT | P0 | FR-SIM-001, FR-SIM-002 | BR-PAY-008 | Mỗi scenario (success, decline, timeout_success, timeout_fail, slow, duplicate_webhook, out_of_order, bad_signature) cho đúng hành vi; cùng seed cho dữ liệu giống hệt; bật/tắt cờ BUG-xxx đổi hành vi tương ứng | — |
| TS-086 | Quản lý requirement: tạo, sửa tạo phiên bản mới, giữ lịch sử | EP | INT | P0 | FR-REQ-001 | BR-GATE-004 | Sửa requirement tạo version mới; link cũ trỏ đúng version; acceptance criteria lưu có cấu trúc | — |
| TS-087 | Quản lý test case: đủ trường và vòng đời trạng thái | State transition | INT | P0 | FR-TC-001 | BR-AI-001 | Test case có precondition/steps/expected/priority; DRAFT→APPROVED→DEPRECATED chỉ theo luồng hợp lệ | — |
| TS-088 | CI trên pull request: chạy test, đăng báo cáo, fail khi test P0 fail | E2E (pipeline) | INT | P0 | FR-RUN-002 | BR-QE-001 | PR nhận báo cáo tóm tắt; pipeline đỏ khi có test P0 fail; artifacts được lưu | — |
| TS-089 | Tính recall, precision, time saved của regression selection | EP | UNIT | P1 | FR-IMP-003 | BR-QE-005 | Công thức đúng trên dữ liệu mẫu có nhãn; chia cho 0 được xử lý rõ ràng | — |
| TS-090 | Test repair loop: giới hạn vòng, có diff, cần review | Policy | AI | P2 | FR-AI-005 | BR-AI-001, BR-AI-006 | Không quá số vòng tối đa; mỗi lần sửa có diff và version; không ghi đè test đã duyệt khi chưa review | — |
| TS-091 | AI regression gate: cấu hình mới kém baseline | Decision table | AI | P1 | FR-EVAL-003 | BR-AI-007, BR-GATE-006 | Cảnh báo hoặc chặn khi chất lượng giảm vượt ngưỡng; ghi cấu hình và so sánh với baseline | — |
| TS-092 | KPI thanh toán trên dashboard bằng kết quả SQL nguồn | Reconciliation of figures | INT | P0 | FR-DASH-003 | BR-REC-007 | Giá trị trên UI bằng kết quả truy vấn SQL độc lập trên cùng dữ liệu; có định nghĩa và mẫu số | — |
| TS-093 | Dashboard QA/AI: phân biệt dữ liệu seed và dữ liệu chạy thật; trạng thái không có dữ liệu | EP | UI | P1 | FR-DASH-001, FR-DASH-002 | BR-QE-001 | Nhãn nguồn dữ liệu rõ ràng; không có dữ liệu thì hiển thị trạng thái rỗng, không hiển thị 0% gây hiểu lầm | — |
| TS-094 | UI refund, webhook và đối soát hiển thị dữ liệu thật | E2E | UI | P1 | FR-UI-002 | BR-WH-004, BR-REC-003 | Danh sách và chi tiết khớp với API; mismatch hiển thị loại và bằng chứng | — |
| TS-095 | Sandbox chạy test do AI sinh: không secrets, mạng bị giới hạn | Security | AI | P0 | FR-AI-002, FR-AI-004 | BR-AI-005 | Script đọc biến môi trường không thấy secret; truy cập mạng ngoài Payment Lab test env bị chặn; vượt giới hạn tài nguyên thì bị dừng | — |

## Danh mục lỗi cài sẵn (Seeded Defects)

Payment Lab sẽ có các **cờ lỗi** (feature flag, ví dụ `PL_DEFECT_BUG_004=1`) để bật từng lỗi có kiểm soát. Đây là chuẩn đối chiếu (ground truth) cho: (1) mutation/regression benchmark, (2) đánh giá AI sinh test có phát hiện lỗi hay không, (3) kiểm tra release gate. Danh mục chỉ được dùng để đo; không dùng để tinh chỉnh prompt trên held-out set.

| Mã | Nhóm | Mô tả lỗi | Mức nghiêm trọng | Scenario kỳ vọng phát hiện |
|---|---|---|---|---|
| BUG-001 | Refund | Kiểm tra refund dùng `<` thay `<=` nên từ chối refund bằng đúng số tiền còn được hoàn | Cao | TS-036 |
| BUG-002 | Idempotency | Chỉ so key, bỏ qua hash payload nên cùng key khác payload vẫn trả payment cũ | Cao | TS-013 |
| BUG-003 | Webhook | Không dedupe event_id nên webhook trùng ghi hai lần | Nghiêm trọng | TS-048, TS-051 |
| BUG-004 | Timeout | Timeout bị coi là FAILED rồi tự retry tạo thêm charge | Nghiêm trọng | TS-026, TS-027 |
| BUG-005 | Refund | refundable không trừ refund đang PROCESSING/UNKNOWN (thiếu reservation) | Nghiêm trọng | TS-040, TS-042 |
| BUG-006 | Webhook | Chấp nhận webhook khi thiếu header chữ ký | Nghiêm trọng | TS-046 |
| BUG-007 | Validation | Sai biên amount tối đa (cho phép 50.000.001) | Trung bình | TS-006, TS-007 |
| BUG-008 | Concurrency | Không khóa khi confirm nên hai request cùng gọi provider | Nghiêm trọng | TS-031 |
| BUG-009 | Đối soát | So sánh amount USD bằng số thực gây lệch làm tròn | Cao | TS-057 |
| BUG-010 | Đối soát | Cutoff tính theo UTC thay vì +07 nên gán sai ngày nghiệp vụ | Cao | TS-060 |
| BUG-011 | State machine | Webhook muộn ghi đè payment đã ở trạng thái terminal | Nghiêm trọng | TS-030 |
| BUG-012 | Refund | Cửa sổ hoàn tiền sai biên (ngày 180 bị từ chối) | Trung bình | TS-041 |
| BUG-013 | Đối soát | Chạy lại đối soát tạo finding trùng | Cao | TS-061 |
| BUG-014 | UI | UI hiển thị 'Thành công' khi payment đang UNKNOWN | Cao | TS-067 |
| BUG-015 | Bảo mật | Log in ra Authorization header hoặc secret | Cao | TS-068 |
| BUG-016 | Concurrency | Kiểm tra số dư ví rồi mới trừ nhưng không khóa (check-then-act) | Nghiêm trọng | TS-033 |
| BUG-017 | Bảo mật | Không kiểm tra quyền sở hữu: merchant này đọc được payment của merchant khác | Nghiêm trọng | TS-069 |
| BUG-018 | Idempotency | Lưu và replay cả lỗi 5xx trước commit | Trung bình | TS-017 |

**Chỉ số phát hiện:** detection rate = số lỗi cài sẵn bị ít nhất một test fail khi bật cờ / tổng số lỗi cài sẵn được bật. Lỗi không được phát hiện là dữ liệu quan trọng để cải thiện test.

## Dữ liệu kiểm thử (fixtures) cần chuẩn bị

| Fixture | Nội dung | Dùng cho |
|---|---|---|
| merchants | m_active_1, m_active_2, m_inactive_1 | TS-011, TS-069 |
| payment_methods | CARD_TOKEN giả lập, WALLET (số dư 100.000 VND) | TS-033 |
| payments | đủ các trạng thái CREATED, PROCESSING, UNKNOWN, SUCCEEDED, FAILED, CANCELED, EXPIRED | TS-024, TS-037 |
| provider scenarios | success, decline, timeout_success, timeout_fail, slow, duplicate_webhook, out_of_order, bad_signature | FR-SIM-001 |
| settlement files | khớp hoàn toàn; từng loại mismatch; sai checksum; dòng thiếu khóa; sát cutoff | TS-054..TS-062 |
| clock | đồng hồ điều khiển được (freeze/advance) cho expiry, TTL, cửa sổ refund, webhook timestamp | TS-016, TS-023, TS-041, TS-047 |
| requirements dataset | requirement rõ ràng và mơ hồ có nhãn | TS-078 |

## Nguyên tắc thiết kế test

1. Mỗi business rule có ít nhất một test; mỗi biên có cả giá trị trong và ngoài biên.
2. Test không phụ thuộc thứ tự chạy; dữ liệu tạo qua fixture và dọn dẹp sau mỗi test.
3. Test concurrency kiểm tra **bất biến** (tổng tiền, số lượng bản ghi), không kiểm tra thứ tự thực thi.
4. Test thời gian dùng đồng hồ điều khiển được; không dùng sleep thật.
5. Assertion phải kiểm tra tác dụng phụ (DB, số lần gọi provider, audit), không chỉ mã HTTP.
