from __future__ import annotations

from app.repository import list_processable_notifications, list_teams_conversation_refs, mark_notification_result
from app.settings import settings
from app.teams_bot import build_text_card, send_card_to_teams_webhook, send_text_to_graph_channel, send_text_to_teams_conversation


def process_notification_queue(limit: int = 1000) -> dict:
    queued = list_processable_notifications(limit=limit)
    processed = 0
    sent = 0
    retried = 0
    failed = 0

    for item in queued:
        processed += 1
        payload = item.get("payload") or {}
        text = payload.get("text", "TeamsWork notification")
        target = payload.get("target") or {}
        result = {"sent": False, "reason": "not attempted"}

        if settings.teams_integration_mode == "simulation":
            result = (
                {"sent": False, "reason": "simulated send failure"}
                if payload.get("simulate_failure")
                else {"sent": True, "reason": "simulation mode"}
            )
            updated = mark_notification_result(
                notification_id=int(item["id"]),
                success=bool(result.get("sent")),
                error_message=result.get("reason"),
            )
            if result.get("sent"):
                sent += 1
            elif updated and updated.get("status") == "failed":
                failed += 1
            else:
                retried += 1
            continue

        conversation_refs: list[dict] = []
        if item.get("user_id") is not None:
            conversation_refs = list_teams_conversation_refs(user_id=int(item["user_id"]), limit=1)

        if target.get("type") in {"channel", "project_channel"} or settings.teams_proactive_mode == "graph":
            result = send_text_to_graph_channel(
                text,
                team_id=target.get("team_id"),
                channel_id=target.get("channel_id"),
            )
            if not result.get("sent") and conversation_refs:
                result = send_text_to_teams_conversation(conversation_refs[0], text)
        elif settings.teams_proactive_mode == "bot" and conversation_refs:
            result = send_text_to_teams_conversation(conversation_refs[0], text)
        elif conversation_refs:
            # Prefer direct conversation when available, even in mixed mode.
            result = send_text_to_teams_conversation(conversation_refs[0], text)
            if not result.get("sent"):
                card = build_text_card(title="TeamsWork Proactive Message", message=text)
                result = send_card_to_teams_webhook(card)
        else:
            card = build_text_card(title="TeamsWork Proactive Message", message=text)
            result = send_card_to_teams_webhook(card)

        success = bool(result.get("sent"))
        updated = mark_notification_result(
            notification_id=int(item["id"]),
            success=success,
            error_message=(result.get("reason") or result.get("response_text") or "send failed"),
        )
        if success:
            sent += 1
        else:
            if updated and updated.get("status") == "failed":
                failed += 1
            else:
                retried += 1

    return {
        "processed": processed,
        "sent": sent,
        "retried": retried,
        "failed": failed,
    }
