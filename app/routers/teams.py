from datetime import datetime, timedelta, timezone
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.auth import current_role_code, get_current_user, is_member_role, require_email_domain_allowed, require_permission, require_roles
from app.deps import require_project_access
from app.kpi import calculate_monthly_kpi_from_transactions, compute_dashboard_metrics, policy_from_row
from app.proactive_worker import process_notification_queue
from app.repository import (
    all_tasks_with_users,
    bulk_update_tasks,
    count_notifications_by_status,
    create_audit_log,
    create_app_notification,
    create_task,
    get_user_by_aad_object_id,
    get_user_by_id,
    get_user_by_username_or_email,
    get_task_by_id,
    get_notification_by_id,
    list_notifications,
    list_tasks,
    get_kpi_policy,
    list_kpi_target_progress,
    list_kpi_transactions,
    rebuild_kpi_transactions,
    queue_notification,
    requeue_notification,
    update_task_status,
    upsert_teams_conversation_ref,
    upsert_user_from_aad,
    user_exists,
)
from app.schemas import (
    NotificationQueueOut,
    QueueProcessOut,
    TeamsSummaryOut,
    TeamsBotActivity,
    UserOut,
)
from app.settings import settings
from app.teams_auth import get_teams_claims, get_teams_user_identity
from app.teams_bot import (
    build_deadline_card,
    build_kpi_summary_card,
    build_task_action_card,
    find_tasks_due_within_24h,
    send_card_to_teams_webhook,
)

router = APIRouter(tags=["teams"])

BOT_HELP_TEXT = (
    "TeamsWork bot commands: /help, /task-list, /team-kpi, /my-deadlines, "
    "/top-kpi, /search <keyword>, /new-task title=<title> assignee=<email|id> due=<YYYY-MM-DD>, "
    "/assign <task_id> <email|id>, /status <task_id> <todo|doing|done>, /report [YYYY-MM]"
)
BOT_SIGN_IN_TEXT = "Open the TeamsWork tab and sign in before using this bot command."


def _extract_bot_aad_object_id(activity: TeamsBotActivity) -> str | None:
    if not activity.from_property:
        return None
    value = activity.from_property.get("aadObjectId") or activity.from_property.get("id")
    return str(value).strip() if value else None


def _resolve_bot_user(activity: TeamsBotActivity) -> dict | None:
    aad_object_id = _extract_bot_aad_object_id(activity)
    if not aad_object_id:
        return None
    return get_user_by_aad_object_id(aad_object_id)


def _normalize_bot_text(text: str | None) -> str:
    value = re.sub(r"<at>.*?</at>", " ", text or "", flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"\s+", " ", value).strip()


def _parse_bot_command(text: str | None) -> tuple[str, str]:
    normalized = _normalize_bot_text(text)
    if not normalized:
        return "", ""
    parts = normalized.split(" ", 1)
    aliases = {"help": "/help", "kpi": "/team-kpi", "deadlines": "/my-deadlines"}
    command = aliases.get(parts[0].lower(), parts[0].lower())
    argument = parts[1].strip() if len(parts) > 1 else ""
    return command, argument


def _format_task_line(task: dict) -> str:
    deadline = str(task.get("deadline") or "")[:10] or "no deadline"
    return f"#{task.get('id')} {task.get('title')} [{task.get('status')}] due {deadline}"


def _bot_task_list(user: dict) -> str:
    tasks = list_tasks(assignee_id=int(user["id"]) if is_member_role(user) else None)
    active = [task for task in tasks if task.get("status") != "done"][:5]
    if not active:
        return "No active tasks found."
    return "Task list:\n" + "\n".join(_format_task_line(task) for task in active)


def _bot_my_deadlines(user: dict) -> str:
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=7)
    tasks = []
    for task in list_tasks(assignee_id=int(user["id"])):
        if task.get("status") == "done" or not task.get("deadline"):
            continue
        try:
            deadline = datetime.fromisoformat(str(task["deadline"]))
        except ValueError:
            continue
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline <= horizon:
            tasks.append(task)
    if not tasks:
        return "No personal deadlines due in the next 7 days."
    return "My deadlines:\n" + "\n".join(_format_task_line(task) for task in tasks[:5])


def _monthly_kpi_rows(month: str, user_id: int | None = None) -> list[dict]:
    rebuild_kpi_transactions(month, policy_from_row(get_kpi_policy()))
    monthly = calculate_monthly_kpi_from_transactions(
        list_kpi_transactions(month, user_id=user_id, include_reversed=False),
        month,
    )
    return sorted(monthly.values(), key=lambda item: item["score"], reverse=True)


def _bot_team_kpi(user: dict) -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    if current_role_code(user) not in {"ADMIN", "MANAGER", "HR"}:
        rows = _monthly_kpi_rows(month, user_id=int(user["id"]))
        if not rows:
            return f"No KPI data found for {month}."
        return f"My KPI {month}: {rows[0]['score']} points."
    rows = _monthly_kpi_rows(month)
    if not rows:
        return f"No team KPI data found for {month}."
    avg = round(sum(float(row["score"]) for row in rows) / len(rows), 2)
    return f"Team KPI {month}: {len(rows)} users, average {avg} points."


def _bot_top_kpi(user: dict) -> str:
    if current_role_code(user) not in {"ADMIN", "MANAGER", "HR"}:
        return "Open the TeamsWork tab to view your personal KPI."
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    rows = _monthly_kpi_rows(month)[:5]
    if not rows:
        return f"No KPI ranking data found for {month}."
    lines = [f"{index}. {row['user_name']}: {row['score']}" for index, row in enumerate(rows, start=1)]
    return f"Top KPI {month}:\n" + "\n".join(lines)


def _bot_search(user: dict, keyword: str) -> str:
    query = keyword.strip()
    if len(query) < 2:
        return "Use /search <keyword> with at least 2 characters."
    tasks = list_tasks(
        assignee_id=int(user["id"]) if is_member_role(user) else None,
        keyword=query,
    )[:5]
    if not tasks:
        return "No matching tasks found."
    return "Search results:\n" + "\n".join(_format_task_line(task) for task in tasks)


def _parse_key_values(argument: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for match in re.finditer(r"(\w+)=((?:\"[^\"]+\")|(?:'[^']+')|(?:\S+))", argument):
        value = match.group(2).strip()
        if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
            value = value[1:-1]
        pairs[match.group(1).lower()] = value.strip()
    return pairs


def _resolve_user_reference(value: str | None) -> dict | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return get_user_by_id(int(raw))
    return get_user_by_username_or_email(raw)


def _parse_due_date(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return datetime.now(timezone.utc) + timedelta(days=7)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _task_visible_to_bot_user(task: dict, user: dict) -> bool:
    if int(task["assignee_id"]) == int(user["id"]):
        return True
    project_id = task.get("project_id")
    if project_id is None:
        return current_role_code(user) in {"ADMIN", "MANAGER", "HR"}
    try:
        require_project_access(user, int(project_id))
    except HTTPException:
        return False
    return True


def _bot_status_update(user: dict, task_id: int, status: str) -> str:
    if status not in {"todo", "doing", "done"}:
        return "Usage: /status <task_id> <todo|doing|done>"
    task = get_task_by_id(task_id)
    if not task:
        return "Task not found."
    if not _task_visible_to_bot_user(task, user):
        return "You do not have access to this task."
    try:
        if int(task["assignee_id"]) == int(user["id"]):
            require_permission(user, "tasks.update_own")
        else:
            require_permission(user, "tasks.update_any")
    except HTTPException:
        return "You do not have permission to update this task."
    row = update_task_status(task_id, status)
    if not row:
        return "Task not found."
    create_audit_log(user["id"], "teams_bot_status", "task", task_id, f"status={status}")
    if task["status"] != status:
        create_app_notification(
            user_id=int(row["assignee_id"]),
            notification_type="task_status_changed",
            title="Task status updated from Teams",
            message=f'"{row["title"]}" moved to {status}',
            entity_type="task",
            entity_id=task_id,
        )
    return f"Task #{task_id} moved to {status}."


def _bot_assign_task(user: dict, task_id: int, assignee_ref: str | None) -> str:
    task = get_task_by_id(task_id)
    if not task:
        return "Task not found."
    assignee = _resolve_user_reference(assignee_ref)
    if not assignee:
        return "Usage: /assign <task_id> <assignee_email|assignee_id>"
    if not _task_visible_to_bot_user(task, user):
        return "You do not have access to this task."
    try:
        require_permission(user, "tasks.update_any")
    except HTTPException:
        return "You do not have permission to assign tasks."
    updated = bulk_update_tasks([task_id], assignee_id=int(assignee["id"]))
    if not updated:
        return "Task not found."
    create_audit_log(user["id"], "teams_bot_assign", "task", task_id, f"assignee={assignee['id']}")
    create_app_notification(
        user_id=int(assignee["id"]),
        notification_type="task_status_changed",
        title="Task assigned from Teams",
        message=f'You were assigned "{task["title"]}"',
        entity_type="task",
        entity_id=task_id,
    )
    return f"Task #{task_id} assigned to {assignee.get('full_name') or assignee.get('email')}."


def _bot_new_task(user: dict, argument: str) -> str:
    try:
        require_permission(user, "tasks.create")
    except HTTPException:
        return "You do not have permission to create tasks."
    pairs = _parse_key_values(argument)
    title = (pairs.get("title") or "").strip()
    assignee = _resolve_user_reference(pairs.get("assignee"))
    due = _parse_due_date(pairs.get("due") or pairs.get("deadline"))
    if len(title) < 2 or not assignee or not due:
        return 'Usage: /new-task title="Task title" assignee=<email|id> due=<YYYY-MM-DD>'
    points = int(pairs.get("points") or pairs.get("story_points") or 1)
    difficulty = (pairs.get("difficulty") or "medium").lower()
    if points < 1 or points > 100 or difficulty not in {"easy", "medium", "hard"}:
        return "Usage: story points must be 1-100 and difficulty must be easy|medium|hard."
    task = create_task(
        title=title,
        description=pairs.get("description"),
        assignee_id=int(assignee["id"]),
        project_id=None,
        sprint_id=None,
        story_points=points,
        difficulty=difficulty,
        deadline_iso=due.isoformat(),
        priority=(pairs.get("priority") or "medium").lower(),
    )
    create_audit_log(user["id"], "teams_bot_create", "task", task["id"], f"assign_to={task['assignee_id']}")
    create_app_notification(
        user_id=int(assignee["id"]),
        notification_type="task_status_changed",
        title="Task created from Teams",
        message=f'You were assigned "{task["title"]}"',
        entity_type="task",
        entity_id=int(task["id"]),
    )
    return f"Created task #{task['id']}: {task['title']}."


def _bot_report(user: dict, argument: str) -> str:
    month = argument.strip() or datetime.now(timezone.utc).strftime("%Y-%m")
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        return "Usage: /report [YYYY-MM]"
    tasks = all_tasks_with_users()
    user_id = int(user["id"]) if is_member_role(user) else None
    if user_id is not None:
        tasks = [task for task in tasks if int(task["assignee_id"]) == user_id]
    rows = _monthly_kpi_rows(month, user_id=user_id)
    metrics = compute_dashboard_metrics(tasks, {int(row["user_id"]): row for row in rows}, month)
    return (
        f"Report {month}: {metrics['total_tasks']} tasks, {metrics['done_tasks']} done, "
        f"{metrics['overdue_tasks']} overdue, avg KPI {metrics['avg_kpi_score']}."
    )


def _handle_bot_command(activity: TeamsBotActivity) -> dict:
    command, argument = _parse_bot_command(activity.text)
    if command == "/help":
        return {"type": "message", "text": BOT_HELP_TEXT}
    if command not in {
        "/task-list",
        "/team-kpi",
        "/my-deadlines",
        "/top-kpi",
        "/search",
        "/new-task",
        "/assign",
        "/status",
        "/report",
    }:
        return {"type": "message", "text": f"Unknown command. {BOT_HELP_TEXT}"}

    user = _resolve_bot_user(activity)
    if not user:
        return {"type": "message", "text": BOT_SIGN_IN_TEXT}
    if not user.get("is_active", True):
        return {"type": "message", "text": "Open the TeamsWork tab to verify your account status."}

    handlers = {
        "/task-list": lambda: _bot_task_list(user),
        "/team-kpi": lambda: _bot_team_kpi(user),
        "/my-deadlines": lambda: _bot_my_deadlines(user),
        "/top-kpi": lambda: _bot_top_kpi(user),
        "/search": lambda: _bot_search(user, argument),
        "/new-task": lambda: _bot_new_task(user, argument),
        "/assign": lambda: _bot_assign_task(user, int(argument.split()[0]), argument.split()[1] if len(argument.split()) > 1 else None)
        if argument.split() and argument.split()[0].isdigit()
        else "Usage: /assign <task_id> <assignee_email|assignee_id>",
        "/status": lambda: _bot_status_update(user, int(argument.split()[0]), argument.split()[1].lower() if len(argument.split()) > 1 else "")
        if argument.split() and argument.split()[0].isdigit()
        else "Usage: /status <task_id> <todo|doing|done>",
        "/report": lambda: _bot_report(user, argument),
    }
    return {"type": "message", "text": handlers[command]()}


def _queue_stats() -> dict:
    return count_notifications_by_status()


@router.get("/integrations/teams/summary", response_model=TeamsSummaryOut)
def teams_summary_endpoint(
    month: str = Query(description="YYYY-MM"),
    task_limit: int = Query(default=30, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
) -> dict:
    tasks_for_metrics = all_tasks_with_users()
    if is_member_role(current_user):
        tasks_for_metrics = [
            task for task in tasks_for_metrics
            if int(task["assignee_id"]) == int(current_user["id"])
        ]
        task_rows = sorted(
            list_tasks(assignee_id=int(current_user["id"])),
            key=lambda task: int(task["id"]),
            reverse=True,
        )[:task_limit]
    else:
        task_rows = sorted(
            list_tasks(),
            key=lambda task: int(task["id"]),
            reverse=True,
        )[:task_limit]

    rebuild_kpi_transactions(month, policy_from_row(get_kpi_policy()))
    monthly_kpi = calculate_monthly_kpi_from_transactions(
        list_kpi_transactions(
            month,
            user_id=int(current_user["id"]) if is_member_role(current_user) else None,
            include_reversed=False,
        ),
        month,
    )
    progress = {int(item["user_id"]): item for item in list_kpi_target_progress(month)}
    for item in monthly_kpi.values():
        target = progress.get(int(item["user_id"]))
        if target:
            item["target_score"] = target["target_score"]
            item["progress_percent"] = target["progress_percent"]
            item["gap"] = target["gap"]
    kpi_rows = sorted(
        monthly_kpi.values(),
        key=lambda item: item["score"],
        reverse=True,
    )
    if is_member_role(current_user):
        kpi_rows = [row for row in kpi_rows if int(row["user_id"]) == int(current_user["id"])]

    can_manage_queue = current_role_code(current_user) in {"ADMIN", "MANAGER", "HR"}
    return {
        "month": month,
        "dashboard": compute_dashboard_metrics(tasks_for_metrics, monthly_kpi, month),
        "kpi": kpi_rows,
        "tasks": task_rows,
        "can_manage_queue": can_manage_queue,
        "queue_stats": _queue_stats() if can_manage_queue else None,
    }


@router.get("/integrations/teams/aad/me")
def teams_me_endpoint(
    identity: dict = Depends(get_teams_user_identity),
    _: dict = Depends(get_teams_claims),
) -> dict:
    return identity


@router.post("/integrations/teams/aad/sync", response_model=UserOut)
def teams_sync_user_endpoint(
    identity: dict = Depends(get_teams_user_identity),
    _: dict = Depends(get_teams_claims),
) -> dict:
    aad_object_id = identity.get("aad_object_id")
    if not aad_object_id:
        raise HTTPException(status_code=400, detail="missing aad_object_id in token")
    require_email_domain_allowed(identity.get("email"))
    user = upsert_user_from_aad(
        aad_object_id=aad_object_id,
        display_name=identity.get("display_name"),
        email=identity.get("email"),
    )
    create_audit_log(user.get("id"), "sync", "aad_user", user.get("id"), "aad sync")
    return user


@router.post("/integrations/teams/reminders/run")
def run_teams_deadline_reminders(current_user: dict = Depends(get_current_user)) -> dict:
    require_roles(current_user, {"admin", "manager"})
    tasks = all_tasks_with_users()
    due_tasks = find_tasks_due_within_24h(tasks)

    sent = 0
    previews: list[dict] = []
    for task in due_tasks:
        card = build_deadline_card(task)
        previews.append({"task_id": task.get("id"), "card": card})
        if send_card_to_teams_webhook(card).get("sent"):
            sent += 1

    create_audit_log(
        current_user["id"], "notify", "teams_deadline_reminders", None,
        f"due={len(due_tasks)} sent={sent}",
    )
    return {"due_within_24h": len(due_tasks), "sent": sent, "preview": previews[:3]}


@router.post("/integrations/teams/bot/messages")
def teams_bot_messages_endpoint(activity: TeamsBotActivity) -> dict:
    aad_object_id = _extract_bot_aad_object_id(activity)
    bot_user = _resolve_bot_user(activity)
    conversation_id = activity.conversation.get("id") if activity.conversation else None
    if conversation_id:
        upsert_teams_conversation_ref(
            user_id=int(bot_user["id"]) if bot_user else None,
            aad_object_id=aad_object_id,
            conversation_id=conversation_id,
            service_url=activity.serviceUrl,
            tenant_id=(activity.conversation or {}).get("tenantId"),
            channel_id=activity.channelId,
        )

    if activity.type != "message":
        return {"type": "message", "text": "Event received"}

    return _handle_bot_command(activity)

def _card_action_value(activity: TeamsBotActivity) -> dict:
    if not isinstance(activity.value, dict):
        raise HTTPException(status_code=400, detail="card action payload is required")
    return activity.value


@router.post("/integrations/teams/card/actions")
def teams_card_actions_endpoint(activity: TeamsBotActivity) -> dict:
    value = _card_action_value(activity)
    action = str(value.get("action") or "").strip().lower()
    if action not in {"task_view", "task_status", "task_assign", "acknowledge"}:
        raise HTTPException(status_code=400, detail="unsupported card action")

    user = _resolve_bot_user(activity)
    if not user:
        raise HTTPException(status_code=403, detail="mapped TeamsWork user is required")

    if action == "acknowledge":
        create_audit_log(user["id"], "teams_card_ack", str(value.get("kind") or "card"), None, "acknowledged")
        return {"type": "message", "text": "Acknowledged."}

    raw_task_id = value.get("task_id")
    try:
        task_id = int(raw_task_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="valid task_id is required") from exc
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    if not _task_visible_to_bot_user(task, user):
        raise HTTPException(status_code=403, detail="forbidden")

    if action == "task_view":
        card = build_task_action_card(task)
        return {"type": "message", "text": f"Task #{task_id}: {task['title']}", "card": card}
    if action == "task_status":
        status = str(value.get("status") or "").strip().lower()
        if status not in {"todo", "doing", "done"}:
            raise HTTPException(status_code=400, detail="status must be one of todo|doing|done")
        return {"type": "message", "text": _bot_status_update(user, task_id, status)}
    assignee = value.get("assignee_id") or value.get("assignee")
    return {"type": "message", "text": _bot_assign_task(user, task_id, str(assignee) if assignee is not None else None)}


@router.post("/integrations/teams/proactive/queue", response_model=NotificationQueueOut)
def queue_proactive_notification(
    message: str = Query(..., min_length=2),
    user_id: int | None = Query(default=None),
    target_type: str = Query(default="user"),
    team_id: str | None = Query(default=None),
    channel_id: str | None = Query(default=None),
    dedup_key: str | None = Query(default=None),
    max_attempts: int = Query(default=3, ge=1, le=10),
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager", "hr"})
    if target_type not in {"user", "channel", "project_channel", "webhook"}:
        raise HTTPException(status_code=400, detail="target_type must be one of user|channel|project_channel|webhook")
    payload = {"type": "message", "text": message, "target": {"type": target_type}}
    if dedup_key:
        payload["dedup_key"] = dedup_key.strip()
    if team_id:
        payload["target"]["team_id"] = team_id.strip()
    if channel_id:
        payload["target"]["channel_id"] = channel_id.strip()
    item = queue_notification(
        user_id=user_id,
        channel="teams",
        payload=payload,
        max_attempts=max_attempts,
    )
    create_audit_log(current_user["id"], "queue", "notification", item["id"], "teams proactive")
    return item


@router.get("/integrations/teams/proactive/queue", response_model=list[NotificationQueueOut])
def list_proactive_notifications(
    status: str = Query(default="queued"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    require_roles(current_user, {"admin", "manager", "hr"})
    if status not in {"queued", "sent", "failed", "all"}:
        raise HTTPException(status_code=400, detail="status must be one of queued|sent|failed|all")
    return list_notifications(status=status, limit=limit)


@router.post("/integrations/teams/proactive/process", response_model=QueueProcessOut)
def process_proactive_queue(
    limit: int = Query(default=1000, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager", "hr"})
    result = process_notification_queue(limit=limit)
    create_audit_log(current_user["id"], "process", "notification_queue", None, f"processed={result['processed']}")
    return result


@router.post("/integrations/teams/proactive/requeue/{notification_id}", response_model=NotificationQueueOut)
def requeue_failed_notification(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager", "hr"})
    item = get_notification_by_id(notification_id)
    if not item:
        raise HTTPException(status_code=404, detail="notification not found")
    if item.get("status") != "failed":
        raise HTTPException(status_code=400, detail="only failed notifications can be requeued")
    updated = requeue_notification(notification_id)
    if not updated:
        raise HTTPException(status_code=404, detail="notification not found")
    create_audit_log(current_user["id"], "requeue", "notification", notification_id, "teams proactive")
    return updated


@router.get("/teams/tab")
def teams_tab_page() -> Response:
    html = f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
  <title>TeamsWork Integration Tab</title>
  <script src='https://res.cdn.office.net/teams-js/2.19.0/js/MicrosoftTeams.min.js'></script>
  <style>
    body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;background:#f4f6fa}}
    .card{{background:#fff;border:1px solid #dde5f0;border-radius:12px;padding:20px;max-width:600px}}
    h2{{color:#2b579a;margin-top:0}}button{{padding:10px 18px;background:#2b579a;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px}}
    pre{{background:#f4f6fa;border-radius:8px;padding:12px;overflow-x:auto;font-size:12px}}
  </style>
</head>
<body>
  <div class='card'>
    <h2>🔗 TeamsWork – Kết nối tài khoản Azure AD</h2>
    <p>Nhấn nút bên dưới để xác thực tài khoản Microsoft Teams của bạn với TeamsWork.</p>
    <button id='btn'>Lấy thông tin tài khoản</button>
    <pre id='out'>Đang chờ...</pre>
  </div>
  <script>
    const out=document.getElementById('out');
    document.getElementById('btn').onclick=async()=>{{
      try{{
        await microsoftTeams.app.initialize();
        const token=await microsoftTeams.authentication.getAuthToken({{resources:[]}});
        const res=await fetch('{settings.app_base_url}/integrations/teams/aad/me',{{headers:{{Authorization:'Bearer '+token}}}});
        out.textContent=JSON.stringify(await res.json(),null,2);
      }}catch(e){{out.textContent='Lỗi: '+(e?.message||e);}}
    }};
  </script>
</body></html>"""
    return Response(content=html, media_type="text/html")


@router.get("/teams/tab/prod")
def teams_tab_prod_page() -> Response:
    html = """<!doctype html>
<html>
<head>
  <meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
  <title>TeamsWork Production Tab</title>
  <script src='https://res.cdn.office.net/teams-js/2.19.0/js/MicrosoftTeams.min.js'></script>
  <style>
    :root{--brand:#2b579a;--bg:#f4f6fb;--card:#fff;--border:#dde5f0;--text:#1e2a3a;--muted:#64748b;--green:#059669;--amber:#d97706;--red:#dc2626}
    *{box-sizing:border-box}body{margin:0;font-family:Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--text);font-size:14px}
    button,select{font:inherit}.wrap{max-width:1180px;margin:0 auto;padding:14px}.head{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:12px}
    .logo{font-size:20px;font-weight:700;color:var(--brand)}.sub{font-size:12px;color:var(--muted);margin-top:2px}.actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
    .btn{border:1px solid var(--brand);background:#fff;color:var(--brand);padding:7px 12px;border-radius:8px;cursor:pointer;font-size:13px;line-height:1.2}.btn.primary{background:var(--brand);color:#fff}.btn.danger{border-color:var(--red);color:var(--red)}.btn:disabled{opacity:.55;cursor:not-allowed}
    .stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:12px}.panel{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px}.k{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px}.v{font-size:24px;font-weight:700;color:var(--brand);margin-top:3px}
    .layout{display:grid;grid-template-columns:minmax(0,2fr) minmax(280px,1fr);gap:12px}.section-title{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:10px}.section-title h2{font-size:15px;margin:0}.board{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.col{background:#f8fafc;border:1px solid var(--border);border-radius:8px;padding:10px;min-height:210px}.col h3{margin:0 0 9px 0;font-size:13px;display:flex;justify-content:space-between;gap:6px}
    .badge{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;white-space:nowrap}.badge-todo{background:#f3f4f6;color:#4b5563}.badge-doing{background:#fef3c7;color:var(--amber)}.badge-done{background:#d1fae5;color:var(--green)}.badge-overdue,.badge-failed{background:#fee2e2;color:var(--red)}.badge-info{background:#dbeafe;color:var(--brand)}
    .task{width:100%;text-align:left;border:1px solid var(--border);border-radius:8px;padding:10px;margin-bottom:8px;background:#fff;cursor:pointer}.task:hover{border-color:#a9b9d1;box-shadow:0 1px 5px rgba(30,42,58,.08)}.task .t{font-size:13px;font-weight:650;margin-bottom:6px;overflow-wrap:anywhere}.task .m{font-size:11px;color:var(--muted);display:flex;gap:7px;flex-wrap:wrap}.task-actions{display:flex;justify-content:flex-end;margin-top:8px}
    .side{display:grid;gap:12px}.table{width:100%;border-collapse:collapse;font-size:12px}.table th,.table td{text-align:left;border-bottom:1px solid var(--border);padding:7px 4px}.table th{color:var(--muted)}.queue-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px}.queue-stat{border:1px solid var(--border);border-radius:8px;padding:8px;background:#f8fafc}.queue-list{display:grid;gap:8px;max-height:300px;overflow:auto}.queue-item{border:1px solid var(--border);border-radius:8px;background:#fff;padding:9px}.queue-line{display:flex;justify-content:space-between;gap:8px;align-items:center}.queue-msg{font-size:12px;color:#334155;overflow-wrap:anywhere;margin-top:5px}.filters{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}
    .state{border:1px dashed #cbd5e1;border-radius:8px;padding:12px;color:var(--muted);background:#f8fafc;font-size:13px;text-align:center}.error{border-color:#fecaca;background:#fff1f2;color:#991b1b}.hidden{display:none!important}.banner{margin-bottom:12px}.skeleton{position:relative;overflow:hidden;color:transparent;background:#e8eef7;border-radius:6px}.skeleton:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.65),transparent);animation:shine 1.2s infinite}@keyframes shine{from{transform:translateX(-100%)}to{transform:translateX(100%)}}
    .drawer-backdrop{position:fixed;inset:0;background:rgba(15,23,42,.36);display:flex;justify-content:flex-end;z-index:50}.drawer{width:min(460px,100vw);height:100%;background:#fff;border-left:1px solid var(--border);box-shadow:-12px 0 24px rgba(15,23,42,.16);display:flex;flex-direction:column}.drawer-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;padding:14px;border-bottom:1px solid var(--border)}.drawer-title{font-size:18px;font-weight:700;margin:2px 0 0;overflow-wrap:anywhere}.drawer-body{padding:14px;overflow:auto}.drawer-section{border-bottom:1px solid var(--border);padding-bottom:12px;margin-bottom:12px}.drawer-section:last-child{border-bottom:0}.meta-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.meta{border:1px solid var(--border);border-radius:8px;padding:8px;background:#f8fafc}.meta span{display:block;font-size:11px;color:var(--muted);margin-bottom:3px}.meta strong{font-size:13px;overflow-wrap:anywhere}.seg{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:10px}.comment,.activity{border:1px solid var(--border);border-radius:8px;padding:8px;margin-top:7px;background:#fff}.comment small,.activity small{color:var(--muted)}
    @media(max-width:940px){.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.layout{grid-template-columns:1fr}.board{grid-template-columns:1fr}.head{align-items:flex-start;flex-direction:column}.actions{width:100%}.actions .btn{flex:1}.drawer{width:100vw}}
  </style>
</head>
<body>
  <div class='wrap'>
    <div class='head'><div><div class='logo'>TeamsWork</div><div class='sub' id='identityLine'>Teams tab production</div></div><div class='actions'><button class='btn' id='retryBtn'>Thử lại</button><button class='btn primary' id='refresh'>Làm mới</button></div></div>
    <div id='errorBanner' class='state error banner hidden' data-state="error"></div>
    <div class='stats'><div class='panel'><div class='k'>Tổng công việc</div><div class='v' id='total' data-state="loading">-</div></div><div class='panel'><div class='k'>Hoàn thành</div><div class='v' id='done' data-state="loading">-</div></div><div class='panel'><div class='k'>Quá hạn</div><div class='v' id='overdue' data-state="loading">-</div></div><div class='panel'><div class='k'>KPI trung bình</div><div class='v' id='kpi' data-state="loading">-</div></div></div>
    <div class='layout'>
      <main class='panel'><div class='section-title'><h2>Bảng công việc</h2><span class='badge badge-info' id='taskCount'>0 task</span></div><div id='boardEmpty' class='state hidden' data-state="empty">Chưa có công việc phù hợp để hiển thị.</div><div class='board' id='taskBoard'><div class='col'><h3><span class='badge badge-todo'>To do</span><span id='count-todo'>0</span></h3><div id='col-todo'><div class='state' data-state="loading">Đang tải...</div></div></div><div class='col'><h3><span class='badge badge-doing'>Đang làm</span><span id='count-doing'>0</span></h3><div id='col-doing'><div class='state' data-state="loading">Đang tải...</div></div></div><div class='col'><h3><span class='badge badge-done'>Hoàn thành</span><span id='count-done'>0</span></h3><div id='col-done'><div class='state' data-state="loading">Đang tải...</div></div></div></div></main>
      <aside class='side'><section class='panel'><div class='section-title'><h2>KPI tháng</h2><span class='badge badge-info' id='monthBadge'>-</span></div><div id='kpiEmpty' class='state hidden' data-state="empty">Chưa có dữ liệu KPI trong tháng này.</div><table class='table' id='kpiTable'><thead><tr><th>Nhân sự</th><th>Điểm</th><th>Đúng hạn</th><th>Trễ</th></tr></thead><tbody id='kpiRows'><tr><td colspan='4'><div class='state' data-state="loading">Đang tải KPI...</div></td></tr></tbody></table></section><section class='panel hidden' id='queuePanel'><div class='section-title'><h2>Teams queue</h2><button class='btn' id='processQueueBtn'>Process</button></div><div class='queue-stats'><div class='queue-stat'><div class='k'>Queued</div><strong id='queuedCount'>0</strong></div><div class='queue-stat'><div class='k'>Sent</div><strong id='sentCount'>0</strong></div><div class='queue-stat'><div class='k'>Failed</div><strong id='failedCount'>0</strong></div></div><div class='filters'><select id='queueFilter' aria-label='Queue filter'><option value='queued'>Queued</option><option value='failed'>Failed</option><option value='sent'>Sent</option><option value='all'>All</option></select><button class='btn' id='reloadQueueBtn'>Tải queue</button></div><div id='queueList' class='queue-list'><div class='state' data-state="loading">Đang tải queue...</div></div></section></aside>
    </div>
  </div>
  <div id='taskDrawer' class='drawer-backdrop hidden' onclick='if(event.target===this) closeTaskDrawer()'><aside class='drawer' aria-label='Task detail drawer'><div class='drawer-head'><div><div class='k'>Chi tiết công việc</div><div class='drawer-title' id='drawerTitle'>Task</div></div><button class='btn' onclick='closeTaskDrawer()' aria-label='Đóng'>Đóng</button></div><div id='drawerBody' class='drawer-body'><div class='state' data-state="loading">Đang tải chi tiết...</div></div></aside></div>
  <script>
    const month=new Date().toISOString().slice(0,7),baseUrl='__APP_BASE_URL__',statuses=['todo','doing','done'];
    let authHeaders={'X-User-Id':localStorage.getItem('tw_uid')||'1'},summaryCache=null,teamsContext=null;
    const labels={todo:'To do',doing:'Đang làm',done:'Hoàn thành',overdue:'Quá hạn',late:'Trễ',on_time:'Đúng hạn'};
    function $(id){return document.getElementById(id)}function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function safeDate(v){return v?String(v).slice(0,10):'-'}function clearError(){$('errorBanner').classList.add('hidden');$('errorBanner').textContent=''}function showError(m){$('errorBanner').textContent=m||'Không tải được dữ liệu TeamsWork. Vui lòng thử lại.';$('errorBanner').classList.remove('hidden')}
    async function api(path,opt={}){const headers={...authHeaders,...(opt.headers||{})};if(opt.body)headers['Content-Type']='application/json';const res=await fetch(baseUrl+path,{...opt,headers});if(!res.ok)throw new Error('request_failed');return res.status===204?null:res.json()}
    async function syncIdentity(){let uid=localStorage.getItem('tw_uid')||'1';authHeaders={'X-User-Id':uid};try{if(window.microsoftTeams){await microsoftTeams.app.initialize();try{teamsContext=await microsoftTeams.app.getContext()}catch(_){}const tok=await microsoftTeams.authentication.getAuthToken({resources:[]});const me=await fetch(baseUrl+'/integrations/teams/aad/sync',{method:'POST',headers:{Authorization:'Bearer '+tok}});if(me.ok){const u=await me.json();uid=String(u.id);localStorage.setItem('tw_uid',uid);authHeaders={'X-User-Id':uid,Authorization:'Bearer '+tok};$('identityLine').textContent='Đã đồng bộ: '+(u.full_name||u.email||('User '+uid))}}}catch(_){$('identityLine').textContent='Dev fallback: X-User-Id '+uid}}
    function setLoading(){['total','done','overdue','kpi'].forEach(id=>{$(id).textContent='-';$(id).classList.add('skeleton')});statuses.forEach(s=>{$('col-'+s).innerHTML='<div class="state" data-state="loading">Đang tải...</div>'});$('kpiRows').innerHTML='<tr><td colspan="4"><div class="state" data-state="loading">Đang tải KPI...</div></td></tr>'}
    function card(t){const next=t.status==='todo'?'doing':t.status==='doing'?'done':null;return `<button class="task" data-task-id="${esc(t.id)}" onclick="openTaskDrawer(${Number(t.id)})"><div class="t">${esc(t.title)}</div><div class="m"><span>SP ${esc(t.story_points)}</span><span>${esc(t.difficulty||'-')}</span><span>${safeDate(t.deadline)}</span><span class="badge badge-${esc(t.status)}">${esc(labels[t.status]||t.status)}</span></div><div class="task-actions">${next?`<span class="btn" onclick="event.stopPropagation(); updateTaskStatus(${Number(t.id)}, '${next}')">${esc(labels[next])}</span>`:''}</div></button>`}
    function renderBoard(tasks){$('taskCount').textContent=tasks.length+' task';$('boardEmpty').classList.toggle('hidden',tasks.length>0);statuses.forEach(s=>{const items=tasks.filter(t=>t.status===s);$('count-'+s).textContent=items.length;$('col-'+s).innerHTML=items.length?items.map(card).join(''):`<div class="state" data-state="empty">Không có task ${esc(labels[s].toLowerCase())}.</div>`})}
    function renderKpi(rows){$('kpiEmpty').classList.toggle('hidden',rows.length>0);$('kpiRows').innerHTML=rows.length?rows.slice(0,8).map(r=>`<tr><td>${esc(r.user_name)}</td><td><strong>${esc(r.score)}</strong></td><td>${esc(r.done_on_time)}</td><td>${esc((r.done_late||0)+(r.overdue_unfinished||0))}</td></tr>`).join(''):''}
    function renderSummary(summary){summaryCache=summary;const d=summary.dashboard||{};$('monthBadge').textContent=summary.month||month;$('total').textContent=d.total_tasks??'-';$('done').textContent=d.done_tasks??'-';$('overdue').textContent=d.overdue_tasks??'-';$('kpi').textContent=d.avg_kpi_score??'-';['total','done','overdue','kpi'].forEach(id=>$(id).classList.remove('skeleton'));renderBoard(summary.tasks||[]);renderKpi(summary.kpi||[]);if(summary.can_manage_queue){$('queuePanel').classList.remove('hidden');const qs=summary.queue_stats||{};$('queuedCount').textContent=qs.queued??0;$('sentCount').textContent=qs.sent??0;$('failedCount').textContent=qs.failed??0;loadQueue()}else{$('queuePanel').classList.add('hidden')}}
    async function load(){clearError();setLoading();try{await syncIdentity();const scope=teamsContext&&teamsContext.channel&&teamsContext.channel.id?'&channel_context=1':'';renderSummary(await api('/integrations/teams/summary?month='+month+scope))}catch(_){showError('Không tải được dashboard TeamsWork. Kiểm tra đăng nhập hoặc thử lại sau.');statuses.forEach(s=>{$('col-'+s).innerHTML='<div class="state error" data-state="error">Không tải được task.</div>'})}}
    async function updateTaskStatus(taskId,newStatus){clearError();try{await api(`/tasks/${taskId}/status`,{method:'PATCH',body:JSON.stringify({status:newStatus})});await load();if(!$('taskDrawer').classList.contains('hidden'))openTaskDrawer(taskId)}catch(_){showError('Không cập nhật được trạng thái task. Vui lòng kiểm tra quyền hoặc thử lại.')}}
    async function openTaskDrawer(taskId){$('taskDrawer').classList.remove('hidden');$('drawerTitle').textContent='Task #'+taskId;$('drawerBody').innerHTML='<div class="state" data-state="loading">Đang tải chi tiết...</div>';try{renderTaskDetail(await api(`/tasks/${taskId}`))}catch(_){$('drawerBody').innerHTML='<div class="state error" data-state="error">Không tải được chi tiết task.</div>'}}
    function closeTaskDrawer(){$('taskDrawer').classList.add('hidden')}function meta(label,value){return `<div class="meta"><span>${esc(label)}</span><strong>${esc(value??'-')}</strong></div>`}
    function renderTaskDetail(task){$('drawerTitle').textContent=task.title||('Task #'+task.id);const comments=task.comments||[],logs=task.activity_logs||[];$('drawerBody').innerHTML=`<div class="drawer-section"><span class="badge badge-${esc(task.status)}">${esc(labels[task.status]||task.status)}</span> <span class="badge ${task.due_state==='overdue'?'badge-overdue':'badge-info'}">${esc(labels[task.due_state]||task.due_state)}</span><p>${esc(task.description||'Chưa có mô tả')}</p><div class="seg">${statuses.map(s=>`<button class="btn ${task.status===s?'primary':''}" onclick="updateTaskStatus(${Number(task.id)}, '${s}')" ${task.status===s?'disabled':''}>${esc(labels[s])}</button>`).join('')}</div></div><div class="drawer-section meta-grid">${meta('Assignee',task.assignee_name||('User '+task.assignee_id))}${meta('Project',task.project_name||'-')}${meta('Sprint',task.sprint_name||'-')}${meta('Deadline',safeDate(task.deadline))}${meta('Story points',task.story_points)}${meta('Difficulty',task.difficulty)}</div><div class="drawer-section"><div class="section-title"><h2>Bình luận</h2><span class="badge badge-info">${comments.length}</span></div>${comments.length?comments.map(c=>`<div class="comment"><strong>${esc(c.author_name||('User '+c.author_user_id))}</strong><div>${esc(c.body)}</div><small>${esc(safeDate(c.created_at))}</small></div>`).join(''):'<div class="state" data-state="empty">Chưa có bình luận.</div>'}</div><div class="drawer-section"><div class="section-title"><h2>Hoạt động</h2><span class="badge badge-info">${logs.length}</span></div>${logs.length?logs.map(a=>`<div class="activity"><strong>${esc(a.action)}</strong><div>${esc(a.detail||'')}</div><small>${esc(a.actor_name||'System')} · ${esc(safeDate(a.created_at))}</small></div>`).join(''):'<div class="state" data-state="empty">Chưa có hoạt động.</div>'}</div>`}
    async function loadQueue(){const status=$('queueFilter').value;$('queueList').innerHTML='<div class="state" data-state="loading">Đang tải queue...</div>';try{const items=await api('/integrations/teams/proactive/queue?status='+encodeURIComponent(status)+'&limit=50');$('queueList').innerHTML=items.length?items.map(queueItem).join(''):'<div class="state" data-state="empty">Queue đang trống.</div>'}catch(_){$('queueList').innerHTML='<div class="state error" data-state="error">Không tải được queue.</div>'}}
    function queueItem(item){const msg=(item.payload&&item.payload.text)||item.channel||'Teams notification';return `<div class="queue-item"><div class="queue-line"><span class="badge badge-${item.status==='failed'?'failed':'info'}">#${esc(item.id)} ${esc(item.status)}</span>${item.status==='failed'?`<button class="btn danger" onclick="requeue(${Number(item.id)})">Requeue</button>`:''}</div><div class="queue-msg">${esc(msg)}</div><div class="m">Attempts ${esc(item.attempts)}/${esc(item.max_attempts)} · ${esc(safeDate(item.created_at))}</div></div>`}
    async function processQueue(){try{await api('/integrations/teams/proactive/process',{method:'POST'});await load()}catch(_){showError('Không process được Teams queue.')}}async function requeue(id){try{await api(`/integrations/teams/proactive/requeue/${id}`,{method:'POST'});await load()}catch(_){showError('Không requeue được notification.')}}
    $('refresh').onclick=load;$('retryBtn').onclick=load;$('reloadQueueBtn').onclick=loadQueue;$('queueFilter').onchange=loadQueue;$('processQueueBtn').onclick=processQueue;load();
  </script>
</body></html>""".replace("__APP_BASE_URL__", settings.app_base_url)
    return Response(content=html, media_type="text/html")
