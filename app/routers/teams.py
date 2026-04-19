from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.auth import get_current_user, require_roles
from app.proactive_worker import process_notification_queue
from app.repository import (
    all_tasks_with_users,
    create_audit_log,
    get_notification_by_id,
    list_notifications,
    queue_notification,
    requeue_notification,
    upsert_teams_conversation_ref,
    upsert_user_from_aad,
)
from app.schemas import (
    NotificationQueueOut,
    QueueProcessOut,
    TeamsBotActivity,
    UserOut,
)
from app.settings import settings
from app.teams_auth import get_teams_claims, get_teams_user_identity
from app.teams_bot import build_deadline_card, find_tasks_due_within_24h, send_card_to_teams_webhook

router = APIRouter(tags=["teams"])


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
    aad_object_id = None
    if activity.from_property:
        aad_object_id = activity.from_property.get("aadObjectId") or activity.from_property.get("id")
    conversation_id = activity.conversation.get("id") if activity.conversation else None
    if conversation_id:
        upsert_teams_conversation_ref(
            user_id=None,
            aad_object_id=aad_object_id,
            conversation_id=conversation_id,
            service_url=activity.serviceUrl,
            tenant_id=(activity.conversation or {}).get("tenantId"),
            channel_id=activity.channelId,
        )

    if activity.type != "message":
        return {"type": "message", "text": "Event received"}

    text = (activity.text or "").strip().lower()
    commands = {
        "/help": "TeamsWork bot commands: /help, /kpi-me, /my-deadlines",
        "help": "TeamsWork bot commands: /help, /kpi-me, /my-deadlines",
        "/kpi-me": f"Xem chi tiết KPI tại tab TeamsWork. Kỳ hiện tại: {datetime.now(timezone.utc).strftime('%Y-%m')}",
        "kpi": f"Xem chi tiết KPI tại tab TeamsWork. Kỳ hiện tại: {datetime.now(timezone.utc).strftime('%Y-%m')}",
        "/my-deadlines": "Mở tab TeamsWork để xem deadline sắp tới trong 24h.",
        "deadlines": "Mở tab TeamsWork để xem deadline sắp tới trong 24h.",
    }
    return {"type": "message", "text": commands.get(text, "Lệnh không hợp lệ. Dùng /help")}


@router.post("/integrations/teams/proactive/queue", response_model=NotificationQueueOut)
def queue_proactive_notification(
    message: str = Query(..., min_length=2),
    user_id: int | None = Query(default=None),
    max_attempts: int = Query(default=3, ge=1, le=10),
    current_user: dict = Depends(get_current_user),
) -> dict:
    require_roles(current_user, {"admin", "manager", "hr"})
    item = queue_notification(
        user_id=user_id,
        channel="teams",
        payload={"type": "message", "text": message},
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
    limit: int = Query(default=50, ge=1, le=200),
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
    html = f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
  <title>TeamsWork Production Tab</title>
  <script src='https://res.cdn.office.net/teams-js/2.19.0/js/MicrosoftTeams.min.js'></script>
  <style>
    :root{{--brand:#2b579a;--bg:#f4f6fb;--card:#fff;--border:#dde5f0;--text:#1e2a3a}}
    *{{box-sizing:border-box}}body{{margin:0;font-family:Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--text)}}
    .wrap{{max-width:1100px;margin:0 auto;padding:16px}}
    .head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}}
    .logo{{font-size:20px;font-weight:700;color:var(--brand)}}
    .btn{{border:1px solid var(--brand);background:#fff;color:var(--brand);padding:7px 14px;border-radius:8px;cursor:pointer;font-size:13px}}
    .grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}}
    .card{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px}}
    .k{{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.5px}}
    .v{{font-size:26px;font-weight:700;color:var(--brand);margin-top:2px}}
    .board{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
    .col{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px}}
    .col h3{{margin:0 0 10px 0;font-size:13px;font-weight:600;color:#374151;display:flex;align-items:center;gap:6px}}
    .badge{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}}
    .badge-todo{{background:#f3f4f6;color:#6b7280}}.badge-doing{{background:#fef3c7;color:#d97706}}.badge-done{{background:#d1fae5;color:#059669}}
    .task{{border:1px solid var(--border);border-radius:10px;padding:10px;margin-bottom:8px;background:#fafbff}}
    .task .t{{font-size:13px;font-weight:600;margin-bottom:4px}}.task .m{{font-size:11px;color:#6b7280}}
    @media(max-width:900px){{.grid{{grid-template-columns:repeat(2,1fr)}}.board{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
  <div class='wrap'>
    <div class='head'>
      <div class='logo'>📋 TeamsWork</div>
      <button class='btn' id='refresh'>↻ Làm mới</button>
    </div>
    <div class='grid'>
      <div class='card'><div class='k'>Tổng công việc</div><div class='v' id='total'>-</div></div>
      <div class='card'><div class='k'>Hoàn thành</div><div class='v' id='done' style='color:#059669'>-</div></div>
      <div class='card'><div class='k'>Quá hạn</div><div class='v' id='overdue' style='color:#dc2626'>-</div></div>
      <div class='card'><div class='k'>KPI trung bình</div><div class='v' id='kpi'>-</div></div>
    </div>
    <div class='board'>
      <div class='col'><h3><span class='badge badge-todo'>To Do</span></h3><div id='col-todo'></div></div>
      <div class='col'><h3><span class='badge badge-doing'>Đang làm</span></h3><div id='col-doing'></div></div>
      <div class='col'><h3><span class='badge badge-done'>Hoàn thành</span></h3><div id='col-done'></div></div>
    </div>
  </div>
  <script>
    const month=new Date().toISOString().slice(0,7);
    function card(t){{return`<div class="task"><div class="t">${{t.title}}</div><div class="m">SP: ${{t.story_points}} · Deadline: ${{(t.deadline||'').slice(0,10)}}</div></div>`;}}
    async function load(){{
      let uid=localStorage.getItem('tw_uid')||'1';
      const h={{'X-User-Id':uid}};
      try{{
        await microsoftTeams.app.initialize();
        const tok=await microsoftTeams.authentication.getAuthToken({{resources:[]}});
        const me=await fetch('{settings.app_base_url}/integrations/teams/aad/sync',{{method:'POST',headers:{{Authorization:'Bearer '+tok}}}});
        if(me.ok){{const u=await me.json();uid=String(u.id);localStorage.setItem('tw_uid',uid);h['X-User-Id']=uid;}}
      }}catch(_){{}}
      const d=await fetch('{settings.app_base_url}/dashboard/summary?month='+month,{{headers:h}}).then(r=>r.json()).catch(()=>({{}}));
      document.getElementById('total').textContent=d.total_tasks??'-';
      document.getElementById('done').textContent=d.done_tasks??'-';
      document.getElementById('overdue').textContent=d.overdue_tasks??'-';
      document.getElementById('kpi').textContent=d.avg_kpi_score??'-';
      const tasks=await fetch('{settings.app_base_url}/tasks',{{headers:h}}).then(r=>r.json()).catch(()=>[]);
      document.getElementById('col-todo').innerHTML=tasks.filter(t=>t.status==='todo').map(card).join('');
      document.getElementById('col-doing').innerHTML=tasks.filter(t=>t.status==='doing').map(card).join('');
      document.getElementById('col-done').innerHTML=tasks.filter(t=>t.status==='done').map(card).join('');
    }}
    document.getElementById('refresh').onclick=load;
    load();
  </script>
</body></html>"""
    return Response(content=html, media_type="text/html")
