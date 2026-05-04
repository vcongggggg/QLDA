# AGENTS.md - Luật vận hành AI Agent cho TeamsWork

## Project Identity

TeamsWork là ứng dụng quản lý công việc, dự án, sprint và KPI nội bộ. Hệ thống có API FastAPI, giao diện web tĩnh, báo cáo CSV/XLSX/PDF, tích hợp Microsoft Teams và module AI phân rã yêu cầu thành task để manager duyệt trước khi import.

Mục tiêu của AI Agent trong repo này là hỗ trợ phát triển có kiểm soát: đọc kỹ codebase, giữ đúng nghiệp vụ TeamsWork, ưu tiên test và tài liệu, không tự mở rộng phạm vi.

## Stack hiện tại

- Python 3.12+, FastAPI, Pydantic.
- SQLite cho local/dev, PostgreSQL cho docker/production-like.
- Pytest cho kiểm thử.
- Microsoft Teams integration: Teams tab, AAD sync, bot callback, proactive notification queue.
- AI task breakdown qua OpenAI-compatible provider hoặc heuristic fallback.

## Core Principles

- Bám sát sản phẩm TeamsWork: task, KPI, RBAC, report, Teams, AI task generation.
- Đọc trước khi sửa: router, schema, repository, test và tài liệu liên quan.
- Thay đổi nhỏ, có mục tiêu rõ, không refactor lan rộng nếu không cần.
- Không thêm dependency nếu chưa có yêu cầu rõ và chưa giải thích trade-off.
- Không để AI tự quyết định nghiệp vụ KPI, quyền truy cập hoặc dữ liệu sản phẩm.
- Với thay đổi liên quan auth, KPI, AI import, report hoặc Teams, luôn cập nhật test/checklist tương ứng.

## Agent Roles Rút Gọn

- `planner`: làm rõ yêu cầu, phạm vi, non-goal, rủi ro và test plan.
- `architect`: dùng khi đổi kiến trúc auth, database, AI provider, Teams hoặc report.
- `backend`: triển khai FastAPI/router/schema/repository theo pattern hiện có.
- `database`: kiểm tra schema, query, transaction, SQLite/PostgreSQL compatibility.
- `QA`: viết/chạy pytest, kiểm tra regression cho flow chính.
- `security`: kiểm tra RBAC, JWT/header fallback, secret, upload, Teams token, error leakage.
- `doc`: cập nhật README, runbook, spec và checklist khi behavior thay đổi.

## Trước Khi Sửa Code

- Xác định yêu cầu thuộc nhóm: docs, backend, database, AI, Teams, security hay test.
- Đọc file liên quan trước: `app/main.py`, router liên quan, `app/schemas.py`, `app/repository.py`, test tương ứng.
- Kiểm tra worktree để không ghi đè thay đổi của người khác.
- Với feature lớn, đưa plan ngắn gồm file dự kiến sửa, rủi ro, test cần chạy.
- Nếu nhiệm vụ chỉ yêu cầu tài liệu, chỉ sửa tài liệu.

## Quy Tắc KPI

- Công thức KPI hiện tại nằm ở `app/kpi.py`, không tự đổi trong code hoặc tài liệu nghiệp vụ nếu chưa có human approval.
- Difficulty multiplier hiện tại: `easy = 1.0`, `medium = 1.5`, `hard = 2.0`.
- Task đúng hạn: `+10 * multiplier`.
- Task hoàn thành trễ: `+5 * multiplier`.
- Task chưa xong và deadline thuộc tháng KPI: `-5 * multiplier`.
- Manual adjustment cộng/trừ trực tiếp vào điểm cuối, phải có `reason` và audit log.
- AI không được tự bịa điểm KPI, công thức KPI, adjustment hoặc lý do đánh giá.

## Quality Gate Tối Thiểu

Chạy tối thiểu trước khi merge/demo/nộp bài:

```powershell
pytest -q
```

Khi đụng vùng rủi ro, chạy thêm:

```powershell
pytest tests/test_api_flow.py tests/test_ai_task_breakdown.py tests/test_kpi.py
```

Checklist tối thiểu:

- Auth/RBAC đúng vai trò `admin`, `manager`, `staff`, `hr`.
- KPI đúng công thức và edge case trong `docs/KPI_VALIDATION_RULES.md`.
- AI task generation có validation, fallback và human approval.
- Teams queue/reminder không nuốt lỗi âm thầm.
- Report export trả đúng content type và quyền truy cập.
- Không commit `.env`, token, API key hoặc secret thật.

## Security Rules

- Production auth phải ưu tiên JWT bearer; header fallback chỉ dành cho local/dev.
- Endpoint đặc quyền phải gọi `require_roles`.
- Staff chỉ được xem/cập nhật dữ liệu của mình nếu nghiệp vụ yêu cầu.
- Upload `.docx` phải kiểm tra extension, kích thước và nội dung tối thiểu.
- Không log secret, token, Authorization header hoặc dữ liệu nhạy cảm.
- Teams AAD token và webhook phải được xem là trust boundary.
- Không expose stack trace hoặc lỗi provider AI trực tiếp cho người dùng cuối.

## Git Workflow

- Không dùng `git reset --hard` hoặc checkout để xóa thay đổi nếu chưa được yêu cầu rõ.
- Không revert thay đổi không do mình tạo.
- Commit nên nhỏ, theo một mục tiêu, message nêu rõ phạm vi.
- Trước khi PR/merge: xem diff, chạy quality gate, cập nhật docs nếu behavior đổi.
- Với thay đổi lớn: ghi rõ test đã chạy và rủi ro còn lại trong mô tả PR/báo cáo.
