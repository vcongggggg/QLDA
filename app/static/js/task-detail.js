async function openTaskDetail(taskId) {
  state.activeTaskId = Number(taskId);
  const overlay = document.getElementById('taskDetailOverlay');
  const body = document.getElementById('taskDetailBody');
  if (!overlay || !body) return;
  overlay.classList.remove('hidden');
  body.innerHTML = '<div class="skeleton" style="height:220px"></div>';
  try {
    const task = await api(`/tasks/${taskId}`);
    renderTaskDetail(task);
  } catch (e) {
    body.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${escHtml(e.message)}</div>`;
  }
}

function closeTaskDetail() {
  const overlay = document.getElementById('taskDetailOverlay');
  if (overlay) overlay.classList.add('hidden');
  state.activeTaskId = null;
}

function renderTaskDetail(task) {
  const body = document.getElementById('taskDetailBody');
  if (!body) return;
  const comments = task.comments || [];
  const logs = task.activity_logs || [];
  body.innerHTML = `
    <div class="task-detail-section">
      <div class="task-detail-kicker">Task #${task.id}</div>
      <h2 class="task-detail-title">${escHtml(task.title)}</h2>
      <p class="task-detail-description">${escHtml(task.description || 'Chưa có mô tả')}</p>
      <div class="task-detail-status-row">
        <span class="badge badge-${task.status}">${statusLabel(task.status)}</span>
        <span class="badge badge-${task.difficulty}">${diffLabel(task.difficulty)}</span>
        <span class="due-pill ${dueStateClass(task.due_state)}">${dueStateLabel(task.due_state)}</span>
      </div>
    </div>

    <div class="task-detail-grid">
      ${taskDetailField('Assignee', task.assignee_name || `User ${task.assignee_id}`)}
      ${taskDetailField('Project', task.project_name || '-')}
      ${taskDetailField('Sprint', task.sprint_name || '-')}
      ${taskDetailField('Difficulty', diffLabel(task.difficulty))}
      ${taskDetailField('Story points', task.story_points)}
      ${taskDetailField('Deadline', fmtDateTime(task.deadline))}
      ${taskDetailField('Completed at', fmtDateTime(task.completed_at))}
    </div>

    ${taskDeadlineExtensionSection(task)}

    ${taskAiDetailSection(task.ai_detail)}

    <div class="task-detail-section">
      <div class="task-detail-subhead">
        <h3>Comments</h3>
        <span class="tag">${comments.length}</span>
      </div>
      <div class="comment-form">
        <textarea id="taskCommentInput" class="textarea" rows="3" maxlength="2000" placeholder="Thêm comment cho task này..."></textarea>
        <button type="button" class="btn btn-primary btn-sm" onclick="submitTaskComment()">Gửi comment</button>
      </div>
      <div class="task-thread">
        ${comments.length ? comments.map(commentItem).join('') : '<div class="empty-state compact">Chưa có comment</div>'}
      </div>
    </div>

    <div class="task-detail-section">
      <div class="task-detail-subhead">
        <h3>Activity log</h3>
        <span class="tag">${logs.length}</span>
      </div>
      <div class="activity-list">
        ${logs.length ? logs.map(activityItem).join('') : '<div class="empty-state compact">Chưa có activity</div>'}
      </div>
    </div>
  `;
}

function taskDetailField(label, value) {
  return `
    <div class="task-detail-field">
      <span>${escHtml(label)}</span>
      <strong>${escHtml(value ?? '-')}</strong>
    </div>`;
}

function taskDeadlineInputValue(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function taskDeadlineExtensionSection(task) {
  if (!canDo('taskDeadlineExtend') || task.status === 'done') return '';
  return `
    <div class="task-detail-section">
      <div class="task-detail-subhead">
        <h3>Deadline extension</h3>
        <span class="tag">Manager</span>
      </div>
      <div class="task-detail-grid">
        <label class="task-detail-field">
          <span>New deadline</span>
          <input id="taskDeadlineExtensionInput" class="input" type="datetime-local" value="${escHtml(taskDeadlineInputValue(task.deadline))}">
        </label>
      </div>
      <div class="comment-form">
        <textarea id="taskDeadlineExtensionReason" class="textarea" rows="3" maxlength="500" placeholder="Reason required"></textarea>
        <button id="taskDeadlineExtensionSubmit" type="button" class="btn btn-primary btn-sm" onclick="submitTaskDeadlineExtension()">Extend deadline</button>
      </div>
    </div>`;
}

function taskAiDetailSection(detail) {
  if (!detail) return '';
  return `
    <div class="task-detail-section ai-work-package">
      <div class="task-detail-subhead">
        <h3>AI work package</h3>
        <span class="tag">Draft #${escHtml(detail.source_ai_draft_id)}</span>
      </div>
      <div class="task-detail-grid">
        ${taskDetailField('Type', detail.type || '-')}
        ${taskDetailField('Suggested role', detail.suggested_role || '-')}
      </div>
      ${detail.business_goal ? `<p class="task-detail-description"><strong>Business goal:</strong> ${escHtml(detail.business_goal)}</p>` : ''}
      ${aiListSection('Subtasks', detail.subtasks)}
      ${aiListSection('Acceptance criteria', detail.acceptance_criteria)}
      ${aiListSection('Data requirements', detail.data_requirements)}
      ${aiListSection('UI components', detail.ui_components)}
      ${aiListSection('Test cases', detail.test_cases)}
      ${aiListSection('Dependencies', detail.dependencies)}
      ${aiListSection('Risks', detail.risks)}
      ${detail.demo_value ? `<p class="task-detail-description"><strong>Demo value:</strong> ${escHtml(detail.demo_value)}</p>` : ''}
    </div>`;
}

function aiListSection(label, items) {
  const values = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!values.length) return '';
  return `
    <div class="ai-detail-list">
      <strong>${escHtml(label)}</strong>
      <ul>${values.map(item => `<li>${escHtml(item)}</li>`).join('')}</ul>
    </div>`;
}

function commentItem(c) {
  return `
    <div class="comment-item">
      <div class="comment-meta">
        <strong>${escHtml(c.author_name || `User ${c.author_user_id}`)}</strong>
        <span>${fmtDateTime(c.created_at)}</span>
      </div>
      <div class="comment-body">${escHtml(c.body)}</div>
    </div>`;
}

function activityItem(log) {
  return `
    <div class="activity-item">
      <div>
        <strong>${escHtml(log.action)}</strong>
        <span>${escHtml(log.actor_name || (log.actor_user_id ? `User ${log.actor_user_id}` : 'System'))}</span>
      </div>
      <div class="activity-detail">${escHtml(log.detail || '-')}</div>
      <time>${fmtDateTime(log.created_at)}</time>
    </div>`;
}

async function submitTaskComment() {
  const input = document.getElementById('taskCommentInput');
  const body = (input?.value || '').trim();
  if (!state.activeTaskId || !body) {
    toast('Vui lòng nhập nội dung comment', 'error');
    return;
  }
  try {
    await api(`/tasks/${state.activeTaskId}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ body }),
    });
    toast('Đã thêm comment', 'success');
    openTaskDetail(state.activeTaskId);
    loadNotificationCount();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function submitTaskDeadlineExtension() {
  if (!canDo('taskDeadlineExtend')) {
    toast('Ban khong co quyen gia han deadline', 'error');
    return;
  }
  const deadlineInput = document.getElementById('taskDeadlineExtensionInput');
  const reasonInput = document.getElementById('taskDeadlineExtensionReason');
  const button = document.getElementById('taskDeadlineExtensionSubmit');
  const reason = (reasonInput?.value || '').trim();
  if (!state.activeTaskId || !deadlineInput?.value || !reason) {
    toast('Nhap deadline moi va ly do gia han', 'error');
    return;
  }
  const deadline = new Date(deadlineInput.value);
  if (Number.isNaN(deadline.getTime())) {
    toast('Deadline khong hop le', 'error');
    return;
  }
  if (button) button.disabled = true;
  try {
    await api(`/tasks/${state.activeTaskId}/deadline-extension`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ deadline: deadline.toISOString(), reason }),
    });
    toast('Da gia han deadline', 'success');
    await openTaskDetail(state.activeTaskId);
    if (state.currentSection === 'kanban') loadKanban();
    if (state.currentSection === 'timeline') loadTimeline();
    loadNotificationCount();
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    if (button) button.disabled = false;
  }
}
