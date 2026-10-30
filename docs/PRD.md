# PRD — SentinelQA Intelligence Platform & Payment Lab

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | 0.1 (bản nháp để review) |
| Ngày | 2026-10-29 |
| Tác giả | Toney |
| Trạng thái | Draft — cần review và chốt các mục ở phần 12 trước khi bắt đầu Phase 1 |
| Tài liệu liên quan | [Glossary](domain-glossary.md) · [Payment lifecycle](domain/payment-lifecycle.md) · [Business rules](domain/business-rules.md) · [Use cases](business-analysis/02_use_cases.md) · [User stories](business-analysis/03_user_stories.md) · [Metrics](metrics.md) · [Roadmap](roadmap.md) |

> **Lưu ý trung thực:** Payment Lab là hệ thống **mô phỏng** để học tập và làm portfolio. Không xử lý tiền thật, không lưu số thẻ thật, không kết nối ngân hàng hay cổng thanh toán thật. Các quy tắc nghiệp vụ trong tài liệu là mô hình học tập có chủ đích, không phải mô tả chuẩn của mọi tổ chức thanh toán.

---

## 1. Tóm tắt

SentinelQA gồm **hai hệ thống** kết nối với nhau:

1. **Payment Lab** — một hệ thống thanh toán số mô phỏng (payment, refund, webhook, reconciliation, provider simulator). Đây là *đối tượng được kiểm thử*, có nghiệp vụ đủ phức tạp để tạo ra các lỗi thật: trừ tiền hai lần, giao dịch treo, hoàn vượt mức, đối soát lệch.
2. **SentinelQA** — nền tảng Quality Engineering: quản lý requirement và truy vết, thực thi test, chọn regression theo thay đổi, đo hiệu quả bộ test (mutation testing), phân tích lỗi và flaky, AI Agent sinh test có kiểm chứng, đánh giá AI bằng benchmark, và **release gate** Pass/Warn/Block giải thích được.

Mục tiêu sản phẩm: trả lời được năm câu hỏi của một đội phần mềm — *Cần test gì? Test có hiệu quả không? Vì sao lỗi? AI có đáng tin không? Có nên phát hành không?* — trong bối cảnh nghiệp vụ thanh toán.

Mục tiêu portfolio: một codebase, nhiều bộ hồ sơ (QA Automation/SDET, AI Engineer, Backend, BA, DA), mỗi bộ có bằng chứng riêng và đo lường được.

## 2. Bối cảnh và vấn đề

### 2.1 Vấn đề của nghiệp vụ thanh toán (Payment Lab mô phỏng)
- Mạng và đối tác không đáng tin cậy: timeout không có nghĩa là thất bại. Coi timeout là thất bại rồi cho khách thử lại là nguyên nhân kinh điển của trừ tiền hai lần.
- Cùng một yêu cầu có thể đến nhiều lần (retry, double-click, webhook gửi lặp), nên hệ thống phải idempotent.
- Nhiều tiến trình cùng thao tác trên một tài nguyên (số dư, số tiền còn hoàn) tạo race condition.
- Dữ liệu hai phía (nội bộ và đối tác) không bao giờ tự khớp; cần đối soát có phân loại sai lệch.

### 2.2 Vấn đề của đội kiểm thử (SentinelQA giải quyết)
- Test pass nhưng không biết test có đủ mạnh để bắt lỗi hay không.
- Mỗi thay đổi đều chạy toàn bộ regression (chậm) hoặc chọn thủ công (dễ sót).
- Test lỗi không rõ do ứng dụng, test script, môi trường hay dữ liệu; flaky test gây nhiễu.
- Test do AI sinh ra nghe hợp lý nhưng chưa chắc kiểm tra đúng nghiệp vụ.
- Quyết định phát hành dựa trên cảm tính thay vì bằng chứng truy vết được.

### 2.3 Hiện trạng và sản phẩm tương tự
Đã có nhiều sản phẩm giải quyết từng phần: nền tảng AI testing (mabl, Katalon…), framework browser testing (Playwright), nền tảng đánh giá và quan sát LLM (Arize Phoenix, LangSmith, promptfoo…) và công cụ mô phỏng thanh toán (ví dụ PayLab). SentinelQA **không** tuyên bố là đầu tiên. Điểm khác biệt có chủ đích là **giao điểm** của ba thứ: kiểm thử có hiểu nghiệp vụ thanh toán, AI Agent kiểm chứng bằng kết quả thực thi, và đo chất lượng test/AI trên cùng một bộ benchmark có lỗi cài sẵn (ground truth). *Cần xác minh lại bức tranh cạnh tranh trước khi công bố định vị.*

## 3. Mục tiêu và phi mục tiêu

### 3.1 Mục tiêu
| ID | Mục tiêu | Cách xác minh |
|---|---|---|
| G-01 | Có Payment Lab đủ nghiệp vụ để làm đối tượng kiểm thử thật | Toàn bộ FR-PAY/REF/WH/REC mức Must đạt acceptance criteria |
| G-02 | Có bộ automation chạy end-to-end trên CI với bằng chứng | Một lệnh chạy được; CI xanh; artifacts đầy đủ |
| G-03 | Chứng minh hiệu quả test bằng số liệu | Mutation score và detection rate trên 18 seeded defects |
| G-04 | Chứng minh AI Agent có giá trị thật so với baseline | So sánh ít nhất 3 phương pháp trên cùng dataset |
| G-05 | Quyết định release giải thích được | Mỗi quyết định có rule ID, snapshot đầu vào, tái lập được |
| G-06 | Bộ tài liệu BA và phân tích dữ liệu hoàn chỉnh | Traceability đầy đủ; KPI có SQL nguồn |
| G-07 | Người khác chạy lại được | README + một lệnh dựng môi trường từ trạng thái sạch |

### 3.2 Phi mục tiêu (không làm)
- Không xử lý tiền thật, thẻ thật, KYC thật; không tuyên bố tuân thủ PCI DSS.
- Không huấn luyện foundation model; không xây vector database trừ khi có bài toán truy xuất được benchmark chứng minh.
- Không dùng Kubernetes, Kafka, microservices (dùng modular monolith + worker).
- Không thực thi code tùy ý của người dùng trên server công khai.
- Không tuyên bố con số thành tích trước khi đo.

## 4. Người dùng (persona)

| Persona | Vai trò | Nhu cầu chính | Nỗi đau hiện tại |
|---|---|---|---|
| **Linh** | QA Engineer / SDET | Viết, chạy, gỡ lỗi test; hiểu vì sao fail | Test flaky, khó tái lập lỗi nghiệp vụ |
| **Minh** | QA Lead | Biết yêu cầu nào đã được kiểm thử tốt; quyết định phạm vi regression | Không đo được hiệu quả test, chạy full suite tốn thời gian |
| **Huy** | Merchant Developer | Tích hợp API thanh toán an toàn, retry không sợ trùng | Lỗi mơ hồ, trạng thái không rõ sau timeout |
| **Trang** | Payment Operations / Finance Reconciliation Analyst | Điều tra giao dịch, đối soát cuối ngày | Dữ liệu lệch, xử lý bằng bảng tính thủ công |
| **An** | AI Engineer | Đánh giá model/prompt/agent một cách khoa học | Demo đẹp nhưng không có số liệu so sánh |
| **Khoa** | Release Manager | Quyết định có phát hành hay không | Thiếu bằng chứng tổng hợp, dựa vào cảm tính |
| **Bảo** | Refund Approver | Duyệt hoàn tiền giá trị lớn | Thiếu kiểm soát maker-checker |

## 5. Phạm vi

### 5.1 Trong phạm vi (v1.0 — phát hành portfolio)
Mức ưu tiên theo MoSCoW; cột Phase tham chiếu [roadmap](roadmap.md).
- **Must:** toàn bộ luồng cốt lõi của Payment Lab; automation API/UI; traceability; release gate; AI Agent sinh test có review; evaluation dataset và benchmark; analytics KPI thanh toán.
- **Should:** change impact, mutation testing, flaky/failure intelligence, tool-using agent, dashboard QA/AI, RBAC, refund timeout, webhook out-of-order.
- **Could:** maker-checker refund, velocity rules, test repair loop.
- **Won't (v1.0):** xem 3.2 và mục 5.2.

### 5.2 Ngoài phạm vi
Thanh toán thẻ thật, 3-D Secure, chargeback/dispute thật, multi-currency FX, settlement nhiều ngày, đa tenant production, mobile app, giao diện phức tạp ngoài các màn hình đã nêu.

## 6. Kịch bản demo xuyên suốt (Golden Path GP-01)

**Tình huống:** *Khách thanh toán bị timeout nhưng nhà cung cấp đã ghi nhận giao dịch thành công.*

| Bước | Hành động | Vai trò chứng minh |
|---|---|---|
| 1 | Requirement FR-PAY-006 và BR-PAY-008/009 được viết, có acceptance criteria | BA |
| 2 | Provider Simulator bật scenario `timeout_success` | Backend / QA |
| 3 | Merchant tạo và confirm payment → status `UNKNOWN`; hệ thống hỏi lại trạng thái → `SUCCEEDED`; provider chỉ có một charge | Backend |
| 4 | File settlement của provider chứa giao dịch; đối soát cho kết quả khớp | Backend / DA |
| 5 | Test TS-026, TS-027, TS-028 chạy trên CI, có log và artifacts | QA Automation |
| 6 | Bật cờ lỗi BUG-004 (timeout bị coi là FAILED rồi retry): regression selection chọn đúng test, test fail, release gate **BLOCK** kèm rule ID | QA Intelligence |
| 7 | AI Agent sinh test từ requirement; human duyệt; benchmark đo agent có phát hiện BUG-004 hay không | AI Engineer |
| 8 | Dashboard hiển thị timeout recovery rate và tác động của lỗi lên success rate; khuyến nghị dựa trên dữ liệu | DA / BA |

**Acceptance criteria của GP-01:** chạy lại được từ môi trường sạch bằng hướng dẫn trong README; mọi số liệu trên dashboard truy ngược được đến bản ghi nguồn; kết quả BLOCK/PASS tái lập được.

## 7. Yêu cầu chức năng

Ghi chú: ID dùng xuyên suốt cho traceability. Quy tắc nghiệp vụ chi tiết ở [business-rules.md](domain/business-rules.md). Ma trận truy vết đầy đủ ở [09_traceability_matrix.csv](business-analysis/09_traceability_matrix.csv).

### Payment Lab — Thanh toán

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-PAY-001 | Must | 1 | Tạo payment | Tạo payment ở trạng thái CREATED với amount, currency, merchant_reference, payment_method; trả payment_id và expires_at. |
| FR-PAY-002 | Must | 1 | Validate đầu vào | Kiểm tra amount, currency, merchant, payment method theo BR-PAY-001..004; lỗi trả về theo error schema thống nhất có field cụ thể. |
| FR-PAY-003 | Must | 1 | Idempotency khi tạo payment | Bắt buộc Idempotency-Key; replay, conflict và in-flight xử lý theo BR-IDEM. |
| FR-PAY-004 | Must | 1 | Confirm payment qua provider | Confirm chuyển CREATED→PROCESSING, gọi Provider Simulator và cập nhật kết quả. |
| FR-PAY-005 | Must | 1 | State machine | Chỉ cho phép chuyển trạng thái hợp lệ; chuyển sai trả 409 INVALID_STATE_TRANSITION. |
| FR-PAY-006 | Must | 1 | Xử lý timeout | Timeout đưa payment sang UNKNOWN, hỏi lại trạng thái với backoff, không tự charge lại (BR-PAY-008/009). |
| FR-PAY-007 | Should | 1 | Hủy payment | Cho phép cancel khi payment còn CREATED. |
| FR-PAY-008 | Should | 1 | Hết hạn payment | Payment CREATED quá 30 phút chuyển EXPIRED. |
| FR-PAY-009 | Must | 1 | Truy vấn payment | GET theo id; list có filter (status, khoảng thời gian, merchant) và phân trang theo cursor. |
| FR-PAY-010 | Must | 1 | Audit trail | Mỗi transition ghi bản ghi lịch sử append-only. |
| FR-PAY-011 | Must | 1 | Chống thanh toán trùng đơn hàng | Mỗi merchant_reference chỉ có tối đa một payment SUCCEEDED, kể cả khi confirm đồng thời. |
| FR-PAY-012 | Should | 1 | Mô phỏng ví (wallet balance) | Payment method WALLET kiểm tra số dư; số dư không âm dưới tải đồng thời. |

### Payment Lab — Hoàn tiền

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-REF-001 | Must | 1 | Hoàn tiền toàn phần | Tạo refund bằng đúng số tiền còn được hoàn của payment SUCCEEDED. |
| FR-REF-002 | Must | 1 | Hoàn tiền một phần nhiều lần | Cho phép nhiều refund một phần cho một payment (tối đa 10). |
| FR-REF-003 | Must | 1 | Giới hạn refundable | Tính refundable có tính phần đang giữ chỗ (reservation); chặn hoàn vượt mức kể cả đồng thời. |
| FR-REF-004 | Must | 1 | Idempotency khi refund | Refund dùng Idempotency-Key giống payment. |
| FR-REF-005 | Should | 1 | Refund timeout/UNKNOWN | Refund timeout vào UNKNOWN, giữ reservation đến khi xác định kết quả. |
| FR-REF-006 | Could | 1 | Maker-checker cho refund lớn | Refund từ ngưỡng trở lên cần người duyệt khác người tạo. |

### Payment Lab — Webhook

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-WH-001 | Must | 1 | Xác thực webhook | Kiểm tra chữ ký HMAC-SHA256 và timestamp trong dung sai. |
| FR-WH-002 | Must | 1 | Chống xử lý lặp webhook | Dedupe theo (provider, event_id); trùng thì ack và không phát sinh tác dụng phụ. |
| FR-WH-003 | Should | 1 | Xử lý sự kiện sai thứ tự | Bỏ qua sự kiện cũ (stale) và đệm/thử lại sự kiện phụ thuộc. |
| FR-WH-004 | Must | 1 | Lưu sự kiện thô và kết quả xử lý | Lưu raw payload, trạng thái xác thực và kết quả xử lý (PROCESSED, IGNORED, STALE, ORPHAN, FAILED). |

### Payment Lab — Đối soát

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-REC-001 | Must | 1 | Nhập settlement file | Nhập file CSV của provider giả lập; validate header, số dòng, checksum; dòng lỗi vào quarantine. |
| FR-REC-002 | Must | 1 | So khớp và phân loại mismatch | So khớp theo provider_reference; phân loại theo taxonomy BR-REC-003. |
| FR-REC-003 | Must | 1 | Chạy lại đối soát idempotent | Cùng đầu vào cho cùng kết quả, không tạo finding trùng. |
| FR-REC-004 | Should | 1 | Vòng đời xử lý mismatch | OPEN → INVESTIGATING → RESOLVED/WRITTEN_OFF kèm lý do và người xử lý. |
| FR-REC-005 | Must | 1 | Báo cáo đối soát | Số bản ghi khớp, lệch, đang mở theo loại; đảm bảo bất biến bảo toàn số lượng. |

### Payment Lab — Provider Simulator & dữ liệu

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-SIM-001 | Must | 1 | Kịch bản Provider Simulator | success, decline, timeout_success, timeout_fail, slow, duplicate_webhook, out_of_order, bad_signature. |
| FR-SIM-002 | Must | 1 | Seed và fault injection | Dữ liệu tổng hợp tái lập bằng seed; cờ bật/tắt lỗi cài sẵn (seeded defects). |
| FR-SIM-003 | Could | 1 | Quy tắc velocity đơn giản | Cảnh báo nhiều giao dịch trong thời gian ngắn hoặc vượt ngưỡng trên dữ liệu tổng hợp. |

### Payment Lab — Giao diện

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-UI-001 | Must | 1 | Giao diện Payment Lab | Tạo payment, danh sách, chi tiết và timeline trạng thái. |
| FR-UI-002 | Should | 1 | Giao diện refund, webhook, đối soát | Xem refund, webhook events, batch đối soát và mismatch. |

### SentinelQA — Requirements & Traceability

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-REQ-001 | Must | 2 | Quản lý requirement | ID, mô tả, mức ưu tiên, mức độ nghiêm trọng nghiệp vụ, acceptance criteria, phiên bản. |
| FR-REQ-002 | Must | 2 | Liên kết truy vết | Liên kết requirement ↔ test case ↔ defect ↔ test run. |
| FR-REQ-003 | Must | 2 | Phát hiện khoảng trống coverage | Liệt kê requirement chưa có test và test chưa từng chạy; phân biệt 'có test' với 'đã kiểm thử đạt'. |

### SentinelQA — Test management

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-TC-001 | Must | 2 | Quản lý test case | Precondition, steps, expected, priority, tags, kỹ thuật thiết kế, trạng thái (DRAFT/APPROVED/DEPRECATED). |

### SentinelQA — Thực thi & CI

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-RUN-001 | Must | 2 | Thực thi test và lưu bằng chứng | Worker chạy pytest/Playwright; lưu result, log, screenshot/trace, commit SHA, môi trường. |
| FR-RUN-002 | Must | 2 | Tích hợp CI | GitHub Actions chạy test và gửi báo cáo cho pull request. |

### SentinelQA — Change impact & regression selection

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-IMP-001 | Should | 3 | Chọn regression test từ Git diff | Đọc diff, chọn test bị ảnh hưởng và lưu lý do chọn. |
| FR-IMP-002 | Should | 3 | Fallback chạy toàn bộ | Khi không phân tích được hoặc độ tin cậy thấp, chạy toàn bộ suite. |
| FR-IMP-003 | Should | 3 | Benchmark regression selection | So sánh recall, precision, thời gian với baseline run-all và changed-file rules. |

### SentinelQA — Mutation testing

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-MUT-001 | Should | 2 | Mutation testing | Sinh mutant có kiểm soát trên module nghiệp vụ; báo cáo killed/survived/equivalent/invalid và mutation score. |

### SentinelQA — Failure & flaky intelligence

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-FLK-001 | Should | 3 | Phân loại failure | ASSERTION, APPLICATION_ERROR, ENVIRONMENT, TIMEOUT, TEST_DEFECT, UNKNOWN kèm bằng chứng. |
| FR-FLK-002 | Should | 3 | Phát hiện flaky test | Chạy lặp N lần trong điều kiện tương đương và tính flaky rate. |

### SentinelQA — Release gate

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-GATE-001 | Must | 3 | Release gate Pass/Warn/Block | Quy tắc xác định, giải thích được, kiểm thử được. |
| FR-GATE-002 | Must | 3 | Lưu quyết định release | Lưu decision, rule IDs, snapshot đầu vào, ngưỡng, phiên bản rule set. |

### SentinelQA — AI Agents

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-AI-001 | Must | 4 | LLM adapter và structured output | Adapter thay được provider; schema validation; retry/timeout; trace model, prompt version, token, latency, cost. |
| FR-AI-002 | Must | 4 | Requirements-to-Tests Agent | Sinh scenario/test từ requirement, gắn requirement_id, đánh dấu yêu cầu mơ hồ. |
| FR-AI-003 | Must | 4 | Human review và approval | DRAFT → APPROVED/REJECTED bởi người; agent không tự duyệt. |
| FR-AI-004 | Should | 4 | Tool-using QA Agent | Agent gọi tool trong allow-list, giới hạn bước/thời gian/chi phí, lưu trace đầy đủ. |
| FR-AI-005 | Could | 4 | Test repair loop | Đề xuất sửa test lỗi, có diff, giới hạn vòng lặp, cần review. |

### SentinelQA — AI Evaluation

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-EVAL-001 | Must | 5 | Evaluation dataset có phiên bản | Dataset có nhãn, hướng dẫn gán nhãn, dev set và held-out set. |
| FR-EVAL-002 | Must | 5 | Benchmark runner | Chạy nhiều cấu hình (model, prompt, chiến lược) trên cùng dataset; xuất bảng metric và error analysis. |
| FR-EVAL-003 | Should | 5 | AI regression gate trong CI | Cảnh báo/chặn khi chất lượng AI giảm so với baseline sau khi đổi model/prompt/code. |

### SentinelQA — Analytics & dashboard

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-DASH-001 | Should | 5 | Dashboard QA | Pass/fail trend, flaky rate, mutation score, regression time saved, requirement coverage. |
| FR-DASH-002 | Should | 5 | Dashboard AI | Điểm evaluation theo cấu hình, chi phí, độ trễ, tool-call error, lỗi phổ biến. |
| FR-DASH-003 | Must | 5 | Analytics thanh toán (SQL KPI) | Payment success rate, failure breakdown, refund rate, timeout recovery, reconciliation mismatch; mỗi KPI có SQL nguồn. |

### Bảo mật & truy cập

| ID | Ưu tiên | Phase | Yêu cầu | Mô tả |
|---|---|---|---|---|
| FR-SEC-001 | Should | 6 | Xác thực và phân quyền | Role-based access (merchant, qa_engineer, approver, admin); merchant không đọc dữ liệu của merchant khác. |

**Tổng:** 58 yêu cầu chức năng — Must 37, Should 18, Could 3.

## 8. Yêu cầu phi chức năng

| ID | Yêu cầu | Tiêu chí / cách xác minh |
|---|---|---|
| NFR-001 | **Tính đúng của tiền:** lưu số nguyên minor unit hoặc NUMERIC có quy tắc; cấm số thực | Review code + test BR-PAY-001, TS-057 |
| NFR-002 | **Tái lập:** dựng môi trường từ trạng thái sạch bằng một lệnh; seed xác định | Một người khác làm theo README thành công |
| NFR-003 | **Hiệu năng (mục tiêu giả thuyết, sẽ đo):** tạo payment p95 < 300 ms ở 20 req/s trên máy dev; ghi rõ cấu hình đo | Locust, báo cáo p50/p95, lặp ≥ 5 lần |
| NFR-004 | **Khả năng quan sát:** mọi request có correlation_id; log có cấu trúc (JSON) | Tìm được toàn bộ dấu vết của một giao dịch bằng correlation_id |
| NFR-005 | **Bảo mật:** không secret trong repo/log; webhook ký HMAC; RBAC; giới hạn kích thước request; rate limit | TS-046, TS-047, TS-068, TS-069; quét secret trong CI |
| NFR-006 | **Nhất quán:** các bất biến về tiền (BR-REF-008, BR-PAY-013, BR-PAY-005, BR-REC-007) luôn đúng dưới concurrency | Test concurrency và property-based |
| NFR-007 | **Tài nguyên:** stack MVP (DB + API + web, worker khi cần) chạy được trong khoảng 4 GB RAM; AI gọi qua API ngoài, không chạy model nội bộ | Đo bằng docker stats |
| NFR-008 | **Chất lượng mã:** type hints, lint, format, type check bắt buộc trong CI | CI fail nếu vi phạm |
| NFR-009 | **Tài liệu:** mỗi quyết định kiến trúc quan trọng có ADR | Thư mục docs/architecture/adr |
| NFR-010 | **Quyền riêng tư:** chỉ dữ liệu tổng hợp; không PII thật | Rà soát dataset trước khi publish |

## 9. Ràng buộc, giả định, phụ thuộc

**Ràng buộc:** một người thực hiện; ngân sách hạ tầng thấp; máy phát triển hạn chế tài nguyên.
**Giả định:** có thể dùng LLM API bên ngoài với hạn mức chi phí nhỏ; GitHub Actions miễn phí đủ cho CI; có thể deploy bản demo bằng dịch vụ miễn phí hoặc giá thấp.
**Phụ thuộc:** Python, FastAPI, PostgreSQL, React/TypeScript, pytest, Playwright, Docker, GitHub Actions, một LLM provider có tool calling và structured output.

## 10. Chỉ số thành công

Định nghĩa, công thức, mẫu số và nguồn dữ liệu của từng chỉ số nằm ở [metrics.md](metrics.md). Nguyên tắc: **đặt tiêu chí trước, đo sau, công bố cả kết quả xấu**. Các con số mục tiêu trong metrics.md là *giả thuyết cần kiểm chứng*, không phải thành tích.

## 11. Rủi ro

| ID | Rủi ro | Khả năng | Tác động | Giảm thiểu |
|---|---|---|---|---|
| R-01 | Scope quá lớn cho một người | Cao | Cao | Làm theo phase; khi chậm giữ trục Payment Lab → Automation → AI Evaluation → BA/DA; hoãn mutation, change impact, fraud rules |
| R-02 | Hiểu sai nghiệp vụ thanh toán | Trung bình | Cao | Đối chiếu tài liệu công khai của các PSP (idempotency, webhook, refund); ghi rõ đây là mô hình đơn giản hóa; review với người có kinh nghiệm nếu có thể |
| R-03 | Code do AI hỗ trợ nhưng không giải thích được | Trung bình | Cao | Thay đổi nhỏ, viết test trước, tự giải thích từng quyết định bằng ADR |
| R-04 | Benchmark thiếu khách quan | Trung bình | Cao | Held-out set, baseline, seed, công bố kết quả xấu |
| R-05 | Chi phí LLM vượt dự kiến | Thấp | Trung bình | Giới hạn chi phí mỗi run, cache, dataset nhỏ ban đầu |
| R-06 | Mutation tool không hỗ trợ tốt phiên bản Python | Trung bình | Thấp | Giới hạn module thuần Python; tự tạo mutant có kiểm soát |
| R-07 | Demo không chạy khi deploy | Trung bình | Trung bình | Test dựng từ môi trường sạch từ sớm; docker compose là nguồn sự thật |
| R-08 | Rủi ro an toàn khi chạy test do AI sinh | Thấp | Cao | Sandbox, allow-list, không chạy trên server công khai |

## 12. Câu hỏi mở cần chốt

| # | Câu hỏi | Gợi ý quyết định | Hạn chốt |
|---|---|---|---|
| Q-01 | Ngôn ngữ tài liệu: tiếng Việt hay tiếng Anh? | Code, API, commit, README tóm tắt bằng tiếng Anh; tài liệu phân tích chi tiết bằng tiếng Việt; có bản tóm tắt tiếng Anh cho nhà tuyển dụng nước ngoài | Tuần 1 |
| Q-02 | LLM provider và ngân sách mỗi tháng? | Chọn provider có tool calling + structured output; đặt trần chi phí; thiết kế adapter để thay được | Tuần 12 |
| Q-03 | Có tách Payment Lab thành repo riêng không? | Giữ monorepo ở v1.0 | Tuần 2 |
| Q-04 | Ngưỡng release gate (mutation score, flaky rate) | Đặt tạm theo baseline đo thực tế, sau đó cố định và ghi lý do | Tuần 14 |
| Q-05 | Dashboard dùng React tự xây hay BI tool? | Tự xây bằng React cho sản phẩm; thêm một notebook/BI riêng cho case study DA | Tuần 21 |
| Q-06 | Hạn mức, ngưỡng nghiệp vụ trong BR (50 triệu VND, 180 ngày, 10 refund) | Đây là giá trị mô hình hóa; ghi rõ là tham số cấu hình được | Tuần 2 |

## 13. Lịch sử thay đổi

| Phiên bản | Ngày | Thay đổi |
|---|---|---|
| 0.1 | 2026-10-29 | Bản nháp đầu tiên |
