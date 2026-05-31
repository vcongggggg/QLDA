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
    </div>`;
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
