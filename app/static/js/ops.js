let opsDebounceTimer = null;

function buildOpsUrl() {
  const params = new URLSearchParams();
  const actor = document.getElementById('opsActorFilter')?.value;
  const action = document.getElementById('opsActionFilter')?.value.trim();
  const entity = document.getElementById('opsEntityFilter')?.value.trim();
  const keyword = document.getElementById('opsKeywordFilter')?.value.trim();
  const dateFrom = document.getElementById('opsDateFromFilter')?.value;
  const dateTo = document.getElementById('opsDateToFilter')?.value;
  if (actor) params.set('actor_id', actor);
  if (action) params.set('action', action);
  if (entity) params.set('entity_type', entity);
  if (keyword) params.set('keyword', keyword);
  if (dateFrom) params.set('date_from', new Date(`${dateFrom}T00:00:00Z`).toISOString());
  if (dateTo) params.set('date_to', new Date(`${dateTo}T23:59:59Z`).toISOString());
  params.set('limit', '100');
  const query = params.toString();
  return query ? `/monitoring/ops?${query}` : '/monitoring/ops';
}

function loadOpsDashboardDebounced() {
  clearTimeout(opsDebounceTimer);
  opsDebounceTimer = setTimeout(() => loadOpsDashboard(), 250);
}

function setOpsLoading() {
  const stats = document.getElementById('opsStats');
  if (stats) {
    stats.innerHTML = `
      <div class="stat-card skeleton"></div>
      <div class="stat-card skeleton"></div>
      <div class="stat-card skeleton"></div>
      <div class="stat-card skeleton"></div>`;
  }
  ['opsAuditTable', 'opsFailedQueueTable', 'opsOverdueTables'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = '<div class="skeleton" style="height:120px"></div>';
  });
}

async function loadOpsDashboard() {
  const alert = document.getElementById('opsAlert');
  if (alert) alert.classList.add('hidden');
  setOpsLoading();
  try {
    const data = await api(buildOpsUrl());
    renderOpsStats(data);
    renderOpsAudit(data.audit_logs || []);
    renderOpsQueue(data.notification_queue || {}, Boolean(data.can_manage_queue));
    renderOpsOverdue(data.overdue_spike || {});
  } catch (e) {
    const message = escHtml(e.message || 'Cannot load Audit & Ops');
    const stats = document.getElementById('opsStats');
    if (stats) stats.innerHTML = `<div class="stat-card"><div class="empty-state compact">${message}</div></div>`;
    ['opsAuditTable', 'opsFailedQueueTable', 'opsOverdueTables'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = `<div class="empty-state compact">${message}</div>`;
    });
  }
}

function renderOpsStats(data) {
  const queue = data.notification_queue || {};
  const spike = data.overdue_spike || {};
  const cards = [
    { icon: 'bell', label: 'Queued', value: queue.queued_count || 0, cls: 'warning' },
    { icon: 'check-circle', label: 'Sent', value: queue.sent_count || 0, cls: 'success' },
    { icon: 'x-circle', label: 'Failed', value: queue.failed_count || 0, cls: 'danger' },
    { icon: 'alert-triangle', label: 'Overdue', value: spike.overdue_count || 0, cls: spike.alert ? 'danger' : 'neutral' },
  ];
  const stats = document.getElementById('opsStats');
  if (!stats) return;
  stats.innerHTML = cards.map(card => `
    <div class="stat-card ops-stat-card ${card.cls}">
      <div class="stat-icon">${icon(card.icon, 'stat-svg')}</div>
      <div class="stat-value">${card.value}</div>
      <div class="stat-label">${escHtml(card.label)}</div>
    </div>`).join('');
}

function renderOpsAudit(logs) {
  const el = document.getElementById('opsAuditTable');
  if (!el) return;
  if (!logs.length) {
    el.innerHTML = '<div class="empty-state compact">Chưa có audit log phù hợp với bộ lọc.</div>';
    return;
  }
  el.innerHTML = `
    <table class="audit-table">
      <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Entity</th><th>Detail</th></tr></thead>
      <tbody>
        ${logs.map(log => `
          <tr>
            <td style="white-space:nowrap">${fmtDateTime(log.created_at)}</td>
            <td>${escHtml(log.actor_name || (log.actor_user_id ? `User ${log.actor_user_id}` : 'System'))}</td>
            <td><code>${escHtml(log.action)}</code></td>
            <td><code>${escHtml(log.entity)}${log.entity_id ? ' #' + escHtml(log.entity_id) : ''}</code></td>
            <td>${escHtml(log.detail || '-')}</td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function renderOpsQueue(queue, canManage) {
  const processBtn = document.getElementById('opsProcessQueueBtn');
  if (processBtn) processBtn.classList.toggle('hidden', !canManage);
  const el = document.getElementById('opsFailedQueueTable');
  if (!el) return;
  const items = queue.latest_failed_items || [];
  if (!items.length) {
    el.innerHTML = '<div class="empty-state compact">Không có notification queue thất bại.</div>';
    return;
  }
  el.innerHTML = `
    <table class="audit-table ops-queue-table">
      <thead><tr><th>ID</th><th>User</th><th>Attempts</th><th>Error</th><th></th></tr></thead>
      <tbody>
        ${items.map(item => `
          <tr>
            <td><span class="badge badge-hard">#${item.id}</span></td>
            <td>${escHtml(item.user_id || '-')}</td>
            <td>${escHtml(item.attempts)}/${escHtml(item.max_attempts)}</td>
            <td>${escHtml(item.last_error_summary || '-')}</td>
            <td>${canManage ? `<button class="btn btn-outline btn-sm" onclick="requeueOpsItem(${Number(item.id)})">Requeue</button>` : ''}</td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function renderOpsOverdue(spike) {
  const alert = document.getElementById('opsAlert');
  if (alert) {
    alert.textContent = spike.alert
      ? `Overdue spike alert: ${spike.overdue_count || 0} tasks exceed threshold ${spike.threshold || 0}.`
      : '';
    alert.classList.toggle('hidden', !spike.alert);
  }
  const el = document.getElementById('opsOverdueTables');
  if (!el) return;
  const projects = spike.top_projects || [];
  const sprints = spike.top_sprints || [];
  if (!projects.length && !sprints.length) {
    el.innerHTML = '<div class="empty-state compact">Không có task quá hạn.</div>';
    return;
  }
  el.innerHTML = `
    <div class="ops-table-stack">
      <table class="audit-table">
        <thead><tr><th>Project</th><th>Overdue</th></tr></thead>
        <tbody>${projects.map(item => `
          <tr><td>${escHtml(item.project_name || 'Unassigned')}</td><td><span class="badge badge-hard">${item.overdue_count}</span></td></tr>`).join('')}</tbody>
      </table>
      <table class="audit-table">
        <thead><tr><th>Sprint</th><th>Project</th><th>Overdue</th></tr></thead>
        <tbody>${sprints.map(item => `
          <tr><td>${escHtml(item.sprint_name || 'Unassigned')}</td><td>${escHtml(item.project_name || 'Unassigned')}</td><td><span class="badge badge-hard">${item.overdue_count}</span></td></tr>`).join('')}</tbody>
      </table>
    </div>`;
}

async function processOpsQueue() {
  try {
    await api('/integrations/teams/proactive/process', { method: 'POST' });
    await loadOpsDashboard();
    toast('Queue processed', 'success');
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function requeueOpsItem(id) {
  try {
    await api(`/integrations/teams/proactive/requeue/${id}`, { method: 'POST' });
    await loadOpsDashboard();
    toast('Notification requeued', 'success');
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function resetOpsFilters() {
  ['opsActorFilter', 'opsActionFilter', 'opsEntityFilter', 'opsKeywordFilter', 'opsDateFromFilter', 'opsDateToFilter'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  await loadOpsDashboard();
}
