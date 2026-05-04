# Quality Gate cho TeamsWork

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

- Không commit `.env`, token, API key, secret thật.
- Không expose stack trace hoặc lỗi provider AI thô cho người dùng cuối.
- Không dùng input người dùng để tạo SQL string thủ công.
- Upload file có kiểm tra extension, size và nội dung.
- Audit log được ghi cho hành động quan trọng: seed, KPI adjustment, AI preview/import, Teams queue/process.
- Cấu hình production phải tắt dev-only fallback nếu có JWT.

## 8. Done Criteria

Một thay đổi được coi là xong khi:

- Đúng yêu cầu và không mở rộng scope ngoài ý muốn.
- Test liên quan chạy xanh.
- Checklist vùng rủi ro đã được kiểm tra.
- Không có secret hoặc dữ liệu nhạy cảm trong diff.
- Tài liệu được cập nhật nếu behavior, endpoint, KPI hoặc workflow đổi.
- Người review có thể giải thích thay đổi bằng file, test và rủi ro còn lại.
