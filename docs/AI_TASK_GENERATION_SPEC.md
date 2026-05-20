# AI Task Generation Spec cho TeamsWork

AI task generation chi tao task de xuat. Task that trong Kanban chi duoc tao sau khi manager/admin review va import AI draft.

## 1. Muc Tieu

- Nhan yeu cau dang text hoac file `.docx`.
- Phan ra thanh danh sach task co cau truc.
- Luu ket qua thanh AI draft voi lifecycle `draft -> reviewed -> imported`.
- Cho manager/admin xem, chinh/chon task truoc khi import vao Kanban.
- Co fallback khi AI provider loi de demo khong bi dung luong.
- Khong de AI tu bia KPI, assignee, adjustment hoac deadline tuyet doi.

## 2. API Va Input

Endpoint:

- `POST /ai/task-breakdown`: nhan text, tao AI draft `draft`.
- `POST /ai/task-breakdown/docx`: nhan file `.docx`, tao AI draft `draft`.
- `GET /ai/task-breakdown/drafts`: xem danh sach AI draft.
- `GET /ai/task-breakdown/drafts/{draft_id}`: xem chi tiet AI draft.
- `PATCH /ai/task-breakdown/drafts/{draft_id}/review`: chinh task de xuat, luu note/reason, chuyen sang `reviewed`.
- `POST /ai/task-breakdown/import`: import draft thanh task that va chuyen sang `imported`.

Input preview text:

```json
{
  "text": "Yeu cau nghiep vu hoac mo ta tinh nang",
  "project_context": "Boi canh du an, tuy chon",
  "max_tasks": 8,
  "use_rag": true,
  "rag_query": null
}
```

Input review:

```json
{
  "items": [
    {
      "title": "Tao dashboard KPI",
      "description": "Hien thi KPI theo thang cho manager",
      "story_points": 5,
      "difficulty": "medium",
      "deadline_offset_days": 7,
      "rationale": "Can de manager theo doi hieu suat",
      "selected": true
    }
  ],
  "review_note": "Da duyet cac task phu hop",
  "edit_reason": "Chinh title va bo task trung lap"
}
```

Input import:

```json
{
  "ai_draft_id": 12,
  "assignee_id": 2,
  "project_id": null,
  "sprint_id": null,
  "base_deadline": "2026-05-04T00:00:00Z"
}
```

## 3. Output Va Du Lieu Luu

Response preview giu shape cu va them draft metadata:

```json
{
  "ai_draft_id": 12,
  "status": "draft",
  "source": "openai_compatible",
  "items": [],
  "warnings": [],
  "retrieved_context_count": 0,
  "retrieved_sources": []
}
```

Bang `ai_task_drafts` luu:

- `source_type`: `text` hoac `docx`.
- `source_summary` / `source_name`.
- `generated_tasks`: JSON task de xuat.
- `status`: `draft`, `reviewed`, `imported`.
- `reviewer_id`, `reviewed_at`, `imported_at`.
- `review_note`, `edit_reason`.
- `created_by`, `created_at`.

## 4. Validation Rules

- `text`: 10 den 50000 ky tu.
- `project_context`: toi da 2000 ky tu.
- `max_tasks`: 1 den 30.
- `.docx`: chi nhan extension `.docx`, toi da 2MB, noi dung extract it nhat 10 ky tu.
- Item: `title` 2..200, `description` toi da 1200, `story_points` 1..13, `difficulty` chi `easy|medium|hard`, `deadline_offset_days` 1..90.
- Chi `admin`/`manager` co quyen preview/review/import theo permissions `ai.preview` va `ai.import`.
- Import chi nhan draft status `draft` hoac `reviewed`; draft `imported` bi tu choi de chan import lai.
- Phai co it nhat mot item `selected = true`.
- Deadline that = `base_deadline + deadline_offset_days`, luu theo UTC.

## 5. Human Approval Flow

1. Manager/admin nhap text hoac upload `.docx`.
2. He thong phan ra task de xuat va luu AI draft status `draft`; chua tao task that.
3. Manager/admin mo bang `AI drafts`, xem rationale, chinh/bat/tat selected.
4. Manager/admin luu review note/edit reason; draft chuyen sang `reviewed`.
5. Manager/admin chon assignee, project, sprint va base deadline neu can.
6. Manager/admin import; he thong tao task that, ghi audit log, va chuyen draft sang `imported`.

Staff khong duoc goi preview/review/import AI task neu khong co permission tuong ung.

## 6. Fallback Khi AI Loi

1. Neu `AI_PROVIDER=openai_compatible` va co `AI_API_KEY`, goi model chinh.
2. Neu model chinh loi va co `AI_FALLBACK_MODEL`, thu model fallback.
3. Neu provider/fallback van loi hoac khong co API key, dung heuristic local.
4. Response kem `warnings` tong quat; khong expose secret/token/provider stack trace.

Fallback van chi tao draft de xuat, khong tu tao task that.

## 7. Audit Log

- Preview text: action `preview`, entity `ai_task_breakdown`, entity id la draft id.
- Preview docx: action `preview`, entity `ai_task_breakdown_docx`, entity id la draft id.
- Review draft: action `review`, entity `ai_task_draft`.
- Import draft: action `import`, entity `ai_task_draft`.
- Task duoc tao: action `create`, entity `task`, detail co draft id.

## 8. Test Cases

- Local heuristic extract duoc task.
- Provider chinh loi thi goi fallback model.
- Khong co API key thi dung heuristic.
- Preview text tao draft va khong lam tang task that.
- Preview docx tao draft.
- Manager review draft va `review_note`/`edit_reason` duoc luu.
- Import reviewed draft tao task that.
- Khong import lai draft da `imported`.
- Staff bi chan preview/list/review/import.
- File sai extension va `.docx` qua ngan bi reject.
- Difficulty sai hoac deadline offset ngoai range bi reject o tang schema/validation phu hop.
