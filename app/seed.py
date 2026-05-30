from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from typing import Any

from app.database import get_connection
from app.passwords import hash_password
from app.rag import chunk_text, get_embedding_provider, pgvector_enabled
from app.repository import store_rag_chunk_embedding
from app.settings import settings


DEMO_NOW = datetime(2026, 8, 10, 9, 0, 0, tzinfo=timezone.utc)
DEMO_NOW_ISO = DEMO_NOW.isoformat()
DEMO_NAMESPACE = "teamswork_full_demo"
FULL_DEMO_PASSWORD = "Demo@123"
RESET_ALLOWED_ENVS = {"development", "dev", "local", "demo", "test", "testing"}

DEMO_TABLES = (
    "rag_chunk_embeddings",
    "rag_document_permissions",
    "rag_chunks",
    "rag_documents",
    "kpi_adjustments",
    "task_ai_details",
    "ai_task_drafts",
    "audit_logs",
    "app_notifications",
    "notification_queue",
    "teams_conversation_refs",
    "weekly_status_updates",
    "project_risks",
    "sprint_capacity_plans",
    "task_comments",
    "tasks",
    "sprints",
    "project_members",
    "projects",
    "departments",
    "users",
)


AUTH_DEMO_ACCOUNTS = (
    ("TeamsWork Admin", "admin@teamswork.local", "Admin@123", "ADMIN", "ADM", "System Admin"),
    ("TeamsWork Manager", "manager@teamswork.local", "Manager@123", "MANAGER", "PMO", "Department Manager"),
    ("TeamsWork Leader", "leader@teamswork.local", "Leader@123", "LEADER", "ENG", "Team Leader"),
    ("TeamsWork Member", "member@teamswork.local", "Member@123", "MEMBER", "ENG", "Member"),
    ("TeamsWork HR", "hr@teamswork.local", "Hr@123", "HR", "HR", "HR Specialist"),
    ("TeamsWork Auditor", "auditor@teamswork.local", "Auditor@123", "AUDITOR", "AUD", "Auditor"),
)

DEPARTMENTS = (
    ("PMO", "PMO"),
    ("Product & BA", "PBA"),
    ("UI/UX Design", "UXD"),
    ("Web Engineering", "WEB"),
    ("Mobile Engineering", "MOB"),
    ("QA", "QA"),
    ("Operations", "OPS"),
)


def seed_auth_demo_accounts() -> None:
    departments = (
        ("Administration", "ADM"),
        ("Project Management", "PMO"),
        ("Engineering", "ENG"),
        ("Human Resources", "HR"),
        ("Audit", "AUD"),
    )
    with get_connection() as conn:
        for name, code in departments:
            conn.execute(
                """
                /* no-returning-id */ INSERT INTO departments (name, code, description, is_active, created_at)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(code) DO UPDATE SET name = excluded.name, is_active = 1
                """,
                (name, code, f"Default {name} department", DEMO_NOW_ISO),
            )
        dep_ids = {
            str(row["code"]): int(row["id"])
            for row in conn.execute("SELECT id, code FROM departments").fetchall()
        }
        for full_name, email, password, role_id, department_code, position in AUTH_DEMO_ACCOUNTS:
            department_id = dep_ids[department_code]
            department_name = conn.execute("SELECT name FROM departments WHERE id = ?", (department_id,)).fetchone()["name"]
            existing = conn.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email.lower(),)).fetchone()
            role = role_id.lower() if role_id != "MEMBER" else "staff"
            if existing:
                conn.execute(
                    """
                    UPDATE users
                    SET full_name = ?, role = ?, role_id = ?, department = ?, department_id = ?,
                        position = ?, password_hash = COALESCE(password_hash, ?), is_active = 1, updated_at = ?
                    WHERE id = ?
                    """,
                    (full_name, role, role_id, department_name, department_id, position, hash_password(password), DEMO_NOW_ISO, existing["id"]),
                )
                continue
            conn.execute(
                """
                INSERT INTO users
                (full_name, email, aad_object_id, role, department, password_hash, role_id, department_id, position, avatar_url, is_active, created_at, updated_at)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, NULL, 1, ?, ?)
                """,
                (full_name, email.lower(), role, department_name, hash_password(password), role_id, department_id, position, DEMO_NOW_ISO, DEMO_NOW_ISO),
            )

USERS = (
    ("Nguyễn Minh An", "an.nguyen@teamswork.example.com", None, "admin", "PMO"),
    ("Trần Hoàng Phúc", "phuc.tran@teamswork.example.com", None, "manager", "PMO"),
    ("Lê Thu Hà", "ha.le@teamswork.example.com", None, "manager", "PMO"),
    ("Phạm Quốc Bảo", "bao.pham@teamswork.example.com", None, "manager", "PMO"),
    ("Võ Ngọc Linh", "linh.vo@teamswork.example.com", None, "staff", "Product & BA"),
    ("Đặng Minh Châu", "chau.dang@teamswork.example.com", None, "staff", "Product & BA"),
    ("Bùi Thanh Mai", "mai.bui@teamswork.example.com", None, "staff", "UI/UX Design"),
    ("Hoàng Gia Huy", "huy.hoang@teamswork.example.com", None, "staff", "UI/UX Design"),
    ("Đỗ Tuấn Kiệt", "kiet.do@teamswork.example.com", None, "staff", "Web Engineering"),
    ("Nguyễn Đức Long", "long.nguyen@teamswork.example.com", None, "staff", "Web Engineering"),
    ("Trịnh Hải Nam", "nam.trinh@teamswork.example.com", None, "staff", "Web Engineering"),
    ("Lê Anh Khoa", "khoa.le@teamswork.example.com", None, "staff", "Web Engineering"),
    ("Phạm Minh Quân", "quan.pham@teamswork.example.com", None, "staff", "Web Engineering"),
    ("Vũ Thanh Tùng", "tung.vu@teamswork.example.com", None, "staff", "Web Engineering"),
    ("Nguyễn Gia Bảo", "giabao.nguyen@teamswork.example.com", None, "staff", "Mobile Engineering"),
    ("Trần Nhật Minh", "minh.tran@teamswork.example.com", None, "staff", "Mobile Engineering"),
    ("Đỗ Quỳnh Như", "nhu.do@teamswork.example.com", None, "staff", "Mobile Engineering"),
    ("Hồ Thị Yến", "yen.ho@teamswork.example.com", None, "staff", "QA"),
    ("Phan Bảo Ngọc", "ngoc.phan@teamswork.example.com", None, "staff", "QA"),
    ("Mai Khánh Vy", "vy.mai@teamswork.example.com", None, "hr", "Operations"),
)

PROJECTS = (
    {
        "name": "TeamsWork Internal PM & KPI",
        "department_code": "WEB",
        "manager_email": "phuc.tran@teamswork.example.com",
        "start": "2026-06-01T09:00:00+00:00",
        "end": "2026-08-31T18:00:00+00:00",
        "goal": "Xây dựng hệ thống nội bộ để quản lý công việc, sprint, KPI, báo cáo và thông báo.",
        "epics": (
            "Authentication & RBAC",
            "Project/Sprint/Task Management",
            "KPI Dashboard",
            "AI Task Breakdown",
            "Report & Notification",
        ),
    },
    {
        "name": "ShopMate Mobile Commerce",
        "department_code": "MOB",
        "manager_email": "ha.le@teamswork.example.com",
        "start": "2026-06-03T09:00:00+00:00",
        "end": "2026-08-28T18:00:00+00:00",
        "goal": "Xây dựng ứng dụng thương mại di động cho mua hàng, theo dõi đơn và tích điểm.",
        "epics": (
            "Login/Profile",
            "Product Catalog",
            "Cart & Order Flow",
            "Loyalty/Voucher",
            "Push Notification",
            "Admin Sync API",
        ),
    },
    {
        "name": "FieldOps Service Mobile",
        "department_code": "MOB",
        "manager_email": "bao.pham@teamswork.example.com",
        "start": "2026-06-10T09:00:00+00:00",
        "end": "2026-08-30T18:00:00+00:00",
        "goal": "Xây dựng ứng dụng hiện trường để kỹ thuật viên nhận ticket, check-in và tải ảnh nghiệm thu.",
        "epics": (
            "Ticket Assignment",
            "Technician Mobile Workflow",
            "GPS Check-in",
            "Offline Sync",
            "Photo Evidence Upload",
            "SLA Dashboard",
        ),
    },
)

SPRINTS = (
    ("Sprint 0: Khởi động & Lập kế hoạch", "Chốt phạm vi, backlog, vai trò và cơ chế quản trị triển khai", "2026-06-01", "2026-06-07", "completed"),
    ("Sprint 1: Nền tảng", "Thiết lập kiến trúc, xác thực, môi trường và các luồng cơ bản", "2026-06-08", "2026-06-21", "completed"),
    ("Sprint 2: Tính năng lõi", "Hoàn thiện các luồng nghiệp vụ chính và mô hình dữ liệu", "2026-06-22", "2026-07-05", "completed"),
    ("Sprint 3: Tích hợp & Báo cáo", "Kết nối tích hợp, báo cáo, dashboard và luồng vận hành", "2026-07-06", "2026-07-19", "completed"),
    ("Sprint 4: Ổn định", "Sửa lỗi tích hợp, xử lý ca biên và chuẩn bị bản demo beta", "2026-07-20", "2026-08-02", "active"),
    ("Sprint 5: UAT & Chuẩn bị demo", "Hỗ trợ phản hồi UAT, kịch bản demo và bản ứng viên phát hành", "2026-08-03", "2026-08-16", "planned"),
    ("Sprint 6: Bàn giao & Sửa lỗi cuối", "Hoàn tất bàn giao, lỗi cuối và tài liệu phát hành", "2026-08-17", "2026-08-30", "planned"),
)

PROJECT_TEAMS = {
    "TeamsWork Internal PM & KPI": (
        ("phuc.tran@teamswork.example.com", "project_manager"),
        ("linh.vo@teamswork.example.com", "business_analyst"),
        ("mai.bui@teamswork.example.com", "ui_ux_designer"),
        ("kiet.do@teamswork.example.com", "backend_developer"),
        ("long.nguyen@teamswork.example.com", "backend_developer"),
        ("khoa.le@teamswork.example.com", "frontend_developer"),
        ("quan.pham@teamswork.example.com", "frontend_developer"),
        ("yen.ho@teamswork.example.com", "qa_tester"),
    ),
    "ShopMate Mobile Commerce": (
        ("ha.le@teamswork.example.com", "project_manager"),
        ("chau.dang@teamswork.example.com", "business_analyst"),
        ("huy.hoang@teamswork.example.com", "ui_ux_designer"),
        ("long.nguyen@teamswork.example.com", "backend_developer"),
        ("giabao.nguyen@teamswork.example.com", "mobile_developer"),
        ("minh.tran@teamswork.example.com", "mobile_developer"),
        ("tung.vu@teamswork.example.com", "frontend_developer"),
        ("ngoc.phan@teamswork.example.com", "qa_tester"),
    ),
    "FieldOps Service Mobile": (
        ("bao.pham@teamswork.example.com", "project_manager"),
        ("linh.vo@teamswork.example.com", "business_analyst"),
        ("mai.bui@teamswork.example.com", "ui_ux_designer"),
        ("nam.trinh@teamswork.example.com", "backend_developer"),
        ("giabao.nguyen@teamswork.example.com", "mobile_developer"),
        ("minh.tran@teamswork.example.com", "mobile_developer"),
        ("nhu.do@teamswork.example.com", "mobile_developer"),
        ("yen.ho@teamswork.example.com", "qa_tester"),
    ),
}

DEMO_PROJECT_NAMES = tuple(project["name"] for project in PROJECTS)

FULL_DEMO_DEPARTMENTS = (
    ("Administration", "ADM", "Admin, RBAC, audit and demo operations."),
    ("Project Management Office", "PMO", "Portfolio planning and delivery governance."),
    ("Product & Business Analysis", "PBA", "Business analysis, requirements and UAT coordination."),
    ("UI/UX Design", "UXD", "Product design, research and usability review."),
    ("Web Engineering", "WEB", "Backend and frontend web delivery team."),
    ("Mobile Engineering", "MOB", "iOS, Android and mobile API integration team."),
    ("Quality Assurance", "QA", "Manual, automation and regression testing."),
    ("Operations", "OPS", "Release, notification and support operations."),
    ("Human Resources", "HR", "People operations and KPI review."),
    ("Audit", "AUD", "Read-only audit and compliance review."),
    ("Engineering", "ENG", "Compatibility department for auth demo accounts."),
)

FULL_DEMO_USERS = (
    ("Nguyen Minh An", "an.nguyen@teamswork.example.com", "admin", "ADMIN", "ADM", "System Admin", FULL_DEMO_PASSWORD),
    ("Tran Hoang Phuc", "phuc.tran@teamswork.example.com", "manager", "MANAGER", "PMO", "Delivery Manager", FULL_DEMO_PASSWORD),
    ("Le Thu Ha", "ha.le@teamswork.example.com", "manager", "MANAGER", "PMO", "Mobile Program Manager", FULL_DEMO_PASSWORD),
    ("Pham Quoc Bao", "bao.pham@teamswork.example.com", "manager", "MANAGER", "PMO", "FieldOps Program Manager", FULL_DEMO_PASSWORD),
    ("Vo Ngoc Linh", "linh.vo@teamswork.example.com", "manager", "LEADER", "PBA", "BA Lead", FULL_DEMO_PASSWORD),
    ("Dang Minh Chau", "chau.dang@teamswork.example.com", "staff", "MEMBER", "PBA", "Business Analyst", FULL_DEMO_PASSWORD),
    ("Bui Thanh Mai", "mai.bui@teamswork.example.com", "manager", "LEADER", "UXD", "UX Lead", FULL_DEMO_PASSWORD),
    ("Hoang Gia Huy", "huy.hoang@teamswork.example.com", "staff", "MEMBER", "UXD", "Product Designer", FULL_DEMO_PASSWORD),
    ("Do Tuan Kiet", "kiet.do@teamswork.example.com", "staff", "MEMBER", "WEB", "Backend Developer", FULL_DEMO_PASSWORD),
    ("Nguyen Duc Long", "long.nguyen@teamswork.example.com", "staff", "MEMBER", "WEB", "Backend Developer", FULL_DEMO_PASSWORD),
    ("Trinh Hai Nam", "nam.trinh@teamswork.example.com", "staff", "MEMBER", "WEB", "Backend Developer", FULL_DEMO_PASSWORD),
    ("Le Anh Khoa", "khoa.le@teamswork.example.com", "staff", "MEMBER", "WEB", "Frontend Developer", FULL_DEMO_PASSWORD),
    ("Pham Minh Quan", "quan.pham@teamswork.example.com", "staff", "MEMBER", "WEB", "Frontend Developer", FULL_DEMO_PASSWORD),
    ("Vu Thanh Tung", "tung.vu@teamswork.example.com", "staff", "MEMBER", "WEB", "Frontend Developer", FULL_DEMO_PASSWORD),
    ("Nguyen Gia Bao", "giabao.nguyen@teamswork.example.com", "staff", "MEMBER", "MOB", "Mobile Developer", FULL_DEMO_PASSWORD),
    ("Tran Nhat Minh", "minh.tran@teamswork.example.com", "staff", "MEMBER", "MOB", "Mobile Developer", FULL_DEMO_PASSWORD),
    ("Do Quynh Nhu", "nhu.do@teamswork.example.com", "staff", "MEMBER", "MOB", "Mobile Developer", FULL_DEMO_PASSWORD),
    ("Ho Thi Yen", "yen.ho@teamswork.example.com", "staff", "MEMBER", "QA", "QA Engineer", FULL_DEMO_PASSWORD),
    ("Phan Bao Ngoc", "ngoc.phan@teamswork.example.com", "staff", "MEMBER", "QA", "QA Engineer", FULL_DEMO_PASSWORD),
    ("Mai Khanh Vy", "vy.mai@teamswork.example.com", "hr", "HR", "HR", "HR Specialist", FULL_DEMO_PASSWORD),
    ("TeamsWork Admin", "admin@teamswork.local", "admin", "ADMIN", "ADM", "System Admin", "Admin@123"),
    ("TeamsWork Manager", "manager@teamswork.local", "manager", "MANAGER", "PMO", "Department Manager", "Manager@123"),
    ("TeamsWork Leader", "leader@teamswork.local", "manager", "LEADER", "ENG", "Team Leader", "Leader@123"),
    ("TeamsWork Member", "member@teamswork.local", "staff", "MEMBER", "ENG", "Member", "Member@123"),
    ("TeamsWork HR", "hr@teamswork.local", "hr", "HR", "HR", "HR Specialist", "Hr@123"),
    ("TeamsWork Auditor", "auditor@teamswork.local", "hr", "AUDITOR", "AUD", "Auditor", "Auditor@123"),
)

FULL_DEMO_USER_EMAILS = tuple(row[1] for row in FULL_DEMO_USERS)
FULL_DEMO_RAG_SOURCE_LABELS = tuple(
    f"{project_slug}-{doc_slug}"
    for project_slug in ("teamswork", "shopmate", "fieldops")
    for doc_slug in ("brief", "requirements", "uat-notes", "risk-decisions")
)
FULL_DEMO_AI_SOURCE_NAMES = (
    "teamswork_full_demo_kpi_dashboard.txt",
    "teamswork_full_demo_uat_notes.txt",
    "shopmate_full_demo_requirements.txt",
    "fieldops_full_demo_offline_sync.txt",
    "teamswork_full_demo_rbac_permissions.txt",
    "fieldops_full_demo_risk_log.txt",
)

TASK_COUNTS = {
    "TeamsWork Internal PM & KPI": 32,
    "ShopMate Mobile Commerce": 34,
    "FieldOps Service Mobile": 34,
}

ASSIGNEE_BY_EPIC = {
    "Authentication & RBAC": ("kiet.do@teamswork.example.com", "long.nguyen@teamswork.example.com"),
    "Project/Sprint/Task Management": ("khoa.le@teamswork.example.com", "quan.pham@teamswork.example.com"),
    "KPI Dashboard": ("quan.pham@teamswork.example.com", "kiet.do@teamswork.example.com"),
    "AI Task Breakdown": ("long.nguyen@teamswork.example.com", "linh.vo@teamswork.example.com"),
    "Report & Notification": ("yen.ho@teamswork.example.com", "khoa.le@teamswork.example.com"),
    "Login/Profile": ("giabao.nguyen@teamswork.example.com", "chau.dang@teamswork.example.com"),
    "Product Catalog": ("minh.tran@teamswork.example.com", "huy.hoang@teamswork.example.com"),
    "Cart & Order Flow": ("giabao.nguyen@teamswork.example.com", "long.nguyen@teamswork.example.com"),
    "Loyalty/Voucher": ("minh.tran@teamswork.example.com", "tung.vu@teamswork.example.com"),
    "Push Notification": ("giabao.nguyen@teamswork.example.com", "ngoc.phan@teamswork.example.com"),
    "Admin Sync API": ("long.nguyen@teamswork.example.com", "tung.vu@teamswork.example.com"),
    "Ticket Assignment": ("nam.trinh@teamswork.example.com", "linh.vo@teamswork.example.com"),
    "Technician Mobile Workflow": ("nhu.do@teamswork.example.com", "giabao.nguyen@teamswork.example.com"),
    "GPS Check-in": ("minh.tran@teamswork.example.com", "nam.trinh@teamswork.example.com"),
    "Offline Sync": ("nhu.do@teamswork.example.com", "minh.tran@teamswork.example.com"),
    "Photo Evidence Upload": ("giabao.nguyen@teamswork.example.com", "yen.ho@teamswork.example.com"),
    "SLA Dashboard": ("nam.trinh@teamswork.example.com", "mai.bui@teamswork.example.com"),
}

EPIC_LABELS = {
    "Authentication & RBAC": "Xác thực và phân quyền RBAC",
    "Project/Sprint/Task Management": "Quản lý dự án, sprint và task",
    "KPI Dashboard": "Dashboard KPI",
    "AI Task Breakdown": "Phân rã task bằng AI",
    "Report & Notification": "Báo cáo và thông báo",
    "Login/Profile": "Đăng nhập và hồ sơ cá nhân",
    "Product Catalog": "Danh mục sản phẩm",
    "Cart & Order Flow": "Giỏ hàng và đặt hàng",
    "Loyalty/Voucher": "Tích điểm và voucher",
    "Push Notification": "Thông báo đẩy",
    "Admin Sync API": "API đồng bộ quản trị",
    "Ticket Assignment": "Phân công ticket",
    "Technician Mobile Workflow": "Luồng mobile cho kỹ thuật viên",
    "GPS Check-in": "Check-in GPS",
    "Offline Sync": "Đồng bộ offline",
    "Photo Evidence Upload": "Tải ảnh nghiệm thu",
    "SLA Dashboard": "Dashboard SLA",
}

TASK_ACTIONS = (
    "Xác định tiêu chí nghiệm thu cho",
    "Triển khai hợp đồng API cho",
    "Xây dựng luồng chính cho",
    "Tạo quy tắc kiểm tra cho",
    "Kết nối dữ liệu dashboard cho",
    "Bổ sung kiểm thử hồi quy cho",
    "Hoàn thiện ca biên trong",
    "Chuẩn bị ghi chú phát hành cho",
)


def _iso_date(date_value: str, hour: int = 18) -> str:
    return f"{date_value}T{hour:02d}:00:00+00:00"


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _epic_label(epic: str) -> str:
    return EPIC_LABELS.get(epic, epic)


def _table_exists(conn: Any, table: str) -> bool:
    if conn.dialect == "sqlite":
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        return row is not None
    row = conn.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = current_schema()
          AND table_name = ?
        """,
        (table,),
    ).fetchone()
    return row is not None


def _table_columns(conn: Any, table: str) -> set[str]:
    if conn.dialect == "sqlite":
        return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    rows = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = ?
        """,
        (table,),
    ).fetchall()
    return {str(row["column_name"]) for row in rows}


def _reset_sequences(conn: Any) -> None:
    existing = [table for table in DEMO_TABLES if _table_exists(conn, table)]
    if conn.dialect == "sqlite":
        for table in existing:
            conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
        return
    for table in existing:
        conn.execute(f"ALTER SEQUENCE IF EXISTS {table}_id_seq RESTART WITH 1")


def reset_demo_data(conn: Any) -> None:
    for table in DEMO_TABLES:
        if _table_exists(conn, table):
            conn.execute(f"DELETE FROM {table}")
    _reset_sequences(conn)


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


def seed_ai_and_rag(conn: Any, project_ids: dict[str, int], user_ids: dict[str, int]) -> None:
    drafts = [
        ("text", "Khách hàng ShopMate yêu cầu cải thiện giỏ hàng, voucher và theo dõi đơn.", "shopmate-request.txt", "draft", None, None, None, None, None, user_ids["ha.le@teamswork.example.com"], _iso_date("2026-07-18", 10)),
        ("text", "FieldOps cần luồng check-in offline và ảnh nghiệm thu hiện trường.", "fieldops-workflow.txt", "reviewed", user_ids["bao.pham@teamswork.example.com"], _iso_date("2026-07-25", 15), None, "Đã rà soát cho phạm vi Sprint 4.", "Tách offline sync thành các task nhỏ hơn.", user_ids["linh.vo@teamswork.example.com"], _iso_date("2026-07-24", 10)),
        ("text", "TeamsWork KPI Dashboard cần điểm KPI tháng và drilldown task quá hạn.", "teamswork-kpi-plan.txt", "imported", user_ids["phuc.tran@teamswork.example.com"], _iso_date("2026-08-04", 11), _iso_date("2026-08-05", 16), "Đã import các task lõi của KPI dashboard.", None, user_ids["phuc.tran@teamswork.example.com"], _iso_date("2026-08-03", 9)),
        ("text", "Checklist sẵn sàng demo được tạo từ tài liệu RAG và ghi chú UAT.", "demo-readiness-rag-import.txt", "imported", user_ids["phuc.tran@teamswork.example.com"], _iso_date("2026-08-08", 14), _iso_date("2026-08-08", 15), "Đã import checklist demo từ ngữ cảnh RAG.", "Gộp task bằng chứng QA bị trùng trước khi import.", user_ids["mai.bui@teamswork.example.com"], _iso_date("2026-08-08", 13)),
    ]
    generated = [
        {"title": "Phân rã yêu cầu thương mại di động", "description": "Tạo backlog cho luồng mua hàng trên mobile.", "story_points": 3, "difficulty": "medium", "deadline_offset_days": 7, "rationale": "Làm rõ phạm vi", "selected": True},
        {"title": "Rà soát luồng đồng bộ offline", "description": "Kiểm tra xung đột dữ liệu và hành vi retry.", "story_points": 5, "difficulty": "hard", "deadline_offset_days": 10, "rationale": "Giảm rủi ro hiện trường", "selected": True},
        {"title": "Import task KPI dashboard", "description": "Tạo task cho điểm KPI và drilldown task quá hạn.", "story_points": 5, "difficulty": "hard", "deadline_offset_days": 8, "rationale": "Quan trọng cho demo", "selected": True},
        {"title": "Chuẩn bị checklist sẵn sàng demo", "description": "Tạo task cho diễn tập kịch bản, bằng chứng kiểm thử và bàn giao stakeholder.", "story_points": 3, "difficulty": "medium", "deadline_offset_days": 5, "rationale": "Import từ ghi chú UAT có hỗ trợ RAG", "selected": True},
    ]
    rows = []
    for item in generated:
        item.setdefault("type", "dashboard" if "dashboard" in item["title"].lower() else "implementation")
        item.setdefault("business_goal", f"Demo-ready work package for {item['title']}.")
        item.setdefault("subtasks", ["Clarify scope", "Implement core workflow", "Prepare review evidence"])
        item.setdefault("acceptance_criteria", ["Manager can review the outcome", "Selected task can be imported safely"])
        item.setdefault("data_requirements", ["AI draft JSON", "Project context", "Assigned user"])
        item.setdefault("ui_components", ["AI draft review drawer", "Task detail drawer"])
        item.setdefault("test_cases", ["Validate happy path", "Validate empty-state behavior"])
        item.setdefault("dependencies", ["Manager approval"])
        item.setdefault("risks", ["Scope may need final review before import"])
        item.setdefault("demo_value", "Shows AI-generated work packages with reviewable implementation details.")
        item.setdefault("suggested_role", "Manager")
    for idx, draft in enumerate(drafts):
        rows.append((*draft[:3], json.dumps([generated[idx]], ensure_ascii=True), *draft[3:]))
    conn.executemany(
        """
        INSERT INTO ai_task_drafts
        (source_type, source_summary, source_name, generated_tasks, status, reviewer_id, reviewed_at, imported_at, review_note, edit_reason, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    docs = [
        ("Tóm tắt dự án TeamsWork", "teamswork-brief", "TeamsWork Internal PM & KPI", "TeamsWork tập trung vào theo dõi sprint, tính KPI, phân quyền RBAC, phân rã task bằng AI và báo cáo thông báo cho quản trị nội bộ."),
        ("Yêu cầu thương mại di động", "shopmate-requirements", "ShopMate Mobile Commerce", "Ứng dụng ShopMate gồm đăng nhập hồ sơ, danh mục sản phẩm, giỏ hàng thanh toán, theo dõi đơn, voucher tích điểm, push notification và API đồng bộ admin."),
        ("Luồng SLA FieldOps", "fieldops-sla", "FieldOps Service Mobile", "FieldOps hỗ trợ phân công ticket, luồng kỹ thuật viên, GPS check-in, đồng bộ offline, tải ảnh nghiệm thu và dashboard SLA."),
        ("Checklist sẵn sàng demo và UAT", "demo-readiness-checklist", "TeamsWork Internal PM & KPI", "Sẵn sàng demo cần có kịch bản trình bày, comment đã seed, bằng chứng AI import có hỗ trợ RAG, ảnh chụp KPI tháng 06 07 08, drilldown task quá hạn và ghi chú ký duyệt UAT."),
    ]
    for title, source, project_name, content in docs:
        cursor = conn.execute(
            """
            INSERT INTO rag_documents (title, source_label, project_id, storage_path, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, source, project_ids[project_name], None, user_ids["an.nguyen@teamswork.example.com"], _iso_date("2026-07-10", 9)),
        )
        document_id = int(cursor.lastrowid)
        chunks = [content, f"Ghi chú demo cho {project_name}: dùng tài liệu này làm ngữ cảnh RAG khi phân rã task bằng AI."]
        for chunk_index, chunk in enumerate(chunks):
            chunk_cursor = conn.execute(
                """
                INSERT INTO rag_chunks
                (document_id, content, source_label, chunk_index, char_count, token_estimate, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (document_id, chunk, source, chunk_index, len(chunk), max(1, len(chunk.split())), _iso_date("2026-07-10", 9)),
            )
            embedding_column = "embedding_json" if "embedding_json" in _table_columns(conn, "rag_chunk_embeddings") else "embedding"
            conn.execute(
                f"""
                INSERT INTO rag_chunk_embeddings
                (chunk_id, provider, model, dim, version, {embedding_column}, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (int(chunk_cursor.lastrowid), "demo", "lexical-placeholder", 1536, "v1", None, _iso_date("2026-07-10", 9)),
            )
        conn.execute(
            """
            INSERT INTO rag_document_permissions
            (document_id, project_id, user_id, role_slug, access_level, created_at)
            VALUES (?, ?, NULL, 'manager', 'query', ?)
            """,
            (document_id, project_ids[project_name], _iso_date("2026-07-10", 9)),
        )


def _count(conn: Any, table: str) -> int:
    if not _table_exists(conn, table):
        return 0
    row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
    return int(row["c"] if row else 0)


def _summary_counts(conn: Any) -> dict[str, int]:
    tables = (
        "users",
        "departments",
        "projects",
        "sprints",
        "project_members",
        "tasks",
        "sprint_capacity_plans",
        "project_risks",
        "weekly_status_updates",
        "kpi_adjustments",
        "task_comments",
        "app_notifications",
        "notification_queue",
        "audit_logs",
        "ai_task_drafts",
        "rag_documents",
        "rag_chunks",
    )
    return {table: _count(conn, table) for table in tables}


def _placeholders(values: tuple[Any, ...] | list[Any]) -> str:
    return ", ".join("?" for _ in values)


def _validate_seed_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in {"upsert", "reset"}:
        raise ValueError("mode must be 'upsert' or 'reset'")
    return normalized


def _ensure_reset_allowed(force: bool) -> None:
    if force:
        return
    if settings.app_env not in RESET_ALLOWED_ENVS:
        raise RuntimeError(
            "Refusing demo seed reset outside local/dev/demo/test. "
            "Pass force=True only for an explicitly approved non-production reset."
        )


def _select_ids(conn: Any, table: str, where_sql: str, params: tuple[Any, ...]) -> list[int]:
    if not _table_exists(conn, table):
        return []
    rows = conn.execute(f"SELECT id FROM {table} WHERE {where_sql}", params).fetchall()
    return [int(row["id"]) for row in rows]


def _delete_by_ids(conn: Any, table: str, ids: list[int]) -> None:
    if not ids or not _table_exists(conn, table):
        return
    conn.execute(f"DELETE FROM {table} WHERE id IN ({_placeholders(ids)})", tuple(ids))


def _delete_full_demo_rag(conn: Any, project_ids: list[int] | None = None) -> None:
    if not _table_exists(conn, "rag_documents"):
        return
    source_params = tuple(FULL_DEMO_RAG_SOURCE_LABELS)
    clauses = [f"source_label IN ({_placeholders(source_params)})"]
    params: list[Any] = list(source_params)
    if project_ids:
        clauses.append(f"project_id IN ({_placeholders(project_ids)})")
        params.extend(project_ids)
        if _table_exists(conn, "rag_document_permissions"):
            conn.execute(
                f"DELETE FROM rag_document_permissions WHERE project_id IN ({_placeholders(project_ids)})",
                tuple(project_ids),
            )
    doc_ids = _select_ids(conn, "rag_documents", " OR ".join(clauses), tuple(params))
    if not doc_ids:
        return
    chunk_ids = _select_ids(conn, "rag_chunks", f"document_id IN ({_placeholders(doc_ids)})", tuple(doc_ids))
    if chunk_ids and _table_exists(conn, "rag_chunk_embeddings"):
        conn.execute(f"DELETE FROM rag_chunk_embeddings WHERE chunk_id IN ({_placeholders(chunk_ids)})", tuple(chunk_ids))
    if _table_exists(conn, "rag_document_permissions"):
        conn.execute(f"DELETE FROM rag_document_permissions WHERE document_id IN ({_placeholders(doc_ids)})", tuple(doc_ids))
    if chunk_ids:
        conn.execute(f"DELETE FROM rag_chunks WHERE id IN ({_placeholders(chunk_ids)})", tuple(chunk_ids))
    conn.execute(f"DELETE FROM rag_documents WHERE id IN ({_placeholders(doc_ids)})", tuple(doc_ids))


def _delete_full_demo_project_children(conn: Any, project_ids: dict[str, int]) -> None:
    ids = list(project_ids.values())
    if not ids:
        return
    _delete_full_demo_rag(conn, ids)
    task_ids = _select_ids(conn, "tasks", f"project_id IN ({_placeholders(ids)})", tuple(ids))
    sprint_ids = _select_ids(conn, "sprints", f"project_id IN ({_placeholders(ids)})", tuple(ids))
    if task_ids and _table_exists(conn, "task_comments"):
        conn.execute(f"DELETE FROM task_comments WHERE task_id IN ({_placeholders(task_ids)})", tuple(task_ids))
    if task_ids and _table_exists(conn, "app_notifications"):
        conn.execute(
            f"DELETE FROM app_notifications WHERE entity_type = 'task' AND entity_id IN ({_placeholders(task_ids)})",
            tuple(task_ids),
        )
    if task_ids and _table_exists(conn, "task_ai_details"):
        conn.execute(f"DELETE FROM task_ai_details WHERE task_id IN ({_placeholders(task_ids)})", tuple(task_ids))
    _delete_by_ids(conn, "tasks", task_ids)
    if sprint_ids and _table_exists(conn, "sprint_capacity_plans"):
        conn.execute(f"DELETE FROM sprint_capacity_plans WHERE sprint_id IN ({_placeholders(sprint_ids)})", tuple(sprint_ids))
    if _table_exists(conn, "weekly_status_updates"):
        conn.execute(f"DELETE FROM weekly_status_updates WHERE project_id IN ({_placeholders(ids)})", tuple(ids))
    if _table_exists(conn, "project_risks"):
        conn.execute(f"DELETE FROM project_risks WHERE project_id IN ({_placeholders(ids)})", tuple(ids))
    if _table_exists(conn, "project_members"):
        conn.execute(f"DELETE FROM project_members WHERE project_id IN ({_placeholders(ids)})", tuple(ids))
    _delete_by_ids(conn, "sprints", sprint_ids)


def _delete_full_demo_global_children(conn: Any) -> None:
    if _table_exists(conn, "kpi_adjustments"):
        conn.execute("DELETE FROM kpi_adjustments WHERE reason LIKE ?", (f"%[{DEMO_NAMESPACE}]%",))
    if _table_exists(conn, "ai_task_drafts"):
        if _table_exists(conn, "task_ai_details"):
            conn.execute(
                f"""
                DELETE FROM task_ai_details
                WHERE source_ai_draft_id IN (
                    SELECT id FROM ai_task_drafts WHERE source_name IN ({_placeholders(FULL_DEMO_AI_SOURCE_NAMES)})
                )
                """,
                FULL_DEMO_AI_SOURCE_NAMES,
            )
        conn.execute(
            f"DELETE FROM ai_task_drafts WHERE source_name IN ({_placeholders(FULL_DEMO_AI_SOURCE_NAMES)})",
            FULL_DEMO_AI_SOURCE_NAMES,
        )
    if _table_exists(conn, "audit_logs"):
        conn.execute("DELETE FROM audit_logs WHERE detail LIKE ?", (f"%[{DEMO_NAMESPACE}]%",))
    if _table_exists(conn, "notification_queue"):
        conn.execute("DELETE FROM notification_queue WHERE payload LIKE ?", (f"%{DEMO_NAMESPACE}%",))


def _full_demo_project_ids(conn: Any) -> dict[str, int]:
    rows = conn.execute(
        f"SELECT id, name FROM projects WHERE name IN ({_placeholders(DEMO_PROJECT_NAMES)})",
        DEMO_PROJECT_NAMES,
    ).fetchall()
    return {str(row["name"]): int(row["id"]) for row in rows}


def _upsert_full_demo_departments(conn: Any) -> dict[str, int]:
    columns = _table_columns(conn, "departments")
    for name, code, description in FULL_DEMO_DEPARTMENTS:
        if {"description", "is_active"}.issubset(columns):
            conn.execute(
                """
                /* no-returning-id */ INSERT INTO departments (name, code, description, is_active, created_at)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    is_active = 1
                """,
                (name, code, description, DEMO_NOW_ISO),
            )
        else:
            conn.execute(
                """
                /* no-returning-id */ INSERT INTO departments (name, code, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET name = excluded.name
                """,
                (name, code, DEMO_NOW_ISO),
            )
    rows = conn.execute("SELECT id, code FROM departments").fetchall()
    return {str(row["code"]): int(row["id"]) for row in rows}


def _upsert_full_demo_users(conn: Any, department_ids: dict[str, int]) -> dict[str, int]:
    for full_name, email, role, role_id, department_code, position, password in FULL_DEMO_USERS:
        department_id = department_ids[department_code]
        department_name = conn.execute("SELECT name FROM departments WHERE id = ?", (department_id,)).fetchone()["name"]
        existing = conn.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email.lower(),)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE users
                SET full_name = ?, role = ?, role_id = ?, department = ?, department_id = ?,
                    position = ?, password_hash = COALESCE(password_hash, ?), is_active = 1, updated_at = ?
                WHERE id = ?
                """,
                (
                    full_name,
                    role,
                    role_id,
                    department_name,
                    department_id,
                    position,
                    hash_password(password),
                    DEMO_NOW_ISO,
                    existing["id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO users
                (full_name, email, aad_object_id, role, department, password_hash, role_id, department_id, position, avatar_url, is_active, created_at, updated_at)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, NULL, 1, ?, ?)
                """,
                (
                    full_name,
                    email.lower(),
                    role,
                    department_name,
                    hash_password(password),
                    role_id,
                    department_id,
                    position,
                    DEMO_NOW_ISO,
                    DEMO_NOW_ISO,
                ),
            )
    _assign_demo_department_managers(conn)
    rows = conn.execute(
        f"SELECT id, email FROM users WHERE LOWER(email) IN ({_placeholders(FULL_DEMO_USER_EMAILS)})",
        tuple(email.lower() for email in FULL_DEMO_USER_EMAILS),
    ).fetchall()
    return {str(row["email"]).lower(): int(row["id"]) for row in rows}


def _assign_demo_department_managers(conn: Any) -> None:
    if "manager_user_id" not in _table_columns(conn, "departments"):
        return
    manager_by_department = {
        "ADM": "an.nguyen@teamswork.example.com",
        "PMO": "phuc.tran@teamswork.example.com",
        "PBA": "linh.vo@teamswork.example.com",
        "UXD": "mai.bui@teamswork.example.com",
        "WEB": "phuc.tran@teamswork.example.com",
        "MOB": "ha.le@teamswork.example.com",
        "QA": "yen.ho@teamswork.example.com",
        "OPS": "bao.pham@teamswork.example.com",
        "HR": "vy.mai@teamswork.example.com",
        "AUD": "auditor@teamswork.local",
    }
    for code, email in manager_by_department.items():
        row = conn.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email.lower(),)).fetchone()
        if row:
            conn.execute("UPDATE departments SET manager_user_id = ? WHERE code = ?", (int(row["id"]), code))


def _upsert_full_demo_projects(conn: Any, department_ids: dict[str, int], user_ids: dict[str, int]) -> dict[str, int]:
    descriptions = {
        "TeamsWork Internal PM & KPI": (
            f"[{DEMO_NAMESPACE}] Internal QLDA/TeamsWork demo project for RBAC, KPI dashboard, "
            "project progress, sprint review, AI task draft, Teams notification and overdue task workflows."
        ),
        "ShopMate Mobile Commerce": (
            f"[{DEMO_NAMESPACE}] Mobile commerce delivery project for requirements, UAT, cart, order tracking, "
            "voucher, push notification and sprint review demo scenarios."
        ),
        "FieldOps Service Mobile": (
            f"[{DEMO_NAMESPACE}] Field service mobile project for offline sync, GPS check-in, photo evidence, "
            "SLA dashboard, risk mitigation and project progress tracking."
        ),
    }
    for project in PROJECTS:
        name = str(project["name"])
        existing = conn.execute("SELECT id FROM projects WHERE name = ?", (name,)).fetchone()
        params = (
            descriptions[name],
            department_ids[str(project["department_code"])],
            user_ids[str(project["manager_email"]).lower()],
            project["start"],
            project["end"],
            "active",
            DEMO_NOW_ISO,
        )
        if existing:
            conn.execute(
                """
                UPDATE projects
                SET description = ?, department_id = ?, manager_id = ?, start_date = ?, end_date = ?,
                    status = ?, created_at = ?
                WHERE id = ?
                """,
                (*params, int(existing["id"])),
            )
        else:
            conn.execute(
                """
                INSERT INTO projects
                (name, description, department_id, manager_id, start_date, end_date, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, *params),
            )
    return _full_demo_project_ids(conn)


def _seed_full_demo_kpi_adjustments(conn: Any, user_ids: dict[str, int]) -> None:
    rows = (
        ("kiet.do@teamswork.example.com", "2026-06", 5.0, "Supported urgent RBAC release"),
        ("quan.pham@teamswork.example.com", "2026-07", -3.0, "Missed project progress update"),
        ("long.nguyen@teamswork.example.com", "2026-07", 8.0, "Resolved production-style demo blocker"),
        ("giabao.nguyen@teamswork.example.com", "2026-08", -5.0, "Overdue task was not escalated"),
        ("yen.ho@teamswork.example.com", "2026-08", 4.0, "Extra QA regression support"),
    )
    admin_id = user_ids["an.nguyen@teamswork.example.com"]
    conn.executemany(
        """
        INSERT INTO kpi_adjustments (user_id, month, points, reason, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (user_ids[email], month, points, f"[{DEMO_NAMESPACE}] {reason}", admin_id, _iso_date(f"{month}-28", 17))
            for email, month, points, reason in rows
        ],
    )


def _seed_full_demo_notifications_comments_audit(conn: Any, user_ids: dict[str, int], project_ids: dict[str, int]) -> None:
    tasks = conn.execute(
        f"""
        SELECT t.id, t.title, t.assignee_id, t.status, t.deadline, p.name AS project_name, s.name AS sprint_name
        FROM tasks t
        JOIN projects p ON p.id = t.project_id
        LEFT JOIN sprints s ON s.id = t.sprint_id
        WHERE p.name IN ({_placeholders(DEMO_PROJECT_NAMES)})
        ORDER BY t.id
        """,
        DEMO_PROJECT_NAMES,
    ).fetchall()
    if not tasks:
        return
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
        project_name = str(task["project_name"])
        sprint_name = str(task["sprint_name"] or "unplanned sprint")
        comments.append(
            (
                task_id,
                comment_authors[idx % len(comment_authors)],
                f"[{DEMO_NAMESPACE}] {project_name} / {sprint_name}: PM reviewed task '{title}' for sprint review and project progress.",
                _iso_date(f"2026-08-{1 + (idx % 9):02d}", 9 + (idx % 4)),
            )
        )
        comments.append(
            (
                task_id,
                comment_authors[(idx + 1) % len(comment_authors)],
                f"[{DEMO_NAMESPACE}] QA and BA notes for '{title}': confirm UAT evidence, overdue task risk and acceptance criteria.",
                _iso_date(f"2026-08-{1 + (idx % 9):02d}", 13 + (idx % 4)),
            )
        )
        if idx % 2 == 0:
            comments.append(
                (
                    task_id,
                    comment_authors[(idx + 2) % len(comment_authors)],
                    f"[{DEMO_NAMESPACE}] Teams notification follow-up for '{title}' is ready for manager and member visibility demo.",
                    _iso_date(f"2026-08-{2 + (idx % 8):02d}", 16),
                )
            )
    conn.executemany(
        "INSERT INTO task_comments (task_id, author_user_id, body, created_at) VALUES (?, ?, ?, ?)",
        comments,
    )
    notifications = []
    notification_types = ("task_status_changed", "task_comment", "task_due_soon", "task_overdue")
    for idx, task in enumerate(tasks[:12]):
        notifications.append(
            (
                int(task["assignee_id"]),
                notification_types[idx % len(notification_types)],
                "TeamsWork demo task update",
                f"[{DEMO_NAMESPACE}] Task '{task['title']}' needs attention for project progress, sprint review or overdue task handling.",
                "task",
                int(task["id"]),
                idx % 5 == 0,
                _iso_date(f"2026-08-{1 + (idx % 9):02d}", 10),
                _iso_date(f"2026-08-{1 + (idx % 9):02d}", 11) if idx % 5 == 0 else None,
            )
        )
    conn.executemany(
        """
        INSERT INTO app_notifications
        (user_id, type, title, message, entity_type, entity_id, is_read, created_at, read_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        notifications,
    )
    queue_rows = (
        ("phuc.tran@teamswork.example.com", "queued", 0, None, None),
        ("ha.le@teamswork.example.com", "sent", 1, None, _iso_date("2026-08-08", 8)),
        ("bao.pham@teamswork.example.com", "failed", 3, "Demo Teams webhook is intentionally not configured", _iso_date("2026-08-07", 8)),
        ("yen.ho@teamswork.example.com", "queued", 0, None, None),
        ("vy.mai@teamswork.example.com", "queued", 0, None, None),
    )
    conn.executemany(
        """
        INSERT INTO notification_queue
        (user_id, channel, payload, status, attempts, max_attempts, last_error, next_retry_at, created_at, sent_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                user_ids[email],
                "teams",
                json.dumps(
                    {
                        "demo_namespace": DEMO_NAMESPACE,
                        "message": "Demo Teams notification for KPI dashboard, overdue task and sprint review.",
                    },
                    ensure_ascii=True,
                ),
                status,
                attempts,
                3,
                last_error,
                None,
                _iso_date("2026-08-09", 8),
                sent_at,
            )
            for email, status, attempts, last_error, sent_at in queue_rows
        ],
    )
    audit_rows = [
        (user_ids["an.nguyen@teamswork.example.com"], "seed_full_demo", "system", None, f"[{DEMO_NAMESPACE}] Upserted demo seed data", DEMO_NOW_ISO),
        (user_ids["phuc.tran@teamswork.example.com"], "review_project_progress", "project", project_ids["TeamsWork Internal PM & KPI"], f"[{DEMO_NAMESPACE}] Reviewed KPI dashboard project progress", _iso_date("2026-08-08", 15)),
        (user_ids["ha.le@teamswork.example.com"], "review_uat", "project", project_ids["ShopMate Mobile Commerce"], f"[{DEMO_NAMESPACE}] Reviewed UAT notes and sprint review", _iso_date("2026-08-08", 16)),
        (user_ids["bao.pham@teamswork.example.com"], "mitigate_risk", "project", project_ids["FieldOps Service Mobile"], f"[{DEMO_NAMESPACE}] Updated risk mitigation plan", _iso_date("2026-08-08", 17)),
    ]
    conn.executemany(
        "INSERT INTO audit_logs (actor_user_id, action, entity, entity_id, detail, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        audit_rows,
    )


def _seed_full_demo_ai_drafts(conn: Any, user_ids: dict[str, int]) -> None:
    generated = [
        {"title": "Prepare KPI dashboard drilldown", "description": "Show monthly KPI, overdue task and adjustment detail.", "story_points": 5, "difficulty": "hard", "deadline_offset_days": 7, "selected": True},
        {"title": "Run UAT sprint review checklist", "description": "Collect UAT evidence and sprint review notes.", "story_points": 3, "difficulty": "medium", "deadline_offset_days": 5, "selected": True},
    ]
    rows = (
        ("text", "KPI dashboard needs project progress, overdue task and member drilldown.", FULL_DEMO_AI_SOURCE_NAMES[0], "draft", None, None, None, None, None, "phuc.tran@teamswork.example.com"),
        ("text", "UAT notes mention sprint review, RBAC role permission and Teams notification acceptance.", FULL_DEMO_AI_SOURCE_NAMES[1], "reviewed", "phuc.tran@teamswork.example.com", _iso_date("2026-08-07", 14), None, "Reviewed for Sprint 5.", None, "mai.bui@teamswork.example.com"),
        ("text", "ShopMate requirements include voucher, cart, order tracking and push notification.", FULL_DEMO_AI_SOURCE_NAMES[2], "imported", "ha.le@teamswork.example.com", _iso_date("2026-08-04", 13), _iso_date("2026-08-05", 10), "Imported core stories.", None, "ha.le@teamswork.example.com"),
        ("text", "FieldOps offline sync requires retry, conflict handling and SLA dashboard tasks.", FULL_DEMO_AI_SOURCE_NAMES[3], "reviewed", "bao.pham@teamswork.example.com", _iso_date("2026-08-05", 13), None, "Split offline sync work.", "Separated risk task.", "linh.vo@teamswork.example.com"),
        ("text", "RBAC permission matrix covers admin, manager, member, HR and auditor read-only scenarios.", FULL_DEMO_AI_SOURCE_NAMES[4], "draft", None, None, None, None, None, "an.nguyen@teamswork.example.com"),
        ("text", "Risk log requires mitigation tasks for overdue work and UAT blocker escalation.", FULL_DEMO_AI_SOURCE_NAMES[5], "imported", "bao.pham@teamswork.example.com", _iso_date("2026-08-06", 13), _iso_date("2026-08-06", 16), "Imported mitigation tasks.", None, "bao.pham@teamswork.example.com"),
    )
    conn.executemany(
        """
        INSERT INTO ai_task_drafts
        (source_type, source_summary, source_name, generated_tasks, status, reviewer_id, reviewed_at, imported_at, review_note, edit_reason, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                source_type,
                summary,
                source_name,
                json.dumps(generated, ensure_ascii=True),
                status,
                user_ids[reviewer] if reviewer else None,
                reviewed_at,
                imported_at,
                review_note,
                edit_reason,
                user_ids[created_by],
                _iso_date("2026-08-03", 9),
            )
            for source_type, summary, source_name, status, reviewer, reviewed_at, imported_at, review_note, edit_reason, created_by in rows
        ],
    )


def _rag_demo_documents() -> tuple[tuple[str, str, str, str], ...]:
    project_specs = (
        ("TeamsWork Internal PM & KPI", "teamswork", "KPI dashboard, RBAC, project progress, Teams notification"),
        ("ShopMate Mobile Commerce", "shopmate", "UAT, sprint review, mobile requirements, Teams notification"),
        ("FieldOps Service Mobile", "fieldops", "risk mitigation, overdue task, offline sync, project progress"),
    )
    docs: list[tuple[str, str, str, str]] = []
    for project_name, slug, focus in project_specs:
        docs.extend(
            (
                (project_name, f"{slug}-brief", f"{project_name} demo brief", _build_rag_demo_content(project_name, focus, "brief")),
                (project_name, f"{slug}-requirements", f"{project_name} requirements and role permissions", _build_rag_demo_content(project_name, focus, "requirements")),
                (project_name, f"{slug}-uat-notes", f"{project_name} sprint and UAT notes", _build_rag_demo_content(project_name, focus, "uat-notes")),
                (project_name, f"{slug}-risk-decisions", f"{project_name} risk and decision log", _build_rag_demo_content(project_name, focus, "risk-decisions")),
            )
        )
    return tuple(docs)


def _build_rag_demo_content(project_name: str, focus: str, doc_type: str) -> str:
    query_bank = (
        "Member có thể xem những chức năng nào? Member có thể xem task, notification, KPI cá nhân và RAG project context. "
        "Manager theo dõi tiến độ task của team như thế nào? Manager theo dõi project progress, sprint review, overdue task và Teams notification. "
        "Admin quản lý người dùng và phòng ban như thế nào? Admin quản lý users, departments, RBAC role permission và audit log. "
        "KPI được tính như thế nào? KPI được tính từ done on-time, done late, overdue task, story_points, difficulty và kpi_adjustments. "
        "Dự án demo hiện tại có những sprint/task nào? Dự án demo có completed sprint, active sprint, planned sprint, todo task, doing task và done task. "
        "Khi task bị quá hạn thì xử lý thế nào? Khi overdue task xảy ra, member cập nhật blocker, manager tạo risk mitigation và Teams notification nhắc owner. "
        "Auditor có quyền xem gì? Auditor xem audit log, report read-only, project progress và evidence. "
        "HR có thể xem KPI nhân sự không? HR có thể xem KPI nhân sự, department report và team performance. "
    )
    shared = (
        f"{project_name} {doc_type} [{DEMO_NAMESPACE}]. "
        "Member có thể xem task được giao, project mà mình là project member, notification liên quan, "
        "RAG project context được cấp quyền và KPI cá nhân khi RBAC role permission cho phép. "
        "Manager theo dõi tiến độ task của team qua project progress, sprint review, overdue task, workload, "
        "weekly RAG status Red Amber Green và Teams notification. "
        "Admin quản lý người dùng, phòng ban, role permission, RBAC, audit log và dữ liệu seed demo. "
        "HR có thể xem KPI nhân sự, department, team report và adjustment hợp lệ; HR không cần project membership để xem báo cáo tổng quan. "
        "Auditor có quyền xem audit log, report read-only, project progress và evidence, nhưng không tạo hoặc sửa task. "
        "KPI được tính từ task done on-time, done late, overdue task chưa hoàn thành, story_points, difficulty và kpi_adjustments positive hoặc negative. "
        "Khi task bị quá hạn, member cập nhật blocker, manager review risk mitigation, QA xác nhận impact, và Teams notification nhắc owner. "
    )
    project_detail = (
        f"Focus keywords: {focus}. "
        "The demo data includes completed, active and planned sprint records, todo doing done tasks, due soon tasks, "
        "done late tasks, done on-time tasks, UAT notes, risk mitigation actions and decision log entries. "
        "Use this document for lexical fallback queries without a real embedding provider. "
    )
    return " ".join([query_bank, shared, project_detail, query_bank, shared, project_detail, query_bank])


def _seed_rag_documents_with_conn(conn: Any, project_ids: dict[str, int], user_ids: dict[str, int]) -> list[int]:
    _delete_full_demo_rag(conn, list(project_ids.values()))
    created_chunk_ids: list[int] = []
    admin_id = user_ids["an.nguyen@teamswork.example.com"]
    for project_name, source_label, title, content in _rag_demo_documents():
        chunks = chunk_text(content)
        cursor = conn.execute(
            """
            INSERT INTO rag_documents (title, source_label, project_id, storage_path, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, source_label, project_ids[project_name], None, admin_id, DEMO_NOW_ISO),
        )
        document_id = int(cursor.lastrowid)
        for chunk_index, chunk in enumerate(chunks):
            chunk_cursor = conn.execute(
                """
                INSERT INTO rag_chunks
                (document_id, content, source_label, chunk_index, char_count, token_estimate, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    chunk.content,
                    source_label,
                    chunk_index,
                    chunk.char_count,
                    chunk.token_estimate,
                    DEMO_NOW_ISO,
                ),
            )
            chunk_id = int(chunk_cursor.lastrowid)
            created_chunk_ids.append(chunk_id)
            embedding_column = "embedding_json" if "embedding_json" in _table_columns(conn, "rag_chunk_embeddings") else "embedding"
            conn.execute(
                f"""
                INSERT INTO rag_chunk_embeddings
                (chunk_id, provider, model, dim, version, {embedding_column}, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (chunk_id, "demo", "lexical-placeholder", 1536, "v1", None, DEMO_NOW_ISO),
            )
        conn.execute(
            """
            INSERT INTO rag_document_permissions
            (document_id, project_id, user_id, role_slug, access_level, created_at)
            VALUES (?, ?, NULL, NULL, 'query', ?)
            """,
            (document_id, project_ids[project_name], DEMO_NOW_ISO),
        )
    return created_chunk_ids


def _try_store_seed_embeddings(chunk_ids: list[int]) -> list[str]:
    warnings: list[str] = []
    provider = get_embedding_provider()
    if provider is None or not pgvector_enabled():
        return warnings
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT id, content FROM rag_chunks WHERE id IN ({_placeholders(chunk_ids)})",
            tuple(chunk_ids),
        ).fetchall() if chunk_ids else []
    for row in rows:
        try:
            embedding = provider.embed(str(row["content"]))
            store_rag_chunk_embedding(
                chunk_id=int(row["id"]),
                provider=provider.provider,
                model=provider.model,
                dim=provider.dim,
                version=provider.version,
                embedding=embedding,
            )
        except Exception as exc:
            warnings.append(f"Embedding failed for chunk {row['id']}: {exc}")
            break
    return warnings


def seed_rag_demo_data(mode: str = "upsert", force: bool = False) -> dict:
    normalized_mode = _validate_seed_mode(mode)
    if normalized_mode == "reset":
        _ensure_reset_allowed(force)
    with get_connection() as conn:
        department_ids = _upsert_full_demo_departments(conn)
        user_ids = _upsert_full_demo_users(conn, department_ids)
        project_ids = _upsert_full_demo_projects(conn, department_ids, user_ids)
        chunk_ids = _seed_rag_documents_with_conn(conn, project_ids, user_ids)
        counts = _summary_counts(conn)
    warnings = _try_store_seed_embeddings(chunk_ids)
    with get_connection() as conn:
        counts = _summary_counts(conn)
    return {
        "message": "RAG demo data seeded",
        "mode": normalized_mode,
        "demo_namespace": DEMO_NAMESPACE,
        "demo_now": DEMO_NOW_ISO,
        "warnings": warnings,
        "counts": counts,
    }


def seed_full_demo_data(mode: str = "upsert", force: bool = False) -> dict:
    normalized_mode = _validate_seed_mode(mode)
    if normalized_mode == "reset":
        _ensure_reset_allowed(force)
    with get_connection() as conn:
        department_ids = _upsert_full_demo_departments(conn)
        user_ids = _upsert_full_demo_users(conn, department_ids)
        project_ids = _upsert_full_demo_projects(conn, department_ids, user_ids)
        _delete_full_demo_project_children(conn, project_ids)
        _delete_full_demo_global_children(conn)
        if normalized_mode == "reset":
            conn.execute(
                f"DELETE FROM projects WHERE name IN ({_placeholders(DEMO_PROJECT_NAMES)})",
                DEMO_PROJECT_NAMES,
            )
            project_ids = _upsert_full_demo_projects(conn, department_ids, user_ids)
        sprint_ids = seed_sprints(conn, project_ids)
        seed_members(conn, project_ids, user_ids)
        seed_tasks(conn, project_ids, sprint_ids, user_ids)
        seed_capacity(conn, project_ids, sprint_ids)
        seed_risks(conn, project_ids, user_ids)
        seed_weekly_updates(conn, project_ids, sprint_ids, user_ids)
        _seed_full_demo_kpi_adjustments(conn, user_ids)
        _seed_full_demo_notifications_comments_audit(conn, user_ids, project_ids)
        _seed_full_demo_ai_drafts(conn, user_ids)
        chunk_ids = _seed_rag_documents_with_conn(conn, project_ids, user_ids)
        counts = _summary_counts(conn)
    warnings = _try_store_seed_embeddings(chunk_ids)
    with get_connection() as conn:
        counts = _summary_counts(conn)
    return {
        "message": "Full demo data seeded",
        "mode": normalized_mode,
        "demo_namespace": DEMO_NAMESPACE,
        "demo_now": DEMO_NOW_ISO,
        "warnings": warnings,
        "counts": counts,
    }


def seed_data() -> dict:
    """Legacy destructive demo reset used by /seed/init and existing tests."""
    with get_connection() as conn:
        reset_demo_data(conn)
        department_ids = seed_departments(conn)
        user_ids = seed_users(conn)
        project_ids = seed_projects(conn, department_ids, user_ids)
        sprint_ids = seed_sprints(conn, project_ids)
        seed_members(conn, project_ids, user_ids)
        seed_tasks(conn, project_ids, sprint_ids, user_ids)
        seed_capacity(conn, project_ids, sprint_ids)
        seed_risks(conn, project_ids, user_ids)
        seed_weekly_updates(conn, project_ids, sprint_ids, user_ids)
        seed_kpi_adjustments(conn, user_ids)
        seed_notifications_comments_audit(conn, user_ids)
        seed_ai_and_rag(conn, project_ids, user_ids)
        counts = _summary_counts(conn)
    return {
        "message": "Demo data reset and seeded",
        "demo_now": DEMO_NOW_ISO,
        "counts": counts,
    }
