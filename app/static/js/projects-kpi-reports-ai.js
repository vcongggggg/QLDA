async function loadProjects() {
  const grid = document.getElementById('projectGrid');
  const statusFilter = document.getElementById('projectStatusFilter').value;
  grid.innerHTML = '<div class="skeleton" style="height:160px"></div>'.repeat(3);

  let url = '/projects';
  if (statusFilter) url += `?status=${statusFilter}`;

  try {
    const projects = await api(url);
    document.getElementById('projectCount').textContent = `${projects.length} d? án`;

    if (!projects.length) {
      grid.innerHTML = `<div class="card" style="grid-column:1/-1"><div class="empty-state"><div>${icon('folder', 'empty-icon')}</div>Không có d? án nào</div></div>`;
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
    grid.innerHTML = `<div class="card"><div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${e.message}</div></div>`;
  }
}

function projectCard(p) {
  const pct = p.progress?.completion_rate ?? 0;
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
          <span>Ti?n d?</span>
          <strong>${pct.toFixed(0)}%</strong>
        </div>
        <div class="progress-bar">
          <div class="progress-fill ${fillCls}" style="width:${pct}%"></div>
        </div>
      </div>
      <div class="project-footer">
        <span>${icon('list-checks', 'text-icon')} ${p.progress?.done_tasks ?? 0}/${p.progress?.total_tasks ?? 0} tasks</span>
        <span>${icon('calendar', 'text-icon')} ${start} ? ${end}</span>
      </div>
      <div class="project-footer">
        <button type="button" class="btn btn-outline btn-sm" onclick="openProjectDetail(${Number(p.id)})">Backlog / Sprint</button>
        ${canDo('sprintManage') ? `<button type="button" class="btn btn-outline btn-sm" onclick="quickCreateSprint(${Number(p.id)})">Tạo sprint</button>` : ''}
      </div>
    </div>`;
}

function showProjectCreateModal() {
  if (!canDo('projectCreate')) {
    toast('Ban khong co quyen tao project', 'error');
    return;
  }
  const form = document.getElementById('projectCreateForm');
  if (form) form.reset();
  const managerInput = document.getElementById('projectCreateManagerId');
  if (managerInput && state.currentUser?.id) managerInput.value = state.currentUser.id;
  const startInput = document.getElementById('projectCreateStart');
  const endInput = document.getElementById('projectCreateEnd');
  if (startInput && !startInput.value) startInput.value = DEFAULT_WORK_DATE;
  if (endInput && !endInput.value) endInput.value = DEFAULT_WORK_DATE;
  document.getElementById('projectCreateOverlay')?.classList.remove('hidden');
}

function closeProjectCreate() {
  document.getElementById('projectCreateOverlay')?.classList.add('hidden');
}

function dateInputToIso(value, endOfDay = false) {
  if (!value) return null;
  const suffix = endOfDay ? 'T17:00:00' : 'T09:00:00';
  const date = new Date(`${value}${suffix}`);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

async function submitProjectCreate(event) {
  event.preventDefault();
  if (!canDo('projectCreate')) {
    toast('Ban khong co quyen tao project', 'error');
    return;
  }
  const name = document.getElementById('projectCreateName').value.trim();
  const description = document.getElementById('projectCreateDescription').value.trim() || null;
  const managerValue = document.getElementById('projectCreateManagerId').value;
  const payload = {
    name,
    description,
    manager_id: managerValue ? Number(managerValue) : null,
    status: document.getElementById('projectCreateStatus').value,
    start_date: dateInputToIso(document.getElementById('projectCreateStart').value),
    end_date: dateInputToIso(document.getElementById('projectCreateEnd').value, true),
  };
  try {
    const project = await api('/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    toast('Da tao project', 'success');
    closeProjectCreate();
    await loadProjects();
    openProjectDetail(project.id);
  } catch (e) {
    toast(e.message, 'error');
  }
}

function closeProjectDetail() {
  document.getElementById('projectDetailOverlay')?.classList.add('hidden');
}

async function openProjectDetail(projectId) {
  const overlay = document.getElementById('projectDetailOverlay');
  const body = document.getElementById('projectDetailBody');
  if (!overlay || !body) return;
  overlay.classList.remove('hidden');
  body.innerHTML = '<div class="skeleton" style="height:240px"></div>';
  try {
    const [progress, backlog, sprints, members] = await Promise.all([
      api(`/projects/${projectId}/progress`).catch(() => null),
      api(`/projects/${projectId}/backlog`).catch(() => []),
      api(`/projects/${projectId}/sprints`).catch(() => []),
      api(`/projects/${projectId}/members`).catch(() => []),
    ]);
    body.innerHTML = projectDetailHtml(projectId, progress, backlog, sprints, members);
  } catch (e) {
    body.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${escHtml(e.message)}</div>`;
  }
}

function projectDetailHtml(projectId, progress, backlog, sprints, members) {
  const backlogRows = (backlog || []).map(t => `
    <tr>
      <td><strong>${escHtml(t.title)}</strong><br><span class="text-muted">#${Number(t.id)}</span></td>
      <td>${escHtml(statusLabel(t.status))}</td>
      <td>${Number(t.story_points || 0)}</td>
      <td>${new Date(t.deadline).toLocaleDateString('vi-VN')}</td>
      <td><button type="button" class="btn btn-outline btn-sm" onclick="openTaskDetail(${Number(t.id)})">Chi tiết</button></td>
    </tr>`).join('');
  const sprintOptions = (sprints || []).map(s => `<option value="${Number(s.id)}">${escHtml(s.name)} (${escHtml(s.status)})</option>`).join('');
  return `
    <div class="task-detail-section">
      <div class="task-detail-subhead">
        <h3>Progress</h3>
        <span class="tag">${Number(progress?.completion_rate || 0).toFixed(0)}%</span>
      </div>
      <div class="task-detail-grid">
        ${taskDetailField('Tasks', `${progress?.done_tasks ?? 0}/${progress?.total_tasks ?? 0}`)}
        ${taskDetailField('Overdue', progress?.overdue_tasks ?? 0)}
        ${taskDetailField('Story points', `${progress?.completed_story_points ?? 0}/${progress?.total_story_points ?? 0}`)}
        ${taskDetailField('Latest update', progress?.latest_status_update?.week_label || '-')}
        ${taskDetailField('Trend', progress?.trend_direction || 'flat')}
        ${taskDetailField('Members', members?.length ?? 0)}
      </div>
    </div>
    <div class="task-detail-section">
      <div class="task-detail-subhead">
        <h3>Sprints</h3>
        <span class="tag">${sprints?.length ?? 0}</span>
      </div>
      <div class="activity-list">
        ${(sprints || []).map(s => `<div class="activity-item"><div><strong>${escHtml(s.name)}</strong><span>${escHtml(s.status)}</span></div><div>${fmtDateTime(s.start_date)} - ${fmtDateTime(s.end_date)}</div></div>`).join('') || '<div class="empty-state compact">Chua co sprint</div>'}
      </div>
      ${canDo('sprintManage') ? `<button type="button" class="btn btn-outline btn-sm" onclick="quickCreateSprint(${Number(projectId)})">Tạo sprint</button>` : ''}
    </div>
    <div class="task-detail-section">
      <div class="task-detail-subhead">
        <h3>Backlog</h3>
        <span class="tag">${backlog?.length ?? 0}</span>
      </div>
      ${canDo('sprintManage') && (backlog || []).length && (sprints || []).length ? `
        <div class="comment-form">
          <select id="projectBacklogSprintTarget" class="select">${sprintOptions}</select>
          <button type="button" class="btn btn-primary btn-sm" onclick="moveVisibleBacklogToSprint(${Number(projectId)})">Đưa backlog vào sprint</button>
        </div>` : ''}
      <table class="kanban-list-table">
        <thead><tr><th>Task</th><th>Status</th><th>SP</th><th>Deadline</th><th></th></tr></thead>
        <tbody>${backlogRows || '<tr><td colspan="5"><div class="empty-state compact">Backlog rong</div></td></tr>'}</tbody>
      </table>
    </div>`;
}

async function quickCreateSprint(projectId) {
  if (!canDo('sprintManage')) {
    toast('Ban khong co quyen tao sprint', 'error');
    return;
  }
  const name = prompt('Ten sprint moi');
  if (!name || !name.trim()) return;
  const start = new Date();
  const end = new Date();
  end.setDate(end.getDate() + 14);
  try {
    await api(`/projects/${projectId}/sprints`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.trim(), goal: null, start_date: start.toISOString(), end_date: end.toISOString() }),
    });
    toast('Da tao sprint', 'success');
    openProjectDetail(projectId);
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function moveVisibleBacklogToSprint(projectId) {
  const sprintId = Number(document.getElementById('projectBacklogSprintTarget')?.value || 0);
  if (!sprintId) return;
  try {
    const backlog = await api(`/projects/${projectId}/backlog`);
    const taskIds = backlog.map(t => Number(t.id));
    if (!taskIds.length) return;
    const result = await api(`/projects/${projectId}/backlog/move-to-sprint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_ids: taskIds, sprint_id: sprintId }),
    });
    toast(`Da chuyen ${result.updated || 0} task`, 'success');
    openProjectDetail(projectId);
    if (state.currentSection === 'kanban') loadKanban();
  } catch (e) {
    toast(e.message, 'error');
  }
}

// -------------------------------- KPI ----------

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
      el.innerHTML = `<div class="empty-state"><div>${icon('bar-chart', 'empty-icon')}</div>Chua có d? li?u KPI tháng ${state.month}</div>`;
      return;
    }
    el.innerHTML = `
      <table class="kpi-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Nhân s?</th>
            <th>Ði?m KPI</th>
            <th>X?p lo?i</th>
            <th>Done</th>
            <th>Quá h?n</th>
            <th>T?ng SP</th>
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
    el.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${e.message}</div>`;
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
          label: 'Ði?m KPI',
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
              label: ctx => `KPI: ${ctx.raw} di?m`
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

// -------------------------------- REPORTS ------

function setupReports() {
  loadKpiReportSummary();
  loadReportAnalytics();
  loadReportSchedules();
}

function downloadReport(type, fmt) {
  if (!canDo('reportExport')) {
    toast('Ban khong co quyen xuat bao cao', 'error');
    return;
  }
  let url = '';
  switch (type) {
    case 'kpi':       url = `/reports/kpi.${fmt}?month=${state.month}`; break;
    case 'portfolio': url = `/reports/portfolio/summary.${fmt}`; break;
    case 'progress':  url = `/reports/projects/progress.${fmt}`; break;
    case 'analytics': url = `/reports/analytics.${fmt}?month=${state.month}`; break;
  }
  if (!url) return;
  triggerDownload(url);
}

function downloadSprintReport(fmt) {
  if (!canDo('reportExport')) {
    toast('Ban khong co quyen xuat bao cao', 'error');
    return;
  }
  const id = document.getElementById('sprintReportId').value;
  if (!id) { toast('Vui lòng nh?p Sprint ID', 'error'); return; }
  triggerDownload(`/reports/sprints/${id}/review.${fmt}`);
}

function triggerDownload(url) {
  const a = document.createElement('a');
  a.href = url;
  a.click();
}

async function loadKpiReportSummary() {
  const el = document.getElementById('kpiReportSummary');
  if (!el) return;
  try {
    const data = await api(`/reports/kpi/summary?month=${state.month}`);
    el.textContent = `${data.user_count || 0} users | avg ${data.average_score || 0} | below target ${data.below_target_count || 0}`;
  } catch (e) {
    el.textContent = e.message;
  }
}

async function loadReportAnalytics() {
  const stats = document.getElementById('analyticsStats');
  const table = document.getElementById('analyticsWorkloadTable');
  if (stats) stats.innerHTML = '<div class="skeleton" style="height:96px"></div>';
  try {
    const data = await api(`/reports/analytics/summary?month=${state.month}`);
    const productivity = data.productivity || {};
    const backlog = data.backlog_health || {};
    const cycleTime = data.cycle_time || {};
    stats.innerHTML = `
      <div class="stat-mini-grid">
        <div><strong>${productivity.done_tasks ?? 0}</strong><span>Done</span></div>
        <div><strong>${productivity.completion_rate ?? 0}%</strong><span>Completion</span></div>
        <div><strong>${backlog.overdue_open_tasks ?? 0}</strong><span>Overdue</span></div>
        <div><strong>${cycleTime.avg_cycle_time_days ?? '-'}</strong><span>Avg days</span></div>
      </div>`;
    const workload = data.workload_distribution || [];
    renderAnalyticsWorkloadChart(workload);
    renderAnalyticsStatusChart(data.task_status || {});
    renderAnalyticsVelocityChart(data.velocity || []);
    renderAnalyticsProjectEffortChart(data.project_effort || []);
    renderAnalyticsDependencySummary(data.dependency_map || {});
    if (table) {
      table.innerHTML = workload.length ? `
        <table class="audit-table compact-table">
          <thead><tr><th>User</th><th>Open</th><th>Done</th><th>Overdue</th><th>SP</th></tr></thead>
          <tbody>${workload.map(row => `<tr><td>${escHtml(row.assignee_name || `User ${row.user_id}`)}</td><td>${row.open_tasks ?? 0}</td><td>${row.done_tasks ?? 0}</td><td>${row.overdue_open_tasks ?? 0}</td><td>${row.story_points ?? 0}</td></tr>`).join('')}</tbody>
        </table>` : '<div class="empty-state compact">No workload data.</div>';
    }
  } catch (e) {
    if (stats) stats.innerHTML = `<div class="empty-state compact">${escHtml(e.message)}</div>`;
    renderAnalyticsWorkloadChart([]);
    renderAnalyticsStatusChart({});
    renderAnalyticsVelocityChart([]);
    renderAnalyticsProjectEffortChart([]);
    renderAnalyticsDependencySummary({});
  }
}

function renderAnalyticsWorkloadChart(workload) {
  const ctx = document.getElementById('analyticsWorkloadChart');
  if (!ctx || typeof Chart === 'undefined') return;
  if (state.charts.analyticsWorkload) state.charts.analyticsWorkload.destroy();
  state.charts.analyticsWorkload = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: workload.map(row => row.assignee_name || `User ${row.user_id}`),
      datasets: [
        { label: 'Open', data: workload.map(row => row.open_tasks ?? 0), backgroundColor: '#F59E0B' },
        { label: 'Done', data: workload.map(row => row.done_tasks ?? 0), backgroundColor: '#10B981' },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
  });
}

function renderAnalyticsStatusChart(status) {
  const ctx = document.getElementById('analyticsStatusChart');
  if (!ctx || typeof Chart === 'undefined') return;
  if (state.charts.analyticsStatus) state.charts.analyticsStatus.destroy();
  state.charts.analyticsStatus = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Todo', 'Doing', 'Done'],
      datasets: [{
        data: [status.todo_tasks ?? 0, status.doing_tasks ?? 0, status.done_tasks ?? 0],
        backgroundColor: ['#94A3B8', '#F59E0B', '#10B981'],
      }],
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
  });
}

function renderAnalyticsVelocityChart(rows) {
  const ctx = document.getElementById('analyticsVelocityChart');
  if (!ctx || typeof Chart === 'undefined') return;
  if (state.charts.analyticsVelocity) state.charts.analyticsVelocity.destroy();
  state.charts.analyticsVelocity = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: rows.map(row => row.sprint_name || `Sprint ${row.sprint_id}`),
      datasets: [
        { label: 'Planned SP', data: rows.map(row => row.planned_story_points ?? 0), backgroundColor: '#CBD5E1' },
        { label: 'Completed SP', data: rows.map(row => row.completed_story_points ?? 0), backgroundColor: '#2563EB' },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
  });
}

function renderAnalyticsProjectEffortChart(rows) {
  const ctx = document.getElementById('analyticsProjectEffortChart');
  if (!ctx || typeof Chart === 'undefined') return;
  const topRows = rows.slice(0, 8);
  if (state.charts.analyticsProjectEffort) state.charts.analyticsProjectEffort.destroy();
  state.charts.analyticsProjectEffort = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: topRows.map(row => row.project_name || `Project ${row.project_id}`),
      datasets: [
        { label: 'Story points', data: topRows.map(row => row.story_points ?? 0), backgroundColor: '#7C3AED' },
        { label: 'Completed SP', data: topRows.map(row => row.completed_story_points ?? 0), backgroundColor: '#10B981' },
      ],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } },
    },
  });
}

function renderAnalyticsDependencySummary(summary) {
  const el = document.getElementById('analyticsDependencySummary');
  if (!el) return;
  el.innerHTML = `
    <div class="analytics-stats">
      <div class="analytics-stat">
        <div class="analytics-value">${summary.total_dependency_edges ?? 0}</div>
        <div class="analytics-label">Edges</div>
        <div class="analytics-note">Task dependency links in scope</div>
      </div>
      <div class="analytics-stat">
        <div class="analytics-value">${summary.blocked_tasks ?? 0}</div>
        <div class="analytics-label">Blocked tasks</div>
        <div class="analytics-note">Tasks waiting on dependencies</div>
      </div>
      <div class="analytics-stat">
        <div class="analytics-value">${summary.dependency_source_tasks ?? 0}</div>
        <div class="analytics-label">Source tasks</div>
        <div class="analytics-note">Tasks used as dependency evidence</div>
      </div>
    </div>`;
}

async function loadReportSchedules() {
  const list = document.getElementById('scheduledReportsList');
  if (!list) return;
  list.innerHTML = '<div class="skeleton" style="height:96px"></div>';
  try {
    const rows = await api('/reports/schedules');
    if (!rows.length) {
      list.innerHTML = '<div class="empty-state compact">No scheduled reports yet.</div>';
      return;
    }
    list.innerHTML = rows.map(row => `
      <div class="schedule-row">
        <strong>${escHtml(row.name)}</strong>
        <span class="tag">${escHtml(row.report_type)} / ${escHtml(row.format)}</span>
        <span class="text-sm text-muted">${escHtml(row.frequency)} · next ${safeDate(row.next_run_at)}</span>
        <button class="btn btn-outline btn-sm" type="button" onclick="runReportSchedule(${Number(row.id)})">Run</button>
      </div>`).join('');
  } catch (e) {
    list.innerHTML = `<div class="empty-state compact">${escHtml(e.message)}</div>`;
  }
}

async function createReportSchedule() {
  const recipients = document.getElementById('scheduleRecipients').value.split(',').map(v => v.trim()).filter(Boolean);
  try {
    await api('/reports/schedules', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.getElementById('scheduleName').value.trim(),
        report_type: document.getElementById('scheduleReportType').value,
        format: document.getElementById('scheduleFormat').value,
        frequency: document.getElementById('scheduleFrequency').value,
        recipients,
        next_run_at: new Date(document.getElementById('scheduleNextRun').value).toISOString(),
      }),
    });
    toast('Scheduled report created', 'success');
    await loadReportSchedules();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function runReportSchedule(scheduleId) {
  try {
    await api(`/reports/schedules/${scheduleId}/run`, { method: 'POST' });
    toast('Scheduled report run logged', 'success');
    await loadReportSchedules();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function runDueReportSchedules() {
  try {
    const result = await api('/reports/schedules/run-due', { method: 'POST' });
    toast(`Due schedules processed: ${result.processed ?? 0}`, 'success');
    await loadReportSchedules();
  } catch (e) {
    toast(e.message, 'error');
  }
}
