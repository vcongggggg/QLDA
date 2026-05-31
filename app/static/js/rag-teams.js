async function loadRagDocuments() {
  const el = document.getElementById('ragDocuments');
  if (!el) return;
  el.innerHTML = '<div class="skeleton" style="height:96px"></div>';
  try {
    const docs = await api('/rag/documents');
    if (!docs.length) {
      el.innerHTML = '<div class="empty-state compact">Chưa có tài liệu RAG</div>';
      return;
    }
    el.innerHTML = `
      <table class="audit-table">
        <thead><tr><th>Tài liệu</th><th>Nguồn</th><th>Chunks</th><th></th></tr></thead>
        <tbody>
          ${docs.map(d => `
            <tr>
              <td><strong>${escHtml(d.title)}</strong></td>
              <td>${escHtml(d.source_label || '-')}</td>
              <td>${d.chunk_count || 0}</td>
              <td><button class="btn btn-outline btn-sm" onclick="deleteRagDocument(${d.id})">Xóa</button></td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  } catch (e) {
    el.innerHTML = `<div class="empty-state compact">${escHtml(e.message)}</div>`;
  }
}

let kanbanDebounceTimer = null;

function loadKanbanDebounced() {
  clearTimeout(kanbanDebounceTimer);
  kanbanDebounceTimer = setTimeout(() => loadKanban(), 250);
}

async function onKanbanProjectFilterChange() {
  await loadKanbanSprints();
  await loadKanban();
}

function updateKanbanAssigneeVisibility() {
  const assignee = document.getElementById('kanbanAssigneeFilter');
  if (!assignee) return;
  const isStaff = state.currentUserRole === 'staff';
  assignee.style.display = isStaff ? 'none' : '';
  assignee.disabled = isStaff;
  if (isStaff) assignee.value = '';
}

async function loadKanbanFilterOptions() {
  updateKanbanAssigneeVisibility();
  await loadKanbanSavedFilters();
  const project = document.getElementById('kanbanProjectFilter');
  if (project && project.options.length === 1) {
    try {
      const projects = await api('/projects');
      projects.forEach(p => {
        const option = document.createElement('option');
        option.value = p.id;
        option.textContent = p.name;
        project.appendChild(option);
      });
    } catch (_) {}
  }

  const assignee = document.getElementById('kanbanAssigneeFilter');
  if (assignee && !assignee.disabled && assignee.options.length === 1) {
    try {
      const users = await api('/users');
      users.forEach(u => {
        const option = document.createElement('option');
        option.value = u.id;
        option.textContent = `${u.full_name} (${u.role})`;
        assignee.appendChild(option);
      });
    } catch (_) {
      assignee.disabled = true;
    }
  }

  await loadKanbanSprints(false);
}

async function loadKanbanSprints(resetValue = true) {
  const project = document.getElementById('kanbanProjectFilter');
  const sprint = document.getElementById('kanbanSprintFilter');
  if (!project || !sprint) return;
  const previous = resetValue ? '' : sprint.value;
  sprint.innerHTML = '<option value="">All sprints</option>';
  sprint.disabled = true;
  if (!project.value) return;

  try {
    const sprints = await api(`/projects/${project.value}/sprints`);
    sprints.forEach(item => {
      const option = document.createElement('option');
      option.value = item.id;
      option.textContent = item.name;
      sprint.appendChild(option);
    });
    sprint.disabled = false;
    if (previous && Array.from(sprint.options).some(option => option.value === previous)) {
      sprint.value = previous;
    }
  } catch (_) {}
}

function buildKanbanTaskUrl() {
  const params = buildKanbanFilterParams();
  const query = params.toString();
  return query ? `/tasks?${query}` : '/tasks';
}

function buildKanbanSummaryUrl() {
  const params = buildKanbanFilterParams();
  const query = params.toString();
  return query ? `/kanban/summary?${query}` : '/kanban/summary';
}

function buildKanbanFilterParams() {
  const params = new URLSearchParams();
  const projectId = document.getElementById('kanbanProjectFilter')?.value;
  const sprintId = document.getElementById('kanbanSprintFilter')?.value;
  const assignee = document.getElementById('kanbanAssigneeFilter');
  const status = document.getElementById('kanbanStatusFilter')?.value;
  const overdue = document.getElementById('kanbanOverdueFilter')?.value;
  const keyword = document.getElementById('kanbanKeywordFilter')?.value.trim();
  const deadlineFrom = document.getElementById('kanbanDeadlineFromFilter')?.value;
  const deadlineTo = document.getElementById('kanbanDeadlineToFilter')?.value;

  if (projectId) params.set('project_id', projectId);
  if (sprintId) params.set('sprint_id', sprintId);
  if (assignee && !assignee.disabled && assignee.value) params.set('assignee_id', assignee.value);
  if (status) params.set('status', status);
  if (overdue) params.set('overdue', overdue);
  if (keyword) params.set('keyword', keyword);
  if (deadlineFrom) params.set('deadline_from', new Date(`${deadlineFrom}T00:00:00Z`).toISOString());
  if (deadlineTo) params.set('deadline_to', new Date(`${deadlineTo}T23:59:59Z`).toISOString());
  return params;
}

function currentKanbanFilters() {
  return Object.fromEntries(buildKanbanFilterParams().entries());
}

async function loadKanbanSavedFilters() {
  const select = document.getElementById('kanbanSavedFilterSelect');
  if (!select || select.dataset.loaded === '1') return;
  try {
    const rows = await api('/kanban/saved-filters');
    select.innerHTML = '<option value="">Saved filters</option>' + rows.map(row => `<option value="${row.id}" data-filters="${escHtml(JSON.stringify(row.filters || {}))}">${escHtml(row.name)}${row.is_default ? ' *' : ''}</option>`).join('');
    select.dataset.loaded = '1';
  } catch (_) {}
}

async function applyKanbanSavedFilter() {
  const select = document.getElementById('kanbanSavedFilterSelect');
  const option = select?.selectedOptions?.[0];
  if (!option || !option.dataset.filters) return;
  localStorage.setItem('teamswork.kanban.savedFilterId', select.value || '');
  const filters = JSON.parse(option.dataset.filters || '{}');
  const mapping = {
    project_id: 'kanbanProjectFilter',
    sprint_id: 'kanbanSprintFilter',
    assignee_id: 'kanbanAssigneeFilter',
    status: 'kanbanStatusFilter',
    overdue: 'kanbanOverdueFilter',
    keyword: 'kanbanKeywordFilter',
  };
  Object.entries(mapping).forEach(([key, id]) => {
    const el = document.getElementById(id);
    if (el && filters[key] != null) el.value = filters[key];
  });
  if (filters.deadline_from) document.getElementById('kanbanDeadlineFromFilter').value = String(filters.deadline_from).slice(0, 10);
  if (filters.deadline_to) document.getElementById('kanbanDeadlineToFilter').value = String(filters.deadline_to).slice(0, 10);
  await loadKanbanSprints(false);
  await loadKanban();
}

async function saveCurrentKanbanFilter() {
  const name = prompt('Saved filter name');
  if (!name) return;
  const isDefault = Boolean(document.getElementById('kanbanDefaultFilterCheck')?.checked);
  try {
    await api('/kanban/saved-filters', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, filters: currentKanbanFilters(), is_default: isDefault }),
    });
    const select = document.getElementById('kanbanSavedFilterSelect');
    if (select) select.dataset.loaded = '0';
    await loadKanbanSavedFilters();
    toast('Da luu filter Kanban', 'success');
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function deleteCurrentKanbanFilter() {
  const select = document.getElementById('kanbanSavedFilterSelect');
  if (!select?.value) return;
  try {
    await api(`/kanban/saved-filters/${select.value}`, { method: 'DELETE' });
    localStorage.removeItem('teamswork.kanban.savedFilterId');
    select.dataset.loaded = '0';
    await loadKanbanSavedFilters();
    toast('Da xoa filter Kanban', 'success');
  } catch (e) {
    toast(e.message, 'error');
  }
}

function exportKanbanTasks(fmt) {
  if (!canDo('reportExport')) {
    toast('Ban khong co quyen xuat bao cao', 'error');
    return;
  }
  const query = buildKanbanFilterParams().toString();
  triggerDownload(`/reports/tasks.${fmt}${query ? `?${query}` : ''}`);
}

async function importKanbanTasks() {
  const input = document.getElementById('taskImportFile');
  if (!input?.files?.length) {
    toast('Chon file CSV hoac XLSX', 'error');
    return;
  }
  const form = new FormData();
  form.append('file', input.files[0]);
  try {
    const result = await api('/tasks/import', { method: 'POST', body: form });
    input.value = '';
    toast(`Da import ${result.created_count} task`, 'success');
    await loadKanban();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function resetKanbanFilters() {
  ['kanbanProjectFilter', 'kanbanAssigneeFilter', 'kanbanStatusFilter', 'kanbanOverdueFilter'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  ['kanbanKeywordFilter', 'kanbanDeadlineFromFilter', 'kanbanDeadlineToFilter'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  const saved = document.getElementById('kanbanSavedFilterSelect');
  if (saved) saved.value = '';
  await loadKanbanSprints();
  await loadKanban();
}

async function createRagDocument() {
  if (!canDo('ragManage')) {
    toast('Ban khong co quyen quan ly RAG', 'error');
    return;
  }
  const title = document.getElementById('ragTitle').value.trim();
  const source = document.getElementById('ragSource').value.trim();
  const projectId = document.getElementById('ragProjectSelect')?.value;
  const content = document.getElementById('ragContent').value.trim();
  if (title.length < 2 || content.length < 20 || !projectId) {
    toast('Nhập tiêu đề và nội dung RAG đủ dài', 'error');
    return;
  }
  try {
    await api('/rag/documents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, source_label: source || null, project_id: Number(projectId), content }),
    });
    document.getElementById('ragTitle').value = '';
    document.getElementById('ragSource').value = '';
    document.getElementById('ragContent').value = '';
    await loadRagDocuments();
    toast('Đã thêm tài liệu RAG', 'success');
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function deleteRagDocument(id) {
  if (!canDo('ragManage')) {
    toast('Ban khong co quyen quan ly RAG', 'error');
    return;
  }
  try {
    await api(`/rag/documents/${id}`, { method: 'DELETE' });
    await loadRagDocuments();
    toast('Đã xóa tài liệu RAG', 'success');
  } catch (e) {
    toast(e.message, 'error');
  }
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
    let queued = 0;
    let sent = 0;
    let failed = 0;
    const canManageQueue = ['ADMIN', 'MANAGER', 'HR'].includes(currentRoleCode());
    if (canManageQueue) {
      const all = await api('/integrations/teams/proactive/queue?status=all&limit=200');
      queued = all.filter(n => n.status === 'queued').length;
      sent = all.filter(n => n.status === 'sent').length;
      failed = all.filter(n => n.status === 'failed').length;
    } else {
      await api(`/integrations/teams/summary?month=${state.month}`);
    }
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
    statsEl.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${e.message}</div>`;
  }
}

// ════════════════════════════════ ADMIN ════════

// Audit & Ops
