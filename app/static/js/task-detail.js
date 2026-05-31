async function openTaskDetail(taskId) {
  state.activeTaskId = Number(taskId);
  const overlay = document.getElementById('taskDetailOverlay');
  const body = document.getElementById('taskDetailBody');
  if (!overlay || !body) return;
  overlay.classList.remove('hidden');
  body.innerHTML = '<div class="skeleton" style="height:220px"></div>';
  try {
    const task = await api(`/tasks/${taskId}`);
    state.activeTask = task;
    renderTaskDetail(task);
  } catch (e) {
    body.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${escHtml(e.message)}</div>`;
  }
}

function closeTaskDetail() {
  const overlay = document.getElementById('taskDetailOverlay');
  if (overlay) overlay.classList.add('hidden');
  state.activeTaskId = null;
  state.activeTask = null;
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
        <span class="badge badge-priority-${task.priority || 'medium'}">${priorityLabel(task.priority || 'medium')}</span>
        <span class="due-pill ${dueStateClass(task.due_state)}">${dueStateLabel(task.due_state)}</span>
      </div>
    </div>

    <div class="task-detail-grid">
      ${taskDetailField('Assignee', task.assignee_name || `User ${task.assignee_id}`)}
      ${taskDetailField('Project', task.project_name || '-')}
      ${taskDetailField('Sprint', task.sprint_name || '-')}
      ${taskDetailField('Difficulty', diffLabel(task.difficulty))}
      ${taskDetailField('Priority', priorityLabel(task.priority || 'medium'))}
      ${taskDetailField('Story points', task.story_points)}
      ${taskDetailField('Deadline', fmtDateTime(task.deadline))}
      ${taskDetailField('Completed at', fmtDateTime(task.completed_at))}
    </div>

    ${taskDeadlineExtensionSection(task)}

    ${renderTaskDetailLabelsSection(task)}

    ${renderTaskDetailSubtasksSection(task)}

    ${renderTaskDetailChecklistSection(task)}

    ${renderTaskAttachmentsSection(task)}

    ${renderTaskActionsSection(task)}

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

function renderTaskDetailChecklistSection(task) {
  const checklist = task.checklist || [];
  const isCompleted = (item) => item.startsWith('[x] ');
  const getCleanText = (item) => item.startsWith('[x] ') ? item.substring(4) : (item.startsWith('[ ] ') ? item.substring(4) : item);

  return `
    <div class="task-detail-section">
      <div class="task-detail-subhead">
        <h3>Checklist</h3>
        <span class="tag" id="taskDetailChecklistProgress">${checklist.filter(isCompleted).length}/${checklist.length}</span>
      </div>
      <div id="taskDetailChecklistList" style="display:flex; flex-direction:column; gap:6px; margin-bottom:12px;">
        ${checklist.map((item, index) => {
          const checked = isCompleted(item);
          const cleanText = getCleanText(item);
          return `
            <div style="display:flex; align-items:center; gap:8px; background:#f8fafc; padding:6px 10px; border-radius:6px; border:1px solid #e2e8f0;">
              <input type="checkbox" ${checked ? 'checked' : ''} onchange="toggleTaskDetailChecklistItem(${index}, this.checked)" style="width:16px; height:16px; cursor:pointer;" />
              <span style="flex:1; font-size:13px; ${checked ? 'text-decoration:line-through; color:var(--text-3);' : ''}">${escHtml(cleanText)}</span>
              <button type="button" class="btn btn-outline btn-sm" onclick="deleteTaskDetailChecklistItem(${index})" style="color:red; border-color:transparent; padding:2px 6px; background:transparent; font-size:16px; font-weight:bold; cursor:pointer;">×</button>
            </div>`;
        }).join('') || '<div class="text-sm text-muted">Chưa có checklist item.</div>'}
      </div>
      <div class="comment-form" style="display:flex; gap:8px;">
        <input id="taskDetailChecklistInput" class="input" type="text" placeholder="Thêm checklist item..." style="flex:1" />
        <button type="button" class="btn btn-outline btn-sm" onclick="addTaskDetailChecklistItem()">Thêm</button>
      </div>
    </div>`;
}

async function toggleTaskDetailChecklistItem(index, checked) {
  if (!state.activeTask) return;
  const checklist = state.activeTask.checklist || [];
  if (index < 0 || index >= checklist.length) return;
  
  const item = checklist[index];
  const cleanText = item.startsWith('[x] ') ? item.substring(4) : (item.startsWith('[ ] ') ? item.substring(4) : item);
  checklist[index] = checked ? `[x] ${cleanText}` : `[ ] ${cleanText}`;
  
  try {
    await saveTaskDetailChecklist(checklist);
  } catch (e) {
    toast(`Lỗi cập nhật checklist: ${e.message}`, 'error');
    openTaskDetail(state.activeTaskId);
  }
}

async function deleteTaskDetailChecklistItem(index) {
  if (!state.activeTask) return;
  const checklist = state.activeTask.checklist || [];
  if (index < 0 || index >= checklist.length) return;
  
  checklist.splice(index, 1);
  
  try {
    await saveTaskDetailChecklist(checklist);
  } catch (e) {
    toast(`Lỗi xóa checklist item: ${e.message}`, 'error');
    openTaskDetail(state.activeTaskId);
  }
}

async function addTaskDetailChecklistItem() {
  if (!state.activeTask) return;
  const input = document.getElementById('taskDetailChecklistInput');
  const text = (input?.value || '').trim();
  if (!text) return;
  
  const checklist = state.activeTask.checklist || [];
  checklist.push(`[ ] ${text}`);
  
  try {
    await saveTaskDetailChecklist(checklist);
    if (input) input.value = '';
  } catch (e) {
    toast(`Lỗi thêm checklist item: ${e.message}`, 'error');
    openTaskDetail(state.activeTaskId);
  }
}

async function saveTaskDetailChecklist(checklist) {
  const taskId = state.activeTaskId;
  await api(`/tasks/${taskId}/metadata`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ checklist }),
  });
  
  state.activeTask.checklist = checklist;
  renderTaskDetail(state.activeTask);
  
  if (state.currentSection === 'kanban') {
    loadKanban();
  }
  if (state.currentSection === 'timeline') {
    loadTimeline();
  }
}

function renderTaskAttachmentsSection(task) {
  const attachments = task.attachment_metadata || [];
  
  const formatSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const isImage = (name) => /\.(jpg|jpeg|png|gif|webp)$/i.test(name);
  const isPdf = (name) => /\.pdf$/i.test(name);

  return `
    <div class="task-detail-section">
      <div class="task-detail-subhead">
        <h3>Tài liệu đính kèm</h3>
        <span class="tag" id="taskDetailAttachmentsCount">${attachments.length}</span>
      </div>
      
      <div id="taskDetailAttachmentsList" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap:12px; margin-bottom:12px;">
        ${attachments.map((att, index) => {
          let previewHtml = `<div style="height:80px; display:flex; align-items:center; justify-content:center; background:#f1f5f9; border-radius:4px; color:#64748b; font-size:24px;">📝</div>`;
          if (isImage(att.name)) {
            previewHtml = `<img src="${att.url}" alt="${escHtml(att.name)}" style="height:80px; width:100%; object-fit:cover; border-radius:4px; border:1px solid #e2e8f0;" />`;
          } else if (isPdf(att.name)) {
            previewHtml = `<div style="height:80px; display:flex; align-items:center; justify-content:center; background:#fee2e2; border-radius:4px; color:#b91c1c; font-size:24px; font-weight:bold;">PDF</div>`;
          }
          
          return `
            <div class="attachment-card" style="display:flex; flex-direction:column; background:#fff; border:1px solid #e2e8f0; border-radius:6px; padding:6px; position:relative; overflow:hidden;">
              ${previewHtml}
              <div style="margin-top:6px; display:flex; flex-direction:column; gap:2px; min-width:0;">
                <a href="${att.url}" target="_blank" download style="font-size:11.5px; font-weight:600; text-decoration:none; color:var(--brand); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${escHtml(att.name)}">${escHtml(att.name)}</a>
                <span style="font-size:10px; color:#64748b;">${formatSize(att.size)}</span>
              </div>
              <button type="button" onclick="deleteTaskAttachment('${escHtml(att.url)}')" style="position:absolute; top:4px; right:4px; background:rgba(255,255,255,0.8); border:none; border-radius:50%; width:20px; height:20px; display:grid; place-items:center; color:red; cursor:pointer; font-weight:bold; font-size:12px; border:1px solid #fca5a5;">×</button>
            </div>`;
        }).join('') || '<div class="text-sm text-muted" style="grid-column:1/-1;">Chưa có tài liệu đính kèm.</div>'}
      </div>
      
      <div style="display:flex; align-items:center;">
        <input type="file" id="taskAttachmentInput" style="display:none;" onchange="uploadTaskAttachment()" />
        <button type="button" class="btn btn-outline btn-sm" onclick="document.getElementById('taskAttachmentInput').click()">
          ${icon('plus', 'text-icon')} Thêm đính kèm
        </button>
        <span style="font-size:11px; color:#64748b; margin-left:8px;">Tối đa 50MB (Ảnh, PDF, tài liệu...)</span>
      </div>
    </div>`;
}

async function uploadTaskAttachment() {
  if (!state.activeTaskId) return;
  const input = document.getElementById('taskAttachmentInput');
  const file = input?.files[0];
  if (!file) return;

  const MAX_SIZE = 50 * 1024 * 1024;
  if (file.size > MAX_SIZE) {
    toast('File upload vượt quá dung lượng cho phép (50MB)', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);
  toast('Đang tải file lên...', 'info');

  try {
    const task = await api(`/tasks/${state.activeTaskId}/attachments`, {
      method: 'POST',
      body: formData,
    });
    
    toast('Tải file lên thành công', 'success');
    state.activeTask = task;
    renderTaskDetail(task);
    
    if (state.currentSection === 'kanban') loadKanban();
    if (state.currentSection === 'timeline') loadTimeline();
  } catch (e) {
    toast(`Lỗi upload file: ${e.message}`, 'error');
  } finally {
    if (input) input.value = '';
  }
}

async function deleteTaskAttachment(url) {
  if (!state.activeTaskId || !confirm('Bạn có chắc chắn muốn xóa file đính kèm này?')) return;
  
  try {
    const task = await api(`/tasks/${state.activeTaskId}/attachments`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    
    toast('Đã xóa file đính kèm', 'success');
    state.activeTask = task;
    renderTaskDetail(task);
    
    if (state.currentSection === 'kanban') loadKanban();
    if (state.currentSection === 'timeline') loadTimeline();
  } catch (e) {
    toast(`Lỗi xóa file: ${e.message}`, 'error');
  }
}

function renderTaskDetailLabelsSection(task) {
  const labels = task.labels || [];
  return `
    <div class="task-detail-section">
      <div class="task-detail-subhead">
        <h3>Nhãn (Labels)</h3>
        <span class="tag" id="taskDetailLabelsCount">${labels.length}</span>
      </div>
      <div id="taskDetailLabelsList" style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px;">
        ${labels.map((l, index) => {
          const { bg, fg, border } = hashStringToColor(l);
          return `
            <span class="badge" style="background:${bg}; color:${fg}; border:1px solid ${border}; padding:3px 8px; font-size:11px; border-radius:4px; font-weight:bold; display:inline-flex; align-items:center; gap:4px;">
              ${escHtml(l)}
              <span onclick="deleteTaskDetailLabel(${index})" style="cursor:pointer; font-weight:bold; font-size:12px; line-height:1; opacity:0.7; transition: opacity 0.2s;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.7">×</span>
            </span>`;
        }).join('') || '<div class="text-sm text-muted">Chưa có nhãn.</div>'}
      </div>
      <div class="comment-form" style="display:flex; gap:8px;">
        <input id="taskDetailLabelInput" class="input" type="text" placeholder="Thêm nhãn mới..." style="flex:1" onkeydown="if(event.key==='Enter') addTaskDetailLabel()" />
        <button type="button" class="btn btn-outline btn-sm" onclick="addTaskDetailLabel()">Thêm</button>
      </div>
    </div>`;
}

async function deleteTaskDetailLabel(index) {
  if (!state.activeTask) return;
  const labels = state.activeTask.labels || [];
  if (index < 0 || index >= labels.length) return;
  labels.splice(index, 1);
  try {
    await saveTaskDetailLabels(labels);
  } catch (e) {
    toast(`Lỗi gỡ nhãn: ${e.message}`, 'error');
    openTaskDetail(state.activeTaskId);
  }
}

async function addTaskDetailLabel() {
  if (!state.activeTask) return;
  const input = document.getElementById('taskDetailLabelInput');
  const text = (input?.value || '').trim();
  if (!text) return;
  
  const labels = state.activeTask.labels || [];
  if (labels.includes(text)) {
    toast('Nhãn này đã tồn tại', 'warning');
    return;
  }
  labels.push(text);
  try {
    await saveTaskDetailLabels(labels);
    if (input) input.value = '';
  } catch (e) {
    toast(`Lỗi thêm nhãn: ${e.message}`, 'error');
    openTaskDetail(state.activeTaskId);
  }
}

async function saveTaskDetailLabels(labels) {
  const taskId = state.activeTaskId;
  await api(`/tasks/${taskId}/metadata`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ labels }),
  });
  state.activeTask.labels = labels;
  renderTaskDetail(state.activeTask);
  if (state.currentSection === 'kanban') {
    loadKanban();
  }
  if (state.currentSection === 'timeline') {
    loadTimeline();
  }
}

function renderTaskDetailSubtasksSection(task) {
  const subtasks = task.subtasks || [];
  const isCompleted = (item) => item.startsWith('[x] ');
  const getCleanText = (item) => item.startsWith('[x] ') ? item.substring(4) : (item.startsWith('[ ] ') ? item.substring(4) : item);

  return `
    <div class="task-detail-section">
      <div class="task-detail-subhead">
        <h3>Công việc con (Subtasks)</h3>
        <span class="tag" id="taskDetailSubtasksProgress">${subtasks.filter(isCompleted).length}/${subtasks.length}</span>
      </div>
      <div id="taskDetailSubtasksList" style="display:flex; flex-direction:column; gap:6px; margin-bottom:12px;">
        ${subtasks.map((item, index) => {
          const checked = isCompleted(item);
          const cleanText = getCleanText(item);
          return `
            <div style="display:flex; align-items:center; gap:8px; background:#f0f9ff; padding:6px 10px; border-radius:6px; border:1px solid #bae6fd;">
              <input type="checkbox" ${checked ? 'checked' : ''} onchange="toggleTaskDetailSubtaskItem(${index}, this.checked)" style="width:16px; height:16px; cursor:pointer;" />
              <span style="flex:1; font-size:13px; ${checked ? 'text-decoration:line-through; color:var(--text-3);' : ''}">${escHtml(cleanText)}</span>
              <button type="button" class="btn btn-outline btn-sm" onclick="deleteTaskDetailSubtaskItem(${index})" style="color:red; border-color:transparent; padding:2px 6px; background:transparent; font-size:16px; font-weight:bold; cursor:pointer;">×</button>
            </div>`;
        }).join('') || '<div class="text-sm text-muted">Chưa có công việc con.</div>'}
      </div>
      <div class="comment-form" style="display:flex; gap:8px;">
        <input id="taskDetailSubtasksInput" class="input" type="text" placeholder="Thêm công việc con..." style="flex:1" onkeydown="if(event.key==='Enter') addTaskDetailSubtaskItem()" />
        <button type="button" class="btn btn-outline btn-sm" onclick="addTaskDetailSubtaskItem()">Thêm</button>
      </div>
    </div>`;
}

async function toggleTaskDetailSubtaskItem(index, checked) {
  if (!state.activeTask) return;
  const subtasks = state.activeTask.subtasks || [];
  if (index < 0 || index >= subtasks.length) return;
  
  const item = subtasks[index];
  const cleanText = item.startsWith('[x] ') ? item.substring(4) : (item.startsWith('[ ] ') ? item.substring(4) : item);
  subtasks[index] = checked ? `[x] ${cleanText}` : `[ ] ${cleanText}`;
  
  try {
    await saveTaskDetailSubtasks(subtasks);
  } catch (e) {
    toast(`Lỗi cập nhật subtask: ${e.message}`, 'error');
    openTaskDetail(state.activeTaskId);
  }
}

async function deleteTaskDetailSubtaskItem(index) {
  if (!state.activeTask) return;
  const subtasks = state.activeTask.subtasks || [];
  if (index < 0 || index >= subtasks.length) return;
  
  subtasks.splice(index, 1);
  
  try {
    await saveTaskDetailSubtasks(subtasks);
  } catch (e) {
    toast(`Lỗi xóa subtask: ${e.message}`, 'error');
    openTaskDetail(state.activeTaskId);
  }
}

async function addTaskDetailSubtaskItem() {
  if (!state.activeTask) return;
  const input = document.getElementById('taskDetailSubtasksInput');
  const text = (input?.value || '').trim();
  if (!text) return;
  
  const subtasks = state.activeTask.subtasks || [];
  subtasks.push(`[ ] ${text}`);
  
  try {
    await saveTaskDetailSubtasks(subtasks);
    if (input) input.value = '';
  } catch (e) {
    toast(`Lỗi thêm subtask: ${e.message}`, 'error');
    openTaskDetail(state.activeTaskId);
  }
}

async function saveTaskDetailSubtasks(subtasks) {
  const taskId = state.activeTaskId;
  await api(`/tasks/${taskId}/metadata`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subtasks }),
  });
  
  state.activeTask.subtasks = subtasks;
  renderTaskDetail(state.activeTask);
  
  if (state.currentSection === 'kanban') {
    loadKanban();
  }
  if (state.currentSection === 'timeline') {
    loadTimeline();
  }
}

function renderTaskActionsSection(task) {
  const isAuthorized = ['ADMIN', 'MANAGER'].includes(currentRoleCode());
  if (!isAuthorized) return '';
  return `
    <div class="task-detail-section" style="border-top:1px solid #e2e8f0; padding-top:12px; margin-top:12px;">
      <button type="button" class="btn btn-outline btn-sm" onclick="duplicateTaskUI(${task.id})" style="display:inline-flex; align-items:center; gap:6px;">
        ${icon('copy', 'text-icon')} Nhân bản công việc
      </button>
    </div>`;
}

async function duplicateTaskUI(taskId) {
  const task = state.activeTask;
  if (!task) return;
  const defaultTitle = `${task.title} (copy)`;
  const newTitle = prompt('Nhập tiêu đề cho công việc nhân bản:', defaultTitle);
  if (newTitle === null) return;
  const titleVal = newTitle.trim();
  if (!titleVal) {
    toast('Tiêu đề không được để trống', 'error');
    return;
  }
  try {
    toast('Đang nhân bản công việc...', 'info');
    const response = await api(`/tasks/${taskId}/duplicate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: titleVal
      })
    });
    toast('Nhân bản công việc thành công', 'success');
    closeTaskDetail();
    if (state.currentSection === 'kanban') {
      loadKanban();
    }
    if (state.currentSection === 'timeline') {
      loadTimeline();
    }
  } catch (e) {
    toast(`Lỗi nhân bản: ${e.message}`, 'error');
  }
}
