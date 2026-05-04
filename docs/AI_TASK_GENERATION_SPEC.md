# AI Task Generation Spec cho TeamsWork

Tài liệu này đặc tả tính năng AI tạo task/phân rã task cho TeamsWork. AI chỉ đề xuất task; task thật chỉ được tạo sau khi người có quyền duyệt và import.

## 1. Mục Tiêu

- Nhận yêu cầu dạng text hoặc file `.docx`.
- Phân rã thành danh sách task có cấu trúc.
- Cho manager/admin xem, chỉnh/chọn task trước khi import vào Kanban.
- Có fallback khi AI provider lỗi để demo không bị dừng.
- Không để AI tự bịa dữ liệu KPI, assignee hoặc adjustment.

## 2. Input

Endpoint hiện có:

- `POST /ai/task-breakdown`: nhận text.
- `POST /ai/task-breakdown/docx`: nhận file `.docx`.
- `POST /ai/task-breakdown/import`: import các task đã chọn.

Input preview text:

```json
{
  "text": "Yêu cầu nghiệp vụ hoặc mô tả tính năng",
  "project_context": "Bối cảnh dự án, tùy chọn",
  "max_tasks": 8
}
```

Input import:

```json
{
  "assignee_id": 2,
  "project_id": null,
  "sprint_id": null,
  "base_deadline": "2026-05-04T00:00:00Z",
  "items": []
}
```

## 3. Output JSON Đề Xuất

Response preview nên giữ shape ổn định:

```json
{
  "source": "openai_compatible",
  "items": [
    {
      "title": "Tạo dashboard KPI",
      "description": "Hiển thị KPI theo tháng cho manager",
      "story_points": 5,
      "difficulty": "medium",
      "deadline_offset_days": 7,
      "rationale": "Cần để manager theo dõi hiệu suất",
      "selected": true
    }
  ],
  "warnings": []
}
```

Giá trị `source` hợp lệ hiện tại:

- `openai_compatible`: dùng AI provider thành công.
- `heuristic`: dùng fallback local.

## 4. Validation Rules

Request:

- `text`: 10 đến 50000 ký tự.
- `project_context`: tối đa 2000 ký tự.
- `max_tasks`: 1 đến 30.
- `.docx`: chỉ nhận extension `.docx`, kích thước tối đa 2MB, nội dung extract được ít nhất 10 ký tự.

Item:

- `title`: 2 đến 200 ký tự.
- `description`: tối đa 1200 ký tự.
- `story_points`: 1 đến 13.
- `difficulty`: chỉ `easy`, `medium`, `hard`.
- `deadline_offset_days`: 1 đến 90.
- `rationale`: tối đa 500 ký tự.
- `selected`: boolean.

Import:

- Chỉ `admin`, `manager` được preview/import.
- `assignee_id` phải tồn tại.
- `project_id` và `sprint_id` nếu có thì phải tồn tại.
- Phải có ít nhất một item `selected = true`.
- Deadline thật = `base_deadline + deadline_offset_days`, lưu theo UTC.
- Task import vào trạng thái ban đầu theo logic `create_task`.

## 5. Fallback Khi AI Lỗi

Luồng fallback hiện tại:

1. Nếu cấu hình `AI_PROVIDER=openai_compatible` và có `AI_API_KEY`, gọi model chính.
2. Nếu model chính lỗi và có `AI_FALLBACK_MODEL`, thử model fallback.
3. Nếu provider/fallback vẫn lỗi hoặc không có API key, dùng heuristic local.
4. Response phải kèm `warnings` để người dùng biết nguồn và lỗi tổng quát.

Fallback không được làm mất quyền kiểm soát của người dùng: preview vẫn chỉ là đề xuất, không tự tạo task.

## 6. Human Approval Flow

Luồng chuẩn:

1. Manager/admin nhập text hoặc upload `.docx`.
2. Hệ thống trả danh sách task đề xuất.
3. Manager/admin xem `rationale`, bỏ chọn task không phù hợp.
4. Manager/admin chọn assignee, project, sprint và base deadline nếu cần.
5. Manager/admin import.
6. Hệ thống tạo task thật và ghi audit log.

Staff không được gọi preview/import AI task.

## 7. Audit Log

Các hành động phải ghi audit log:

- Preview từ text: action `preview`, entity `ai_task_breakdown`.
- Preview từ docx: action `preview`, entity `ai_task_breakdown_docx`.
- Import task: action `create`, entity `task`, detail `created from AI task breakdown`.

Audit log cần đủ để trả lời:

- Ai đã chạy AI preview/import?
- Nguồn task là AI hay heuristic?
- Bao nhiêu item được đề xuất?
- Task nào được tạo thật?

## 8. Test Cases

Tối thiểu phải có:

- Local heuristic extract được task từ text tiếng Việt.
- Provider chính lỗi thì gọi fallback model.
- Không có API key thì dùng heuristic.
- Preview không làm tăng số lượng task.
- Import tạo đúng số task được chọn.
- Staff bị chặn preview/import.
- `.docx` hợp lệ được xử lý.
- File sai extension bị reject.
- `.docx` quá ngắn bị reject.
- Import không có item selected bị reject.
- Difficulty sai bị reject hoặc normalize ở tầng phù hợp.
- `deadline_offset_days` ngoài `1..90` bị reject.

## 9. Không Để AI Tự Bịa Dữ Liệu KPI

AI task generation không được:

- Tự tạo điểm KPI.
- Tự tạo manual adjustment.
- Tự gán KPI tier/xếp loại nếu không dựa trên `app/kpi.py`.
- Tự bịa assignee hoặc user không tồn tại.
- Tự đổi difficulty để thao túng điểm KPI.
- Tự tạo deadline tuyệt đối không qua `base_deadline + deadline_offset_days`.

Nếu sau này thêm KPI explanation, nội dung giải thích phải dựa trên dữ liệu thật từ task, deadline, completed_at và adjustment đã lưu trong database.
