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
