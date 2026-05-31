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

__all__ = [name for name in globals() if not name.startswith("__")]
