# Metrics — Định nghĩa, công thức, mẫu số và quy tắc công bố

Phiên bản 0.1. Mọi chỉ số có: định nghĩa, công thức, mẫu số, nguồn dữ liệu, loại trừ, và (nếu có) **mục tiêu giả thuyết**. Mục tiêu là *giả thuyết đặt trước* để kiểm chứng; không phải thành tích và không được ghi vào CV trước khi đo.

## 1. Quy tắc công bố (áp dụng cho mọi benchmark)

1. **Đặt tiêu chí trước, đo sau.** Ghi ngưỡng và phương pháp vào repo (commit) trước khi chạy.
2. **Tái lập:** ghi commit SHA, dataset version, seed, model/prompt version, cấu hình máy, số lần lặp.
3. **Lặp lại:** mỗi phép đo chạy ít nhất 5 lần; báo cáo median và khoảng (min–max hoặc IQR), không chỉ trung bình.
4. **Held-out:** dataset đánh giá cuối không dùng để chỉnh prompt hay rule.
5. **Công bố kết quả xấu:** phương pháp kém baseline ở đâu, lỗi nào không được phát hiện.
6. **Không dùng một điểm tổng hợp duy nhất** che giấu điểm yếu; luôn có bảng chi tiết.
7. **Dữ liệu mô phỏng phải được gắn nhãn là mô phỏng** (ví dụ "defect escape rate trên bộ dữ liệu mô phỏng").
8. Chia cho 0 hoặc mẫu số quá nhỏ: hiển thị "không đủ dữ liệu (n = …)" thay vì phần trăm.

## 2. Chỉ số thanh toán (Payment KPIs — nhánh DA)

Ngày nghiệp vụ theo Asia/Ho_Chi_Minh. Mỗi KPI phải có file SQL trong `analytics/sql/` và được đối chiếu với giá trị trên dashboard (TS-092).

| Mã | Chỉ số | Công thức | Mẫu số / phạm vi | Loại trừ |
|---|---|---|---|---|
| K-01 | Payment success rate | `#SUCCEEDED / (#SUCCEEDED + #FAILED)` | Payment có kết quả cuối trong kỳ | CREATED, PROCESSING, UNKNOWN, CANCELED, EXPIRED (báo cáo riêng) |
| K-02 | Failure rate theo nguyên nhân | `#FAILED theo failure_code / #FAILED` | Payment FAILED trong kỳ | — |
| K-03 | Timeout rate | `#payment từng qua UNKNOWN / #payment đã confirm` | Payment đã confirm | — |
| K-04 | Timeout recovery rate | `#UNKNOWN → SUCCEEDED hoặc FAILED trong ≤5 lần hỏi / #payment từng UNKNOWN` | Payment từng UNKNOWN | Báo `needs_review` riêng |
| K-05 | Unresolved UNKNOWN | `#payment UNKNOWN & needs_review` | Thời điểm đo | — |
| K-06 | Refund rate (số lượng) | `#payment có refund SUCCEEDED / #payment SUCCEEDED` | Payment SUCCEEDED trong kỳ | — |
| K-07 | Refund rate (giá trị) | `Σ refund SUCCEEDED / Σ payment SUCCEEDED` | Theo currency, không cộng VND với USD | — |
| K-08 | Duplicate prevention rate | `#request replay / #request có Idempotency-Key lặp` | Request lặp key | — |
| K-09 | Reconciliation match rate | `#MATCHED / tổng reference duy nhất` | Một run ACTIVE | Quarantine báo riêng |
| K-10 | Mismatch rate theo loại | `#reference có mismatch loại T / tổng reference` | Một run ACTIVE | — |
| K-11 | Open mismatch aging | Phân phối tuổi của finding OPEN/INVESTIGATING | Thời điểm đo | — |
| K-12 | Webhook duplicate rate | `#DUPLICATE / #webhook nhận` | Kỳ đo | Chữ ký sai báo riêng |
| K-13 | Webhook processing lag | p50/p95 của `processed_at − received_at` | Webhook PROCESSED | — |

*Phân tích kèm theo:* kiểm tra cỡ mẫu trước khi kết luận về một phương thức thanh toán; báo cáo khoảng tin cậy khi so sánh tỷ lệ giữa các nhóm nhỏ; tách dữ liệu seed và dữ liệu chạy thật.

## 3. Chỉ số chất lượng kiểm thử (QA KPIs)

| Mã | Chỉ số | Công thức | Mẫu số / phạm vi | Mục tiêu giả thuyết |
|---|---|---|---|---|
| Q-01 | Requirement coverage (có test) | `#requirement Must có ≥1 test APPROVED / #requirement Must` | Requirement Must hiện hành | 100% |
| Q-02 | Requirement verified | `#requirement Must có test mới nhất PASS / #requirement Must` | Cùng trên | Báo cáo, không đặt ngưỡng cứng |
| Q-03 | Test pass rate | `#PASS / (#PASS + #FAIL + #ERROR)` | Một run | — (phân loại failure kèm theo) |
| Q-04 | Mutation score | `killed / (total − equivalent − invalid)` | Module trong phạm vi, một mutation run | ≥ 80% module nghiệp vụ lõi *(giả thuyết)* |
| Q-05 | Seeded defect detection rate | `#BUG-xxx bị ≥1 test fail khi bật cờ / #BUG-xxx được bật` | 18 lỗi cài sẵn | ≥ 90% *(giả thuyết)* |
| Q-06 | Regression recall | `TP / (TP + FN)` | Test thực sự bị ảnh hưởng (nhãn chuẩn) theo commit | ≥ 95% *(giả thuyết)* |
| Q-07 | Regression precision | `TP / (TP + FP)` | Test được chọn | Báo cáo |
| Q-08 | Regression time saved | `(T_full − T_selected) / T_full` | Cùng môi trường, cùng suite, ≥5 lần lặp | ≥ 40% với recall ≥ 95% *(giả thuyết)* |
| Q-09 | Flaky rate | `#test flaky / #test được rerun` | Cửa sổ: nêu rõ (ví dụ 30 ngày), N=10 lần rerun | Báo cáo trước/sau cô lập |
| Q-10 | Failure classification accuracy | Precision/recall mỗi lớp + confusion matrix | Tập lỗi có nhãn | Báo cáo từng lớp |
| Q-11 | Defect escape rate (mô phỏng) | `#lỗi phát hiện sau release mô phỏng / tổng lỗi` | Kịch bản mô phỏng có nhãn | Báo cáo, ghi rõ là mô phỏng |
| Q-12 | Gate decision correctness | `#quyết định đúng kỳ vọng / #kịch bản gate` | Bộ kịch bản Pass/Warn/Block có đáp án | 100% (là logic xác định) |
| Q-13 | Suite runtime p50/p95 | Thời gian chạy theo nhóm test | Môi trường CI cố định | Báo cáo |

Tính recall/precision cần **nhãn chuẩn** (ground truth) cho "test thực sự bị ảnh hưởng": xác định bằng phân tích thủ công và thực nghiệm (cài lỗi vào commit, xem test nào fail khi chạy toàn bộ). Không dùng chính kết quả của SentinelQA để tạo nhãn.

## 4. Chỉ số AI (AI KPIs)

So sánh tối thiểu 4 phương pháp trên cùng dataset: **M0** test viết tay (tham chiếu); **A1** prompt cơ bản; **A2** structured output + validation; **A3** agent có execution feedback. Nếu ngân sách cho phép, thêm ít nhất 2 model.

| Mã | Chỉ số | Công thức / cách đo | Ghi chú |
|---|---|---|---|
| A-01 | Schema validity | `#output hợp lệ / #output` | Trước retry và sau retry (báo cả hai) |
| A-02 | Requirement coverage | `#hành vi bắt buộc được test bao phủ / #hành vi bắt buộc` | Theo `expected_behaviors` của dataset |
| A-03 | Execution success | `#script chạy được (không lỗi cú pháp/môi trường) / #script` | Trong sandbox |
| A-04 | Assertion validity | `#test có assertion đúng oracle / #test` | Chấm bởi evaluator + kiểm tra thủ công mẫu; ghi tỷ lệ đồng thuận |
| A-05 | Mutation / seeded-defect detection | `#BUG phát hiện bởi test AI / #BUG trong phạm vi requirement` | Chỉ số quan trọng nhất |
| A-06 | Unsupported claims | `#kết luận thiếu bằng chứng / #kết luận` | Agent điều tra lỗi |
| A-07 | Ambiguity handling | Precision/recall gắn cờ AMBIGUOUS trên yêu cầu có nhãn | Không tự bịa rule |
| A-08 | Tool-call correctness | `#tool call đúng tool và tham số / #tool call` | Từ trace |
| A-09 | Policy violations | `#tool call ngoài allow-list hoặc cố self-approve` | Mục tiêu: 0 được thực thi; đếm cả số lần bị chặn |
| A-10 | Cost per accepted test | `Σ cost / #test được người duyệt APPROVED` | Ghi giá model tại thời điểm đo |
| A-11 | Latency | p50/p95 mỗi lần sinh và kiểm chứng | — |
| A-12 | Human acceptance rate | `#APPROVED / #DRAFT` | Kèm lý do từ chối phổ biến |

**Bảng báo cáo bắt buộc:** mỗi phương pháp một hàng, mỗi chỉ số một cột; thêm mục *error analysis* với ví dụ lỗi tiêu biểu và trường hợp agent làm kết quả **tệ hơn** baseline.

## 5. Chỉ số release gate

Rule set `v1` (ngưỡng đặt tạm, sẽ cố định sau khi có baseline thật — câu hỏi Q-04 trong PRD):

| Quy tắc | Điều kiện | Kết quả | Mã |
|---|---|---|---|
| G-B1 | Có test FAIL gắn requirement mức Critical | BLOCK | BR-GATE-003 |
| G-B2 | Vi phạm bất biến về tiền (INV-01..INV-04) | BLOCK | BR-GATE-003 |
| G-W1 | Requirement Must không có test APPROVED | WARN | BR-GATE-004 |
| G-W2 | Mutation score dưới ngưỡng module | WARN | BR-GATE-004 |
| G-W3 | Flaky rate trên ngưỡng | WARN | BR-GATE-004 |
| G-W4 | Có mismatch đối soát severity HIGH đang OPEN | WARN | BR-GATE-004 |
| G-W5 | Thiếu tín hiệu bắt buộc (mutation, coverage, kết quả run) | WARN (tối thiểu) | BR-GATE-002 |
| G-P | Không vi phạm quy tắc nào | PASS | — |

Thứ tự ưu tiên: BLOCK > WARN > PASS. Mỗi quyết định lưu danh sách rule đã kích hoạt, giá trị đầu vào, ngưỡng và phiên bản rule set.

## 6. Chỉ số hiệu năng và độ tin cậy hệ thống

| Mã | Chỉ số | Cách đo |
|---|---|---|
| P-01 | Latency p50/p95/p99 của tạo payment, confirm, refund | Locust, môi trường và cấu hình máy ghi rõ |
| P-02 | Throughput tối đa ổn định (error rate < 1%) | Tăng tải theo bậc |
| P-03 | Error rate theo mã | Log có cấu trúc |
| P-04 | Vi phạm bất biến dưới tải | Kiểm tra INV-01..INV-08 sau mỗi kịch bản; **mục tiêu 0** |
| P-05 | Sử dụng RAM của stack | `docker stats` |

Phân biệt lỗi do giới hạn máy chạy test với lỗi của ứng dụng.

## 7. Công thức tham khảo (văn bản thuần)

```
Time saved      = (T_full − T_selected) / T_full × 100%
Recall          = TP / (TP + FN)
Precision       = TP / (TP + FP)
F1              = 2 × Precision × Recall / (Precision + Recall)
Mutation score  = killed / (total − equivalent − invalid)
Success rate    = SUCCEEDED / (SUCCEEDED + FAILED)
Refundable      = amount − Σ SUCCEEDED − Σ giữ chỗ (PENDING_APPROVAL, REQUESTED, PROCESSING, UNKNOWN)
Cost / accepted = Σ cost_usd / #APPROVED
```

## 8. Định nghĩa "đủ dữ liệu" tối thiểu

| Chỉ số | Tối thiểu để công bố |
|---|---|
| Tỷ lệ theo nhóm (K-01, K-04…) | n ≥ 30 mỗi nhóm; dưới đó ghi "không đủ dữ liệu" |
| Regression benchmark | ≥ 20 commit mô phỏng với nhãn chuẩn |
| Flaky | ≥ 10 lần rerun mỗi test được xét |
| Mutation | ≥ 100 mutant hợp lệ trên module lõi, hoặc toàn bộ mutant nếu ít hơn (ghi rõ) |
| AI evaluation | ≥ 50 case trong held-out; ≥ 3 lần lặp cho phần có tính ngẫu nhiên |
