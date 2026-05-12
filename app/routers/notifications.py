from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, require_roles
from app.repository import (
    count_unread_app_notifications,
    create_app_notification,
    create_audit_log,
    list_app_notifications,
    list_tasks,
    mark_all_app_notifications_read,
    mark_app_notification_read,
    notification_exists_for_event,
)
from app.schemas import AppNotificationOut, MarkAllReadOut, TaskReminderRunOut, UnreadNotificationCountOut

router = APIRouter(tags=["notifications"])


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _today_window(now: datetime) -> tuple[str, str]:
    start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


@router.get("/notifications", response_model=list[AppNotificationOut])
def list_notifications_endpoint(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    return list_app_notifications(user_id=int(current_user["id"]), unread_only=unread_only, limit=limit)


@router.get("/notifications/unread-count", response_model=UnreadNotificationCountOut)
def unread_count_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    return {"unread_count": count_unread_app_notifications(int(current_user["id"]))}


@router.patch("/notifications/{notification_id}/read", response_model=AppNotificationOut)
def mark_notification_read_endpoint(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    notification = mark_app_notification_read(notification_id, int(current_user["id"]))
    if not notification:
        raise HTTPException(status_code=404, detail="notification not found")
    return notification


@router.patch("/notifications/read-all", response_model=MarkAllReadOut)
def mark_all_notifications_read_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    return {"updated": mark_all_app_notifications_read(int(current_user["id"]))}


@router.post("/notifications/task-reminders/run", response_model=TaskReminderRunOut)
def run_task_reminders_endpoint(current_user: dict = Depends(get_current_user)) -> dict:
    require_roles(current_user, {"admin", "manager"})
    now = datetime.now(timezone.utc)
    soon_until = now + timedelta(hours=24)
    window_start, window_end = _today_window(now)
    result = {"due_soon_created": 0, "overdue_created": 0, "skipped_duplicates": 0}

    for task in list_tasks():
        if task["status"] == "done":
            continue
        deadline = _parse_dt(str(task["deadline"]))
        if deadline < now:
            notification_type = "task_overdue"
            title = "Task overdue"
            message = f'"{task["title"]}" is overdue'
            counter = "overdue_created"
        elif deadline <= soon_until:
            notification_type = "task_due_soon"
            title = "Task due soon"
            message = f'"{task["title"]}" is due within 24 hours'
            counter = "due_soon_created"
        else:
            continue

        exists = notification_exists_for_event(
            user_id=int(task["assignee_id"]),
            notification_type=notification_type,
            entity_type="task",
            entity_id=int(task["id"]),
            window_start_iso=window_start,
            window_end_iso=window_end,
        )
        if exists:
            result["skipped_duplicates"] += 1
            continue

        create_app_notification(
            user_id=int(task["assignee_id"]),
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type="task",
            entity_id=int(task["id"]),
        )
        result[counter] += 1

    create_audit_log(
        current_user["id"],
        "run",
        "task_reminders",
        None,
        f"due_soon={result['due_soon_created']} overdue={result['overdue_created']} skipped={result['skipped_duplicates']}",
    )
    return result
