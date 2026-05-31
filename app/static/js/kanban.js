function initKanbanDragDrop() {
  const board =
    document.getElementById('kanban-board') ||
    document.querySelector('#sec-kanban .kanban-board');
  if (!board || board.dataset.dndInit === '1') return;
  board.dataset.dndInit = '1';

  const statusByColId = { 'col-todo': 'todo', 'col-doing': 'doing', 'col-done': 'done' };

  board.addEventListener('dragstart', (e) => {
    const card = e.target.closest('.task-card[draggable="true"]');
    if (!card) return;
    if (!canDo('taskUpdate')) {
      e.preventDefault();
      return;
    }
    state.draggingTaskId = Number(card.dataset.taskId);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData(
      'text/plain',
      JSON.stringify({ id: Number(card.dataset.taskId), from: card.dataset.status || '' })
    );
    card.classList.add('is-dragging');
  });

  board.addEventListener('dragend', (e) => {
    const card = e.target.closest('.task-card');
    if (card) card.classList.remove('is-dragging');
    document.querySelectorAll('.kanban-cards').forEach((z) => z.classList.remove('kanban-drop-active'));
    setTimeout(() => { state.draggingTaskId = null; }, 0);
  });

  board.addEventListener('click', (e) => {
    if (state.draggingTaskId) return;
    if (e.target.closest('button, a, input, select, textarea')) return;
    const card = e.target.closest('.task-card');
    if (!card) return;
    openTaskDetail(Number(card.dataset.taskId));
  });

  /* capture: true — dragover phải preventDefault trên vùng cột kể cả khi con trỏ đang ở thẻ con (empty-state, task-card) */
  ['col-todo', 'col-doing', 'col-done'].forEach((id) => {
    const zone = document.getElementById(id);
    if (!zone) return;

    zone.addEventListener(
      'dragover',
      (e) => {
        if (!canDo('taskUpdate')) return;
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
        zone.classList.add('kanban-drop-active');
      },
      true
    );

    zone.addEventListener(
      'dragleave',
      (e) => {
        if (!zone.contains(e.relatedTarget)) {
          zone.classList.remove('kanban-drop-active');
        }
      },
      true
    );

    zone.addEventListener(
      'drop',
      async (e) => {
        if (!canDo('taskUpdate')) return;
        e.preventDefault();
        e.stopPropagation();
        zone.classList.remove('kanban-drop-active');
        const newStatus = statusByColId[zone.id];
        if (!newStatus) return;
        let payload;
        try {
          payload = JSON.parse(e.dataTransfer.getData('text/plain') || '{}');
        } catch {
          return;
        }
        const taskId = payload && payload.id;
        if (!taskId) return;
        if (payload.from && payload.from === newStatus) return;
        const countBadge = document.getElementById(`cnt-${newStatus}`);
        if (countBadge?.classList.contains('badge-hard')) {
          toast('WIP limit warning: target column is already over limit', 'warning');
        }
        try {
          await updateTaskStatus(Number(taskId), newStatus, { silent: false });
        } catch (err) {
          toast(String(err?.message || err), 'error');
        }
      },
      true
    );
  });
}

// ════════════════════════════════ KANBAN ═══════

function currentKanbanView() {
  state.kanbanView = state.kanbanView || 'board';
  return state.kanbanView;
}

function setKanbanView(view) {
  state.kanbanView = view === 'list' ? 'list' : 'board';
  updateKanbanViewControls();
  loadKanban();
}

function updateKanbanViewControls() {
  const isList = currentKanbanView() === 'list';
  const board = document.getElementById('kanban-board');
  const list = document.getElementById('kanban-list');
  const boardBtn = document.getElementById('kanbanBoardViewBtn');
  const listBtn = document.getElementById('kanbanListViewBtn');
  if (board) board.classList.toggle('hidden', isList);
  if (list) list.classList.toggle('hidden', !isList);
  if (boardBtn) {
    boardBtn.classList.toggle('active', !isList);
    boardBtn.setAttribute('aria-pressed', String(!isList));
  }
  if (listBtn) {
    listBtn.classList.toggle('active', isList);
    listBtn.setAttribute('aria-pressed', String(isList));
  }
}

async function loadKanban() {
  const cols = {
    todo:  document.getElementById('col-todo'),
    doing: document.getElementById('col-doing'),
    done:  document.getElementById('col-done'),
  };

  Object.values(cols).forEach(c => { c.innerHTML = '<div class="skeleton" style="height:64px;margin:4px 0"></div>'; });
  const list = document.getElementById('kanban-list');
  const summaryPanel = document.getElementById('kanbanSummaryPanel');
  if (list) list.innerHTML = '<div class="skeleton" style="height:72px"></div>';
  if (summaryPanel) summaryPanel.innerHTML = '<div class="skeleton" style="height:74px"></div>';
  updateKanbanViewControls();

  try {
    await loadKanbanFilterOptions();
    const url = buildKanbanTaskUrl();
    const tasks = await api(url);
    const summary = await api(buildKanbanSummaryUrl()).catch(() => null);
    await loadWorkloadWarnings();
    const grouped = { todo: [], doing: [], done: [] };
    tasks.forEach(t => { if (grouped[t.status]) grouped[t.status].push(t); });

    const summaryByStatus = new Map((summary?.columns || []).map(item => [item.status, item]));
    ['todo', 'doing', 'done'].forEach(status => {
      const item = summaryByStatus.get(status) || {
        task_count: grouped[status].length,
        story_points: grouped[status].reduce((sum, t) => sum + Number(t.story_points || 0), 0),
      };
      const el = document.getElementById(`cnt-${status}`);
      if (!el) return;
      el.textContent = `${item.task_count} / ${item.story_points} SP${item.wip_limit != null ? ` / WIP ${item.wip_limit}` : ''}`;
      el.classList.toggle('badge-hard', Boolean(item.wip_exceeded));
    });
    document.getElementById('kanbanCount').textContent = `${tasks.length} công việc`;
    renderKanbanSummary(summary, tasks);
    renderKanbanList(tasks);

    Object.entries(grouped).forEach(([status, items]) => {
      const col = cols[status];
      if (!items.length) {
        col.innerHTML = `<div class="empty-state" style="padding:20px"><div>${icon('list-checks', 'empty-icon')}</div>Trống <span class="text-sm text-muted">(kéo thả thẻ vào đây)</span></div>`;
        return;
      }
      col.innerHTML = items.map(t => taskCard(t)).join('');
    });
  } catch (e) {
    Object.values(cols).forEach(c => {
      c.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${e.message}</div>`;
    });
    if (list) list.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${escHtml(e.message)}</div>`;
    if (summaryPanel) summaryPanel.innerHTML = '';
  }
}

function renderKanbanSummary(summary, tasks) {
  const panel = document.getElementById('kanbanSummaryPanel');
  if (!panel) return;
  const safeSummary = summary || {};
  const columns = safeSummary.columns || [];
  const overdue = safeSummary.overdue_open_tasks ?? tasks.filter(isTaskOverdue).length;
  const wipExceeded = safeSummary.wip_exceeded_columns ?? columns.filter(col => col.wip_exceeded).length;
  const activeFilters = Array.from(buildKanbanFilterParams().keys()).length;
  const storyPoints = safeSummary.total_story_points ?? tasks.reduce((sum, task) => sum + Number(task.story_points || 0), 0);
  panel.innerHTML = `
    <div class="kanban-summary-item">
      <div class="kanban-summary-label">Tasks</div>
      <div class="kanban-summary-value">${Number(safeSummary.total_tasks ?? tasks.length)}</div>
    </div>
    <div class="kanban-summary-item">
      <div class="kanban-summary-label">Story points</div>
      <div class="kanban-summary-value">${Number(storyPoints)}</div>
    </div>
    <div class="kanban-summary-item">
      <div class="kanban-summary-label">Overdue open</div>
      <div class="kanban-summary-value ${overdue > 0 ? 'text-danger' : ''}">${Number(overdue)}</div>
    </div>
    <div class="kanban-summary-item">
      <div class="kanban-summary-label">WIP warnings / filters</div>
      <div class="kanban-summary-value ${wipExceeded > 0 ? 'text-danger' : ''}">${Number(wipExceeded)} / ${activeFilters}</div>
    </div>`;
}

function renderKanbanList(tasks) {
  const list = document.getElementById('kanban-list');
  if (!list) return;
  if (!tasks.length) {
    list.innerHTML = `<div class="empty-state compact">${icon('list-checks', 'empty-icon')}No tasks match the current filters</div>`;
    return;
  }
  list.innerHTML = `
    <table class="kanban-list-table">
      <thead>
        <tr>
          <th>Task</th>
          <th>Status</th>
          <th>Priority</th>
          <th>SP</th>
          <th>Deadline</th>
          <th>Due</th>
        </tr>
      </thead>
      <tbody>
        ${tasks.map(task => {
          const deadline = new Date(task.deadline);
          const overdue = isTaskOverdue(task);
          const daysLeft = Math.ceil((deadline - new Date()) / 86400000);
          return `
            <tr class="kanban-list-row" onclick="openTaskDetail(${Number(task.id)})">
              <td><strong>${escHtml(task.title)}</strong><br><span class="text-muted">#${Number(task.id)}</span></td>
              <td><span class="tag">${escHtml(statusLabel(task.status))}</span></td>
              <td>${escHtml(task.priority || 'medium')}</td>
              <td>${Number(task.story_points || 0)}</td>
              <td>${deadline.toLocaleDateString('vi-VN')}</td>
              <td class="${overdue ? 'text-danger' : ''}">${overdue ? 'Overdue' : `${Math.max(daysLeft, 0)}d`}</td>
            </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}

function isTaskOverdue(task) {
  if (!task || task.status === 'done' || !task.deadline) return false;
  return new Date(task.deadline) < new Date();
}

async function loadWorkloadWarnings() {
  const panel = document.getElementById('workloadWarningsPanel');
  const sprintId = document.getElementById('kanbanSprintFilter')?.value;
  if (!panel) return;
  if (!sprintId) {
    panel.classList.add('hidden');
    panel.innerHTML = '';
    return;
  }

  panel.classList.remove('hidden');
  panel.innerHTML = '<div class="skeleton" style="height:76px"></div>';
  try {
    const rows = await api(`/sprints/${sprintId}/workload-warnings`);
    const warnings = rows.filter(row => row.risk_level !== 'low' || row.overloaded || row.overdue_task_count > 0);
    if (!warnings.length) {
      panel.innerHTML = `
        <div class="workload-header">
          <h3>${icon('alert-triangle', 'heading-icon')}Workload warnings</h3>
        </div>
        <div class="empty-state compact">Không có cảnh báo quá tải</div>`;
      return;
    }

    panel.innerHTML = `
      <div class="workload-header">
        <h3>${icon('alert-triangle', 'heading-icon')}Workload warnings</h3>
        <span class="tag ${warnings.some(row => row.risk_level === 'high') ? 'tag-red' : 'tag-yellow'}">${warnings.length} cảnh báo</span>
      </div>
      <div class="workload-table-wrap">
        <table class="rank-table workload-table">
          <thead>
            <tr>
              <th>Nhân sự</th>
              <th>Workload</th>
              <th>Capacity</th>
              <th>Task mở</th>
              <th>Quá hạn</th>
              <th>Risk</th>
              <th>Lý do</th>
            </tr>
          </thead>
          <tbody>
            ${warnings.map(row => `
              <tr class="workload-risk-${escHtml(row.risk_level)}">
                <td><strong>${escHtml(row.user_name || `User ${row.user_id}`)}</strong></td>
                <td>${Number(row.workload_points || 0)}</td>
                <td>${row.capacity_points == null ? '-' : Number(row.capacity_points).toFixed(1)}</td>
                <td>${Number(row.open_task_count || 0)}</td>
                <td>${Number(row.overdue_task_count || 0)}</td>
                <td><span class="tag ${row.risk_level === 'high' ? 'tag-red' : 'tag-yellow'}">${escHtml(row.risk_level)}</span></td>
                <td>${(row.reasons || []).map(escHtml).join(', ') || '-'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>`;
  } catch (e) {
    panel.innerHTML = `<div class="empty-state compact">${icon('alert-triangle', 'empty-icon')}${escHtml(e.message)}</div>`;
  }
}

function taskCard(t) {
  const now = new Date();
  const deadline = new Date(t.deadline);
  const isOverdue = t.status !== 'done' && deadline < now;
  const daysLeft = Math.ceil((deadline - now) / 86400000);
  const deadlineStr = deadline.toLocaleDateString('vi-VN');

  const nextStatus = canDo('taskUpdate')
    ? (t.status === 'todo' ? 'doing' : t.status === 'doing' ? 'done' : null)
    : null;
  const nextLabel  = nextStatus === 'doing'
    ? `${icon('zap', 'text-icon')} Bắt đầu`
    : nextStatus === 'done'
      ? `${icon('check-circle', 'text-icon')} Hoàn thành`
      : '';

  return `
    <div class="task-card" draggable="${canDo('taskUpdate') ? 'true' : 'false'}" data-task-id="${t.id}" data-status="${t.status}" title="Giữ & kéo sang cột khác">
      <div class="task-card-handle" aria-hidden="true">⋮⋮</div>
      <div class="task-card-title">${escHtml(t.title)}</div>
      <div class="task-card-meta">
        <span class="task-card-sp">SP: ${t.story_points}</span>
        <span class="badge badge-${t.difficulty}">${diffLabel(t.difficulty)}</span>
        <span class="task-card-deadline ${isOverdue ? 'overdue' : ''}">
          ${icon(isOverdue ? 'alert-triangle' : 'calendar', 'text-icon')} ${deadlineStr}
          ${!isOverdue && daysLeft >= 0 ? `(${daysLeft}d)` : ''}
        </span>
      </div>
      ${nextStatus ? `
        <div class="task-card-actions">
          <button type="button" class="btn-mini" onclick="event.stopPropagation();moveTask(${t.id}, '${nextStatus}')">${nextLabel}</button>
        </div>` : ''}
    </div>`;
}

async function updateTaskStatus(taskId, newStatus, { silent = false } = {}) {
  if (!canDo('taskUpdate')) {
    toast('Ban khong co quyen cap nhat task', 'error');
    return;
  }
  await api(`/tasks/${taskId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus }),
  });
  if (!silent) {
    toast(`Đã cập nhật trạng thái: ${statusLabel(newStatus)}`, 'success');
  }
  if (state.currentSection === 'kanban') {
    loadKanban();
  }
  if (state.currentSection === 'timeline') {
    loadTimeline();
  }
  loadNotificationCount();
}

async function moveTask(taskId, newStatus) {
  try {
    await updateTaskStatus(Number(taskId), newStatus, { silent: false });
  } catch (e) {
    toast(`Lỗi: ${e.message}`, 'error');
  }
}

// ════════════════════════════════ PROJECTS ═════

// Timeline
