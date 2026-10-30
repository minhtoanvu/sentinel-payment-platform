# Domain Glossary — Thuật ngữ nghiệp vụ, QE và AI

Phiên bản 0.1. Định nghĩa theo cách dùng **trong dự án này**; một số thuật ngữ được đơn giản hóa so với thực tế ngành. Mục ghi chú "Đơn giản hóa" chỉ rõ chỗ khác biệt.

## 1. Thanh toán (Payments)

| Thuật ngữ | Định nghĩa | Ví dụ / Ghi chú |
|---|---|---|
| **Merchant** | Đơn vị bán hàng nhận thanh toán, tích hợp qua API | Cửa hàng online |
| **Customer / Payer** | Người trả tiền | Dữ liệu tổng hợp trong dự án |
| **Payment** | Một yêu cầu thu tiền, có vòng đời trạng thái | `pay_01H...`, 500.000 VND |
| **Payment method** | Phương thức dùng để trả (thẻ tokenized giả lập, ví) | CARD_TOKEN, WALLET |
| **Payment provider / PSP** | Bên xử lý thanh toán hộ merchant, kết nối ngân hàng/mạng thẻ | Trong dự án: Provider Simulator |
| **Acquirer / Issuer** | Ngân hàng phía merchant / ngân hàng phát hành thẻ phía khách | Chỉ mô tả để hiểu bối cảnh; không mô phỏng |
| **Authorization** | Bước xin phép giữ tiền trên phương tiện thanh toán | *Đơn giản hóa:* Payment Lab gộp authorization và capture trong một bước `confirm` |
| **Capture** | Bước chốt thu tiền sau authorization | Xem trên |
| **Settlement** | Quá trình tiền thực sự được chuyển giữa các bên, thường theo lô và chậm hơn thời gian giao dịch | Provider gửi settlement file |
| **Settlement file** | Báo cáo giao dịch do provider cung cấp để đối soát | CSV có header, row_count, checksum |
| **Refund (hoàn tiền)** | Trả lại một phần hoặc toàn bộ số tiền của payment đã thành công | Có thể nhiều lần, tổng ≤ số tiền gốc |
| **Partial refund** | Hoàn một phần số tiền | 300.000 trên 1.000.000 |
| **Reversal / Void** | Hủy giao dịch trước khi chốt tiền | *Đơn giản hóa:* dự án dùng `cancel` cho payment CREATED |
| **Chargeback / Dispute** | Khiếu nại từ chủ thẻ qua ngân hàng, tiền bị thu hồi | Ngoài phạm vi v1.0 |
| **Refundable amount** | Số tiền còn được hoàn = gốc − đã hoàn − đang giữ chỗ | BR-REF-003 |
| **Reservation (giữ chỗ)** | Phần refundable bị tạm giữ cho refund đang xử lý | Ngăn hoàn vượt mức dưới concurrency |
| **Minor unit** | Đơn vị nhỏ nhất của tiền tệ | VND: 1 đồng (exponent 0); USD: 1 cent (exponent 2) |
| **ISO 4217** | Chuẩn mã tiền tệ và số chữ số thập phân | VND, USD |
| **MDR** | Merchant Discount Rate — phí merchant trả | Ngoài phạm vi |
| **PAN** | Primary Account Number — số thẻ | **Không bao giờ** lưu trong dự án |
| **Tokenization** | Thay dữ liệu nhạy cảm bằng token vô nghĩa | Payment method giả lập dùng token |
| **PCI DSS** | Bộ chuẩn bảo mật dữ liệu thẻ | Dự án không tuyên bố tuân thủ |
| **KYC / AML** | Định danh khách hàng / chống rửa tiền | Ngoài phạm vi |
| **3-D Secure** | Lớp xác thực chủ thẻ bổ sung | Ngoài phạm vi |

## 2. Độ tin cậy và dữ liệu

| Thuật ngữ | Định nghĩa | Ví dụ / Ghi chú |
|---|---|---|
| **Idempotency** | Thực hiện cùng một yêu cầu nhiều lần cho cùng kết quả như một lần | Retry không tạo payment thứ hai |
| **Idempotency key** | Khóa do client sinh để nhận diện một ý định | Header `Idempotency-Key` |
| **Replay** | Trả lại response đã lưu cho request lặp | Header `Idempotent-Replayed: true` |
| **Retry / Backoff** | Thử lại sau lỗi; giãn thời gian giữa các lần | 5-10-20-40-80 giây |
| **Timeout** | Không nhận phản hồi trong thời hạn; **không** đồng nghĩa thất bại | Payment → UNKNOWN |
| **UNKNOWN (trạng thái không xác định)** | Kết quả cuối chưa biết, chờ xác minh | Cần status query/webhook/đối soát |
| **State machine** | Mô hình trạng thái và chuyển trạng thái hợp lệ | payment-lifecycle.md |
| **Terminal state** | Trạng thái cuối, không chuyển tiếp | SUCCEEDED, FAILED, CANCELED, EXPIRED |
| **Race condition** | Kết quả phụ thuộc thứ tự thực thi không kiểm soát của các tiến trình đồng thời | Hai payment cùng tiêu một số dư |
| **Double charge** | Khách bị tính tiền hai lần cho một ý định | Lỗi nghiêm trọng nhất của domain |
| **Webhook** | Provider chủ động gọi HTTP đến hệ thống để báo sự kiện | `payment.succeeded` |
| **HMAC** | Mã xác thực thông điệp dùng khóa bí mật chung | HMAC-SHA256 |
| **Replay attack** | Gửi lại thông điệp hợp lệ đã bắt được | Chống bằng timestamp + dedupe |
| **Event ID / Sequence** | Mã định danh và thứ tự sự kiện từ provider | Dedupe và chống sự kiện cũ |
| **Audit trail** | Nhật ký thay đổi bất biến | `payment_status_history` |
| **Correlation ID** | Mã gắn xuyên suốt một luồng xử lý để truy vết | Có trong log và error response |
| **Ledger** | Sổ cái ghi nhận biến động tiền | Ngoài phạm vi (dùng audit trail + bảng payments/refunds) |

## 3. Đối soát (Reconciliation)

| Thuật ngữ | Định nghĩa | Ví dụ / Ghi chú |
|---|---|---|
| **Reconciliation** | So khớp dữ liệu nội bộ với dữ liệu đối tác để phát hiện sai lệch | Hằng ngày |
| **Business date** | Ngày nghiệp vụ để gom giao dịch | Theo giờ Việt Nam, cutoff 00:00 +07 |
| **Cutoff** | Mốc thời gian chia ngày nghiệp vụ | 23:59:59 và 00:00:00 thuộc hai ngày khác nhau |
| **Match key** | Trường dùng để ghép hai bản ghi | `provider_reference` |
| **Mismatch / Finding** | Một sai lệch phát hiện được | AMOUNT_MISMATCH |
| **Quarantine** | Nơi giữ bản ghi lỗi để xử lý, không bỏ đi im lặng | Dòng thiếu khóa |
| **Orphan** | Sự kiện hoặc bản ghi không có đối tượng tương ứng | Webhook cho payment không tồn tại |
| **Write-off** | Chấp nhận sai lệch và đóng kèm lý do | WRITTEN_OFF |
| **Conservation invariant** | Tổng thành phần phải bằng tổng ban đầu | BR-REC-007 |

## 4. Quality Engineering

| Thuật ngữ | Định nghĩa | Ví dụ / Ghi chú |
|---|---|---|
| **Test oracle** | Cơ chế xác định kết quả đúng của test | Assertion kiểm tra số tiền, trạng thái, tác dụng phụ |
| **Equivalence partitioning (EP)** | Chia dữ liệu thành lớp tương đương, mỗi lớp thử đại diện | Amount hợp lệ / dưới min / trên max |
| **Boundary value analysis (BVA)** | Thử tại và sát biên | 999, 1.000, 50.000.000, 50.000.001 |
| **Decision table** | Bảng tổ hợp điều kiện → hành động | Refund theo trạng thái payment |
| **State transition testing** | Kiểm thử chuyển trạng thái hợp lệ và không hợp lệ | Ma trận state × event |
| **Property / invariant testing** | Kiểm tra tính chất luôn đúng với nhiều đầu vào | Tổng refund ≤ số tiền gốc |
| **Regression testing** | Kiểm tra thay đổi không làm hỏng chức năng cũ | Suite chạy mỗi PR |
| **Regression test selection** | Chỉ chạy tập con test bị ảnh hưởng | Recall, precision, time saved |
| **Mutation testing** | Cài lỗi nhỏ có chủ đích vào mã để xem test có phát hiện không | Đổi `<=` thành `<` |
| **Mutant / Killed / Survived** | Bản mã đã cài lỗi / test phát hiện / test không phát hiện | Survived = điểm yếu của test |
| **Equivalent mutant** | Mutant không đổi hành vi quan sát được nên không thể bị giết | Phải loại khỏi mẫu số, có lý do |
| **Mutation score** | killed / (total − equivalent − invalid) | BR-QE-002 |
| **Seeded defect** | Lỗi cài sẵn cố ý, có mã BUG-xxx | Ground truth cho benchmark |
| **Flaky test** | Test cho kết quả khác nhau trong điều kiện tương đương | BR-QE-003 |
| **Quality gate / Release gate** | Điều kiện tự động quyết định cho đi tiếp hay chặn | PASS / WARN / BLOCK |
| **Traceability** | Liên kết hai chiều requirement ↔ test ↔ defect ↔ kết quả | Traceability matrix |
| **UAT** | User Acceptance Testing — người dùng nghiệp vụ xác nhận | Kịch bản + sign-off |
| **SDET** | Software Development Engineer in Test | Kỹ sư test thiên về lập trình |
| **Defect escape rate** | Tỷ lệ lỗi lọt ra sau phát hành trên tổng lỗi | Dùng dữ liệu mô phỏng, nêu rõ |
| **Page Object Model** | Mẫu thiết kế đóng gói thao tác UI trong lớp | Playwright tests |

## 5. AI Engineering

| Thuật ngữ | Định nghĩa | Ví dụ / Ghi chú |
|---|---|---|
| **LLM** | Mô hình ngôn ngữ lớn | Gọi qua API |
| **Structured output** | Đầu ra theo schema cố định, kiểm chứng được | JSON theo Pydantic schema |
| **Tool calling** | Mô hình yêu cầu hệ thống gọi hàm được cấp quyền | `read_test_logs` |
| **Agent** | Vòng lặp: lập kế hoạch → gọi tool → quan sát → quyết định tiếp | Có giới hạn bước |
| **Allow-list** | Danh sách tool được phép | BR-AI-003 |
| **Trace** | Bản ghi từng bước của agent (model output, tool call, kết quả) | Phục vụ giải thích và debug |
| **Prompt injection** | Dữ liệu chứa chỉ dẫn độc hại nhằm điều khiển mô hình | Trong requirement, log, webhook |
| **Hallucination / Unsupported claim** | Kết luận không có bằng chứng | Metric "unsupported claims" |
| **Human-in-the-loop** | Con người duyệt trước khi hành động có tác động | BR-AI-001 |
| **Evaluation dataset** | Tập mẫu có nhãn để đo chất lượng | Phiên bản hóa |
| **Dev set / Held-out set** | Tập dùng để cải tiến / tập dành riêng để đánh giá cuối | Không chỉnh prompt trên held-out |
| **Baseline** | Phương pháp đối chứng để so sánh | Test viết tay; prompt cơ bản |
| **Assertion validity** | Assertion có kiểm tra đúng hành vi cần kiểm tra | Khác với "test chạy được" |
| **Execution-grounded** | Kết luận dựa trên kết quả thực thi, không chỉ văn bản | Chạy test rồi mới đánh giá |
| **Sandbox** | Môi trường cô lập để chạy mã không tin cậy | BR-AI-005 |
| **Prompt versioning** | Gắn phiên bản cho prompt để tái lập | `prompt_version` |
| **Cost per accepted test** | Chi phí AI chia cho số test được duyệt | Metric AI |

## 6. Vận hành

| Thuật ngữ | Định nghĩa |
|---|---|
| **Modular monolith** | Một ứng dụng triển khai chung nhưng chia module rõ ràng |
| **Worker** | Tiến trình nền thực thi job (chạy test, agent) |
| **CI/CD** | Tích hợp và triển khai liên tục |
| **ADR** | Architecture Decision Record — ghi lại quyết định kiến trúc và lý do |
| **p50 / p95** | Phân vị thứ 50 / 95 của độ trễ |
| **Definition of Done** | Điều kiện để coi một hạng mục là hoàn thành |
