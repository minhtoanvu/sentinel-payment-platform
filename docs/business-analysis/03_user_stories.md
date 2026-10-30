# User Stories và Acceptance Criteria

Phiên bản 0.1. Tổng 31 story, mỗi story liên kết với requirement (FR) và có tiêu chí chấp nhận dạng Given/When/Then. Định nghĩa 'xong' xem [roadmap.md](../roadmap.md#definition-of-done).

| Story | Epic | Ưu tiên | Requirements |
|---|---|---|---|
| US-001 | Thanh toán | Must | FR-PAY-001, FR-PAY-002 |
| US-002 | Thanh toán | Must | FR-PAY-003, FR-REF-004 |
| US-003 | Thanh toán | Must | FR-PAY-004, FR-PAY-005, FR-PAY-012 |
| US-004 | Thanh toán | Must | FR-PAY-006 |
| US-005 | Thanh toán | Must | FR-PAY-011 |
| US-006 | Thanh toán | Must | FR-PAY-009, FR-PAY-010 |
| US-007 | Thanh toán | Should | FR-PAY-007, FR-PAY-008 |
| US-008 | Hoàn tiền | Must | FR-REF-001, FR-REF-003 |
| US-009 | Hoàn tiền | Must | FR-REF-002, FR-REF-003 |
| US-010 | Hoàn tiền | Should | FR-REF-005 |
| US-011 | Hoàn tiền | Could | FR-REF-006 |
| US-012 | Webhook | Must | FR-WH-001, FR-WH-002, FR-WH-004 |
| US-013 | Webhook | Should | FR-WH-003 |
| US-014 | Đối soát | Must | FR-REC-001, FR-REC-002, FR-REC-003 |
| US-015 | Đối soát | Should | FR-REC-004, FR-REC-005 |
| US-016 | Mô phỏng | Must | FR-SIM-001, FR-SIM-002 |
| US-017 | Quản lý chất lượng | Must | FR-REQ-001, FR-REQ-002, FR-REQ-003, FR-TC-001 |
| US-018 | Quản lý chất lượng | Must | FR-RUN-001, FR-RUN-002 |
| US-019 | Quản lý chất lượng | Should | FR-IMP-001, FR-IMP-002, FR-IMP-003 |
| US-020 | Quản lý chất lượng | Should | FR-MUT-001 |
| US-021 | Quản lý chất lượng | Should | FR-FLK-001, FR-FLK-002 |
| US-022 | Release | Must | FR-GATE-001, FR-GATE-002 |
| US-023 | AI | Must | FR-AI-001, FR-AI-002 |
| US-024 | AI | Must | FR-AI-003 |
| US-025 | AI | Should | FR-AI-004 |
| US-026 | AI | Could | FR-AI-005 |
| US-027 | AI | Must | FR-EVAL-001, FR-EVAL-002, FR-EVAL-003 |
| US-028 | Analytics | Must | FR-DASH-003, FR-DASH-001, FR-DASH-002 |
| US-029 | Bảo mật | Should | FR-SEC-001 |
| US-030 | Giao diện | Must | FR-UI-001, FR-UI-002 |
| US-031 | Rủi ro | Could | FR-SIM-003 |

## Epic: Thanh toán

### US-001 — Tạo một payment qua API với số tiền và đơn hàng của tôi

**Là** Merchant Developer, **tôi muốn** tạo một payment qua API với số tiền và đơn hàng của tôi, **để** bắt đầu quy trình thu tiền cho khách.

- Ưu tiên: **Must** · Requirements: FR-PAY-001, FR-PAY-002
- Test scenarios liên quan: TS-001, TS-002, TS-003, TS-004, TS-005, TS-006, TS-007, TS-008, TS-009, TS-010, TS-011

**Acceptance criteria**

1. Given merchant ACTIVE, When gửi POST /payments hợp lệ, Then 201, status=CREATED và expires_at = thời điểm tạo + 30 phút.
2. Given amount VND = 999, When tạo payment, Then 422 AMOUNT_BELOW_MIN và details chỉ ra field amount.
3. Given currency = EUR, When tạo payment, Then 422 UNSUPPORTED_CURRENCY và không có bản ghi nào được tạo.

### US-002 — Gửi lại request khi mạng lỗi mà không sợ tạo giao dịch trùng

**Là** Merchant Developer, **tôi muốn** gửi lại request khi mạng lỗi mà không sợ tạo giao dịch trùng, **để** hệ thống của tôi an toàn khi retry.

- Ưu tiên: **Must** · Requirements: FR-PAY-003, FR-REF-004
- Test scenarios liên quan: TS-012, TS-013, TS-014, TS-015, TS-016, TS-017, TS-039

**Acceptance criteria**

1. Given đã tạo payment với key K, When gửi lại cùng K và cùng payload, Then nhận cùng response, header Idempotent-Replayed=true, DB vẫn một payment.
2. Given key K đã dùng, When gửi K với payload khác, Then 422 IDEMPOTENCY_KEY_REUSED.
3. Given hai request cùng K gửi đồng thời, Then chỉ một payment được tạo; request còn lại nhận replay hoặc 409 REQUEST_IN_PROGRESS.

### US-003 — Xác nhận payment và nhận kết quả cuối cùng

**Là** Merchant Developer, **tôi muốn** xác nhận payment và nhận kết quả cuối cùng, **để** biết khách đã trả tiền hay chưa.

- Ưu tiên: **Must** · Requirements: FR-PAY-004, FR-PAY-005, FR-PAY-012
- Test scenarios liên quan: TS-018, TS-019, TS-020, TS-021, TS-024, TS-030, TS-031, TS-033

**Acceptance criteria**

1. Given payment CREATED và provider thành công, When confirm, Then status đi CREATED→PROCESSING→SUCCEEDED và có 2 bản ghi audit.
2. Given provider từ chối, When confirm, Then status=FAILED kèm failure_code.
3. Given payment đã SUCCEEDED, When confirm lại, Then 409 INVALID_STATE_TRANSITION và không gọi provider.

### US-004 — Hệ thống không coi timeout là thất bại

**Là** Payment Operations Analyst, **tôi muốn** hệ thống không coi timeout là thất bại, **để** tránh tính tiền khách hai lần.

- Ưu tiên: **Must** · Requirements: FR-PAY-006
- Test scenarios liên quan: TS-026, TS-027, TS-028, TS-029, TS-067

**Acceptance criteria**

1. Given provider timeout, When confirm, Then status=UNKNOWN và không có lần charge mới nào được tạo.
2. Given provider thực tế đã thành công, When hệ thống hỏi lại trạng thái, Then status=SUCCEEDED và provider chỉ ghi nhận một lần charge.
3. Given đã hỏi 5 lần vẫn không rõ, Then needs_review=true, status vẫn UNKNOWN và payment xuất hiện trong danh sách cần xử lý.

### US-005 — Đơn hàng chỉ có thể được thanh toán thành công một lần

**Là** Merchant Developer, **tôi muốn** đơn hàng chỉ có thể được thanh toán thành công một lần, **để** tránh khách trả hai lần cho một đơn.

- Ưu tiên: **Must** · Requirements: FR-PAY-011
- Test scenarios liên quan: TS-032

**Acceptance criteria**

1. Given đơn O đã có payment SUCCEEDED, When confirm payment khác cho O, Then 409 ORDER_ALREADY_PAID.
2. Given hai payment cùng O confirm đồng thời, Then chỉ một payment SUCCEEDED.

### US-006 — Xem danh sách và lịch sử trạng thái của giao dịch

**Là** Payment Operations Analyst, **tôi muốn** xem danh sách và lịch sử trạng thái của giao dịch, **để** điều tra khi khách khiếu nại.

- Ưu tiên: **Must** · Requirements: FR-PAY-009, FR-PAY-010
- Test scenarios liên quan: TS-025, TS-065

**Acceptance criteria**

1. Given có nhiều payment, When lọc theo status và khoảng thời gian, Then chỉ trả payment khớp và phân trang theo cursor ổn định.
2. Given payment đã qua nhiều trạng thái, When xem chi tiết, Then thấy timeline đầy đủ (from, to, lý do, thời điểm, correlation_id).

### US-007 — Hủy payment chưa xử lý và để payment quá hạn tự đóng

**Là** Merchant Developer, **tôi muốn** hủy payment chưa xử lý và để payment quá hạn tự đóng, **để** không để giao dịch treo mãi.

- Ưu tiên: **Should** · Requirements: FR-PAY-007, FR-PAY-008
- Test scenarios liên quan: TS-021, TS-022, TS-023

**Acceptance criteria**

1. Given payment CREATED, When cancel, Then status=CANCELED; confirm sau đó bị 409.
2. Given payment PROCESSING, When cancel, Then 409.
3. Given payment CREATED quá 30 phút, Then status=EXPIRED và confirm bị từ chối.

## Epic: Hoàn tiền

### US-008 — Hoàn tiền toàn phần cho một payment đã thành công

**Là** Merchant Developer, **tôi muốn** hoàn tiền toàn phần cho một payment đã thành công, **để** xử lý đơn bị hủy.

- Ưu tiên: **Must** · Requirements: FR-REF-001, FR-REF-003
- Test scenarios liên quan: TS-034, TS-036, TS-037, TS-040, TS-041

**Acceptance criteria**

1. Given payment SUCCEEDED 500.000 VND chưa hoàn, When refund 500.000, Then refund SUCCEEDED và refundable=0.
2. Given payment chưa SUCCEEDED, When refund, Then 409 PAYMENT_NOT_REFUNDABLE.

### US-009 — Hoàn tiền một phần nhiều lần

**Là** Merchant Developer, **tôi muốn** hoàn tiền một phần nhiều lần, **để** trả lại từng phần cho đơn nhiều sản phẩm.

- Ưu tiên: **Must** · Requirements: FR-REF-002, FR-REF-003
- Test scenarios liên quan: TS-035, TS-036, TS-038, TS-040, TS-044

**Acceptance criteria**

1. Given payment 1.000.000 VND, When refund 300.000 rồi 700.000, Then cả hai thành công và refunded_amount=1.000.000.
2. Given refundable=700.000, When refund 700.001, Then 422 REFUND_EXCEEDS_REFUNDABLE.
3. Given hai refund 600.000 gửi đồng thời trên payment 1.000.000, Then tổng SUCCEEDED không vượt 1.000.000.

### US-010 — Refund timeout không làm mất kiểm soát số tiền

**Là** Payment Operations Analyst, **tôi muốn** refund timeout không làm mất kiểm soát số tiền, **để** tránh hoàn vượt khi chưa rõ kết quả.

- Ưu tiên: **Should** · Requirements: FR-REF-005
- Test scenarios liên quan: TS-042

**Acceptance criteria**

1. Given refund timeout, Then refund=UNKNOWN và phần tiền vẫn bị giữ chỗ.
2. Given refund UNKNOWN giữ chỗ, When tạo refund làm vượt refundable, Then bị từ chối.

### US-011 — Duyệt các refund giá trị lớn

**Là** Refund Approver, **tôi muốn** duyệt các refund giá trị lớn, **để** có kiểm soát nội bộ (maker-checker).

- Ưu tiên: **Could** · Requirements: FR-REF-006
- Test scenarios liên quan: TS-043

**Acceptance criteria**

1. Given refund ≥ ngưỡng, Then status=PENDING_APPROVAL và chưa gọi provider.
2. Given người tạo cố tự duyệt, Then 403 SELF_APPROVAL_NOT_ALLOWED.

## Epic: Webhook

### US-012 — Chỉ tin các webhook hợp lệ và không xử lý lặp

**Là** Payment Operations Analyst, **tôi muốn** chỉ tin các webhook hợp lệ và không xử lý lặp, **để** dữ liệu giao dịch luôn đúng.

- Ưu tiên: **Must** · Requirements: FR-WH-001, FR-WH-002, FR-WH-004
- Test scenarios liên quan: TS-045, TS-046, TS-047, TS-048, TS-050, TS-051, TS-052, TS-053, TS-068

**Acceptance criteria**

1. Given chữ ký sai, Then 401, sự kiện được lưu với trạng thái xác thực thất bại và không đổi dữ liệu nghiệp vụ.
2. Given event_id đã xử lý, When nhận lại, Then 200 và số dư/refund không đổi lần hai.
3. Given timestamp lệch quá 5 phút, Then 401.

### US-013 — Hệ thống chịu được webhook đến sai thứ tự

**Là** Payment Operations Analyst, **tôi muốn** hệ thống chịu được webhook đến sai thứ tự, **để** trạng thái cuối cùng vẫn nhất quán.

- Ưu tiên: **Should** · Requirements: FR-WH-003
- Test scenarios liên quan: TS-030, TS-049

**Acceptance criteria**

1. Given refund.succeeded đến trước payment.succeeded, Then sự kiện được đệm và áp dụng đúng sau khi payment SUCCEEDED.
2. Given sự kiện có sequence cũ hơn sự kiện đã áp dụng, Then đánh dấu STALE và không ghi đè.

## Epic: Đối soát

### US-014 — Nhập file settlement và đối soát với dữ liệu nội bộ

**Là** Finance Reconciliation Analyst, **tôi muốn** nhập file settlement và đối soát với dữ liệu nội bộ, **để** phát hiện lệch tiền sớm.

- Ưu tiên: **Must** · Requirements: FR-REC-001, FR-REC-002, FR-REC-003
- Test scenarios liên quan: TS-054, TS-055, TS-056, TS-057, TS-058, TS-059, TS-060, TS-061, TS-062

**Acceptance criteria**

1. Given file hợp lệ khớp hoàn toàn, Then 0 mismatch và matched = tổng số dòng.
2. Given giao dịch chỉ có ở một phía, Then finding MISSING_IN_PROVIDER hoặc MISSING_IN_INTERNAL kèm bằng chứng.
3. Given chạy lại cùng file, Then kết quả giống hệt và không có finding trùng.
4. Given file sai checksum, Then FILE_VALIDATION_FAILED và không tạo run.

### US-015 — Xử lý từng mismatch và xem báo cáo tổng hợp

**Là** Finance Reconciliation Analyst, **tôi muốn** xử lý từng mismatch và xem báo cáo tổng hợp, **để** đóng sổ cuối ngày có căn cứ.

- Ưu tiên: **Should** · Requirements: FR-REC-004, FR-REC-005
- Test scenarios liên quan: TS-054, TS-063, TS-064

**Acceptance criteria**

1. Given finding OPEN, When chuyển RESOLVED, Then bắt buộc có lý do và người xử lý.
2. Given một run, Then báo cáo thỏa: tổng reference = số khớp + số reference có mismatch.

## Epic: Mô phỏng

### US-016 — Kích hoạt các kịch bản provider theo ý muốn bằng seed

**Là** QA Engineer, **tôi muốn** kích hoạt các kịch bản provider theo ý muốn bằng seed, **để** tái lập chính xác lỗi khi kiểm thử.

- Ưu tiên: **Must** · Requirements: FR-SIM-001, FR-SIM-002
- Test scenarios liên quan: TS-085

**Acceptance criteria**

1. Given scenario=timeout_success, When confirm, Then provider ghi nhận thành công nhưng response bị timeout.
2. Given cùng seed, When chạy hai lần, Then dữ liệu sinh ra giống hệt nhau.
3. Given cờ defect BUG-004 bật, Then hành vi lỗi tương ứng xuất hiện và tắt cờ thì biến mất.

## Epic: Quản lý chất lượng

### US-017 — Quản lý requirement và liên kết với test

**Là** QA Lead, **tôi muốn** quản lý requirement và liên kết với test, **để** biết yêu cầu nào đã được kiểm thử.

- Ưu tiên: **Must** · Requirements: FR-REQ-001, FR-REQ-002, FR-REQ-003, FR-TC-001
- Test scenarios liên quan: TS-070, TS-086, TS-087

**Acceptance criteria**

1. Given một requirement, Then liên kết được tới nhiều test case và ngược lại.
2. Given có requirement chưa liên kết test, Then xuất hiện trong báo cáo coverage gap.
3. Given test đã liên kết nhưng chưa từng chạy, Then báo cáo ghi 'chưa chạy' chứ không tính là đã kiểm thử.

### US-018 — Chạy test và xem bằng chứng khi test lỗi

**Là** QA Engineer, **tôi muốn** chạy test và xem bằng chứng khi test lỗi, **để** tìm nguyên nhân nhanh.

- Ưu tiên: **Must** · Requirements: FR-RUN-001, FR-RUN-002
- Test scenarios liên quan: TS-074, TS-088

**Acceptance criteria**

1. Given một lần chạy, Then mỗi result gắn commit SHA, môi trường, thời gian, log và screenshot/trace khi UI test lỗi.
2. Given pull request mới, Then CI chạy test và đăng báo cáo tóm tắt lên PR.

### US-019 — Chỉ chạy các regression test bị ảnh hưởng bởi thay đổi

**Là** QA Lead, **tôi muốn** chỉ chạy các regression test bị ảnh hưởng bởi thay đổi, **để** tiết kiệm thời gian mà không bỏ sót lỗi.

- Ưu tiên: **Should** · Requirements: FR-IMP-001, FR-IMP-002, FR-IMP-003
- Test scenarios liên quan: TS-075, TS-089

**Acceptance criteria**

1. Given một commit, Then hệ thống lưu diff, danh sách test được chọn và lý do cho từng test.
2. Given diff không phân tích được, Then fallback chạy toàn bộ suite.
3. Given tập commit benchmark, Then báo cáo có recall, precision và time saved so với baseline.

### US-020 — Biết test suite có thực sự bắt được lỗi

**Là** QA Engineer, **tôi muốn** biết test suite có thực sự bắt được lỗi, **để** không tin vào test pass một cách mù quáng.

- Ưu tiên: **Should** · Requirements: FR-MUT-001
- Test scenarios liên quan: TS-082

**Acceptance criteria**

1. Given module được chọn, Then mỗi mutant có kết quả killed/survived/equivalent/invalid.
2. Given kết quả, Then mutation score tính đúng theo BR-QE-002 và liệt kê mutant sống cùng test đề xuất bổ sung.

### US-021 — Phân loại lỗi và phát hiện flaky test

**Là** QA Engineer, **tôi muốn** phân loại lỗi và phát hiện flaky test, **để** giảm thời gian điều tra nhiễu.

- Ưu tiên: **Should** · Requirements: FR-FLK-001, FR-FLK-002
- Test scenarios liên quan: TS-076, TS-083

**Acceptance criteria**

1. Given test fail, Then có phân loại kèm bằng chứng; thiếu bằng chứng thì UNKNOWN.
2. Given test chạy lặp 10 lần với kết quả không đồng nhất, Then đánh dấu flaky; flaky rate nêu rõ mẫu số và cửa sổ thời gian.

## Epic: Release

### US-022 — Nhận quyết định Pass/Warn/Block kèm lý do

**Là** Release Manager, **tôi muốn** nhận quyết định Pass/Warn/Block kèm lý do, **để** quyết định phát hành có căn cứ.

- Ưu tiên: **Must** · Requirements: FR-GATE-001, FR-GATE-002
- Test scenarios liên quan: TS-071, TS-072, TS-073

**Acceptance criteria**

1. Given test Critical fail, Then BLOCK và nêu rule ID.
2. Given thiếu dữ liệu mutation, Then tối thiểu WARN, không PASS.
3. Given cùng đầu vào, Then luôn cùng quyết định; snapshot đầu vào được lưu.

## Epic: AI

### US-023 — Agent sinh test từ requirement có cấu trúc kiểm chứng được

**Là** AI Engineer, **tôi muốn** agent sinh test từ requirement có cấu trúc kiểm chứng được, **để** tăng tốc thiết kế test mà vẫn kiểm soát chất lượng.

- Ưu tiên: **Must** · Requirements: FR-AI-001, FR-AI-002
- Test scenarios liên quan: TS-078, TS-080, TS-095

**Acceptance criteria**

1. Given requirement rõ ràng, Then mỗi test có requirement_id, precondition, steps, expected và priority; output qua schema validation.
2. Given requirement mơ hồ, Then gắn cờ AMBIGUOUS với câu hỏi làm rõ, không tự thêm business rule.
3. Given model trả output sai schema, Then bị từ chối và ghi nhận lỗi.

### US-024 — Duyệt hoặc từ chối test do AI đề xuất

**Là** QA Lead, **tôi muốn** duyệt hoặc từ chối test do AI đề xuất, **để** chỉ test đã được con người xác nhận mới vào suite chính.

- Ưu tiên: **Must** · Requirements: FR-AI-003
- Test scenarios liên quan: TS-077

**Acceptance criteria**

1. Given test DRAFT, Then agent không thể chuyển sang APPROVED.
2. Given người duyệt APPROVED, Then test vào suite và lưu người duyệt, thời điểm, phiên bản.

### US-025 — Agent điều tra lỗi bằng công cụ được cấp quyền

**Là** QA Engineer, **tôi muốn** agent điều tra lỗi bằng công cụ được cấp quyền, **để** rút ngắn thời gian tìm nguyên nhân.

- Ưu tiên: **Should** · Requirements: FR-AI-004
- Test scenarios liên quan: TS-079, TS-095

**Acceptance criteria**

1. Given một test fail, Then agent gọi tool trong allow-list, có trace từng bước và kết luận kèm bằng chứng.
2. Given log chứa chỉ dẫn độc hại, Then agent không gọi tool ngoài allow-list.

### US-026 — Agent đề xuất bản sửa cho test lỗi, có diff và giới hạn vòng lặp

**Là** QA Engineer, **tôi muốn** agent đề xuất bản sửa cho test lỗi, có diff và giới hạn vòng lặp, **để** giảm công bảo trì test mà không mất kiểm soát.

- Ưu tiên: **Could** · Requirements: FR-AI-005
- Test scenarios liên quan: TS-090

**Acceptance criteria**

1. Given test do AI sinh bị lỗi chạy, Then agent đề xuất bản sửa kèm diff, tối đa số vòng cho phép.
2. Given bản sửa chưa được duyệt, Then test đã APPROVED không bị ghi đè; báo cáo phân biệt 'script chạy được' với 'script kiểm tra đúng nghiệp vụ'.

### US-027 — So sánh nhiều cấu hình AI trên cùng dataset

**Là** AI Engineer, **tôi muốn** so sánh nhiều cấu hình AI trên cùng dataset, **để** biết cấu hình nào tốt hơn và vì sao.

- Ưu tiên: **Must** · Requirements: FR-EVAL-001, FR-EVAL-002, FR-EVAL-003
- Test scenarios liên quan: TS-081, TS-091

**Acceptance criteria**

1. Given dataset phiên bản V, When chạy hai cấu hình, Then có bảng metric (schema validity, execution success, mutation detection, chi phí, độ trễ).
2. Given cấu hình mới kém baseline vượt ngưỡng, Then CI cảnh báo hoặc chặn.

## Epic: Analytics

### US-028 — Xem KPI thanh toán và KPI chất lượng với định nghĩa rõ ràng

**Là** Data Analyst / QA Lead, **tôi muốn** xem KPI thanh toán và KPI chất lượng với định nghĩa rõ ràng, **để** ra quyết định dựa trên dữ liệu.

- Ưu tiên: **Must** · Requirements: FR-DASH-003, FR-DASH-001, FR-DASH-002
- Test scenarios liên quan: TS-092, TS-093

**Acceptance criteria**

1. Given KPI trên dashboard, Then có định nghĩa, mẫu số và truy vấn SQL nguồn.
2. Given dữ liệu seed demo và dữ liệu từ lần chạy thật, Then dashboard phân biệt rõ hai loại.

## Epic: Bảo mật

### US-029 — Phân quyền theo vai trò

**Là** Admin, **tôi muốn** phân quyền theo vai trò, **để** bảo vệ dữ liệu và hành động nhạy cảm.

- Ưu tiên: **Should** · Requirements: FR-SEC-001
- Test scenarios liên quan: TS-068, TS-069

**Acceptance criteria**

1. Given merchant A, When đọc payment của merchant B, Then 404/403 và không lộ dữ liệu.
2. Given vai trò không đủ quyền, When thực hiện refund approval, Then 403.

## Epic: Giao diện

### US-030 — Dùng giao diện web để tạo và theo dõi giao dịch

**Là** Payment Operations Analyst, **tôi muốn** dùng giao diện web để tạo và theo dõi giao dịch, **để** thao tác và điều tra không cần gọi API thủ công.

- Ưu tiên: **Must** · Requirements: FR-UI-001, FR-UI-002
- Test scenarios liên quan: TS-065, TS-066, TS-067, TS-094

**Acceptance criteria**

1. Given payment ở UNKNOWN, Then UI hiển thị 'Đang chờ xác nhận', không hiển thị 'Thành công'.
2. Given API trả lỗi, Then UI hiển thị lỗi dễ hiểu kèm correlation_id.

## Epic: Rủi ro

### US-031 — Phát hiện mẫu giao dịch bất thường đơn giản

**Là** Risk Analyst, **tôi muốn** phát hiện mẫu giao dịch bất thường đơn giản, **để** cảnh báo sớm trên dữ liệu tổng hợp.

- Ưu tiên: **Could** · Requirements: FR-SIM-003
- Test scenarios liên quan: TS-084

**Acceptance criteria**

1. Given nhiều giao dịch vượt ngưỡng trong cửa sổ thời gian, Then tạo cảnh báo có rule ID; hệ thống không tự chặn giao dịch.
