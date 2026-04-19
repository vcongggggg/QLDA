/* ══════════════════════════════════════════════
   TeamsWork – Client Application
   ══════════════════════════════════════════════ */

// ── State ──────────────────────────────────────
const state = {
  userId: localStorage.getItem('tw_uid') || '1',
  month: new Date().toISOString().slice(0, 7),
  currentSection: 'dashboard',
  charts: {},
};

// ── Init ───────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const mp = document.getElementById('monthPicker');
  if (mp) mp.value = state.month;

  document.getElementById('userIdInput').value = state.userId;
  loadCurrentUser();
  navigate('dashboard');
});

// ── API Helper ─────────────────────────────────
async function api(path, opts = {}) {
  const headers = { 'X-User-Id': state.userId, ...opts.headers };
  try {
    const res = await fetch(path, { ...opts, headers });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    throw e;
  }
}

// ── Toast ──────────────────────────────────────
function toast(msg, type = 'info') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type}`;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add('hidden'), 3500);
}

// ── User ───────────────────────────────────────
async function loadCurrentUser() {
  try {
    const users = await api('/users');
    const me = users.find(u => String(u.id) === String(state.userId));
    if (me) {
      document.getElementById('userName').textContent = me.full_name;
      document.getElementById('userRole').textContent = me.role;
      document.getElementById('userAvatar').textContent = me.full_name.charAt(0).toUpperCase();
    }
  } catch (_) {}
}

function changeUserId(val) {
  state.userId = String(val);
  localStorage.setItem('tw_uid', state.userId);
  loadCurrentUser();
  refreshCurrent();
}

// ── Navigation ─────────────────────────────────
const TITLES = {
  dashboard: 'Dashboard',
  kanban:    'Kanban – Bảng công việc',
  projects:  'Dự án',
  kpi:       'KPI – Chỉ số hiệu suất',
  reports:   'Báo cáo',
  teams:     'Tích hợp Microsoft Teams',
  admin:     'Quản trị hệ thống',
};

function navigate(section) {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.section === section);
  });
  document.querySelectorAll('.section').forEach(el => el.classList.add('hidden'));
  const sec = document.getElementById(`sec-${section}`);
  if (sec) sec.classList.remove('hidden');

  state.currentSection = section;
  document.getElementById('pageTitle').textContent = TITLES[section] || section;
  loadSection(section);
}

function refreshCurrent() {
  loadSection(state.currentSection);
}

function loadSection(section) {
  switch (section) {
    case 'dashboard': loadDashboard(); break;
    case 'kanban':    loadKanban();    break;
    case 'projects':  loadProjects();  break;
    case 'kpi':       loadKPI();       break;
    case 'reports':   setupReports();  break;
    case 'teams':     loadTeams();     break;
    case 'admin':     loadAdmin();     break;
  }
}

function onMonthChange(val) {
  state.month = val;
  document.getElementById('kpiMonth').textContent = val;
  document.getElementById('kpiTableMonth').textContent = val;
  if (state.currentSection === 'dashboard') loadDashboard();
  if (state.currentSection === 'kpi') loadKPI();
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// ════════════════════════════════ DASHBOARD ════

async function loadDashboard() {
  await Promise.all([loadDashStats(), loadKpiRank(), loadProjectOverview()]);
}

async function loadDashStats() {
  const container = document.getElementById('dashStats');
  container.innerHTML = '';
  try {
    const d = await api(`/dashboard/summary?month=${state.month}`);

    const cards = [
      { icon: '📋', label: 'Tổng công việc',   value: d.total_tasks   ?? 0, change: '' },
      { icon: '✅', label: 'Hoàn thành',        value: d.done_tasks    ?? 0, cls: 'up',      change: pct(d.done_tasks, d.total_tasks) },
      { icon: '⚠️', label: 'Quá hạn',           value: d.overdue_tasks ?? 0, cls: 'down',    change: d.overdue_tasks > 0 ? `${d.overdue_tasks} task cần xử lý` : 'Tốt!' },
      { icon: '🎯', label: 'KPI trung bình',    value: (d.avg_kpi_score ?? 0).toFixed(1), cls: kpiCls(d.avg_kpi_score), change: kpiTier(d.avg_kpi_score) },
    ];

    container.innerHTML = cards.map(c => `
      <div class="stat-card">
        <div class="stat-icon">${c.icon}</div>
        <div class="stat-value">${c.value}</div>
        <div class="stat-label">${c.label}</div>
        ${c.change ? `<div class="stat-change ${c.cls || 'neutral'}">${c.change}</div>` : ''}
      </div>
    `).join('');

    // Task status doughnut chart
    renderTaskChart(d.total_tasks ?? 0, d.done_tasks ?? 0,
      (d.total_tasks ?? 0) - (d.done_tasks ?? 0) - (d.overdue_tasks ?? 0),
      d.overdue_tasks ?? 0);

  } catch (e) {
    container.innerHTML = `<div class="stat-card"><div class="empty-state"><div>⚠️</div>Không tải được dữ liệu<br><small>${e.message}</small></div></div>`;
  }
}

function pct(num, total) {
  if (!total) return '–';
  return `${Math.round(num * 100 / total)}%`;
}

function kpiCls(score) {
  if (!score) return 'neutral';
  if (score >= 90) return 'up';
  if (score >= 50) return 'neutral';
  return 'down';
}

function kpiTier(score) {
  if (!score) return '–';
  if (score >= 90) return '⭐ Xuất sắc';
  if (score >= 70) return '👍 Tốt';
  if (score >= 50) return '✔️ Đạt';
  return '❗ Cần cải thiện';
}

function renderTaskChart(total, done, doing, overdue) {
  const ctx = document.getElementById('taskChart');
  if (!ctx) return;
  if (state.charts.taskChart) state.charts.taskChart.destroy();
  state.charts.taskChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Hoàn thành', 'Đang làm', 'Quá hạn'],
      datasets: [{
        data: [done, doing < 0 ? 0 : doing, overdue],
        backgroundColor: ['#10B981', '#F59E0B', '#EF4444'],
        borderWidth: 2,
        borderColor: '#fff',
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 12 }, padding: 12 } }
      },
      cutout: '65%',
    }
  });
}

async function loadKpiRank() {
  const el = document.getElementById('kpiRankTable');
  const monthEl = document.getElementById('kpiMonth');
  if (monthEl) monthEl.textContent = state.month;
  try {
    const rows = await api(`/kpi/monthly?month=${state.month}`);
    if (!rows.length) {
      el.innerHTML = `<div class="empty-state"><div>📊</div>Chưa có dữ liệu KPI tháng này</div>`;
      return;
    }
    el.innerHTML = `
      <table class="rank-table">
        <thead><tr><th>#</th><th>Nhân sự</th><th>Điểm KPI</th><th>Xếp loại</th></tr></thead>
        <tbody>
          ${rows.slice(0, 8).map((r, i) => `
            <tr>
              <td><span class="rank-badge rank-${i < 3 ? i+1 : 'other'}">${i+1}</span></td>
              <td><strong>${r.user_name || `User ${r.user_id}`}</strong></td>
              <td><strong style="color:var(--brand)">${(r.score || 0).toFixed(1)}</strong></td>
              <td><span class="tier ${tierClass(r.score)}">${tierLabel(r.score)}</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  } catch (e) {
    el.innerHTML = `<div class="empty-state"><div>⚠️</div>${e.message}</div>`;
  }
}

async function loadProjectOverview() {
  const el = document.getElementById('projectOverview');
  try {
    const projects = await api('/projects');
    if (!projects.length) {
      el.innerHTML = `<div class="empty-state"><div>📁</div>Chưa có dự án nào</div>`;
      return;
    }
    const rows = await Promise.all(
      projects.slice(0, 6).map(async p => {
        try {
          const progress = await api(`/projects/${p.id}/progress`);
          return { ...p, progress };
        } catch {
          return { ...p, progress: { total_tasks: 0, done_tasks: 0, progress_percent: 0 } };
        }
      })
    );
    el.innerHTML = rows.map(p => {
      const pct = p.progress?.progress_percent ?? 0;
      const fillCls = pct >= 80 ? 'done' : pct < 30 ? 'warning' : '';
      return `
        <div class="project-row">
          <div class="project-row-name">${p.name}</div>
          <span class="badge badge-${p.status}">${statusLabel(p.status)}</span>
          <div class="project-row-bar">
            <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-3);margin-bottom:3px">
              <span>${p.progress?.done_tasks ?? 0}/${p.progress?.total_tasks ?? 0} tasks</span>
              <span>${pct.toFixed(0)}%</span>
            </div>
            <div class="progress-bar"><div class="progress-fill ${fillCls}" style="width:${pct}%"></div></div>
          </div>
        </div>`;
    }).join('');
  } catch (e) {
    el.innerHTML = `<div class="empty-state"><div>⚠️</div>${e.message}</div>`;
  }
}

// ════════════════════════════════ KANBAN ═══════

async function loadKanban() {
  // Populate project filter
  const sel = document.getElementById('kanbanProjectFilter');
  if (sel.options.length === 1) {
    try {
      const projects = await api('/projects');
      projects.forEach(p => {
        const o = document.createElement('option');
        o.value = p.id; o.textContent = p.name;
        sel.appendChild(o);
      });
    } catch (_) {}
  }

  const projectId = sel.value;
  let url = '/tasks';
  if (projectId) url += `?project_id=${projectId}`;

  const cols = {
    todo:  document.getElementById('col-todo'),
    doing: document.getElementById('col-doing'),
    done:  document.getElementById('col-done'),
  };

  Object.values(cols).forEach(c => { c.innerHTML = '<div class="skeleton" style="height:64px;margin:4px 0"></div>'; });

  try {
    const tasks = await api(url);
    const grouped = { todo: [], doing: [], done: [] };
    tasks.forEach(t => { if (grouped[t.status]) grouped[t.status].push(t); });

    document.getElementById('cnt-todo').textContent  = grouped.todo.length;
    document.getElementById('cnt-doing').textContent = grouped.doing.length;
    document.getElementById('cnt-done').textContent  = grouped.done.length;
    document.getElementById('kanbanCount').textContent = `${tasks.length} công việc`;

    Object.entries(grouped).forEach(([status, items]) => {
      const col = cols[status];
      if (!items.length) {
        col.innerHTML = `<div class="empty-state" style="padding:20px"><div>📭</div>Trống</div>`;
        return;
      }
      col.innerHTML = items.map(t => taskCard(t)).join('');
    });
  } catch (e) {
    Object.values(cols).forEach(c => {
      c.innerHTML = `<div class="empty-state"><div>⚠️</div>${e.message}</div>`;
    });
  }
}

function taskCard(t) {
  const now = new Date();
  const deadline = new Date(t.deadline);
  const isOverdue = t.status !== 'done' && deadline < now;
  const daysLeft = Math.ceil((deadline - now) / 86400000);
  const deadlineStr = deadline.toLocaleDateString('vi-VN');

  const nextStatus = t.status === 'todo' ? 'doing' : t.status === 'doing' ? 'done' : null;
  const nextLabel  = nextStatus === 'doing' ? '▶ Bắt đầu' : nextStatus === 'done' ? '✅ Hoàn thành' : '';

  return `
    <div class="task-card">
      <div class="task-card-title">${escHtml(t.title)}</div>
      <div class="task-card-meta">
        <span class="task-card-sp">SP: ${t.story_points}</span>
        <span class="badge badge-${t.difficulty}">${diffLabel(t.difficulty)}</span>
        <span class="task-card-deadline ${isOverdue ? 'overdue' : ''}">
          ${isOverdue ? '⚠️' : '📅'} ${deadlineStr}
          ${!isOverdue && daysLeft >= 0 ? `(${daysLeft}d)` : ''}
        </span>
      </div>
      ${nextStatus ? `
        <div class="task-card-actions">
          <button class="btn-mini" onclick="moveTask(${t.id}, '${nextStatus}')">${nextLabel}</button>
        </div>` : ''}
    </div>`;
}

async function moveTask(taskId, newStatus) {
  try {
    await api(`/tasks/${taskId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    });
    toast(`Đã cập nhật trạng thái: ${statusLabel(newStatus)}`, 'success');
    loadKanban();
  } catch (e) {
    toast(`Lỗi: ${e.message}`, 'error');
  }
}

// ════════════════════════════════ PROJECTS ═════

async function loadProjects() {
  const grid = document.getElementById('projectGrid');
  const statusFilter = document.getElementById('projectStatusFilter').value;
  grid.innerHTML = '<div class="skeleton" style="height:160px"></div>'.repeat(3);

  let url = '/projects';
  if (statusFilter) url += `?status=${statusFilter}`;

  try {
    const projects = await api(url);
    document.getElementById('projectCount').textContent = `${projects.length} dự án`;

    if (!projects.length) {
      grid.innerHTML = `<div class="card" style="grid-column:1/-1"><div class="empty-state"><div>📁</div>Không có dự án nào</div></div>`;
      return;
    }

    const withProgress = await Promise.all(
      projects.map(async p => {
        try {
          const progress = await api(`/projects/${p.id}/progress`);
          return { ...p, progress };
        } catch {
          return { ...p, progress: null };
        }
      })
    );

    grid.innerHTML = withProgress.map(p => projectCard(p)).join('');
  } catch (e) {
    grid.innerHTML = `<div class="card"><div class="empty-state"><div>⚠️</div>${e.message}</div></div>`;
  }
}

function projectCard(p) {
  const pct = p.progress?.progress_percent ?? 0;
  const fillCls = pct >= 80 ? 'done' : pct < 30 ? 'warning' : '';
  const start = p.start_date ? new Date(p.start_date).toLocaleDateString('vi-VN') : '–';
  const end   = p.end_date   ? new Date(p.end_date).toLocaleDateString('vi-VN')   : '–';

  return `
    <div class="project-card">
      <div class="project-card-header">
        <div class="project-name">${escHtml(p.name)}</div>
        <span class="badge badge-${p.status}">${statusLabel(p.status)}</span>
      </div>
      ${p.description ? `<div class="project-desc">${escHtml(p.description)}</div>` : ''}
      <div class="progress-bar-wrap">
        <div class="progress-label">
          <span>Tiến độ</span>
          <strong>${pct.toFixed(0)}%</strong>
        </div>
        <div class="progress-bar">
          <div class="progress-fill ${fillCls}" style="width:${pct}%"></div>
        </div>
      </div>
      <div class="project-footer">
        <span>📋 ${p.progress?.done_tasks ?? 0}/${p.progress?.total_tasks ?? 0} tasks</span>
        <span>📅 ${start} → ${end}</span>
      </div>
    </div>`;
}

// ════════════════════════════════ KPI ══════════

async function loadKPI() {
  document.getElementById('kpiTableMonth').textContent = state.month;
  await Promise.all([loadKpiTable(), loadKpiChart()]);
}

async function loadKpiTable() {
  const el = document.getElementById('kpiFullTable');
  el.innerHTML = '<div class="skeleton" style="height:160px;margin:8px 0"></div>';
  try {
    const rows = await api(`/kpi/monthly?month=${state.month}`);
    if (!rows.length) {
      el.innerHTML = `<div class="empty-state"><div>📊</div>Chưa có dữ liệu KPI tháng ${state.month}</div>`;
      return;
    }
    el.innerHTML = `
      <table class="kpi-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Nhân sự</th>
            <th>Điểm KPI</th>
            <th>Xếp loại</th>
            <th>Done</th>
            <th>Quá hạn</th>
            <th>Tổng SP</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((r, i) => `
            <tr>
              <td><span class="rank-badge rank-${i < 3 ? i+1 : 'other'}">${i+1}</span></td>
              <td><strong>${r.user_name || `User ${r.user_id}`}</strong></td>
              <td>
                <div class="score-bar">
                  <div class="score-fill" style="width:${Math.min(r.score, 100)}px;background:${scoreColor(r.score)}"></div>
                  <span class="score-val" style="color:${scoreColor(r.score)}">${(r.score || 0).toFixed(1)}</span>
                </div>
              </td>
              <td><span class="tier ${tierClass(r.score)}">${tierLabel(r.score)}</span></td>
              <td>${r.done_on_time ?? 0}</td>
              <td style="color:${(r.overdue ?? 0) > 0 ? 'var(--danger)' : 'inherit'}">${r.overdue ?? 0}</td>
              <td>${r.total_story_points ?? 0}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  } catch (e) {
    el.innerHTML = `<div class="empty-state"><div>⚠️</div>${e.message}</div>`;
  }
}

async function loadKpiChart() {
  const ctx = document.getElementById('kpiBarChart');
  if (!ctx) return;
  try {
    const rows = await api(`/kpi/monthly?month=${state.month}`);
    if (!rows.length) return;
    if (state.charts.kpiBar) state.charts.kpiBar.destroy();
    state.charts.kpiBar = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: rows.map(r => r.user_name || `User ${r.user_id}`),
        datasets: [{
          label: 'Điểm KPI',
          data: rows.map(r => (r.score || 0).toFixed(1)),
          backgroundColor: rows.map(r => scoreColor(r.score) + 'CC'),
          borderColor: rows.map(r => scoreColor(r.score)),
          borderWidth: 2,
          borderRadius: 6,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => `KPI: ${ctx.raw} điểm`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 120,
            grid: { color: '#F1F5F9' },
            ticks: { font: { size: 11 } }
          },
          x: {
            grid: { display: false },
            ticks: { font: { size: 11 } }
          }
        }
      }
    });
  } catch (_) {}
}

// ════════════════════════════════ REPORTS ══════

function setupReports() {
  // Nothing to load – buttons use onclick handlers
}

function downloadReport(type, fmt) {
  let url = '';
  switch (type) {
    case 'kpi':       url = `/reports/kpi.${fmt}?month=${state.month}`; break;
    case 'portfolio': url = `/reports/portfolio/summary.${fmt}`; break;
    case 'progress':  url = `/reports/projects/progress.${fmt}`; break;
  }
  if (!url) return;
  triggerDownload(url);
}

function downloadSprintReport(fmt) {
  const id = document.getElementById('sprintReportId').value;
  if (!id) { toast('Vui lòng nhập Sprint ID', 'error'); return; }
  triggerDownload(`/reports/sprints/${id}/review.${fmt}`);
}

function triggerDownload(url) {
  const a = document.createElement('a');
  a.href = url;
  a.click();
}

// ════════════════════════════════ TEAMS ════════

async function loadTeams() {
  // Update URL display
  const base = window.location.origin;
  document.getElementById('teamsTabUrl').textContent = `${base}/teams/tab`;
  document.getElementById('teamsTabProdUrl').textContent = `${base}/teams/tab/prod`;

  // Load notification queue stats
  const statsEl = document.getElementById('notifQueueStats');
  try {
    const all     = await api('/integrations/teams/proactive/queue?status=all&limit=200');
    const queued  = all.filter(n => n.status === 'queued').length;
    const sent    = all.filter(n => n.status === 'sent').length;
    const failed  = all.filter(n => n.status === 'failed').length;
    statsEl.innerHTML = `
      <div class="notif-stats">
        <div class="notif-stat">
          <div class="notif-stat-val" style="color:var(--warning)">${queued}</div>
          <div class="notif-stat-label">Chờ gửi</div>
        </div>
        <div class="notif-stat">
          <div class="notif-stat-val" style="color:var(--success)">${sent}</div>
          <div class="notif-stat-label">Đã gửi</div>
        </div>
        <div class="notif-stat">
          <div class="notif-stat-val" style="color:var(--danger)">${failed}</div>
          <div class="notif-stat-label">Thất bại</div>
        </div>
      </div>`;
  } catch (e) {
    statsEl.innerHTML = `<div class="empty-state"><div>⚠️</div>${e.message}</div>`;
  }
}

// ════════════════════════════════ ADMIN ════════

async function loadAdmin() {
  await Promise.all([loadPlanCompletion(), loadAuditLogs()]);
}

async function loadPlanCompletion() {
  const el = document.getElementById('planCompletion');
  try {
    const plan = await api('/plan/completion');
    const keys = Object.entries(plan).filter(([k]) => k !== 'overall_percent');
    el.innerHTML = `
      <div style="margin-bottom:12px">
        <div class="progress-label">
          <span>Tổng tiến độ</span>
          <strong>${plan.overall_percent ?? 0}%</strong>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${plan.overall_percent ?? 0}%"></div></div>
      </div>
      <div class="plan-list">
        ${keys.map(([k, v]) => `
          <div class="plan-item">
            <span class="plan-check">${v ? '✅' : '⬜'}</span>
            <span style="color:${v ? 'var(--success)' : 'var(--text-2)'}">${formatPlanKey(k)}</span>
          </div>`).join('')}
      </div>`;
  } catch (e) {
    el.innerHTML = `<div class="empty-state"><div>⚠️</div>${e.message}</div>`;
  }
}

async function loadAuditLogs() {
  const el = document.getElementById('auditTable');
  el.innerHTML = '<div class="skeleton" style="height:120px"></div>';
  try {
    const logs = await api('/audit/logs?limit=50');
    if (!logs.length) {
      el.innerHTML = `<div class="empty-state"><div>📋</div>Chưa có nhật ký hoạt động</div>`;
      return;
    }
    el.innerHTML = `
      <table class="audit-table">
        <thead><tr><th>Thời gian</th><th>Người dùng</th><th>Hành động</th><th>Đối tượng</th><th>Chi tiết</th></tr></thead>
        <tbody>
          ${logs.map(l => `
            <tr>
              <td style="white-space:nowrap">${new Date(l.created_at).toLocaleString('vi-VN')}</td>
              <td>User ${l.actor_user_id || '–'}</td>
              <td><code>${l.action}</code></td>
              <td><code>${l.entity}${l.entity_id ? ' #' + l.entity_id : ''}</code></td>
              <td style="color:var(--text-2)">${l.detail || '–'}</td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  } catch (e) {
    el.innerHTML = `<div class="empty-state"><div>⚠️</div>${e.message}</div>`;
  }
}

async function runSeed() {
  const btn = document.getElementById('seedBtn');
  const result = document.getElementById('seedResult');
  btn.disabled = true;
  btn.textContent = 'Đang khởi tạo...';
  try {
    const res = await api('/seed/init', { method: 'POST' });
    const count = Object.entries(res)
      .filter(([k, v]) => typeof v === 'number')
      .map(([k, v]) => `${k}: ${v}`)
      .join(', ');
    result.innerHTML = `<div style="color:var(--success);font-size:13px">✅ Khởi tạo thành công! ${count}</div>`;
    toast('Dữ liệu mẫu đã được khởi tạo', 'success');
  } catch (e) {
    result.innerHTML = `<div style="color:var(--danger);font-size:13px">❌ ${e.message}</div>`;
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Khởi tạo dữ liệu mẫu';
  }
}

// ════════════════════════════════ HELPERS ══════

function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function statusLabel(s) {
  const m = { active: 'Hoạt động', on_hold: 'Tạm dừng', done: 'Hoàn thành', archived: 'Lưu trữ', todo: 'Chưa làm', doing: 'Đang làm' };
  return m[s] || s;
}

function diffLabel(d) {
  return { easy: 'Dễ', medium: 'Trung bình', hard: 'Khó' }[d] || d;
}

function tierClass(score) {
  if (!score) return 'tier-D';
  if (score >= 90) return 'tier-A';
  if (score >= 70) return 'tier-B';
  if (score >= 50) return 'tier-C';
  return 'tier-D';
}

function tierLabel(score) {
  if (!score) return 'Chưa có dữ liệu';
  if (score >= 90) return 'Xuất sắc';
  if (score >= 70) return 'Tốt';
  if (score >= 50) return 'Đạt';
  return 'Cần cải thiện';
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
    task_crud:               'Task CRUD (tạo/sửa/xóa)',
    kpi_engine:              'KPI Engine',
    sprint_management:       'Quản lý Sprint',
    project_management:      'Quản lý Dự án',
    csv_xlsx_reports:        'Báo cáo CSV/XLSX',
    pdf_reports:             'Báo cáo PDF',
    teams_tab_integration:   'Teams Tab tích hợp',
    teams_bot_scaffold:      'Teams Bot scaffold',
    azure_ad_sso:            'Azure AD SSO (production)',
    full_backlog_coverage:   'Toàn bộ backlog',
    docker_deployment:       'Docker deployment',
    ci_pipeline:             'CI/CD Pipeline',
  };
  return m[key] || key.replace(/_/g, ' ');
}
