from app.seeding.shared import *

def _iso_date(date_value: str, hour: int = 18) -> str:
    return f"{date_value}T{hour:02d}:00:00+00:00"


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _epic_label(epic: str) -> str:
    return EPIC_LABELS.get(epic, epic)


def seed_departments(conn: Any) -> dict[str, int]:
    for name, code in DEPARTMENTS:
        conn.execute(
            "INSERT INTO departments (name, code, created_at) VALUES (?, ?, ?)",
            (name, code, _iso_date("2026-05-20", 9)),
        )
    return {row["code"]: int(row["id"]) for row in conn.execute("SELECT id, code FROM departments").fetchall()}


def seed_users(conn: Any) -> dict[str, int]:
    conn.executemany(
        "INSERT INTO users (full_name, email, aad_object_id, role, department) VALUES (?, ?, ?, ?, ?)",
        USERS,
    )
    return {row["email"]: int(row["id"]) for row in conn.execute("SELECT id, email FROM users").fetchall()}


def seed_projects(conn: Any, department_ids: dict[str, int], user_ids: dict[str, int]) -> dict[str, int]:
    for project in PROJECTS:
        description = (
            f"Loại dự án: {'Ứng dụng di động' if 'Mobile' in project['name'] else 'Hệ thống quản trị nội bộ trên web'}\n"
            f"Mục tiêu: {project['goal']}\n"
            f"Nhóm epic: {', '.join(_epic_label(epic) for epic in project['epics'])}"
        )
        conn.execute(
            """
            INSERT INTO projects
            (name, description, department_id, manager_id, start_date, end_date, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
            """,
            (
                project["name"],
                description,
                department_ids[project["department_code"]],
                user_ids[project["manager_email"]],
                project["start"],
                project["end"],
                _iso_date("2026-05-25", 10),
            ),
        )
    return {row["name"]: int(row["id"]) for row in conn.execute("SELECT id, name FROM projects").fetchall()}


def seed_sprints(conn: Any, project_ids: dict[str, int]) -> dict[tuple[str, int], int]:
    for project_name, project_id in project_ids.items():
        for idx, (name, goal, start, end, status) in enumerate(SPRINTS):
            conn.execute(
                """
                INSERT INTO sprints (project_id, name, goal, start_date, end_date, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    name,
                    goal,
                    _iso_date(start, 9),
                    _iso_date(end, 18),
                    status,
                    _iso_date("2026-05-25", 11),
                ),
            )
    rows = conn.execute("SELECT id, project_id, name FROM sprints ORDER BY id").fetchall()
    project_by_id = {value: key for key, value in project_ids.items()}
    sprint_map: dict[tuple[str, int], int] = {}
    for row in rows:
        sprint_number = int(str(row["name"]).split(":", 1)[0].replace("Sprint", "").strip())
        sprint_map[(project_by_id[int(row["project_id"])], sprint_number)] = int(row["id"])
    return sprint_map


def seed_members(conn: Any, project_ids: dict[str, int], user_ids: dict[str, int]) -> None:
    rows = []
    for project_name, members in PROJECT_TEAMS.items():
        for email, project_role in members:
            rows.append((project_ids[project_name], user_ids[email], project_role, _iso_date("2026-05-27", 9)))
    conn.executemany(
        """
        INSERT INTO project_members (project_id, user_id, role, joined_at)
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )


def _status_for_global_index(global_index: int) -> tuple[str, int]:
    if global_index < 40:
        return "done", global_index % 5
    if global_index < 55:
        return "done", global_index % 5
    if global_index < 75:
        return "doing", 5 + (global_index % 2)
    if global_index < 90:
        return "todo", 5 + (global_index % 2)
    return "doing", 4


def _deadline_for_task(status: str, global_index: int, sprint_number: int) -> str:
    if global_index >= 90:
        day = 24 + (global_index % 7)
        return f"2026-07-{day:02d}T18:00:00+00:00"
    if status in {"todo", "doing"} and global_index >= 55:
        day = 11 + (global_index % 6) if sprint_number == 5 else 17 + (global_index % 8)
        return f"2026-08-{day:02d}T18:00:00+00:00"
    start = _dt(_iso_date(SPRINTS[sprint_number][2], 18))
    deadline = start + timedelta(days=2 + (global_index % 8))
    return deadline.isoformat()


def _completed_at_for_task(status: str, global_index: int, deadline: str) -> str | None:
    if status != "done":
        return None
    deadline_dt = _dt(deadline)
    if global_index < 40:
        return (deadline_dt - timedelta(hours=4 + (global_index % 3))).isoformat()
    return (deadline_dt + timedelta(days=1 + (global_index % 3), hours=2)).isoformat()


def seed_tasks(conn: Any, project_ids: dict[str, int], sprint_ids: dict[tuple[str, int], int], user_ids: dict[str, int]) -> None:
    rows = []
    global_index = 0
    points_cycle = (1, 2, 3, 5, 8)
    difficulties = ("easy", "medium", "hard", "medium", "hard")
    for project in PROJECTS:
        project_name = str(project["name"])
        epics = tuple(project["epics"])
        for local_index in range(TASK_COUNTS[project_name]):
            epic = epics[local_index % len(epics)]
            epic_label = _epic_label(epic)
            action = TASK_ACTIONS[(local_index + global_index) % len(TASK_ACTIONS)]
            assignee_pool = ASSIGNEE_BY_EPIC[epic]
            assignee_email = assignee_pool[local_index % len(assignee_pool)]
            status, sprint_number = _status_for_global_index(global_index)
            deadline = _deadline_for_task(status, global_index, sprint_number)
            completed_at = _completed_at_for_task(status, global_index, deadline)
            created_at = (_dt(_iso_date(SPRINTS[sprint_number][2], 10)) - timedelta(days=3)).isoformat()
            updated_at = completed_at or min(DEMO_NOW, _dt(deadline) - timedelta(days=1)).isoformat()
            title = f"{action} {epic_label} #{local_index + 1:02d}"
            description = (
                f"[Epic: {epic_label}] {action} {epic_label} trong dự án {project_name}. "
                "Bao gồm tiêu chí nghiệm thu, ghi chú bàn giao cho người phụ trách và bằng chứng kiểm tra demo."
            )
            rows.append(
                (
                    title,
                    description,
                    user_ids[assignee_email],
                    project_ids[project_name],
                    sprint_ids[(project_name, sprint_number)],
                    points_cycle[global_index % len(points_cycle)],
                    difficulties[global_index % len(difficulties)],
                    status,
                    deadline,
                    completed_at,
                    created_at,
                    updated_at,
                )
            )
            global_index += 1
    conn.executemany(
        """
        INSERT INTO tasks
        (title, description, assignee_id, project_id, sprint_id, story_points, difficulty, status, deadline, completed_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def seed_capacity(conn: Any, project_ids: dict[str, int], sprint_ids: dict[tuple[str, int], int]) -> None:
    rows = []
    member_rows = conn.execute(
        "SELECT project_id, user_id FROM project_members ORDER BY project_id, user_id"
    ).fetchall()
    members_by_project: dict[int, list[int]] = {}
    for row in member_rows:
        members_by_project.setdefault(int(row["project_id"]), []).append(int(row["user_id"]))
    for project_name, project_id in project_ids.items():
        members = members_by_project[project_id]
        for sprint_number in range(7):
            sprint_id = sprint_ids[(project_name, sprint_number)]
            for idx, user_id in enumerate(members):
                capacity = (80.0, 60.0, 40.0)[idx % 3]
                ratio = (0.72, 0.88, 0.95, 0.55, 1.02)[(idx + sprint_number) % 5]
                rows.append((sprint_id, user_id, capacity, round(capacity * ratio, 1), _iso_date(SPRINTS[sprint_number][2], 10)))
    conn.executemany(
        """
        INSERT INTO sprint_capacity_plans (sprint_id, user_id, capacity_hours, allocated_hours, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def seed_risks(conn: Any, project_ids: dict[str, int], user_ids: dict[str, int]) -> None:
    risk_rows = (
        ("TeamsWork Internal PM & KPI", "Dữ liệu KPI có thể chưa đầy đủ", "Thành viên có thể quên cập nhật task trong giai đoạn sprint bận.", "medium", "high", "Nhắc cập nhật hàng tuần và rà soát task cũ trước khi tính KPI.", "phuc.tran@teamswork.example.com", "open"),
        ("TeamsWork Internal PM & KPI", "Rủi ro phân quyền trước demo", "Thay đổi quyền có thể vô tình ẩn màn hình báo cáo.", "low", "high", "Chạy smoke test ma trận vai trò trước mỗi buổi diễn tập demo.", "kiet.do@teamswork.example.com", "mitigated"),
        ("ShopMate Mobile Commerce", "Chậm tích hợp API thanh toán bên thứ ba", "Thông tin sandbox và callback có thể đến muộn hơn kế hoạch.", "high", "high", "Giữ adapter giả lập sẵn sàng và cô lập tích hợp thanh toán sau service contract.", "ha.le@teamswork.example.com", "open"),
        ("ShopMate Mobile Commerce", "Mở rộng phạm vi voucher", "Marketing yêu cầu thêm quy tắc cộng dồn voucher trong UAT.", "medium", "medium", "Đóng phạm vi voucher v1 và đưa biến thể cộng dồn vào backlog thay đổi.", "chau.dang@teamswork.example.com", "open"),
        ("ShopMate Mobile Commerce", "Thiếu độ phủ QA cho push notification", "Ma trận thiết bị có thể chưa bao phủ các phiên bản Android cũ.", "medium", "medium", "Ưu tiên regression trên nhóm thiết bị phổ biến của khách hàng.", "ngoc.phan@teamswork.example.com", "mitigated"),
        ("FieldOps Service Mobile", "Rủi ro xung đột đồng bộ offline", "Kỹ thuật viên có thể chỉnh cùng một ticket khi đang offline.", "high", "high", "Dùng cảnh báo xung đột và hàng chờ rà soát ghi đè phía server.", "bao.pham@teamswork.example.com", "open"),
        ("FieldOps Service Mobile", "Thiếu năng lực mobile giai đoạn cao điểm", "Kỹ sư mobile bị chia sẻ với ShopMate trong cuối tháng 7.", "medium", "high", "Giữ riêng capacity cho các story SLA và tải ảnh nghiệm thu quan trọng.", "giabao.nguyen@teamswork.example.com", "open"),
        ("FieldOps Service Mobile", "Chậm phản hồi từ khách hàng", "Đội vận hành có thể phản hồi UAT chậm cho luồng check-in.", "medium", "medium", "Đặt khung giờ phản hồi cố định và ghi lại các giả định chưa chốt.", "linh.vo@teamswork.example.com", "closed"),
    )
    conn.executemany(
        """
        INSERT INTO project_risks
        (project_id, title, description, probability, impact, mitigation_plan, owner_user_id, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (project_ids[p], title, desc, probability, impact, mitigation, user_ids[owner], status, _iso_date("2026-07-01", 9))
            for p, title, desc, probability, impact, mitigation, owner, status in risk_rows
        ],
    )


def seed_weekly_updates(conn: Any, project_ids: dict[str, int], sprint_ids: dict[tuple[str, int], int], user_ids: dict[str, int]) -> None:
    weeks = (
        ("2026-W23", 8, "green", "Đã hoàn tất kickoff và phân vai rõ ràng.", "Hoàn tất thiết lập kỹ thuật cho Sprint 1.", None, 0),
        ("2026-W24", 18, "green", "Nhóm nền tảng đang đi đúng kế hoạch.", "Chốt xác thực và điều hướng cơ bản.", None, 1),
        ("2026-W25", 31, "amber", "Backlog lõi lớn hơn ước lượng ban đầu.", "Rà lại phạm vi các task polish ưu tiên thấp.", "Cần PM quyết định thứ tự ưu tiên backlog.", 1),
        ("2026-W27", 48, "green", "Tính năng lõi đã dùng được trên staging.", "Bắt đầu kiểm tra tích hợp và báo cáo.", None, 2),
        ("2026-W29", 64, "amber", "QA liên module phát hiện một số lỗi tích hợp.", "Triage lỗi và tập trung vào luồng quan trọng cho demo.", "Thay đổi hợp đồng API cần kiểm thử lại.", 3),
        ("2026-W31", 78, "red", "Blocker UAT đang ảnh hưởng mức sẵn sàng demo.", "Tổ chức xử lý blocker hằng ngày và cập nhật trạng thái liên tục.", "Còn hai task quan trọng quá hạn.", 4),
        ("2026-W32", 86, "amber", "Phần lớn blocker UAT đã xử lý, còn thiếu ghi chú phát hành.", "Hoàn tất kịch bản demo và regression cuối.", None, 5),
    )
    manager_for_project = {
        "TeamsWork Internal PM & KPI": "phuc.tran@teamswork.example.com",
        "ShopMate Mobile Commerce": "ha.le@teamswork.example.com",
        "FieldOps Service Mobile": "bao.pham@teamswork.example.com",
    }
    rows = []
    for project_name, project_id in project_ids.items():
        for week, base_progress, rag, summary, next_steps, blocker, sprint_number in weeks:
            progress = base_progress + (2 if project_name == "TeamsWork Internal PM & KPI" else 0)
            project_rag = "green" if project_name == "TeamsWork Internal PM & KPI" and rag == "amber" else rag
            rows.append(
                (
                    project_id,
                    sprint_ids[(project_name, sprint_number)],
                    week,
                    float(min(progress, 95)),
                    project_rag,
                    f"{project_name}: {summary}",
                    next_steps,
                    blocker,
                    user_ids[manager_for_project[project_name]],
                    _iso_date("2026-08-07", 16),
                )
            )
    conn.executemany(
        """
        INSERT INTO weekly_status_updates
        (project_id, sprint_id, week_label, progress_percent, rag_status, summary, next_steps, blocker, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def seed_kpi_adjustments(conn: Any, user_ids: dict[str, int]) -> None:
    rows = (
        ("kiet.do@teamswork.example.com", "2026-06", 5.0, "+5 điểm: hỗ trợ release gấp"),
        ("quan.pham@teamswork.example.com", "2026-07", -3.0, "-3 điểm: thiếu cập nhật tiến độ"),
        ("long.nguyen@teamswork.example.com", "2026-07", 8.0, "+8 điểm: xử lý lỗi production"),
        ("giabao.nguyen@teamswork.example.com", "2026-08", -5.0, "-5 điểm: để task quá hạn nhưng không báo blocker"),
        ("yen.ho@teamswork.example.com", "2026-08", 4.0, "+4 điểm: hỗ trợ QA regression ngoài phạm vi"),
    )
    admin_id = user_ids["an.nguyen@teamswork.example.com"]
    conn.executemany(
        """
        INSERT INTO kpi_adjustments (user_id, month, points, reason, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [(user_ids[email], month, points, reason, admin_id, _iso_date(f"{month}-28", 17)) for email, month, points, reason in rows],
    )


def seed_notifications_comments_audit(conn: Any, user_ids: dict[str, int]) -> None:
    tasks = conn.execute(
        """
        SELECT
            t.id,
            t.title,
            t.description,
            t.assignee_id,
            t.status,
            t.deadline,
            p.name AS project_name,
            s.name AS sprint_name
        FROM tasks t
        LEFT JOIN projects p ON p.id = t.project_id
        LEFT JOIN sprints s ON s.id = t.sprint_id
        ORDER BY t.id
        """
    ).fetchall()
    comment_authors = (
        user_ids["phuc.tran@teamswork.example.com"],
        user_ids["linh.vo@teamswork.example.com"],
        user_ids["kiet.do@teamswork.example.com"],
        user_ids["mai.bui@teamswork.example.com"],
        user_ids["yen.ho@teamswork.example.com"],
        user_ids["ngoc.phan@teamswork.example.com"],
    )
    comments = []
    for idx, task in enumerate(tasks):
        task_id = int(task["id"])
        title = str(task["title"])
        project_name = str(task["project_name"] or "dự án chưa gán")
        sprint_name = str(task["sprint_name"] or "sprint chưa gán")
        deadline = str(task["deadline"])[:10]
        if task["status"] == "done":
            first_comment = f"Task '{title}' của {project_name} đã hoàn thành trong {sprint_name}; cần giữ lại bằng chứng nghiệm thu cho buổi demo."
            second_comment = f"Đã kiểm tra kết quả của '{title}' so với deadline {deadline}; phần bàn giao có thể đưa vào báo cáo sprint."
            third_comment = f"QA đã đối chiếu '{title}' với tiêu chí nghiệm thu và không còn blocker chính."
        elif task["status"] == "doing":
            first_comment = f"Task '{title}' đang xử lý trong {sprint_name}; cần cập nhật tiến độ trước mốc {deadline}."
            second_comment = f"Với '{title}', vui lòng ghi rõ phần còn lại và blocker nếu có để PM cân đối capacity."
            third_comment = f"QA chuẩn bị checklist regression cho '{title}' để chạy ngay khi chuyển sang trạng thái hoàn thành."
        else:
            first_comment = f"Task '{title}' đang ở backlog của {project_name}; cần xác nhận lại phạm vi trước khi kéo vào doing."
            second_comment = f"Trước khi bắt đầu '{title}', BA cần chốt dữ liệu đầu vào và tiêu chí nghiệm thu cho deadline {deadline}."
            third_comment = f"PM đề nghị đánh giá lại độ ưu tiên của '{title}' trong {sprint_name} để tránh lệch kế hoạch demo."
        comments.append(
            (
                task_id,
                comment_authors[idx % len(comment_authors)],
                first_comment,
                _iso_date(f"2026-08-{1 + (idx % 9):02d}", 9 + (idx % 4)),
            )
        )
        comments.append(
            (
                task_id,
                comment_authors[(idx + 1) % len(comment_authors)],
                second_comment,
                _iso_date(f"2026-08-{1 + (idx % 9):02d}", 13 + (idx % 4)),
            )
        )
        if idx % 2 == 0:
            comments.append(
                (
                    task_id,
                    comment_authors[(idx + 2) % len(comment_authors)],
                    third_comment,
                    _iso_date(f"2026-08-{2 + (idx % 8):02d}", 16),
                )
            )
    conn.executemany(
        "INSERT INTO task_comments (task_id, author_user_id, body, created_at) VALUES (?, ?, ?, ?)",
        comments,
    )
    notifications = [
        (int(tasks[0]["assignee_id"]), "task_status_changed", "Cập nhật trạng thái task", f"'{tasks[0]['title']}' đã chuyển sang hoàn thành.", "task", int(tasks[0]["id"]), True, _iso_date("2026-07-20", 9), _iso_date("2026-07-20", 10)),
        (int(tasks[3]["assignee_id"]), "task_comment", "Có bình luận mới", f"Task '{tasks[3]['title']}' vừa có bình luận mới cần phản hồi.", "task", int(tasks[3]["id"]), False, _iso_date("2026-07-24", 15), None),
        (int(tasks[6]["assignee_id"]), "task_due_soon", "Task sắp đến hạn", f"Task '{tasks[6]['title']}' sắp đến hạn, vui lòng cập nhật tiến độ.", "task", int(tasks[6]["id"]), False, _iso_date("2026-08-09", 9), None),
        (int(tasks[9]["assignee_id"]), "task_overdue", "Task đã quá hạn", f"Task '{tasks[9]['title']}' đã quá hạn theo mốc demo.", "task", int(tasks[9]["id"]), False, _iso_date("2026-08-10", 9), None),
        (int(tasks[14]["assignee_id"]), "task_comment", "QA cần xác nhận", f"QA đã thêm ghi chú kiểm thử cho task '{tasks[14]['title']}'.", "task", int(tasks[14]["id"]), False, _iso_date("2026-08-08", 11), None),
        (int(tasks[22]["assignee_id"]), "task_due_soon", "Cần chuẩn bị demo", f"Task '{tasks[22]['title']}' cần hoàn tất trước buổi chạy thử demo.", "task", int(tasks[22]["id"]), False, _iso_date("2026-08-09", 14), None),
        (int(tasks[37]["assignee_id"]), "task_status_changed", "Task đã được cập nhật", f"PM đã cập nhật trạng thái cho task '{tasks[37]['title']}'.", "task", int(tasks[37]["id"]), False, _iso_date("2026-08-07", 16), None),
    ]
    conn.executemany(
        """
        INSERT INTO app_notifications
        (user_id, type, title, message, entity_type, entity_id, is_read, created_at, read_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        notifications,
    )
    queue_payloads = [
        (user_ids["phuc.tran@teamswork.example.com"], "teams", {"message": "Tổng hợp tuần của TeamsWork đã sẵn sàng."}, "queued", 0, 3, None, None, _iso_date("2026-08-09", 8), None),
        (user_ids["ha.le@teamswork.example.com"], "teams", {"message": "ShopMate cần rà soát blocker UAT trong hôm nay."}, "sent", 1, 3, None, None, _iso_date("2026-08-08", 8), _iso_date("2026-08-08", 8)),
        (user_ids["bao.pham@teamswork.example.com"], "teams", {"message": "FieldOps có cảnh báo task quá hạn cần xử lý."}, "failed", 3, 3, "Webhook demo chưa sẵn sàng", None, _iso_date("2026-08-07", 8), _iso_date("2026-08-07", 8)),
        (user_ids["yen.ho@teamswork.example.com"], "teams", {"message": "QA cần chốt danh sách regression trước buổi demo."}, "queued", 0, 3, None, _iso_date("2026-08-10", 10), _iso_date("2026-08-10", 8), None),
    ]
    conn.executemany(
        """
        INSERT INTO notification_queue
        (user_id, channel, payload, status, attempts, max_attempts, last_error, next_retry_at, created_at, sent_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(u, c, json.dumps(p, ensure_ascii=True), s, a, m, e, n, ca, sa) for u, c, p, s, a, m, e, n, ca, sa in queue_payloads],
    )
    audit_rows = [
        (user_ids["an.nguyen@teamswork.example.com"], "create_project", "project", 1, "Tạo dự án demo TeamsWork", _iso_date("2026-05-25", 10)),
        (user_ids["phuc.tran@teamswork.example.com"], "create_task", "task", int(tasks[0]["id"]), "Tạo backlog task demo", _iso_date("2026-06-03", 9)),
        (user_ids["kiet.do@teamswork.example.com"], "update_task_status", "task", int(tasks[0]["id"]), "status=done", _iso_date("2026-06-10", 17)),
        (user_ids["an.nguyen@teamswork.example.com"], "calculate_kpi", "kpi", None, "month=2026-07", _iso_date("2026-07-31", 17)),
        (user_ids["ha.le@teamswork.example.com"], "import_ai_tasks", "ai_task_draft", 3, "Import các task AI đã chọn", _iso_date("2026-08-05", 16)),
        (user_ids["phuc.tran@teamswork.example.com"], "import_ai_tasks", "ai_task_draft", 4, "Import checklist sẵn sàng demo từ ngữ cảnh RAG", _iso_date("2026-08-08", 15)),
    ]
    conn.executemany(
        "INSERT INTO audit_logs (actor_user_id, action, entity, entity_id, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        audit_rows,
    )
