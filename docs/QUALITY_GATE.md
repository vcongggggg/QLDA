# Quality Gate cho TeamsWork

Codex baseline:

- UI changes must follow `DESIGN.md`.
- Code, RBAC, KPI, AI import, Teams, and security changes must follow `AGENTS.md`.
- `pytest -q` must be scoped by `pytest.ini` to the TeamsWork `tests/` directory so vendored/local folders such as `everything-claude-code/` are not collected.
- New backend code should be added to the domain module under `app/repositories/`, `app/schemas/`, `app/routers/task_routes/`, `app/db/`, or `app/seeding/`; compatibility facades should stay thin.
- Static UI changes should go into `app/static/js/` and `app/static/css/`; keep `app/static/app.js` and `app/static/styles.css` as bootstrap/facade files.

Checklist này dùng trước khi merge, demo hoặc nộp bài. Mục tiêu là bắt lỗi ở các vùng rủi ro: KPI, RBAC/auth, AI task generation, Teams integration, report export và security.

## 1. Test Commands

Chạy toàn bộ test:

```powershell
pytest -q
```

Chạy nhóm test quan trọng:

```powershell
pytest tests/test_api_flow.py tests/test_ai_task_breakdown.py tests/test_kpi.py
```

Khi chỉ sửa KPI:

```powershell
pytest tests/test_kpi.py tests/test_api_flow.py
```

Khi chỉ sửa AI task breakdown:

```powershell
pytest tests/test_ai_task_breakdown.py
```

Final demo evidence commands:

```powershell
python scripts/seed_full_demo.py --reset-demo
python -m compileall app scripts
pytest tests/test_maintenance_hardening.py tests/test_ops_dashboard.py tests/test_auth_security_hardening.py tests/test_notifications.py -q
pytest tests/test_phase6_admin_compliance_maintenance.py tests/test_ops_dashboard.py tests/test_maintenance_hardening.py tests/test_auth_security_hardening.py tests/test_notifications.py -q
python scripts/benchmark_smoke.py --json
curl http://127.0.0.1:8000/monitoring/release-acceptance
python scripts/smoke_check.py --base-url http://127.0.0.1:8000 --user-id 1 --expect-production-auth
python scripts/capture_demo_evidence.py --base-url http://127.0.0.1:8000
```

`smoke_check.py` and `capture_demo_evidence.py` require a running local server. Use `uvicorn app.main:app --reload` in another terminal.

## 2. KPI Validation Checklist

- Công thức đúng theo `docs/KPI_VALIDATION_RULES.md`.
- Task ngoài tháng KPI không bị tính vào tháng đó.
- `easy`, `medium`, `hard` dùng đúng multiplier.
- Có case đúng hạn, trễ hạn, quá hạn chưa xong.
- Manual adjustment cộng/trừ đúng điểm và có reason.
- Báo cáo KPI và dashboard dùng cùng logic với `app/kpi.py`.

## 3. RBAC/Auth Checklist

- Endpoint đặc quyền dùng `require_roles`.
- `admin` có quyền quản trị user, seed, audit, monitoring nhạy cảm.
- `manager` có quyền quản lý project/sprint/task/KPI/AI import theo nghiệp vụ.
- `hr` có quyền xem user, KPI và report liên quan.
- `staff` chỉ xem/cập nhật dữ liệu của mình ở các luồng được phép.
- Production auth không bật header fallback nếu chưa có lý do rõ.
- JWT secret không để trong code hoặc tài liệu thật.

## 4. AI Task Generation Checklist

Phase 1A auth/security checks:

- If `AUTH_ALLOWED_EMAIL_DOMAINS` is configured, password login and Teams/AAD sync must reject emails outside the whitelist.
- Failed login attempts must be recorded in `auth_login_attempts` with safe reason codes only; do not store passwords, bearer tokens, provider raw errors, or raw IP addresses.
- Five failed login attempts for the same email/IP window must block further login for the configured duration.

- `POST /ai/task-breakdown` chỉ cho `admin`, `manager`.
- `POST /ai/task-breakdown/docx` chỉ nhận `.docx`, giới hạn kích thước và reject nội dung quá ngắn.
- Output item có `title`, `story_points`, `difficulty`, `deadline_offset_days`.
- `difficulty` chỉ là `easy`, `medium`, `hard`.
- `deadline_offset_days` trong khoảng `1..90`.
- Provider lỗi thì dùng fallback model hoặc heuristic.
- Preview không tạo task thật.
- Import chỉ tạo các item `selected = true`.
- Import ghi audit log cho task được tạo.

## 5. Teams Integration Checklist

- Teams tab `/teams/tab` và `/teams/tab/prod` render được.
- AAD endpoints xử lý token như trust boundary.
- Reminder runner chỉ cho `admin`, `manager`.
- Proactive queue/list/process/requeue chỉ cho role hợp lệ.
- Queue có trạng thái `queued`, `sent`, `failed` và retry/requeue rõ ràng.
- Bot commands và Adaptive Card actions phải map `aadObjectId` sang TeamsWork user trước khi đọc/ghi dữ liệu.
- Graph/channel posting phải tắt mặc định; test chỉ dùng mock và không cần tenant credentials.
- Teams notification payload có `dedup_key` không được tạo bản ghi trùng trong queue.
- Không log webhook URL, bearer token hoặc Teams token.

## 6. Report Export Checklist

- KPI report: `/reports/kpi.csv`, `/reports/kpi.xlsx`, `/reports/kpi.pdf`.
- Project progress report: CSV/XLSX.
- Sprint review report: CSV/XLSX.
- Portfolio summary report: CSV/XLSX.
- Role `staff` không tải được báo cáo tổng hợp nếu endpoint yêu cầu privileged role.
- Content type và filename đúng định dạng.
- Dữ liệu report khớp repository/KPI logic, không hard-code số demo.

## 7. Security Checklist

Phase 1A export/header checks:

- Audit export `/audit/logs.csv` and `/audit/logs.xlsx` must require `AUDIT_VIEW` and honor the same filters as `/audit/logs`.
- API/static responses should include security headers: `X-Content-Type-Options`, CSP, `Referrer-Policy`, and `X-Frame-Options` where Teams framing does not require an exception.
- Production CSP must not include `unsafe-eval`; local/test may allow it so Playwright string predicates keep working.
- HSTS should only be enabled when `APP_ENV=production` and `SECURITY_HSTS_ENABLED=true`.

- Không commit `.env`, token, API key, secret thật.
- Không expose stack trace hoặc lỗi provider AI thô cho người dùng cuối.
- Không dùng input người dùng để tạo SQL string thủ công.
- Upload file có kiểm tra extension, size và nội dung.
- Audit log được ghi cho hành động quan trọng: seed, KPI adjustment, AI preview/import, Teams queue/process.
- Cấu hình production phải tắt dev-only fallback nếu có JWT.

Phase 6 ops release-gate checks:

- `/monitoring/release-gate` must require privileged ops/audit/admin permission.
- Staff/member users must not see release-gate details.
- Release-gate output must summarize health, readiness, metrics, notification queue counts, audit log availability, and production auth safety.
- Release-gate output must also include maintenance, compliance backlog, retention, synthetic journey, and QA evidence summaries.
- Release-gate output must not include raw webhook URLs, bearer tokens, client secrets, stack traces, provider raw errors, or notification payload bodies.
- Failed Teams notification details must use redacted summaries only.
- `/monitoring/release-acceptance` must require privileged ops/audit/admin permission.
- Release acceptance output must list the 141 completed Must/Should stories from the Phase 1-6 local/release scope, mark them `Done`, and include approved deferrals for external tenant/load/WCAG/UAT evidence where applicable.
- Staff/member users must not see release-acceptance evidence.

Phase 6 admin/compliance/maintenance checks:

- Admin global search, activity, config flags, license status, department ops evidence, admin release panel, system notification broadcast/evidence, QA release evidence, and test-data inventory must be privileged.
- Config flags must redact environment values whose names indicate secrets, tokens, keys, passwords, webhooks, or authorization material.
- GDPR/PDPA delete handling uses request/export/manual-review only; no hard delete is automated in Phase 6.
- Compliance exports must not include password hashes or raw secret material.
- Maintenance log cleanup must support dry-run evidence; destructive cleanup stays deferred unless explicitly approved and audited.
- Phase 6 local endpoints covered by focused tests: `/admin/system-config/overview`, `/admin/license/status`, `/admin/departments/ops-evidence`, `/admin/system-notifications/evidence`, `/admin/release-panel`, `/compliance/evidence`, `/qa/release-evidence`, and `/qa/test-data`.
- Run `python scripts/benchmark_smoke.py --json` for local Phase 6 synthetic journey evidence.

Approved Phase 6 deferrals:

- Live Grafana/Azure Monitor integration and real tenant observability are documented integration points only.
- Hard delete/anonymization automation is deferred behind manual compliance review.
- Broad load/performance testing beyond local benchmark smoke is deferred to production-like test infrastructure.
- Real Azure AD, Teams Graph posting, external WCAG certification, and stakeholder UAT signatures are approved rollout evidence gates when local implementation, mocked integration, RBAC, and docs are complete.

## 8. Done Criteria

Final demo docs must stay current when demo behavior or evidence changes:

- `docs/TEST_EVIDENCE.md`
- `docs/TRACEABILITY_MATRIX.md`
- `docs/FINAL_DEMO_SCRIPT.md`
- `docs/FINAL_DEMO_SLIDES.md`

Một thay đổi được coi là xong khi:

- Đúng yêu cầu và không mở rộng scope ngoài ý muốn.
- Test liên quan chạy xanh.
- Checklist vùng rủi ro đã được kiểm tra.
- Không có secret hoặc dữ liệu nhạy cảm trong diff.
- Tài liệu được cập nhật nếu behavior, endpoint, KPI hoặc workflow đổi.
- Người review có thể giải thích thay đổi bằng file, test và rủi ro còn lại.
