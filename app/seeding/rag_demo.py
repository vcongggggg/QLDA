from app.seeding.shared import *

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
