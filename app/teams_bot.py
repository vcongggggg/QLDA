from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from app.settings import settings


def build_deadline_card(task: dict) -> dict:
    return {
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "size": "Large", "weight": "Bolder", "text": "TeamsWork - Deadline Reminder"},
            {
                "type": "TextBlock",
                "text": f"Task: {task.get('title', 'N/A')}",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": f"Assignee ID: {task.get('assignee_id')}",
            },
            {
                "type": "TextBlock",
                "text": f"Deadline (UTC): {task.get('deadline')}",
                "color": "Attention",
            },
        ],
        "actions": [
            {
                "type": "Action.OpenUrl",
                "title": "Open TeamsWork",
                "url": f"{settings.app_base_url}/teams/tab",
            }
        ],
    }


def build_task_action_card(task: dict) -> dict:
    return {
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "size": "Large", "weight": "Bolder", "text": "TeamsWork - Task Action"},
            {"type": "TextBlock", "text": f"Task #{task.get('id')}: {task.get('title', 'N/A')}", "wrap": True},
            {"type": "TextBlock", "text": f"Status: {task.get('status', 'unknown')}"},
            {"type": "TextBlock", "text": f"Deadline: {task.get('deadline') or 'N/A'}", "wrap": True},
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "Start",
                "data": {"action": "task_status", "task_id": task.get("id"), "status": "doing"},
            },
            {
                "type": "Action.Submit",
                "title": "Done",
                "data": {"action": "task_status", "task_id": task.get("id"), "status": "done"},
            },
            {
                "type": "Action.OpenUrl",
                "title": "Open TeamsWork",
                "url": f"{settings.app_base_url}/teams/tab",
            },
        ],
    }


def build_kpi_summary_card(month: str, rows: list[dict]) -> dict:
    top_rows = rows[:5]
    facts = [
        {"title": str(row.get("user_name", f"User {row.get('user_id')}")), "value": str(row.get("score", 0))}
        for row in top_rows
    ]
    return {
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "size": "Large", "weight": "Bolder", "text": f"TeamsWork - KPI {month}"},
            {"type": "FactSet", "facts": facts or [{"title": "Status", "value": "No KPI data"}]},
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "Acknowledge",
                "data": {"action": "acknowledge", "kind": "kpi_summary", "month": month},
            },
            {
                "type": "Action.OpenUrl",
                "title": "Open TeamsWork",
                "url": f"{settings.app_base_url}/teams/tab",
            },
        ],
    }


def build_text_card(title: str, message: str) -> dict:
    return {
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "size": "Large", "weight": "Bolder", "text": title},
            {"type": "TextBlock", "text": message, "wrap": True},
        ],
    }


def build_incoming_webhook_message(card: dict) -> dict:
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": card,
            }
        ],
    }


def find_tasks_due_within_24h(tasks: list[dict]) -> list[dict]:
    now = datetime.now(timezone.utc)
    end = now + timedelta(hours=24)
    result: list[dict] = []
    for task in tasks:
        if task.get("status") == "done":
            continue
        deadline_raw = task.get("deadline")
        if not deadline_raw:
            continue
        deadline = datetime.fromisoformat(deadline_raw)
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if now <= deadline <= end:
            result.append(task)
    return result


def send_card_to_teams_webhook(card: dict) -> dict:
    if not settings.teams_incoming_webhook_url:
        return {"sent": False, "reason": "TEAMS_INCOMING_WEBHOOK_URL is not configured"}

    payload = build_incoming_webhook_message(card)
    response = httpx.post(settings.teams_incoming_webhook_url, json=payload, timeout=10.0)
    return {"sent": response.status_code in (200, 201), "status_code": response.status_code, "response_text": response.text}


def _bot_tenant() -> str:
    return settings.teams_tenant_id or "common"


def _build_bot_outgoing_activity(text: str) -> dict:
    return {
        "type": "message",
        "text": text,
    }


def _get_bot_access_token() -> dict:
    client_id = settings.teams_bot_app_id or settings.teams_client_id
    client_secret = settings.teams_bot_app_secret or settings.teams_client_secret
    if not client_id or not client_secret:
        return {"ok": False, "reason": "missing bot app credentials"}

    token_url = f"https://login.microsoftonline.com/{_bot_tenant()}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": "https://api.botframework.com/.default",
    }
    try:
        resp = httpx.post(token_url, data=data, timeout=10.0)
    except Exception as exc:
        return {"ok": False, "reason": str(exc)}

    if resp.status_code != 200:
        return {"ok": False, "reason": f"token request failed: {resp.status_code}", "response_text": resp.text}

    payload = resp.json()
    token = payload.get("access_token")
    if not token:
        return {"ok": False, "reason": "missing access_token"}
    return {"ok": True, "token": token}


def send_text_to_teams_conversation(conversation_ref: dict, text: str) -> dict:
    service_url = (conversation_ref.get("service_url") or "").rstrip("/")
    conversation_id = conversation_ref.get("conversation_id")
    if not service_url or not conversation_id:
        return {"sent": False, "reason": "invalid conversation reference"}

    token_result = _get_bot_access_token()
    if not token_result.get("ok"):
        return {"sent": False, "reason": token_result.get("reason", "bot token error")}

    activity = _build_bot_outgoing_activity(text)
    url = f"{service_url}/v3/conversations/{conversation_id}/activities"
    headers = {
        "Authorization": f"Bearer {token_result['token']}",
        "Content-Type": "application/json",
    }

    try:
        resp = httpx.post(url, json=activity, headers=headers, timeout=10.0)
    except Exception as exc:
        return {"sent": False, "reason": str(exc)}

    return {
        "sent": resp.status_code in (200, 201, 202),
        "status_code": resp.status_code,
        "response_text": resp.text,
    }


def _get_graph_access_token() -> dict:
    if settings.teams_proactive_mode != "graph":
        return {"ok": False, "reason": "graph mode is not enabled"}
    if not settings.teams_client_id or not settings.teams_client_secret or not settings.teams_tenant_id:
        return {"ok": False, "reason": "missing graph credentials"}

    token_url = f"https://login.microsoftonline.com/{settings.teams_tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": settings.teams_client_id,
        "client_secret": settings.teams_client_secret,
        "grant_type": "client_credentials",
        "scope": "https://graph.microsoft.com/.default",
    }
    try:
        resp = httpx.post(token_url, data=data, timeout=10.0)
    except Exception:
        return {"ok": False, "reason": "graph token request failed"}
    if resp.status_code != 200:
        return {"ok": False, "reason": f"graph token request failed: {resp.status_code}"}
    token = resp.json().get("access_token")
    if not token:
        return {"ok": False, "reason": "missing graph access token"}
    return {"ok": True, "token": token}


def send_text_to_graph_channel(text: str, team_id: str | None = None, channel_id: str | None = None) -> dict:
    target_team_id = team_id or getattr(settings, "teams_graph_team_id", "")
    target_channel_id = channel_id or getattr(settings, "teams_graph_channel_id", "") or settings.teams_channel_id
    if settings.teams_proactive_mode != "graph":
        return {"sent": False, "reason": "graph mode is not enabled"}
    if not target_team_id or not target_channel_id:
        return {"sent": False, "reason": "missing graph channel target"}

    token_result = _get_graph_access_token()
    if not token_result.get("ok"):
        return {"sent": False, "reason": token_result.get("reason", "graph token error")}

    url = f"https://graph.microsoft.com/v1.0/teams/{target_team_id}/channels/{target_channel_id}/messages"
    headers = {"Authorization": f"Bearer {token_result['token']}", "Content-Type": "application/json"}
    payload = {"body": {"contentType": "text", "content": text}}
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=10.0)
    except Exception:
        return {"sent": False, "reason": "graph post failed"}
    return {
        "sent": resp.status_code in (200, 201, 202),
        "status_code": resp.status_code,
        "reason": None if resp.status_code in (200, 201, 202) else f"graph post failed: {resp.status_code}",
    }
