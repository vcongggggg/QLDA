from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.auth import get_current_user, require_roles
from app.kpi import calculate_monthly_kpi, compute_dashboard_metrics
from app.proactive_worker import process_notification_queue
from app.repository import (
    all_tasks_with_users,
    create_audit_log,
    get_notification_by_id,
    list_notifications,
    list_tasks,
    list_kpi_adjustments_by_month,
    queue_notification,
    requeue_notification,
    upsert_teams_conversation_ref,
    upsert_user_from_aad,
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
from app.teams_bot import build_deadline_card, find_tasks_due_within_24h, send_card_to_teams_webhook

router = APIRouter(tags=["teams"])


def _queue_stats() -> dict:
    rows = list_notifications(status="all", limit=200)
    return {
        "queued": sum(1 for row in rows if row.get("status") == "queued"),
        "sent": sum(1 for row in rows if row.get("status") == "sent"),
        "failed": sum(1 for row in rows if row.get("status") == "failed"),
    }


@router.get("/integrations/teams/summary", response_model=TeamsSummaryOut)
def teams_summary_endpoint(
    month: str = Query(description="YYYY-MM"),
    task_limit: int = Query(default=30, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
) -> dict:
    tasks_for_metrics = all_tasks_with_users()
    if current_user["role"] == "staff":
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

    adjustments = list_kpi_adjustments_by_month(month)
    if current_user["role"] == "staff":
        adjustments = [
            item for item in adjustments
            if int(item["user_id"]) == int(current_user["id"])
        ]
    monthly_kpi = calculate_monthly_kpi(tasks_for_metrics, month, adjustments=adjustments)
    kpi_rows = sorted(
        monthly_kpi.values(),
        key=lambda item: item["score"],
        reverse=True,
    )
    if current_user["role"] == "staff":
        kpi_rows = [row for row in kpi_rows if int(row["user_id"]) == int(current_user["id"])]

    can_manage_queue = current_user["role"] in {"admin", "manager", "hr"}
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
    let authHeaders={'X-User-Id':localStorage.getItem('tw_uid')||'1'},summaryCache=null;
    const labels={todo:'To do',doing:'Đang làm',done:'Hoàn thành',overdue:'Quá hạn',late:'Trễ',on_time:'Đúng hạn'};
    function $(id){return document.getElementById(id)}function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function safeDate(v){return v?String(v).slice(0,10):'-'}function clearError(){$('errorBanner').classList.add('hidden');$('errorBanner').textContent=''}function showError(m){$('errorBanner').textContent=m||'Không tải được dữ liệu TeamsWork. Vui lòng thử lại.';$('errorBanner').classList.remove('hidden')}
    async function api(path,opt={}){const headers={...authHeaders,...(opt.headers||{})};if(opt.body)headers['Content-Type']='application/json';const res=await fetch(baseUrl+path,{...opt,headers});if(!res.ok)throw new Error('request_failed');return res.status===204?null:res.json()}
    async function syncIdentity(){let uid=localStorage.getItem('tw_uid')||'1';authHeaders={'X-User-Id':uid};try{if(window.microsoftTeams){await microsoftTeams.app.initialize();const tok=await microsoftTeams.authentication.getAuthToken({resources:[]});const me=await fetch(baseUrl+'/integrations/teams/aad/sync',{method:'POST',headers:{Authorization:'Bearer '+tok}});if(me.ok){const u=await me.json();uid=String(u.id);localStorage.setItem('tw_uid',uid);authHeaders={'X-User-Id':uid,Authorization:'Bearer '+tok};$('identityLine').textContent='Đã đồng bộ: '+(u.full_name||u.email||('User '+uid))}}}catch(_){$('identityLine').textContent='Dev fallback: X-User-Id '+uid}}
    function setLoading(){['total','done','overdue','kpi'].forEach(id=>{$(id).textContent='-';$(id).classList.add('skeleton')});statuses.forEach(s=>{$('col-'+s).innerHTML='<div class="state" data-state="loading">Đang tải...</div>'});$('kpiRows').innerHTML='<tr><td colspan="4"><div class="state" data-state="loading">Đang tải KPI...</div></td></tr>'}
    function card(t){const next=t.status==='todo'?'doing':t.status==='doing'?'done':null;return `<button class="task" data-task-id="${esc(t.id)}" onclick="openTaskDrawer(${Number(t.id)})"><div class="t">${esc(t.title)}</div><div class="m"><span>SP ${esc(t.story_points)}</span><span>${esc(t.difficulty||'-')}</span><span>${safeDate(t.deadline)}</span><span class="badge badge-${esc(t.status)}">${esc(labels[t.status]||t.status)}</span></div><div class="task-actions">${next?`<span class="btn" onclick="event.stopPropagation(); updateTaskStatus(${Number(t.id)}, '${next}')">${esc(labels[next])}</span>`:''}</div></button>`}
    function renderBoard(tasks){$('taskCount').textContent=tasks.length+' task';$('boardEmpty').classList.toggle('hidden',tasks.length>0);statuses.forEach(s=>{const items=tasks.filter(t=>t.status===s);$('count-'+s).textContent=items.length;$('col-'+s).innerHTML=items.length?items.map(card).join(''):`<div class="state" data-state="empty">Không có task ${esc(labels[s].toLowerCase())}.</div>`})}
    function renderKpi(rows){$('kpiEmpty').classList.toggle('hidden',rows.length>0);$('kpiRows').innerHTML=rows.length?rows.slice(0,8).map(r=>`<tr><td>${esc(r.user_name)}</td><td><strong>${esc(r.score)}</strong></td><td>${esc(r.done_on_time)}</td><td>${esc((r.done_late||0)+(r.overdue_unfinished||0))}</td></tr>`).join(''):''}
    function renderSummary(summary){summaryCache=summary;const d=summary.dashboard||{};$('monthBadge').textContent=summary.month||month;$('total').textContent=d.total_tasks??'-';$('done').textContent=d.done_tasks??'-';$('overdue').textContent=d.overdue_tasks??'-';$('kpi').textContent=d.avg_kpi_score??'-';['total','done','overdue','kpi'].forEach(id=>$(id).classList.remove('skeleton'));renderBoard(summary.tasks||[]);renderKpi(summary.kpi||[]);if(summary.can_manage_queue){$('queuePanel').classList.remove('hidden');const qs=summary.queue_stats||{};$('queuedCount').textContent=qs.queued??0;$('sentCount').textContent=qs.sent??0;$('failedCount').textContent=qs.failed??0;loadQueue()}else{$('queuePanel').classList.add('hidden')}}
    async function load(){clearError();setLoading();try{await syncIdentity();renderSummary(await api('/integrations/teams/summary?month='+month))}catch(_){showError('Không tải được dashboard TeamsWork. Kiểm tra đăng nhập hoặc thử lại sau.');statuses.forEach(s=>{$('col-'+s).innerHTML='<div class="state error" data-state="error">Không tải được task.</div>'})}}
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
        if(me.ok){{const u=await me.json();uid=String(u.id);localStorage.setItem('tw_uid',uid);h['X-User-Id']=uid;h['Authorization']='Bearer '+tok;}}
      }}catch(_){{}}
      const summary=await fetch('{settings.app_base_url}/integrations/teams/summary?month='+month,{{headers:h}}).then(r=>r.json()).catch(()=>({{dashboard:{{}},tasks:[]}}));
      const d=summary.dashboard||{{}};
      document.getElementById('total').textContent=d.total_tasks??'-';
      document.getElementById('done').textContent=d.done_tasks??'-';
      document.getElementById('overdue').textContent=d.overdue_tasks??'-';
      document.getElementById('kpi').textContent=d.avg_kpi_score??'-';
      const tasks=summary.tasks||[];
      document.getElementById('col-todo').innerHTML=tasks.filter(t=>t.status==='todo').map(card).join('');
      document.getElementById('col-doing').innerHTML=tasks.filter(t=>t.status==='doing').map(card).join('');
      document.getElementById('col-done').innerHTML=tasks.filter(t=>t.status==='done').map(card).join('');
    }}
    document.getElementById('refresh').onclick=load;
    load();
  </script>
</body></html>"""
    return Response(content=html, media_type="text/html")
