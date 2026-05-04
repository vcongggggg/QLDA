# AI Agent Operating Model cho TeamsWork

Tài liệu này mô tả cách TeamsWork áp dụng AI Agent ở mức vận hành dự án. Mục tiêu là học tư duy từ `everything-claude-code` nhưng rút gọn để phù hợp với đồ án TeamsWork, không biến repo thành một agent framework phức tạp.

## 1. Human Control Layer

Con người giữ quyền quyết định cuối cùng về phạm vi, nghiệp vụ, bảo mật và công thức KPI.

Áp dụng trong TeamsWork:

- Người dùng hoặc nhóm dự án mô tả yêu cầu, giới hạn scope và tiêu chí nghiệm thu.
- AI được phép đề xuất plan, test, checklist và code change khi được giao.
- AI không tự thêm dependency, đổi công thức KPI, đổi RBAC hoặc thay đổi production auth nếu chưa có yêu cầu rõ.
- Với tính năng lớn như AI task import, KPI explanation, Teams sync hoặc report mới, cần có plan và quality gate trước khi merge/demo.

## 2. Planning Agent Layer

Lớp planning biến yêu cầu mơ hồ thành kế hoạch có thể triển khai.

Vai trò rút gọn:

- `planner`: xác định mục tiêu, non-goal, file liên quan, test cần chạy.
- `architect`: dùng khi đổi luồng dữ liệu, database, auth, AI provider hoặc Teams.
- `product-capability`: mô tả tính năng theo input, output, quyền truy cập, validation và tiêu chí xong.

Output mong muốn:

- Plan ngắn, không quá dài.
- Rủi ro chính: KPI sai, RBAC hở, AI hallucination, Teams retry lỗi, report sai dữ liệu.
- Test plan bám `pytest` và các test hiện có.

## 3. Development Agent Layer

Lớp development triển khai theo stack hiện tại của TeamsWork.

Nguyên tắc:

- Backend dùng FastAPI router, Pydantic schema, repository function và pytest theo pattern hiện có.
- Database phải chạy được với SQLite local và PostgreSQL production-like.
- AI task breakdown chỉ tạo đề xuất, không tự tạo task nếu chưa qua endpoint import và người dùng chọn.
- Frontend web tĩnh chỉ được sửa khi nhiệm vụ yêu cầu UI.

Luồng làm việc chuẩn:

1. Đọc router/schema/repository/test liên quan.
2. Xác định behavior hiện tại trước khi sửa.
3. Sửa nhỏ, tránh refactor ngoài phạm vi.
4. Chạy test liên quan.
5. Cập nhật tài liệu nếu behavior đổi.

## 4. QA/Security Agent Layer

Đây là lớp kiểm soát chất lượng quan trọng nhất cho TeamsWork.

Checklist lõi:

- `pytest -q` chạy xanh.
- Auth/RBAC đúng vai trò `admin`, `manager`, `staff`, `hr`.
- KPI đúng công thức hiện tại và không bị AI tự diễn giải sai.
- AI task generation có output shape ổn định, fallback khi provider lỗi và validation trước import.
- Teams proactive queue có retry/requeue, không báo thành công giả.
- Report CSV/XLSX/PDF đúng content type và chỉ role hợp lệ được tải.
- Không có secret trong repo.

## 5. Product Intelligence Layer

Lớp này dùng AI để tăng năng lực sản phẩm, không chỉ để viết code.

Trong TeamsWork, AI nên hỗ trợ:

- Phân rã yêu cầu thành task có `title`, `description`, `story_points`, `difficulty`, `deadline_offset_days`, `rationale`.
- Gợi ý task cần import nhưng để manager/admin chọn.
- Giải thích KPI dựa trên dữ liệu thật: task đúng hạn, trễ hạn, quá hạn, adjustment.
- Gợi ý rủi ro vận hành: task quá hạn, sprint chậm, nhân sự quá tải, Teams notification thất bại.

Giới hạn:

- AI không được tự bịa assignee, deadline tuyệt đối, điểm KPI hoặc adjustment.
- AI không được thay thế quyết định của manager/admin.
- Mọi dữ liệu AI đề xuất phải qua validation và audit log khi import/tạo bản ghi thật.

## 6. Human-in-the-loop

TeamsWork áp dụng human-in-the-loop ở các điểm sau:

- Duyệt plan trước feature lớn.
- Manager/admin duyệt danh sách task AI trước khi import.
- Người có quyền tạo manual KPI adjustment và phải nhập lý do.
- Người phát triển chạy quality gate trước khi merge/demo/nộp bài.
- Nhóm dự án quyết định khi thay đổi công thức KPI, RBAC hoặc cấu hình production auth.

## 7. Học từ everything-claude-code, nhưng rút gọn

Những phần giữ lại:

- Có `AGENTS.md` làm luật vận hành chính.
- Có vai trò agent rõ ràng: planning, development, QA/security, doc.
- Có quality gate trước khi coi thay đổi là xong.
- Có checklist security và test cho vùng rủi ro.
- Có spec riêng cho KPI và AI task generation.

Những phần không bê nguyên:

- Không cài hệ thống hook tự động phức tạp.
- Không dùng autonomous loop hoặc multi-model orchestration nặng.
- Không tạo hàng chục agent theo domain không liên quan.
- Không áp coverage cứng cho toàn repo ngay lập tức.
- Không biến TeamsWork thành agent harness; TeamsWork vẫn là sản phẩm quản lý công việc/KPI.
