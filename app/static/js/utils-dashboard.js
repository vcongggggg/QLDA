function fmtDateTime(value) {
  return safeDate(value);
}

function safeDate(value, fallback = '-') {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;
  return date.toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function dueStateLabel(value) {
  return { on_time: 'Dung han', late: 'Tre han', overdue: 'Qua han' }[value] || value || '-';
}

function dueStateClass(value) {
  return { on_time: 'due-on-time', late: 'due-late', overdue: 'due-overdue' }[value] || 'due-on-time';
}

function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function statusLabel(s) {
  const m = {
    active: 'Hoat dong',
    on_hold: 'Tam dung',
    done: 'Hoan thanh',
    archived: 'Luu tru',
    todo: 'Chua lam',
    doing: 'Dang lam',
  };
  return m[s] || s;
}

function diffLabel(d) {
  return { easy: 'De', medium: 'Trung binh', hard: 'Kho' }[d] || d;
}

function priorityLabel(p) {
  return { low: 'Thap', medium: 'Trung binh', high: 'Cao', urgent: 'Khan cap' }[p] || p || 'Trung binh';
}

function priorityShortLabel(p) {
  return { low: 'Thap', medium: 'T.Binh', high: 'Cao', urgent: 'Khan cap' }[p] || p || 'T.Binh';
}

function tierClass(score) {
  if (!score) return 'tier-D';
  if (score >= 90) return 'tier-A';
  if (score >= 70) return 'tier-B';
  if (score >= 50) return 'tier-C';
  return 'tier-D';
}

function tierLabel(score) {
  if (!score) return 'Chua co du lieu';
  if (score >= 90) return 'Xuat sac';
  if (score >= 70) return 'Tot';
  if (score >= 50) return 'Dat';
  return 'Can cai thien';
}

function scoreColor(score) {
  if (!score) return '#94A3B8';
  if (score >= 90) return '#059669';
  if (score >= 70) return '#2563EB';
  if (score >= 50) return '#D97706';
  return '#DC2626';
}

function formatPlanKey(key) {
  const m = {
    task_crud: 'Task CRUD (tao/sua/xoa)',
    kpi_engine: 'KPI Engine',
    sprint_management: 'Quan ly Sprint',
    project_management: 'Quan ly Du an',
    csv_xlsx_reports: 'Bao cao CSV/XLSX',
    pdf_reports: 'Bao cao PDF',
    teams_tab_integration: 'Teams Tab tich hop',
    teams_bot_scaffold: 'Teams Bot scaffold',
    azure_ad_sso: 'Azure AD SSO (production)',
    full_backlog_coverage: 'Toan bo backlog',
    docker_deployment: 'Docker deployment',
    ci_pipeline: 'CI/CD Pipeline',
  };
  return m[key] || key.replace(/_/g, ' ');
}

function listToLines(value) {
  return Array.isArray(value) ? value.filter(Boolean).join('\n') : '';
}

function linesToList(value) {
  return String(value || '')
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean);
}

function dashboardRoleLabel(role = currentRoleCode()) {
  return {
    ADMIN: 'Admin',
    MANAGER: 'Manager',
    LEADER: 'Leader',
    MEMBER: 'Member',
    HR: 'HR',
    AUDITOR: 'Auditor',
  }[role] || role || 'User';
}

function dashboardCompletion(done, total) {
  if (!total) return '0%';
  return `${Math.round(Number(done || 0) * 100 / Number(total || 0))}%`;
}

function dashboardDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleDateString('vi-VN');
}

function dashboardNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function dashboardAsOfDate() {
  if (typeof DEFAULT_WORK_DATE !== 'undefined' && DEFAULT_WORK_DATE) {
    return new Date(`${DEFAULT_WORK_DATE}T12:00:00`);
  }
  return new Date();
}

function dashboardTaskDueState(task, asOf = dashboardAsOfDate()) {
  if (!task || task.status === 'done') return 'done';
  if (!task.deadline) return 'scheduled';
  const deadline = new Date(task.deadline);
  if (Number.isNaN(deadline.getTime())) return 'scheduled';
  const msLeft = deadline.getTime() - asOf.getTime();
  if (msLeft < 0) return 'overdue';
  if (msLeft <= 3 * 24 * 60 * 60 * 1000) return 'due_soon';
  return 'scheduled';
}

function dashboardStatusBadge(label, cls = 'info') {
  return `<span class="badge dashboard-badge-${cls}">${escHtml(label)}</span>`;
}

let dashboardSummaryCache = { month: null, promise: null };

function getDashboardSummary() {
  if (dashboardSummaryCache.month !== state.month || !dashboardSummaryCache.promise) {
    dashboardSummaryCache = {
      month: state.month,
      promise: api(`/dashboard/summary?month=${state.month}`),
    };
  }
  return dashboardSummaryCache.promise;
}

// Role-aware dashboard overrides. Function declarations are intentionally placed
// after the original MVP dashboard functions so these are the active versions.
function setDashboardShell() {
  const sec = document.getElementById('sec-dashboard');
  if (!sec) return;
  const role = currentRoleCode();
  const titles = {
    MEMBER: { kpi: 'KPI ca nhan', chart: 'Task cua toi', overview: 'Task cua toi' },
    ADMIN: { kpi: 'Bang xep hang KPI', chart: 'Task toan he thong', overview: 'Tien do du an' },
    AUDITOR: { kpi: 'Bao cao KPI', chart: 'Task toan he thong', overview: 'Audit gan day' },
    HR: { kpi: 'KPI nhan su', chart: 'Tong quan task', overview: 'Tien do du an' },
  };
  const copy = titles[role] || { kpi: 'KPI team', chart: 'Tien do sprint', overview: 'Tien do du an' };
  const identity = state.currentUser?.fullName || state.currentUser?.full_name || state.currentUser?.email || `User ${state.userId}`;
  sec.innerHTML = `
    <div class="dashboard-management-head">
      <div>
        <div class="dashboard-kicker">Tong quan he thong</div>
        <h2>Bang dieu khien quan ly</h2>
        <div class="dashboard-meta">${escHtml(dashboardRoleLabel(role))} · ${escHtml(state.month)} · ${escHtml(identity)} · <span id="dashboardLastUpdated">Dang tai...</span></div>
      </div>
      <div class="dashboard-head-actions">
        <span class="tag tag-yellow" id="dashboardSimulationBadge">Teams Simulation Mode</span>
        <span class="tag" id="dashboardModeBadge">Du lieu hien co</span>
      </div>
    </div>
    <div class="stat-grid" id="dashStats">
      <div class="stat-card skeleton"></div>
      <div class="stat-card skeleton"></div>
      <div class="stat-card skeleton"></div>
      <div class="stat-card skeleton"></div>
    </div>
    <div class="two-col">
      <div class="card">
        <div class="card-header">
          <h3>${icon('trophy', 'heading-icon')}${copy.kpi}</h3>
          <span class="tag" id="kpiMonth">${state.month}</span>
        </div>
        <div id="kpiRankTable"></div>
      </div>
      <div class="card">
        <div class="card-header"><h3>${icon('bar-chart', 'heading-icon')}${copy.chart}</h3></div>
        <div class="chart-wrap"><canvas id="taskChart"></canvas></div>
        <div id="taskChartSummary" class="dashboard-mini-stats"></div>
      </div>
    </div>
    <div class="card mt-16" id="urgentTasksCard">
      <div class="card-header">
        <h3>${icon('alert-triangle', 'heading-icon')}Task can xu ly gap</h3>
        <span class="tag tag-red" id="urgentTaskCount">0 task</span>
      </div>
      <div id="urgentTasksTable"><div class="skeleton" style="height:96px"></div></div>
    </div>
    <div class="card mt-16">
      <div class="card-header"><h3>${icon(role === 'MEMBER' ? 'list-checks' : 'folder', 'heading-icon')}${copy.overview}</h3></div>
      <div id="projectOverview"></div>
    </div>
    <div class="two-col mt-16">
      <div class="card" id="systemHealthCard" aria-live="polite">
        <div class="card-header"><h3>${icon('activity', 'heading-icon')}Suc khoe he thong & audit</h3></div>
        <div id="systemHealthPanel"><div class="skeleton" style="height:96px"></div></div>
      </div>
      <div class="card" id="dashboardInsightCard" aria-live="polite">
        <div class="card-header"><h3>${icon('target', 'heading-icon')}Tin hieu quan ly</h3></div>
        <div id="dashboardInsightPanel"><div class="skeleton" style="height:96px"></div></div>
      </div>
    </div>`;
}

async function loadDashboard() {
  setDashboardShell();
  dashboardSummaryCache = { month: null, promise: null };
  await getDashboardSummary().catch(() => null);
  await Promise.all([
    loadDashStats(),
    loadKpiRank(),
    loadProjectOverview(),
    loadUrgentTasks(),
    loadSystemHealth(),
    loadDashboardInsights(),
  ]);
  const lastUpdated = document.getElementById('dashboardLastUpdated');
  if (lastUpdated) {
    lastUpdated.textContent = `Cap nhat: ${new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`;
  }
}

async function loadDashStats() {
  const container = document.getElementById('dashStats');
  container.innerHTML = '';
  try {
    const d = await getDashboardSummary();
    const role = currentRoleCode();
    const metrics = await api('/monitoring/metrics').catch(() => null);
    const queue = await api('/integrations/teams/proactive/queue?status=all&limit=200').catch(() => null);
    const queuedCount = Array.isArray(queue) ? queue.filter(item => item.status === 'queued').length : metrics?.queued_notifications;
    const failedCount = Array.isArray(queue) ? queue.filter(item => item.status === 'failed').length : metrics?.failed_notifications;
    let cards;

    if (role === 'ADMIN') {
      cards = [
        { icon: 'list-checks', label: 'Tong task', value: metrics?.tasks ?? d.total_tasks ?? 0, change: `${d.done_tasks ?? 0} hoan thanh · ${dashboardCompletion(d.done_tasks, d.total_tasks)}`, cls: 'neutral' },
        { icon: 'alert-triangle', label: 'Task qua han', value: metrics?.overdue_tasks ?? d.overdue_tasks ?? 0, change: (metrics?.overdue_tasks ?? d.overdue_tasks ?? 0) > 0 ? 'Can xu ly ngay' : 'Khong co canh bao', cls: (metrics?.overdue_tasks ?? d.overdue_tasks ?? 0) > 0 ? 'down' : 'up' },
        { icon: 'target', label: 'KPI trung binh', value: (d.avg_kpi_score ?? 0).toFixed(1), cls: kpiCls(d.avg_kpi_score), change: tierLabel(d.avg_kpi_score) },
        { icon: 'activity', label: 'Teams Queue', value: `${failedCount ?? 0}/${queuedCount ?? 0}`, cls: (failedCount ?? 0) > 0 ? 'down' : 'up', change: `${failedCount ?? 0} failed · ${queuedCount ?? 0} pending` },
      ];
    } else if (role === 'MEMBER') {
      cards = [
        { icon: 'list-checks', label: 'Task cua toi', value: d.total_tasks ?? 0, change: `${d.open_tasks ?? 0} dang mo`, cls: 'neutral' },
        { icon: 'calendar', label: 'Dang lam', value: d.doing_tasks ?? 0, cls: 'neutral', change: 'Can cap nhat tien do' },
        { icon: 'alert-triangle', label: 'Task qua han', value: d.overdue_tasks ?? 0, cls: d.overdue_tasks > 0 ? 'down' : 'up', change: d.overdue_tasks > 0 ? 'Can xu ly ngay' : 'On dinh' },
        { icon: 'target', label: 'KPI ca nhan', value: (d.avg_kpi_score ?? 0).toFixed(1), cls: kpiCls(d.avg_kpi_score), change: tierLabel(d.avg_kpi_score) },
      ];
    } else {
      cards = [
        { icon: 'list-checks', label: role === 'AUDITOR' ? 'Tong task' : 'Task team', value: d.total_tasks ?? 0, change: `${d.open_tasks ?? 0} dang mo`, cls: 'neutral' },
        { icon: 'check-circle', label: 'Hoan thanh', value: d.done_tasks ?? 0, cls: 'up', change: dashboardCompletion(d.done_tasks, d.total_tasks) },
        { icon: 'alert-triangle', label: 'Task qua han', value: d.overdue_tasks ?? 0, cls: d.overdue_tasks > 0 ? 'down' : 'up', change: d.overdue_tasks > 0 ? `${d.overdue_tasks} task can xu ly` : 'On dinh' },
        { icon: 'target', label: role === 'HR' ? 'KPI nhan su' : 'KPI team', value: (d.avg_kpi_score ?? 0).toFixed(1), cls: kpiCls(d.avg_kpi_score), change: tierLabel(d.avg_kpi_score) },
      ];
    }

    container.innerHTML = cards.map(c => `
      <div class="stat-card">
        <div class="stat-icon">${icon(c.icon, 'stat-svg')}</div>
        <div class="stat-value">${escHtml(c.value)}</div>
        <div class="stat-label">${escHtml(c.label)}</div>
        ${c.change ? `<div class="stat-change ${c.cls || 'neutral'}">${escHtml(c.change)}</div>` : ''}
      </div>
    `).join('');

    const doingVisible = dashboardNumber(d.doing_tasks, Math.max(0, (d.total_tasks ?? 0) - (d.done_tasks ?? 0) - (d.overdue_tasks ?? 0)));
    renderTaskChart(d.total_tasks ?? 0, d.done_tasks ?? 0, doingVisible, d.overdue_tasks ?? 0);
    renderTaskChartSummary(d, doingVisible);
  } catch (e) {
    container.innerHTML = `<div class="stat-card"><div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>Khong tai duoc dashboard<br><small>${escHtml(e.message)}</small></div></div>`;
  }
}

function renderTaskChartSummary(d, doingVisible) {
  const el = document.getElementById('taskChartSummary');
  if (!el) return;
  el.innerHTML = [
    ['Tong task', d.total_tasks ?? 0],
    ['Hoan thanh', d.done_tasks ?? 0],
    ['Dang lam', doingVisible],
    ['Qua han', d.overdue_tasks ?? 0],
    ['Ty le hoan thanh', `${d.completion_rate ?? 0}%`],
  ].map(([label, value]) => `
    <div class="dashboard-mini-stat">
      <span>${escHtml(label)}</span>
      <strong>${escHtml(value)}</strong>
    </div>`).join('');
}

async function loadDashboardInsights() {
  const el = document.getElementById('dashboardInsightPanel');
  if (!el) return;
  try {
    const role = currentRoleCode();
    const d = await getDashboardSummary();
    if (role === 'MEMBER') {
      const tasks = await api('/tasks');
      const nextTasks = tasks
        .filter(t => t.status !== 'done')
        .sort((a, b) => new Date(a.deadline || 0) - new Date(b.deadline || 0))
        .slice(0, 3);
      el.innerHTML = dashboardInsightGrid([
        ['Task dang mo', d.open_tasks ?? 0, 'Khoi luong ca nhan'],
        ['Hoan thanh', `${d.completion_rate ?? 0}%`, 'Tien do thang hien tai'],
        ['Deadline gan nhat', nextTasks[0]?.title || '-', nextTasks[0]?.deadline ? safeDate(nextTasks[0].deadline) : 'Khong co deadline'],
      ]);
      return;
    }
    if (role === 'ADMIN') {
      const metrics = await api('/monitoring/metrics').catch(() => null);
      el.innerHTML = dashboardInsightGrid([
        ['Hoan thanh', `${d.completion_rate ?? 0}%`, 'Toan bo task dang thay'],
        ['Queue failed', metrics?.failed_notifications ?? 0, 'Suc khoe notification'],
        ['Qua han', d.overdue_tasks ?? 0, 'Can theo doi van hanh'],
      ]);
      return;
    }
    if (role === 'AUDITOR') {
      const analytics = await api(`/reports/analytics/summary?month=${state.month}`).catch(() => null);
      el.innerHTML = dashboardInsightGrid([
        ['Pham vi bao cao', analytics?.scope?.type || 'all', 'Che do doc audit'],
        ['Lien ket phu thuoc', analytics?.dependency_map?.total_dependency_edges ?? 0, 'Bang chung lap ke hoach'],
        ['Task qua han', analytics?.backlog_health?.overdue_open_tasks ?? d.overdue_tasks ?? 0, 'Tin hieu audit'],
      ]);
      return;
    }
    const analytics = await api(`/reports/analytics/summary?month=${state.month}`).catch(() => null);
    el.innerHTML = dashboardInsightGrid([
      ['Hoan thanh', `${d.completion_rate ?? 0}%`, role === 'HR' ? 'Tien do nhan su' : 'Tien do team'],
      ['Phan cong', `${analytics?.utilization?.utilization_rate ?? 0}%`, 'Ty le task co assignee'],
      ['Cycle time', analytics?.cycle_time?.avg_cycle_time_days ?? '-', 'Ngay trung binh de done'],
    ]);
  } catch (e) {
    el.innerHTML = `<div class="empty-state compact">${escHtml(e.message)}</div>`;
  }
}

function dashboardInsightGrid(items) {
  return `
    <div class="analytics-stats">
      ${items.map(([label, value, note]) => `
        <div class="analytics-stat">
          <div class="analytics-value">${escHtml(value)}</div>
          <div class="analytics-label">${escHtml(label)}</div>
          <div class="analytics-note">${escHtml(note)}</div>
        </div>`).join('')}
    </div>`;
}

async function loadKpiRank() {
  const el = document.getElementById('kpiRankTable');
  const monthEl = document.getElementById('kpiMonth');
  if (monthEl) monthEl.textContent = state.month;
  try {
    const rows = await api(`/kpi/monthly?month=${state.month}`);
    if (!rows.length) {
      el.innerHTML = `<div class="empty-state"><div>${icon('bar-chart', 'empty-icon')}</div>Chua co KPI trong thang nay.</div>`;
      return;
    }
    if (isMemberRole()) {
      const r = rows[0];
      el.innerHTML = `
        <div class="personal-kpi">
          <div class="personal-kpi-score" style="color:${scoreColor(r.score)}">${(r.score || 0).toFixed(1)}</div>
          <div><span class="tier ${tierClass(r.score)}">${tierLabel(r.score)}</span></div>
          <div class="text-sm text-muted">Dung han: ${r.done_on_time ?? 0} · Tre: ${r.done_late ?? 0} · Qua han: ${r.overdue_unfinished ?? 0}</div>
        </div>`;
      return;
    }
    el.innerHTML = `
      <div class="dashboard-table-scroll">
        <table class="rank-table dashboard-management-table">
          <thead><tr><th>Rank</th><th>Nhan su</th><th>Done dung han</th><th>Done tre</th><th>Qua han</th><th>KPI score</th><th>Danh gia</th></tr></thead>
          <tbody>
            ${rows.slice(0, 8).map((r, i) => `
              <tr>
                <td><span class="rank-badge rank-${i < 3 ? i+1 : 'other'}">${i+1}</span></td>
                <td><strong>${escHtml(r.user_name || `User ${r.user_id}`)}</strong></td>
                <td>${r.done_on_time ?? 0}</td>
                <td>${r.done_late ?? 0}</td>
                <td>${r.overdue_unfinished ?? 0}</td>
                <td><strong style="color:var(--brand)">${(r.score || 0).toFixed(1)}</strong></td>
                <td><span class="tier ${tierClass(r.score)}">${tierLabel(r.score)}</span></td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>`;
  } catch (e) {
    el.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${escHtml(e.message)}</div>`;
  }
}

async function loadProjectOverview() {
  const el = document.getElementById('projectOverview');
  try {
    if (isMemberRole()) {
      const tasks = await api('/tasks');
      if (!tasks.length) {
        el.innerHTML = `<div class="empty-state"><div>${icon('list-checks', 'empty-icon')}</div>Ban chua co task nao duoc giao.</div>`;
        return;
      }
      el.innerHTML = tasks.slice().sort((a, b) => new Date(a.deadline) - new Date(b.deadline)).slice(0, 6).map(t => `
        <div class="project-row">
          <div class="project-row-name">${escHtml(t.title)}</div>
          <span class="badge badge-${escHtml(t.status)}">${statusLabel(t.status)}</span>
          <span class="text-sm text-muted">${dashboardDate(t.deadline)}</span>
        </div>`).join('');
      return;
    }
    if (currentRoleCode() === 'LEADER') {
      const tasks = await api('/tasks');
      if (!tasks.length) {
        el.innerHTML = `<div class="empty-state"><div>${icon('list-checks', 'empty-icon')}</div>Chua co task nao trong workload.</div>`;
        return;
      }
      el.innerHTML = tasks.slice().sort((a, b) => new Date(a.deadline) - new Date(b.deadline)).slice(0, 6).map(t => `
        <div class="project-row">
          <div class="project-row-name">${escHtml(t.title)}</div>
          <span class="badge badge-${escHtml(t.status)}">${statusLabel(t.status)}</span>
          <span class="text-sm text-muted">${dashboardDate(t.deadline)}</span>
        </div>`).join('');
      return;
    }
    if (currentRoleCode() === 'AUDITOR') {
      const logs = await api('/audit/logs?limit=6').catch(() => []);
      if (!logs.length) {
        el.innerHTML = `<div class="empty-state"><div>${icon('list-checks', 'empty-icon')}</div>Chua co nhat ky audit trong khoang thoi gian nay.</div>`;
        return;
      }
      el.innerHTML = logs.map(l => `
        <div class="project-row">
          <div class="project-row-name">${escHtml(l.action)} <span class="text-sm text-muted">${escHtml(l.entity)}</span></div>
          <span class="text-sm text-muted">${fmtDateTime(l.created_at)}</span>
        </div>`).join('');
      return;
    }
    const projects = await api('/projects');
    if (!projects.length) {
      el.innerHTML = `<div class="empty-state"><div>${icon('folder', 'empty-icon')}</div>Chua co du an nao.</div>`;
      return;
    }
    const rows = await Promise.all(projects.slice(0, 6).map(async p => {
      try {
        const progress = await api(`/projects/${p.id}/progress`);
        return { ...p, progress };
      } catch {
        return { ...p, progress: { total_tasks: 0, done_tasks: 0, completion_rate: 0 } };
      }
    }));
    el.innerHTML = rows.map(p => {
      const done = p.progress?.done_tasks ?? 0;
      const total = p.progress?.total_tasks ?? 0;
      const completion = p.progress?.completion_rate ?? 0;
      const fillCls = completion >= 80 ? 'done' : completion < 30 ? 'warning' : '';
      return `
        <div class="project-row">
          <div class="project-row-name">${escHtml(p.name)}</div>
          <span class="badge badge-${escHtml(p.status)}">${statusLabel(p.status)}</span>
          <div class="project-row-bar">
            <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-3);margin-bottom:3px">
              <span>${done}/${total} tasks</span><span>${completion.toFixed(0)}%</span>
            </div>
            <div class="progress-bar"><div class="progress-fill ${fillCls}" style="width:${completion}%"></div></div>
          </div>
        </div>`;
    }).join('');
  } catch (e) {
    el.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${escHtml(e.message)}</div>`;
  }
}

async function loadUrgentTasks() {
  const el = document.getElementById('urgentTasksTable');
  const countEl = document.getElementById('urgentTaskCount');
  if (!el) return;
  try {
    const tasks = await api('/tasks');
    const asOf = dashboardAsOfDate();
    const urgent = (tasks || [])
      .filter(task => task.status !== 'done')
      .map(task => ({ ...task, due_state: dashboardTaskDueState(task, asOf) }))
      .filter(task => task.due_state === 'overdue' || task.due_state === 'due_soon')
      .sort((a, b) => {
        const stateA = a.due_state === 'overdue' ? 0 : 1;
        const stateB = b.due_state === 'overdue' ? 0 : 1;
        if (stateA !== stateB) return stateA - stateB;
        return new Date(a.deadline || '2999-12-31') - new Date(b.deadline || '2999-12-31');
      })
      .slice(0, 8);
    if (countEl) countEl.textContent = `${urgent.length} task`;
    if (!urgent.length) {
      el.innerHTML = `<div class="empty-state compact">Khong co task qua han hoac den han gan.</div>`;
      return;
    }
    el.innerHTML = `
      <div class="dashboard-table-scroll">
        <table class="rank-table dashboard-management-table">
          <thead><tr><th>Task</th><th>Nguoi phu trach</th><th>Du an</th><th>Deadline</th><th>Trang thai</th></tr></thead>
          <tbody>
            ${urgent.map(task => {
              const stateLabel = task.due_state === 'overdue' ? 'Qua han' : 'Den han gan';
              const stateCls = task.due_state === 'overdue' ? 'danger' : 'warning';
              return `
                <tr>
                  <td><strong>${escHtml(task.title)}</strong></td>
                  <td>${escHtml(task.assignee_name || `User ${task.assignee_id}`)}</td>
                  <td>${escHtml(task.project_name || 'Backlog')}</td>
                  <td>${dashboardDate(task.deadline)}</td>
                  <td>${dashboardStatusBadge(stateLabel, stateCls)}</td>
                </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>`;
  } catch (e) {
    el.innerHTML = `<div class="empty-state compact">${escHtml(e.message)}</div>`;
  }
}

async function loadSystemHealth() {
  const el = document.getElementById('systemHealthPanel');
  if (!el) return;
  const [health, metrics, teams, queue, audit] = await Promise.all([
    api('/health').catch(() => null),
    api('/monitoring/metrics').catch(() => null),
    api('/integrations/teams/health').catch(() => null),
    api('/integrations/teams/proactive/queue?status=all&limit=200').catch(() => null),
    api('/audit/logs?limit=1').catch(() => null),
  ]);
  const queuedCount = Array.isArray(queue) ? queue.filter(item => item.status === 'queued').length : metrics?.queued_notifications;
  const failedCount = Array.isArray(queue) ? queue.filter(item => item.status === 'failed').length : metrics?.failed_notifications;
  const rows = [
    ['API status', health?.status === 'ok' ? 'OK' : 'Limited', health?.status === 'ok' ? 'success' : 'warning'],
    ['Database', metrics ? 'OK' : 'Limited', metrics ? 'success' : 'warning'],
    ['Teams Simulation', teams?.mode || 'Simulation', 'info'],
    ['Graph API', teams?.real_graph_enabled === true ? 'Enabled' : 'Disabled', teams?.real_graph_enabled === true ? 'warning' : 'success'],
    ['Notification Queue', `${queuedCount ?? '-'} pending / ${failedCount ?? '-'} failed`, (failedCount ?? 0) > 0 ? 'danger' : 'success'],
    ['Last sync', new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }), 'info'],
    ['Audit logs', Array.isArray(audit) ? `${audit.length} latest event` : 'Limited', Array.isArray(audit) ? 'success' : 'warning'],
  ];
  el.innerHTML = `
    <div class="dashboard-health-grid">
      ${rows.map(([label, value, cls]) => `
        <div class="dashboard-health-item">
          <span>${escHtml(label)}</span>
          ${dashboardStatusBadge(value, cls)}
        </div>`).join('')}
    </div>`;
}

function hashStringToColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const h = Math.abs(hash % 360);
  const bg = `hsl(${h}, 70%, 92%)`;
  const fg = `hsl(${h}, 80%, 30%)`;
  const border = `hsl(${h}, 60%, 80%)`;
  return { bg, fg, border };
}
