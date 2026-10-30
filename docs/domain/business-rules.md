# Business Rules

Phiên bản 0.1 (bản nháp). Mỗi quy tắc có ID ổn định, được tham chiếu trong test scenario và traceability matrix. Giá trị số (hạn mức, thời hạn, số lần) là **tham số mô hình hóa**, nên đặt trong cấu hình thay vì hardcode.

> Đây là mô hình học tập đơn giản hóa. Trước khi coi một quy tắc là 'đúng nghiệp vụ', hãy đối chiếu với tài liệu công khai của các nhà cung cấp thanh toán thực tế và ghi lại nguồn trong ADR.

## Thanh toán

| ID | Quy tắc | Mã lỗi / kết quả | Test scenarios |
|---|---|---|---|
| BR-PAY-001 | amount là số nguyên dương theo minor unit của currency (VND exponent 0, USD exponent 2); không dùng số thực để tính tiền. | VALIDATION_ERROR | TS-001, TS-002, TS-003, TS-008, TS-084 |
| BR-PAY-002 | Giới hạn một giao dịch: VND 1.000–50.000.000; USD 50–1.000.000 cent (0,50–10.000,00 USD). | AMOUNT_BELOW_MIN / AMOUNT_ABOVE_MAX | TS-004, TS-005, TS-006, TS-007, TS-009, TS-066 |
| BR-PAY-003 | Chỉ hỗ trợ currency VND và USD. | UNSUPPORTED_CURRENCY | TS-010 |
| BR-PAY-004 | Merchant phải ACTIVE mới được tạo payment. | MERCHANT_INACTIVE | TS-011, TS-069 |
| BR-PAY-005 | Mỗi (merchant_id, merchant_reference) có tối đa một payment SUCCEEDED; confirm payment thứ hai phải bị từ chối kể cả khi đồng thời. | ORDER_ALREADY_PAID | TS-032 |
| BR-PAY-006 | Chỉ chuyển trạng thái theo bảng transition trong payment-lifecycle.md. | INVALID_STATE_TRANSITION | TS-018, TS-019, TS-020, TS-021, TS-022, TS-024, TS-065 |
| BR-PAY-007 | SUCCEEDED, FAILED, CANCELED, EXPIRED là terminal; không đổi status (riêng refunded_amount của payment SUCCEEDED thay đổi theo refund). | INVALID_STATE_TRANSITION | TS-020, TS-024 |
| BR-PAY-008 | Provider timeout đưa payment sang UNKNOWN, không phải FAILED; hệ thống không tự tạo lần charge mới cho cùng payment. | — | TS-026, TS-027, TS-028, TS-067, TS-085 |
| BR-PAY-009 | Payment UNKNOWN được hỏi lại trạng thái tối đa 5 lần (backoff 5/10/20/40/80 giây); hết số lần vẫn UNKNOWN thì đặt needs_review=true và giữ nguyên status. | — | TS-027, TS-028, TS-029 |
| BR-PAY-010 | Mọi transition ghi một bản ghi audit append-only (from, to, reason, actor, correlation_id, at); cấm UPDATE/DELETE. | — | TS-025 |
| BR-PAY-011 | Payment CREATED hết hạn sau 30 phút và chuyển EXPIRED. | PAYMENT_EXPIRED | TS-023 |
| BR-PAY-012 | Confirm chỉ hợp lệ khi CREATED; nhiều confirm đồng thời cho cùng payment chỉ gọi provider đúng một lần. | INVALID_STATE_TRANSITION | TS-031 |
| BR-PAY-013 | Payment method WALLET: số dư không bao giờ âm; các payment đồng thời không được cùng tiêu một khoản số dư. | INSUFFICIENT_FUNDS | TS-033 |
| BR-PAY-014 | Kết quả provider đến muộn mâu thuẫn trạng thái terminal (ví dụ đã FAILED nhưng provider báo SUCCEEDED) không tự đổi status; ghi anomaly STATE_CONFLICT và đưa vào đối soát. | — | TS-030 |

## Idempotency

| ID | Quy tắc | Mã lỗi / kết quả | Test scenarios |
|---|---|---|---|
| BR-IDEM-001 | POST tạo payment/refund bắt buộc header Idempotency-Key (8–64 ký tự [A-Za-z0-9_-]). | IDEMPOTENCY_KEY_REQUIRED | TS-014 |
| BR-IDEM-002 | Phạm vi key là (merchant_id, endpoint, key); thời hạn lưu 24 giờ. | — | TS-012, TS-016 |
| BR-IDEM-003 | Cùng key và cùng payload (so bằng hash) trả lại đúng response đã lưu với header Idempotent-Replayed: true, không phát sinh tác dụng phụ. | — | TS-012, TS-039 |
| BR-IDEM-004 | Cùng key nhưng payload khác bị từ chối. | IDEMPOTENCY_KEY_REUSED (422) | TS-013 |
| BR-IDEM-005 | Cùng key khi request đầu còn đang xử lý trả lỗi để client thử lại sau. | REQUEST_IN_PROGRESS (409) | TS-015 |
| BR-IDEM-006 | Lỗi 5xx xảy ra trước khi commit không được lưu (key dùng lại được); kết quả đã commit (2xx và lỗi nghiệp vụ 4xx) được lưu và replay. | — | TS-017 |
| BR-IDEM-007 | Bản ghi idempotency và resource được tạo trong cùng một DB transaction; ràng buộc UNIQUE (merchant_id, endpoint, key) là chốt chặn cuối cùng. | — | TS-015 |

## Hoàn tiền

| ID | Quy tắc | Mã lỗi / kết quả | Test scenarios |
|---|---|---|---|
| BR-REF-001 | Chỉ hoàn tiền payment ở trạng thái SUCCEEDED. | PAYMENT_NOT_REFUNDABLE | TS-034, TS-037 |
| BR-REF-002 | Refund amount ≥ 1 minor unit và cùng currency với payment. | VALIDATION_ERROR / REFUND_CURRENCY_MISMATCH | TS-038 |
| BR-REF-003 | refundable = payment.amount − Σ refund SUCCEEDED − Σ refund đang giữ chỗ (PENDING_APPROVAL, REQUESTED, PROCESSING, UNKNOWN); refund.amount ≤ refundable. | REFUND_EXCEEDS_REFUNDABLE | TS-034, TS-035, TS-036, TS-040, TS-042 |
| BR-REF-004 | Tối đa 10 refund (không tính FAILED/REJECTED) cho một payment. | REFUND_LIMIT_REACHED | TS-044 |
| BR-REF-005 | Cửa sổ hoàn tiền 180 ngày kể từ succeeded_at (ngày thứ 180 còn hợp lệ, ngày thứ 181 bị từ chối). | REFUND_WINDOW_EXPIRED | TS-041 |
| BR-REF-006 | Refund FAILED hoặc REJECTED giải phóng reservation; refund UNKNOWN giữ reservation đến khi xác định kết quả. | — | TS-042 |
| BR-REF-007 | Refund từ 10.000.000 VND (hoặc 400 USD) trở lên cần maker-checker; người duyệt phải khác người tạo. | SELF_APPROVAL_NOT_ALLOWED | TS-043 |
| BR-REF-008 | Bất biến: tổng refund SUCCEEDED không bao giờ vượt payment.amount, kể cả dưới concurrency. | — | TS-040 |

## Webhook

| ID | Quy tắc | Mã lỗi / kết quả | Test scenarios |
|---|---|---|---|
| BR-WH-001 | Xác thực chữ ký HMAC-SHA256 trên chuỗi timestamp.payload bằng secret dùng chung; sai chữ ký thì không xử lý. | INVALID_SIGNATURE (401) | TS-045, TS-046, TS-068 |
| BR-WH-002 | Timestamp chỉ chấp nhận trong ±5 phút (chống replay). | WEBHOOK_TIMESTAMP_OUT_OF_RANGE (401) | TS-047 |
| BR-WH-003 | Dedupe theo (provider, event_id); sự kiện trùng được ack 200 và không phát sinh tác dụng phụ. | — | TS-048, TS-051 |
| BR-WH-004 | Lưu sự kiện trước, ack 2xx sau khi lưu, xử lý tiếp; xử lý lỗi tạm thời thì được thử lại nội bộ. | — | TS-045, TS-053, TS-094 |
| BR-WH-005 | Sự kiện cũ hơn sự kiện đã áp dụng (theo provider_sequence) bị đánh dấu STALE; sự kiện phụ thuộc đến sớm được đệm và thử lại. | — | TS-049 |
| BR-WH-006 | Sự kiện mâu thuẫn trạng thái terminal không đổi status; ghi anomaly STATE_CONFLICT (xem BR-PAY-014). | — | TS-030 |
| BR-WH-007 | Loại sự kiện không biết được lưu với IGNORED; tham chiếu không tồn tại được lưu với ORPHAN và đưa vào đối soát. | — | TS-050, TS-052 |

## Đối soát

| ID | Quy tắc | Mã lỗi / kết quả | Test scenarios |
|---|---|---|---|
| BR-REC-001 | Ngày nghiệp vụ tính theo Asia/Ho_Chi_Minh, cutoff 00:00 (+07); timestamp lưu UTC. | — | TS-060 |
| BR-REC-002 | Khóa so khớp là provider_reference; bản ghi thiếu khóa vào quarantine. | MISSING_PROVIDER_REF | TS-062 |
| BR-REC-003 | Taxonomy mismatch: MISSING_IN_PROVIDER, MISSING_IN_INTERNAL, DUPLICATE_IN_PROVIDER, DUPLICATE_IN_INTERNAL, AMOUNT_MISMATCH, CURRENCY_MISMATCH, STATUS_MISMATCH, CUTOFF_TIMING_DIFF. | — | TS-055, TS-056, TS-058, TS-059, TS-094 |
| BR-REC-004 | So sánh amount và currency chính xác trên số nguyên; trạng thái so qua bảng ánh xạ internal↔provider. | — | TS-054, TS-057, TS-058 |
| BR-REC-005 | Chạy lại với cùng đầu vào cho cùng kết quả; UNIQUE (run_id, provider_reference, mismatch_type); run mới supersede run cũ nhưng giữ lịch sử. | — | TS-061 |
| BR-REC-006 | Vòng đời finding: OPEN → INVESTIGATING → RESOLVED | WRITTEN_OFF, bắt buộc lý do và người xử lý. | — | TS-064 |
| BR-REC-007 | Bảo toàn số lượng: tổng reference duy nhất = số khớp + số reference có ít nhất một mismatch. | — | TS-063, TS-092 |
| BR-REC-008 | File settlement phải qua validate header, row_count, checksum; dòng lỗi vào quarantine kèm lý do, không bỏ qua im lặng. | FILE_VALIDATION_FAILED | TS-062 |

## Quality Engineering

| ID | Quy tắc | Mã lỗi / kết quả | Test scenarios |
|---|---|---|---|
| BR-QE-001 | Mọi test result gắn commit SHA, môi trường, phiên bản runner và thời điểm chạy. | — | TS-074, TS-088, TS-093 |
| BR-QE-002 | mutation_score = killed / (total − equivalent − invalid); loại equivalent phải có lý do ghi lại. | — | TS-082 |
| BR-QE-003 | Test là flaky khi cùng test, cùng commit, cùng môi trường cho ít nhất hai kết quả khác nhau trong N=10 lần chạy lặp. | — | TS-076 |
| BR-QE-004 | Failure phân loại ASSERTION, APPLICATION_ERROR, ENVIRONMENT, TIMEOUT, TEST_DEFECT, UNKNOWN; mặc định UNKNOWN khi thiếu bằng chứng. | — | TS-083 |
| BR-QE-005 | Regression selection luôn có fallback chạy toàn bộ khi diff không phân tích được hoặc độ tin cậy thấp. | — | TS-075, TS-089 |

## Release gate

| ID | Quy tắc | Mã lỗi / kết quả | Test scenarios |
|---|---|---|---|
| BR-GATE-001 | Cùng đầu vào và cùng rule set phải cho cùng quyết định (deterministic). | — | TS-073 |
| BR-GATE-002 | Thiếu tín hiệu bắt buộc không bao giờ được coi là đạt: tối thiểu WARN. | — | TS-072 |
| BR-GATE-003 | BLOCK khi có test fail gắn requirement mức Critical hoặc vi phạm bất biến về tiền; ghi rule ID gây BLOCK. | — | TS-071 |
| BR-GATE-004 | WARN khi requirement Must thiếu test, mutation score dưới ngưỡng, flaky rate trên ngưỡng hoặc còn mismatch đối soát mức cao đang OPEN. | — | TS-070, TS-072, TS-086 |
| BR-GATE-005 | Mỗi quyết định lưu rule IDs, snapshot đầu vào, ngưỡng và phiên bản rule set. | — | TS-071 |
| BR-GATE-006 | Đầu ra LLM không bao giờ là căn cứ duy nhất để PASS hoặc BLOCK. | — | TS-073, TS-091 |

## AI Agent

| ID | Quy tắc | Mã lỗi / kết quả | Test scenarios |
|---|---|---|---|
| BR-AI-001 | Test do AI tạo ở trạng thái DRAFT; chỉ vào suite chính khi người duyệt APPROVED; người duyệt khác tác giả; agent không có quyền approve. | — | TS-077, TS-087, TS-090 |
| BR-AI-002 | Mỗi test phải có requirement_id; yêu cầu mơ hồ được gắn cờ AMBIGUOUS kèm câu hỏi làm rõ, không tự bịa business rule. | — | TS-078 |
| BR-AI-003 | Tool theo allow-list; tối đa 10 bước, giới hạn thời gian và chi phí mỗi lần chạy; tool ngoài danh sách bị chặn và ghi log. | — | TS-079 |
| BR-AI-004 | Dữ liệu không tin cậy (requirement, log, webhook payload, đầu ra LLM) là dữ liệu, không phải chỉ dẫn. | — | TS-079 |
| BR-AI-005 | Test do AI sinh chỉ chạy trong sandbox: không secrets, mạng chỉ tới môi trường test của Payment Lab, giới hạn CPU/RAM/thời gian. | — | TS-095 |
| BR-AI-006 | Test pass không đồng nghĩa test đúng: đánh giá thêm assertion validity và mutation detection. | — | TS-081, TS-090 |
| BR-AI-007 | Mỗi lần gọi model lưu model, prompt_version, token, latency, cost và kết quả validate. | — | TS-080, TS-081, TS-091 |

## Tham số cấu hình mặc định

| Tham số | Giá trị mặc định | Quy tắc |
|---|---|---|
| amount_min / amount_max (VND) | 1.000 / 50.000.000 | BR-PAY-002 |
| amount_min / amount_max (USD cent) | 50 / 1.000.000 | BR-PAY-002 |
| payment_expiry | 30 phút | BR-PAY-011 |
| status_query_max_attempts / backoff | 5 / 5-10-20-40-80 giây | BR-PAY-009 |
| provider_timeout (simulator) | 10 giây | BR-PAY-008 |
| idempotency_ttl | 24 giờ | BR-IDEM-002 |
| refund_window | 180 ngày | BR-REF-005 |
| refund_max_per_payment | 10 | BR-REF-004 |
| refund_approval_threshold | 10.000.000 VND hoặc 400 USD | BR-REF-007 |
| webhook_timestamp_tolerance | ±5 phút | BR-WH-002 |
| business_timezone / cutoff | Asia/Ho_Chi_Minh / 00:00 | BR-REC-001 |
| flaky_rerun_count | 10 | BR-QE-003 |
| agent_max_steps | 10 | BR-AI-003 |

## Bảng ánh xạ trạng thái cho đối soát (BR-REC-004)

| Trạng thái nội bộ | Trạng thái provider tương ứng | Ghi chú |
|---|---|---|
| SUCCEEDED | SETTLED | Khớp |
| FAILED | DECLINED / ERROR | Khớp |
| UNKNOWN | bất kỳ | Luôn tạo finding để xác định lại, không coi là khớp |
| SUCCEEDED | DECLINED / ERROR | STATUS_MISMATCH |
| FAILED | SETTLED | STATUS_MISMATCH (mức nghiêm trọng cao — khách có thể đã bị trừ tiền) |
| Refund SUCCEEDED | REFUNDED | Khớp |

## Danh mục mã lỗi API

| HTTP | Mã | Ý nghĩa |
|---|---|---|
| 400 | IDEMPOTENCY_KEY_REQUIRED | Thiếu hoặc sai định dạng Idempotency-Key |
| 401 | INVALID_SIGNATURE / WEBHOOK_TIMESTAMP_OUT_OF_RANGE | Webhook không xác thực được |
| 403 | MERCHANT_INACTIVE / SELF_APPROVAL_NOT_ALLOWED | Không đủ điều kiện hoặc quyền |
| 404 | NOT_FOUND | Không tồn tại hoặc không thuộc quyền truy cập |
| 409 | INVALID_STATE_TRANSITION / ORDER_ALREADY_PAID / REQUEST_IN_PROGRESS / PAYMENT_NOT_REFUNDABLE | Xung đột trạng thái |
| 410 | PAYMENT_EXPIRED | Payment đã hết hạn |
| 422 | VALIDATION_ERROR / AMOUNT_BELOW_MIN / AMOUNT_ABOVE_MAX / UNSUPPORTED_CURRENCY / IDEMPOTENCY_KEY_REUSED / REFUND_EXCEEDS_REFUNDABLE / REFUND_WINDOW_EXPIRED / REFUND_LIMIT_REACHED / REFUND_CURRENCY_MISMATCH / FILE_VALIDATION_FAILED / INSUFFICIENT_FUNDS | Dữ liệu hoặc quy tắc nghiệp vụ không thỏa |
| 429 | RATE_LIMITED | Vượt giới hạn tần suất |
| 500 | INTERNAL_ERROR | Lỗi hệ thống; không lộ stack trace |
