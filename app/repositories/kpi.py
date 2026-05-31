from app.repositories.shared import *

def create_kpi_adjustment(
    user_id: int,
    month: str,
    points: float,
    reason: str,
    created_by: int,
    status: str = "approved",
    reviewer_id: int | None = None,
    reviewed_at: str | None = None,
    review_reason: str | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO kpi_adjustments
            (user_id, month, points, reason, created_by, created_at, status, reviewer_id, reviewed_at, review_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, month, points, reason, created_by, _now_iso(), status, reviewer_id, reviewed_at, review_reason),
        )
        item_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM kpi_adjustments WHERE id = ?", (item_id,)).fetchone()
    return dict(row)


def list_kpi_adjustments_by_month(month: str, approved_only: bool = True) -> list[dict[str, Any]]:
    with get_connection() as conn:
        status_filter = "AND ka.status = 'approved'" if approved_only else ""
        rows = conn.execute(
            f"""
            SELECT ka.*, u.full_name AS user_name
            FROM kpi_adjustments ka
            JOIN users u ON u.id = ka.user_id
            WHERE ka.month = ?
            {status_filter}
            ORDER BY ka.id ASC
            """,
            (month,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_kpi_adjustment(adjustment_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM kpi_adjustments WHERE id = ?", (adjustment_id,)).fetchone()
    return dict(row) if row else None


def review_kpi_adjustment(adjustment_id: int, status: str, reviewer_id: int, review_reason: str) -> dict[str, Any] | None:
    reviewed_at = _now_iso()
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM kpi_adjustments WHERE id = ?", (adjustment_id,)).fetchone()
        if not existing:
            return None
        conn.execute(
            """
            UPDATE kpi_adjustments
            SET status = ?, reviewer_id = ?, reviewed_at = ?, review_reason = ?
            WHERE id = ?
            """,
            (status, reviewer_id, reviewed_at, review_reason, adjustment_id),
        )
        row = conn.execute("SELECT * FROM kpi_adjustments WHERE id = ?", (adjustment_id,)).fetchone()
    return dict(row) if row else None


def get_kpi_policy() -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM kpi_policies ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def save_kpi_policy(
    difficulty_multiplier: dict[str, float],
    on_time_points: float,
    late_points: float,
    overdue_unfinished_points: float,
    fallback_difficulty: str,
    change_reason: str,
    updated_by: int,
) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO kpi_policies
            (difficulty_multiplier, on_time_points, late_points, overdue_unfinished_points, fallback_difficulty, change_reason, updated_by, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                json.dumps(difficulty_multiplier, ensure_ascii=True, sort_keys=True),
                on_time_points,
                late_points,
                overdue_unfinished_points,
                fallback_difficulty,
                change_reason,
                updated_by,
                _now_iso(),
            ),
        )
        row = conn.execute("SELECT * FROM kpi_policies WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def _kpi_month_from_deadline(deadline: str) -> str:
    return str(deadline)[:7]


def _kpi_task_event(task: dict[str, Any], policy: Any) -> dict[str, Any] | None:
    deadline = str(task.get("deadline") or "")
    if len(deadline) < 7:
        return None
    month = _kpi_month_from_deadline(deadline)
    difficulty = task.get("difficulty") or getattr(policy, "fallback_difficulty", "easy")
    multiplier = policy.multiplier_for(str(difficulty))
    status = str(task.get("status") or "")
    completed_at = task.get("completed_at")
    if status == "done" and completed_at:
        if str(completed_at) <= deadline:
            points = float(policy.on_time_points) * multiplier
            reason = "done_on_time"
        else:
            points = float(policy.late_points) * multiplier
            reason = "done_late"
    elif status != "done":
        points = float(policy.overdue_unfinished_points) * multiplier
        reason = "overdue_unfinished"
    else:
        return None
    return {
        "event_key": f"task:{task['id']}:{month}:{reason}",
        "source_type": "task",
        "source_id": int(task["id"]),
        "user_id": int(task["assignee_id"]),
        "month": month,
        "points": round(points, 2),
        "reason": f"{reason};difficulty={difficulty}",
    }


def _upsert_kpi_transaction(conn: Any, event: dict[str, Any]) -> None:
    existing = conn.execute("SELECT id, status FROM kpi_transactions WHERE event_key = ?", (event["event_key"],)).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE kpi_transactions
            SET source_type = ?, source_id = ?, user_id = ?, month = ?, points = ?, reason = ?,
                status = 'active', reversed_at = NULL
            WHERE event_key = ?
            """,
            (
                event["source_type"],
                event.get("source_id"),
                event["user_id"],
                event["month"],
                event["points"],
                event["reason"],
                event["event_key"],
            ),
        )
        return
    conn.execute(
        """
        INSERT INTO kpi_transactions
        (event_key, source_type, source_id, user_id, month, points, reason, status, created_at, reversed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, NULL)
        """,
        (
            event["event_key"],
            event["source_type"],
            event.get("source_id"),
            event["user_id"],
            event["month"],
            event["points"],
            event["reason"],
            _now_iso(),
        ),
    )


def rebuild_kpi_transactions(month: str, policy: Any) -> dict[str, int]:
    desired_keys: set[str] = set()
    with get_connection() as conn:
        tasks = conn.execute("SELECT * FROM tasks WHERE substr(deadline, 1, 7) = ?", (month,)).fetchall()
        for row in tasks:
            event = _kpi_task_event(dict(row), policy)
            if not event:
                continue
            desired_keys.add(event["event_key"])
            _upsert_kpi_transaction(conn, event)

        adjustments = conn.execute(
            "SELECT * FROM kpi_adjustments WHERE month = ? AND status = 'approved'",
            (month,),
        ).fetchall()
        for row in adjustments:
            adj = dict(row)
            event = {
                "event_key": f"adjustment:{adj['id']}",
                "source_type": "adjustment",
                "source_id": int(adj["id"]),
                "user_id": int(adj["user_id"]),
                "month": month,
                "points": float(adj["points"]),
                "reason": f"manual_adjustment;{adj['reason']}",
            }
            desired_keys.add(event["event_key"])
            _upsert_kpi_transaction(conn, event)

        stale_rows = conn.execute(
            "SELECT event_key FROM kpi_transactions WHERE month = ? AND status = 'active'",
            (month,),
        ).fetchall()
        reversed_count = 0
        for row in stale_rows:
            event_key = str(row["event_key"])
            if event_key not in desired_keys:
                conn.execute(
                    "UPDATE kpi_transactions SET status = 'reversed', reversed_at = ? WHERE event_key = ?",
                    (_now_iso(), event_key),
                )
                reversed_count += 1
        active_count = conn.execute(
            "SELECT COUNT(*) AS c FROM kpi_transactions WHERE month = ? AND status = 'active'",
            (month,),
        ).fetchone()["c"]
    return {"active_count": int(active_count), "reversed_count": reversed_count}


def list_kpi_transactions(month: str, user_id: int | None = None, include_reversed: bool = True) -> list[dict[str, Any]]:
    query = """
        SELECT kt.*, u.full_name AS user_name
        FROM kpi_transactions kt
        JOIN users u ON u.id = kt.user_id
        WHERE kt.month = ?
    """
    params: list[Any] = [month]
    if user_id is not None:
        query += " AND kt.user_id = ?"
        params.append(user_id)
    if not include_reversed:
        query += " AND kt.status = 'active'"
    query += " ORDER BY kt.id ASC"
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def upsert_kpi_target(
    user_id: int,
    month: str,
    target_score: float,
    created_by: int,
    department_id: int | None = None,
    team: str | None = None,
) -> dict[str, Any]:
    now = _now_iso()
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM kpi_targets WHERE user_id = ? AND month = ?", (user_id, month)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE kpi_targets
                SET target_score = ?, department_id = ?, team = ?, updated_at = ?
                WHERE id = ?
                """,
                (target_score, department_id, team, now, existing["id"]),
            )
            target_id = int(existing["id"])
        else:
            cursor = conn.execute(
                """
                INSERT INTO kpi_targets
                (user_id, month, target_score, department_id, team, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, month, target_score, department_id, team, created_by, now, now),
            )
            target_id = int(cursor.lastrowid)
        row = conn.execute(
            """
            SELECT kt.*, u.full_name AS user_name
            FROM kpi_targets kt
            JOIN users u ON u.id = kt.user_id
            WHERE kt.id = ?
            """,
            (target_id,),
        ).fetchone()
    return dict(row)


def update_kpi_target(target_id: int, target_score: float | None = None, department_id: int | None = None, team: str | None = None) -> dict[str, Any] | None:
    with get_connection() as conn:
        current = conn.execute("SELECT * FROM kpi_targets WHERE id = ?", (target_id,)).fetchone()
        if not current:
            return None
        conn.execute(
            """
            UPDATE kpi_targets
            SET target_score = ?, department_id = ?, team = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                float(target_score) if target_score is not None else float(current["target_score"]),
                department_id if department_id is not None else current["department_id"],
                team if team is not None else current["team"],
                _now_iso(),
                target_id,
            ),
        )
        row = conn.execute(
            """
            SELECT kt.*, u.full_name AS user_name
            FROM kpi_targets kt
            JOIN users u ON u.id = kt.user_id
            WHERE kt.id = ?
            """,
            (target_id,),
        ).fetchone()
    return dict(row) if row else None


def list_kpi_targets(month: str | None = None, user_id: int | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT kt.*, u.full_name AS user_name
        FROM kpi_targets kt
        JOIN users u ON u.id = kt.user_id
        WHERE 1=1
    """
    params: list[Any] = []
    if month is not None:
        query += " AND kt.month = ?"
        params.append(month)
    if user_id is not None:
        query += " AND kt.user_id = ?"
        params.append(user_id)
    query += " ORDER BY kt.month DESC, kt.user_id ASC"
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def list_kpi_target_progress(month: str) -> list[dict[str, Any]]:
    targets = list_kpi_targets(month=month)
    transactions = list_kpi_transactions(month=month, include_reversed=False)
    scores: dict[int, float] = {}
    for tx in transactions:
        scores[int(tx["user_id"])] = round(scores.get(int(tx["user_id"]), 0.0) + float(tx["points"]), 2)
    output: list[dict[str, Any]] = []
    with get_connection() as conn:
        for target in targets:
            user_id = int(target["user_id"])
            user = conn.execute(
                """
                SELECT u.full_name, u.department_id, d.name AS department_name
                FROM users u
                LEFT JOIN departments d ON d.id = u.department_id
                WHERE u.id = ?
                """,
                (user_id,),
            ).fetchone()
            score = scores.get(user_id, 0.0)
            target_score = float(target["target_score"])
            progress = round((score / target_score) * 100, 2) if target_score else 0.0
            output.append(
                {
                    "user_id": user_id,
                    "user_name": user["full_name"] if user else target.get("user_name", "Unknown"),
                    "month": month,
                    "score": score,
                    "target_score": target_score,
                    "progress_percent": progress,
                    "gap": round(max(target_score - score, 0.0), 2),
                    "department_id": user["department_id"] if user else target.get("department_id"),
                    "department_name": user["department_name"] if user else None,
                }
            )
    return output
