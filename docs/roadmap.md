# Roadmap, Backlog và Kế hoạch Tuần 1–2

Phiên bản 0.1. Mốc 24 tuần là mốc lập kế hoạch, không phải deadline cứng: nếu một milestone chưa đạt acceptance criteria thì kéo dài milestone đó thay vì bỏ qua hoặc làm nửa vời.

## 1. Tổng quan 6 phase

| Phase | Tuần | Trọng tâm | Sản phẩm bàn giao | Bằng chứng cho |
|---|---|---|---|---|
| 0 | 1–2 | Discovery & Design | PRD, glossary, rules, use cases, stories, test scenarios, ERD, OpenAPI, BPMN | BA |
| 1 | 3–6 | Payment Lab | API, state machine, idempotency, refund, webhook, reconciliation, UI cơ bản, simulator, seed | Backend, BA, DA |
| 2 | 7–10 | Automation & QA | pytest + Playwright, traceability, mutation (khởi đầu), performance/concurrency | QA/SDET |
| 3 | 11–14 | Quality Intelligence | Git diff & selection, benchmark, failure/flaky, release gate | QA/SDET, Backend |
| 4 | 15–18 | AI Agent Engineering | LLM adapter, Requirements-to-Tests Agent, tool agent, review, repair (Could) | AI |
| 5 | 19–21 | AI Evaluation & Data | Dataset, benchmark, dashboard, SQL KPI, case study DA | AI, DA |
| 6 | 22–24 | Production & Portfolio | Security, Docker, CI/CD, deploy, benchmark công bố, README, video | Tất cả |

**Trục ưu tiên khi chậm tiến độ:** Payment Lab → Automation → AI Evaluation → tài liệu BA/DA. Hoãn trước: mutation nâng cao, change impact, fraud rules, test repair. BA và DA **chạy song song** từ Phase 0, không dồn về cuối.

## 2. Milestone và acceptance criteria

| Mốc | Điều kiện đạt (rút gọn) |
|---|---|
| M0 — Design freeze (cuối T2) | PRD 1.0 được review; BPMN AS-IS/TO-BE; OpenAPI + ERD khớp business rules; mọi FR Must có test scenario; traceability không có cảnh báo |
| M1 — Payment Lab MVP (cuối T6) | Tạo/confirm/cancel, idempotency, timeout→UNKNOWN, refund (full/partial, reservation), webhook (ký, dedupe), reconciliation cơ bản, simulator, seed; dựng từ môi trường sạch bằng một lệnh |
| M2 — Automation baseline (cuối T10) | Toàn bộ scenario P0 đã tự động hóa và chạy trên CI; báo cáo có commit/log/trace; test concurrency kiểm tra INV-01..INV-08; coverage gap report |
| M3 — Quality Intelligence (cuối T14) | Regression selection có benchmark (recall/precision/time saved); flaky + failure classification có tập nhãn; release gate rule set v1 kiểm thử đủ biên; detection rate trên 18 seeded defects đã đo |
| M4 — AI Agents (cuối T18) | Agent sinh test có requirement_id, schema validation, sandbox, human review; tool agent có allow-list và trace; red-team prompt injection đạt TS-079 |
| M5 — Evaluation & Analytics (cuối T21) | Dataset phiên bản hóa + held-out; so sánh ≥ 4 phương pháp (M0, A1–A3); dashboard QA/AI; mọi KPI có SQL nguồn; case study DA |
| M6 — Public portfolio (cuối T24) | Demo deploy; README, ADR, threat model, benchmark report, limitations; video 3–5 phút; CV theo từng vị trí |

## 3. Kế hoạch Tuần 1 và Tuần 2 (chi tiết)

### Tuần 1 — Xác định bài toán và nghiệp vụ

| Ngày | Việc | Đầu ra | Tiêu chí xong |
|---|---|---|---|
| 1 | Tạo repo `sentinelqa`, đưa bộ tài liệu này vào, đọc toàn bộ PRD | Repo + commit đầu | Tự giải thích được 5 câu hỏi sản phẩm và golden path GP-01 |
| 2 | Nghiên cứu nghiệp vụ: đọc tài liệu công khai về idempotency, webhook signing, refund, đối soát của các PSP; đối chiếu với BR | Ghi chú nguồn + danh sách điều chỉnh BR | Mỗi BR có ghi chú "đúng/đơn giản hóa/khác thực tế" và nguồn |
| 3 | Rà soát và sửa business rules, glossary; chốt tham số cấu hình | business-rules.md v0.2 | Không còn quy tắc mơ hồ; câu hỏi Q-06 đã chốt |
| 4 | Vẽ BPMN AS-IS và TO-BE cho nghiệp vụ A (timeout & đối soát) bằng Camunda Modeler/draw.io | `04_bpmn_as_is.bpmn`, `05_bpmn_to_be.bpmn` | Có lane, gateway, exception flow; khớp use case UC-03 |
| 5 | Rà soát use cases và user stories, viết thêm exception flow còn thiếu (mục 5 trong payment-lifecycle) | Use cases v0.2 | Mỗi use case có luồng chính, thay thế, ngoại lệ |
| 6 | Rà soát test scenarios: thêm dữ liệu cụ thể cho từng scenario P0 (input/expected cụ thể) | test-scenarios v0.2 | 100% P0 có dữ liệu ví dụ |
| 7 | Review chéo cuối tuần; chốt PRD 0.2; ghi các quyết định vào ADR | PRD 0.2, ADR bổ sung | Danh sách câu hỏi mở còn lại ≤ 3 |

### Tuần 2 — Thiết kế domain, dữ liệu và API

| Ngày | Việc | Đầu ra | Tiêu chí xong |
|---|---|---|---|
| 8 | ERD chi tiết, kiểu dữ liệu, ràng buộc; thiết kế migration 0001–0005 | data-model v0.2 + file migration nháp | Mọi bất biến INV-01..08 có cơ chế DB hoặc khóa tương ứng |
| 9 | Hoàn thiện OpenAPI: ví dụ request/response, mã lỗi cho từng endpoint | openapi.yaml v0.2 | Validate bằng công cụ OpenAPI không lỗi; khớp error catalog |
| 10 | Thiết kế Provider Simulator: kịch bản, định dạng webhook, settlement CSV, status query, cờ BUG-xxx | docs/domain/provider-simulator.md | Mỗi scenario có đặc tả đầu vào/đầu ra |
| 11 | Viết UAT plan và KPI definitions cho nhánh DA (SQL mẫu cho K-01..K-06 trên schema nháp) | `10_uat_plan.md`, `analytics/sql/*.sql` nháp | Mỗi KPI có SQL và dữ liệu mẫu |
| 12 | Thực hành change request: CR-001 (đổi hạn mức) và phân tích tác động bằng traceability | `12_change_request.md` | Danh sách tài liệu/test bị ảnh hưởng đầy đủ |
| 13 | Dựng khung repo: cấu trúc thư mục, Docker Compose rỗng (Postgres + API hello), CI lint, pre-commit | Skeleton chạy được | `docker compose up` và `/health` trả OK; CI xanh |
| 14 | Review M0, cập nhật traceability, chốt backlog Phase 1 | PRD 1.0, backlog | Đạt tiêu chí M0 |

## 4. Backlog Phase 1 (thứ tự đề xuất)

| # | Hạng mục | Requirement | Ghi chú |
|---|---|---|---|
| 1 | Khung ứng dụng, cấu hình, logging có correlation_id, error schema | NFR-004 | Nền cho mọi thứ |
| 2 | Migration merchants, payment_methods, payments, audit | FR-PAY-001, 010 | Test migration từ DB trống |
| 3 | Tạo payment + validate + biên amount | FR-PAY-001/002 | TS-001..011 trước, rồi code |
| 4 | Idempotency (bảng + transaction) | FR-PAY-003 | TS-012..017, test concurrency sớm |
| 5 | State machine (thư viện domain thuần, test tham số hóa) | FR-PAY-005 | TS-024 |
| 6 | Provider Simulator v1 (success, decline, timeout_*) | FR-SIM-001 | Cần trước confirm |
| 7 | Confirm + attempts + khóa dòng | FR-PAY-004 | TS-018..022, 031 |
| 8 | Timeout → UNKNOWN + Status Worker | FR-PAY-006 | TS-026..029 |
| 9 | Chặn trùng đơn hàng | FR-PAY-011 | Partial unique index, TS-032 |
| 10 | Refund + reservation | FR-REF-001..004 | TS-034..041, 040 là bài kiểm tra chính |
| 11 | Webhook (ký, dedupe, lưu thô) | FR-WH-001/002/004 | TS-045..053 |
| 12 | Webhook out-of-order, STATE_CONFLICT | FR-WH-003 | TS-030, 049 |
| 13 | Settlement import + đối soát | FR-REC-001..003, 005 | TS-054..063 |
| 14 | Vòng đời mismatch, UI cơ bản | FR-REC-004, FR-UI-001/002 | |
| 15 | Seed, fault injection, cờ BUG-xxx | FR-SIM-002 | Cờ lỗi tắt mặc định |
| 16 | Ví và kiểm soát số dư; maker-checker; velocity (Could) | FR-PAY-012, FR-REF-006, FR-SIM-003 | Làm cuối phase nếu còn thời gian |

## 5. Quy trình làm việc cho mỗi tính năng

```
Requirement → Design → Test (viết scenario/test trước) → Implement (nhỏ nhất chạy được)
→ Review (edge case, log, lỗi) → Document (README/ADR) → Benchmark (nếu có mục tiêu định lượng) → Merge (CI xanh)
```

### Definition of Done
Một hạng mục chỉ xong khi:
1. Acceptance criteria của story được đáp ứng và có bằng chứng (test, log, ảnh chụp).
2. Có test phù hợp, kết quả được ghi nhận; scenario liên quan chuyển từ PLANNED sang AUTOMATED/PASSED trong traceability.
3. Lỗi quan trọng đã biết được xử lý hoặc ghi rõ trong `docs/limitations.md`.
4. Có log và thông báo lỗi phù hợp; không lộ secret.
5. Tài liệu liên quan được cập nhật (PRD/rules/OpenAPI/ADR).
6. CI pass; lint, type check đạt.
7. Có thể demo lại từ môi trường sạch theo hướng dẫn.
- Bổ sung cho AI: model/prompt version, schema validation, trace, giới hạn chi phí/thời gian, evaluation phù hợp.
- Bổ sung cho benchmark: dataset version, môi trường đo, baseline, công thức metric, số lần lặp.

### Quy ước kỹ thuật
- Nhánh: `main` luôn xanh; nhánh tính năng `feat/<fr-id>-<mô-tả>`; PR nhỏ, một mục đích.
- Commit theo Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`), tham chiếu ID (ví dụ `feat(payment): FR-PAY-006 UNKNOWN on timeout`).
- Code, API, commit bằng tiếng Anh; tài liệu phân tích chi tiết có thể bằng tiếng Việt (Q-01).
- Khi dùng AI hỗ trợ code: thay đổi nhỏ, yêu cầu viết test, tự giải thích được từng đoạn trước khi merge.

## 6. Ánh xạ bằng chứng theo vị trí ứng tuyển

| Vị trí | Hồ sơ nên đặt lên đầu | Câu chuyện phỏng vấn mạnh |
|---|---|---|
| **IT BA / Payment BA** | Business case, stakeholder, BPMN AS-IS/TO-BE, use cases, user stories, business rules, traceability, UAT, change request | "Từ một yêu cầu mơ hồ về hoàn tiền, tôi làm rõ 8 câu hỏi nghiệp vụ, ra business rules, acceptance criteria và test truy vết được" |
| **Data Analyst / BI** | `analytics/` (SQL, notebook, dashboard, insights), KPI definitions, data quality checks | "Timeout recovery rate là bao nhiêu, mẫu số thế nào, kiểm tra cỡ mẫu ra sao, khuyến nghị gì" |
| **QA Automation / SDET** | Test scenarios, framework pytest/Playwright, CI, concurrency tests, mutation, seeded defect detection | "Test pass nhưng mutation score thấp: tôi phát hiện mutant sống nào và bổ sung test gì" |
| **AI Engineer (LLM/agent)** | Agent, trace, evaluation dataset, benchmark so sánh, safety (prompt injection, allow-list) | "Agent cải thiện detection rate ở đâu và làm tệ hơn ở đâu; chi phí mỗi test được duyệt" |
| **Backend Intern** | API, state machine, idempotency, khóa dòng, migration, OpenAPI, ADR | "Hai refund song song không vượt tổng: cơ chế khóa và bằng chứng test" |

Không gửi cùng một CV và README cho mọi vị trí. Dùng chung codebase nhưng mỗi hồ sơ có trang giới thiệu, bằng chứng và câu chuyện riêng. Không tự nhận là chuyên gia mọi lĩnh vực: trình bày chính xác rằng đây là hệ thống mô phỏng tự xây và kiểm thử, kèm nghiên cứu nghiệp vụ.

## 7. Rủi ro tiến độ và cách xử lý

| Dấu hiệu | Hành động |
|---|---|
| Một milestone trễ > 30% thời gian dự kiến | Cắt phạm vi theo trục ưu tiên (mục 1); không mở phase mới |
| Không giải thích được đoạn code đã merge | Quay lại, viết ADR/ghi chú, thêm test; không merge thêm |
| Benchmark cho kết quả xấu | Công bố, phân tích nguyên nhân; không chỉnh held-out để "đẹp" |
| Chi phí LLM tăng | Giảm dataset phát triển, cache, giới hạn bước/chi phí mỗi run |
| Máy chậm/thiếu RAM | Chạy DB + API, bật worker khi cần; AI qua API ngoài; không chạy nhiều container nặng cùng lúc |

## 8. Checklist theo dõi (đánh dấu khi có bằng chứng, không chỉ khi đã viết code)

**Phase 0**
- [ ] PRD 1.0 được review
- [ ] Glossary và business rules đối chiếu nguồn
- [ ] BPMN AS-IS / TO-BE (.bpmn)
- [ ] Use cases + user stories + traceability (không cảnh báo)
- [ ] ERD + OpenAPI validate
- [ ] Provider Simulator spec
- [ ] UAT plan, change request mẫu
- [ ] Skeleton repo + CI xanh

**Phase 1** — [ ] Payment API + state machine · [ ] Idempotency · [ ] Timeout/UNKNOWN · [ ] Refund + reservation · [ ] Webhook · [ ] Reconciliation · [ ] Simulator + cờ lỗi · [ ] UI cơ bản
**Phase 2** — [ ] pytest/Playwright · [ ] Traceability trong ứng dụng · [ ] Concurrency/performance · [ ] Mutation khởi đầu
**Phase 3** — [ ] Git diff selection + benchmark · [ ] Flaky/failure · [ ] Release gate
**Phase 4** — [ ] LLM adapter · [ ] Requirements-to-Tests Agent · [ ] Tool agent + trace · [ ] Review workflow
**Phase 5** — [ ] Dataset + held-out · [ ] Benchmark ≥ 4 phương pháp · [ ] Dashboard · [ ] SQL KPI + case study DA
**Phase 6** — [ ] Security + threat model · [ ] Docker + CI/CD · [ ] Deploy demo · [ ] README/ADR/benchmark/video
