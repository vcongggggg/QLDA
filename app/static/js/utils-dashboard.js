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
  return { on_time: 'Đúng hạn', late: 'Trễ hạn', overdue: 'Quá hạn' }[value] || value || '-';
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

function listToLines(value) {
  return Array.isArray(value) ? value.filter(Boolean).join('\n') : '';
}

function linesToList(value) {
  return String(value || '')
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean);
}

// Role-aware dashboard overrides. Function declarations are intentionally placed
// after the original MVP dashboard functions so these are the active versions.
function setDashboardShell() {
  const sec = document.getElementById('sec-dashboard');
  if (!sec) return;
  const role = currentRoleCode();
  const titles = {
    MEMBER: { kpi: 'KPI cá nhân', chart: 'Progress cá nhân', overview: 'Task của tôi' },
    ADMIN: { kpi: 'Global analytics', chart: 'Task toàn hệ thống', overview: 'System health & audit' },
    AUDITOR: { kpi: 'Báo cáo hệ thống', chart: 'Task toàn hệ thống', overview: 'Audit gần đây' },
    HR: { kpi: 'KPI nhân sự', chart: 'Tổng quan task', overview: 'Nhân sự & phòng ban' },
  };
  const copy = titles[role] || { kpi: 'KPI team', chart: 'Sprint progress', overview: 'Team workload' };
  sec.innerHTML = `
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
      </div>
    </div>
    <div class="card mt-16">
      <div class="card-header"><h3>${icon(role === 'MEMBER' ? 'list-checks' : 'folder', 'heading-icon')}${copy.overview}</h3></div>
      <div id="projectOverview"></div>
    </div>
    <div class="card mt-16" id="dashboardInsightCard" aria-live="polite">
      <div class="card-header"><h3>${icon('activity', 'heading-icon')}Role insights</h3></div>
      <div id="dashboardInsightPanel"><div class="skeleton" style="height:96px"></div></div>
    </div>`;
}

async function loadDashboard() {
  setDashboardShell();
  await Promise.all([loadDashStats(), loadKpiRank(), loadProjectOverview(), loadDashboardInsights()]);
}

async function loadDashStats() {
  const container = document.getElementById('dashStats');
  container.innerHTML = '';
  try {
    const d = await api(`/dashboard/summary?month=${state.month}`);
    const role = currentRoleCode();
    let cards;
    if (role === 'ADMIN') {
      const metrics = await api('/monitoring/metrics').catch(() => null);
      cards = [
        { icon: 'list-checks', label: 'Users', value: metrics?.users ?? '-', change: 'Tài khoản hệ thống' },
        { icon: 'folder', label: 'Projects', value: metrics?.projects ?? 0, change: 'Danh mục đang theo dõi' },
        { icon: 'alert-triangle', label: 'Overdue', value: metrics?.overdue_tasks ?? d.overdue_tasks ?? 0, cls: 'down', change: 'Cần xử lý' },
        { icon: 'activity', label: 'Health', value: (metrics?.failed_notifications ?? 0) > 0 ? 'Warn' : 'OK', cls: (metrics?.failed_notifications ?? 0) > 0 ? 'down' : 'up', change: 'System health' },
      ];
    } else if (role === 'MEMBER') {
      cards = [
        { icon: 'list-checks', label: 'Task của tôi', value: d.total_tasks ?? 0, change: '' },
        { icon: 'calendar', label: 'Đang làm', value: d.doing_tasks ?? 0, cls: 'neutral', change: 'Cần cập nhật tiến độ' },
        { icon: 'alert-triangle', label: 'Deadline gần', value: d.overdue_tasks ?? 0, cls: d.overdue_tasks > 0 ? 'down' : 'up', change: d.overdue_tasks > 0 ? 'Có task quá hạn' : 'Không có quá hạn' },
        { icon: 'target', label: 'KPI cá nhân', value: (d.avg_kpi_score ?? 0).toFixed(1), cls: kpiCls(d.avg_kpi_score), change: kpiTier(d.avg_kpi_score) },
      ];
    } else {
      cards = [
        { icon: 'list-checks', label: role === 'AUDITOR' ? 'Total tasks' : 'Team workload', value: d.total_tasks ?? 0, change: '' },
        { icon: 'check-circle', label: 'Hoàn thành', value: d.done_tasks ?? 0, cls: 'up', change: pct(d.done_tasks, d.total_tasks) },
        { icon: 'alert-triangle', label: 'Overdue tasks', value: d.overdue_tasks ?? 0, cls: 'down', change: d.overdue_tasks > 0 ? `${d.overdue_tasks} task cần xử lý` : 'Tốt' },
        { icon: 'target', label: role === 'HR' ? 'KPI nhân sự' : 'KPI team', value: (d.avg_kpi_score ?? 0).toFixed(1), cls: kpiCls(d.avg_kpi_score), change: kpiTier(d.avg_kpi_score) },
      ];
    }
    container.innerHTML = cards.map(c => `
      <div class="stat-card">
        <div class="stat-icon">${icon(c.icon, 'stat-svg')}</div>
        <div class="stat-value">${escHtml(c.value)}</div>
        <div class="stat-label">${escHtml(c.label)}</div>
        ${c.change ? `<div class="stat-change ${c.cls || 'neutral'}">${c.change}</div>` : ''}
      </div>
    `).join('');
    renderTaskChart(d.total_tasks ?? 0, d.done_tasks ?? 0, (d.total_tasks ?? 0) - (d.done_tasks ?? 0) - (d.overdue_tasks ?? 0), d.overdue_tasks ?? 0);
  } catch (e) {
    container.innerHTML = `<div class="stat-card"><div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>Không tải được dashboard<br><small>${escHtml(e.message)}</small></div></div>`;
  }
}

async function loadDashboardInsights() {
  const el = document.getElementById('dashboardInsightPanel');
  if (!el) return;
  try {
    const role = currentRoleCode();
    const d = await api(`/dashboard/summary?month=${state.month}`);
    if (role === 'MEMBER') {
      const tasks = await api('/tasks');
      const nextTasks = tasks
        .filter(t => t.status !== 'done')
        .sort((a, b) => new Date(a.deadline || 0) - new Date(b.deadline || 0))
        .slice(0, 3);
      el.innerHTML = dashboardInsightGrid([
        ['Open tasks', d.open_tasks ?? 0, 'Personal workload'],
        ['Completion', `${d.completion_rate ?? 0}%`, 'My monthly task progress'],
        ['Next due', nextTasks[0]?.title || '-', nextTasks[0]?.deadline ? safeDate(nextTasks[0].deadline) : 'No open deadline'],
      ]);
      return;
    }
    if (role === 'ADMIN') {
      const metrics = await api('/monitoring/metrics').catch(() => null);
      el.innerHTML = dashboardInsightGrid([
        ['Completion', `${d.completion_rate ?? 0}%`, 'All visible tasks'],
        ['Failed queue', metrics?.failed_notifications ?? 0, 'Notification health'],
        ['Overdue', d.overdue_tasks ?? 0, 'Needs operational follow-up'],
      ]);
      return;
    }
    if (role === 'AUDITOR') {
      const analytics = await api(`/reports/analytics/summary?month=${state.month}`).catch(() => null);
      el.innerHTML = dashboardInsightGrid([
        ['Report scope', analytics?.scope?.type || 'all', 'Read-only evidence view'],
        ['Dependency edges', analytics?.dependency_map?.total_dependency_edges ?? 0, 'Planning traceability'],
        ['Overdue open', analytics?.backlog_health?.overdue_open_tasks ?? d.overdue_tasks ?? 0, 'Audit signal'],
      ]);
      return;
    }
    const analytics = await api(`/reports/analytics/summary?month=${state.month}`).catch(() => null);
    el.innerHTML = dashboardInsightGrid([
      ['Completion', `${d.completion_rate ?? 0}%`, role === 'HR' ? 'People workload progress' : 'Team delivery progress'],
      ['Utilization', `${analytics?.utilization?.utilization_rate ?? 0}%`, 'Assigned task coverage'],
      ['Cycle time', analytics?.cycle_time?.avg_cycle_time_days ?? '-', 'Average done-task days'],
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
      el.innerHTML = `<div class="empty-state"><div>${icon('bar-chart', 'empty-icon')}</div>Chưa có KPI trong tháng này.</div>`;
      return;
    }
    if (isMemberRole()) {
      const r = rows[0];
      el.innerHTML = `
        <div class="personal-kpi">
          <div class="personal-kpi-score" style="color:${scoreColor(r.score)}">${(r.score || 0).toFixed(1)}</div>
          <div><span class="tier ${tierClass(r.score)}">${tierLabel(r.score)}</span></div>
          <div class="text-sm text-muted">Hoàn thành đúng hạn: ${r.done_on_time ?? 0} • Quá hạn: ${r.overdue_unfinished ?? r.overdue ?? 0}</div>
        </div>`;
      return;
    }
    el.innerHTML = `
      <table class="rank-table">
        <thead><tr><th>#</th><th>Nhân sự</th><th>Điểm KPI</th><th>Xếp loại</th></tr></thead>
        <tbody>
          ${rows.slice(0, 8).map((r, i) => `
            <tr>
              <td><span class="rank-badge rank-${i < 3 ? i+1 : 'other'}">${i+1}</span></td>
              <td><strong>${escHtml(r.user_name || `User ${r.user_id}`)}</strong></td>
              <td><strong style="color:var(--brand)">${(r.score || 0).toFixed(1)}</strong></td>
              <td><span class="tier ${tierClass(r.score)}">${tierLabel(r.score)}</span></td>
            </tr>`).join('')}
        </tbody>
      </table>`;
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
        el.innerHTML = `<div class="empty-state"><div>${icon('list-checks', 'empty-icon')}</div>Bạn chưa có task nào được giao.</div>`;
        return;
      }
      el.innerHTML = tasks.slice().sort((a, b) => new Date(a.deadline) - new Date(b.deadline)).slice(0, 6).map(t => `
        <div class="project-row">
          <div class="project-row-name">${escHtml(t.title)}</div>
          <span class="badge badge-${escHtml(t.status)}">${statusLabel(t.status)}</span>
          <span class="text-sm text-muted">${new Date(t.deadline).toLocaleDateString('vi-VN')}</span>
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
          <span class="text-sm text-muted">${new Date(t.deadline).toLocaleDateString('vi-VN')}</span>
        </div>`).join('');
      return;
    }
    if (currentRoleCode() === 'AUDITOR') {
      const logs = await api('/audit/logs?limit=6').catch(() => []);
      if (!logs.length) {
        el.innerHTML = `<div class="empty-state"><div>${icon('list-checks', 'empty-icon')}</div>Chưa có nhật ký audit trong khoảng thời gian này.</div>`;
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
      el.innerHTML = `<div class="empty-state"><div>${icon('folder', 'empty-icon')}</div>Chưa có dự án nào.</div>`;
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
