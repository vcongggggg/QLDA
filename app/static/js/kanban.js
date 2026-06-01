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

    // Populate label filter dynamically with all unique labels present
    const allLabels = new Set();
    tasks.forEach(t => {
      if (Array.isArray(t.labels)) {
        t.labels.forEach(l => { if (l) allLabels.add(l.trim()); });
      }
    });
    const labelFilterSelect = document.getElementById('kanbanLabelFilter');
    if (labelFilterSelect) {
      const selectedLabel = labelFilterSelect.value;
      labelFilterSelect.innerHTML = '<option value="">Tất cả nhãn</option>' + 
        Array.from(allLabels).sort().map(l => `<option value="${escHtml(l)}">${escHtml(l)}</option>`).join('');
      if (selectedLabel && allLabels.has(selectedLabel)) {
        labelFilterSelect.value = selectedLabel;
      }
    }

    // Filter tasks by selected label
    let displayedTasks = tasks;
    const activeLabel = labelFilterSelect?.value;
    if (activeLabel) {
      displayedTasks = tasks.filter(t => Array.isArray(t.labels) && t.labels.includes(activeLabel));
    }

    const grouped = { todo: [], doing: [], done: [] };
    displayedTasks.forEach(t => { if (grouped[t.status]) grouped[t.status].push(t); });

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
    document.getElementById('kanbanCount').textContent = `${displayedTasks.length} công việc`;
    renderKanbanSummary(summary, displayedTasks);
    renderKanbanList(displayedTasks);

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
          const checklist = task.checklist || [];
          const checklistHtml = checklist.length > 0
            ? `<span class="task-card-checklist" style="display:inline-flex; align-items:center; gap:3px; background:#f1f5f9; padding:2px 7px; border-radius:10px; font-weight:600; color:#475569; font-size:11px; margin-left:6px;" title="Tiến độ checklist">
                ${icon('list-checks', 'text-icon')} ${checklist.filter(x => x.startsWith('[x]')).length}/${checklist.length}
               </span>`
            : '';
          const subtasks = task.subtasks || [];
          const subtasksHtml = subtasks.length > 0
            ? `<span class="task-card-subtask-progress" style="display:inline-flex; align-items:center; gap:3px; background:#e0f2fe; padding:2px 7px; border-radius:10px; font-weight:600; color:#0369a1; font-size:11px; margin-left:6px;" title="Tiến độ công việc con">
                ${icon('list', 'text-icon')} ${subtasks.filter(x => x.startsWith('[x]')).length}/${subtasks.length}
               </span>`
            : '';
          const labelsList = task.labels || [];
          const labelsListHtml = labelsList.map(l => {
            const { bg, fg, border } = hashStringToColor(l);
            return `<span style="background:${bg}; color:${fg}; border:1px solid ${border}; padding:1px 5px; font-size:9.5px; border-radius:3px; font-weight:bold; margin-left:4px; display:inline-block; vertical-align:middle;">${escHtml(l)}</span>`;
          }).join('');
          return `
            <tr class="kanban-list-row" onclick="openTaskDetail(${Number(task.id)})">
              <td><strong>${escHtml(task.title)}</strong>${checklistHtml}${subtasksHtml}${labelsListHtml}<br><span class="text-muted">#${Number(task.id)}</span></td>
              <td><span class="tag">${escHtml(statusLabel(task.status))}</span></td>
              <td><span class="badge badge-priority-${task.priority || 'medium'}">${priorityLabel(task.priority || 'medium')}</span></td>
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

  const checklist = t.checklist || [];
  const checklistHtml = checklist.length > 0
    ? `<span class="task-card-checklist" style="display:inline-flex; align-items:center; gap:3px; background:#f1f5f9; padding:2px 7px; border-radius:10px; font-weight:600; color:#475569;" title="Tiến độ checklist">
        ${icon('list-checks', 'text-icon')} ${checklist.filter(x => x.startsWith('[x]')).length}/${checklist.length}
       </span>`
    : '';

  const subtasks = t.subtasks || [];
  const subtasksProgressHtml = subtasks.length > 0
    ? `<span class="task-card-subtask-progress" style="display:inline-flex; align-items:center; gap:3px; background:#e0f2fe; padding:2px 7px; border-radius:10px; font-weight:600; color:#0369a1;" title="Tiến độ công việc con">
        ${icon('list', 'text-icon')} ${subtasks.filter(x => x.startsWith('[x]')).length}/${subtasks.length}
       </span>`
    : '';

  const labels = t.labels || [];
  const labelsHtml = labels.map(l => {
    const { bg, fg, border } = hashStringToColor(l);
    return `<span class="badge" style="background:${bg}; color:${fg}; border:1px solid ${border}; padding:1px 6px; font-size:10px; border-radius:4px; font-weight:bold;">${escHtml(l)}</span>`;
  }).join('');
  const labelsContainer = labels.length > 0
    ? `<div class="task-card-labels" style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:6px;">${labelsHtml}</div>`
    : '';

  return `
    <div class="task-card" draggable="${canDo('taskUpdate') ? 'true' : 'false'}" data-task-id="${t.id}" data-status="${t.status}" title="Giữ & kéo sang cột khác">
      <div class="task-card-handle" aria-hidden="true">⋮⋮</div>
      <div class="task-card-title">${escHtml(t.title)}</div>
      ${labelsContainer}
      <div class="task-card-meta">
        <span class="task-card-sp">SP: ${t.story_points}</span>
        <span class="badge badge-${t.difficulty}">${diffLabel(t.difficulty)}</span>
        <span class="badge badge-priority-${t.priority || 'medium'}">${priorityShortLabel(t.priority || 'medium')}</span>
        ${checklistHtml}
        ${subtasksProgressHtml}
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

// ════════════════════════════════ MANUAL TASK CREATION ═══════
let taskCreateChecklist = [];

async function showCreateTaskModal() {
  if (!canDo('taskCreate')) {
    toast('Bạn không có quyền tạo task', 'error');
    return;
  }
  
  const form = document.getElementById('taskCreateForm');
  if (form) form.reset();
  
  taskCreateChecklist = [];
  renderTaskCreateChecklist();
  updateExpectedKpiPoints();
  
  const deadlineInput = document.getElementById('taskCreateDeadline');
  if (deadlineInput) {
    deadlineInput.value = `${DEFAULT_WORK_DATE}T17:00`;
  }

  // Populate Assignee Select
  const assigneeSelect = document.getElementById('taskCreateAssignee');
  if (assigneeSelect) {
    assigneeSelect.innerHTML = '<option value="">Đang tải...</option>';
    try {
      const users = await api('/users');
      assigneeSelect.innerHTML = users.map(u => `<option value="${u.id}">${escHtml(u.full_name)} (${u.role})</option>`).join('');
    } catch (e) {
      assigneeSelect.innerHTML = '<option value="">Lỗi tải người dùng</option>';
    }
  }

  // Populate Project Select
  const projectSelect = document.getElementById('taskCreateProject');
  if (projectSelect) {
    projectSelect.innerHTML = '<option value="">Không chọn</option>';
    try {
      const projects = await api('/projects');
      projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name;
        projectSelect.appendChild(opt);
      });
    } catch (e) {
      toast('Lỗi tải danh sách dự án', 'error');
    }
  }

  // Disable sprint select by default
  const sprintSelect = document.getElementById('taskCreateSprint');
  if (sprintSelect) {
    sprintSelect.disabled = true;
    sprintSelect.innerHTML = '<option value="">Không chọn</option>';
  }

  const overlay = document.getElementById('taskCreateOverlay');
  if (overlay) overlay.classList.remove('hidden');
}

function closeTaskCreate() {
  const overlay = document.getElementById('taskCreateOverlay');
  if (overlay) overlay.classList.add('hidden');
}

async function onTaskCreateProjectChange() {
  const projectId = document.getElementById('taskCreateProject').value;
  const sprintSelect = document.getElementById('taskCreateSprint');
  if (!sprintSelect) return;

  if (!projectId) {
    sprintSelect.disabled = true;
    sprintSelect.innerHTML = '<option value="">Không chọn</option>';
    return;
  }

  sprintSelect.disabled = false;
  sprintSelect.innerHTML = '<option value="">Đang tải...</option>';

  try {
    const sprints = await api(`/projects/${projectId}/sprints`);
    sprintSelect.innerHTML = '<option value="">Không chọn</option>' + 
      sprints.map(s => `<option value="${s.id}">${escHtml(s.name)} (${s.status})</option>`).join('');
  } catch (e) {
    sprintSelect.innerHTML = '<option value="">Lỗi tải sprints</option>';
  }
}

function updateExpectedKpiPoints() {
  const difficulty = document.getElementById('taskCreateDifficulty').value;
  const indicator = document.getElementById('taskCreateKpiIndicator');
  if (!indicator) return;

  const points = {
    easy: '10.0 điểm',
    medium: '15.0 điểm',
    hard: '20.0 điểm'
  }[difficulty] || '10.0 điểm';
  
  indicator.textContent = points;
}

function addTaskCreateChecklistItem() {
  const input = document.getElementById('taskCreateChecklistInput');
  const text = (input?.value || '').trim();
  if (!text) return;

  taskCreateChecklist.push(`[ ] ${text}`);
  if (input) input.value = '';
  renderTaskCreateChecklist();
}

function removeTaskCreateChecklistItem(index) {
  taskCreateChecklist.splice(index, 1);
  renderTaskCreateChecklist();
}

function renderTaskCreateChecklist() {
  const container = document.getElementById('taskCreateChecklistItems');
  if (!container) return;

  if (taskCreateChecklist.length === 0) {
    container.innerHTML = '<div class="text-sm text-muted">Chưa có checklist item.</div>';
    return;
  }

  container.innerHTML = taskCreateChecklist.map((item, index) => {
    const cleanText = item.startsWith('[ ] ') ? item.substring(4) : (item.startsWith('[x] ') ? item.substring(4) : item);
    return `
      <div style="display:flex; justify-content:space-between; align-items:center; background:#f5f5f5; padding:4px 8px; border-radius:4px;">
        <span class="text-sm">${escHtml(cleanText)}</span>
        <button type="button" class="btn btn-outline btn-sm" onclick="removeTaskCreateChecklistItem(${index})" style="color:red; border-color:red; padding:2px 6px;">Xóa</button>
      </div>`;
  }).join('');
}

async function submitTaskCreate(event) {
  event.preventDefault();
  
  if (!canDo('taskCreate')) {
    toast('Bạn không có quyền tạo task', 'error');
    return;
  }

  const title = document.getElementById('taskCreateTitle').value.trim();
  const description = document.getElementById('taskCreateDescription').value.trim() || null;
  const assigneeId = Number(document.getElementById('taskCreateAssignee').value);
  const projectVal = document.getElementById('taskCreateProject').value;
  const sprintVal = document.getElementById('taskCreateSprint').value;
  const priority = document.getElementById('taskCreatePriority').value;
  const difficulty = document.getElementById('taskCreateDifficulty').value;
  const storyPoints = Number(document.getElementById('taskCreateStoryPoints').value);
  const deadlineStr = document.getElementById('taskCreateDeadline').value;

  if (!title || !assigneeId || !deadlineStr) {
    toast('Vui lòng điền đầy đủ thông tin bắt buộc', 'error');
    return;
  }

  const deadline = new Date(deadlineStr);
  if (Number.isNaN(deadline.getTime())) {
    toast('Deadline không hợp lệ', 'error');
    return;
  }

  try {
    await api('/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        description,
        assignee_id: assigneeId,
        project_id: projectVal ? Number(projectVal) : null,
        sprint_id: sprintVal ? Number(sprintVal) : null,
        priority,
        difficulty,
        story_points: storyPoints,
        deadline: deadline.toISOString(),
        checklist: taskCreateChecklist,
        labels: [],
        subtasks: [],
        dependencies: [],
        attachment_metadata: []
      }),
    });

    toast('Tạo task mới thành công', 'success');
    closeTaskCreate();
    loadKanban();
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ════════════════════════════════ PROJECTS ═════

// Timeline
