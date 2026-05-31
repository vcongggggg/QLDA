async function loadAI() {
  await populateAiSelectors();
  await loadAiDrafts();
  await loadRagDocuments();
  renderAiPreview();
}

async function populateAiSelectors() {
  const assignee = document.getElementById('aiAssigneeSelect');
  const project = document.getElementById('aiProjectSelect');
  const ragProject = document.getElementById('ragProjectSelect');
  if (!assignee || !project) return;

  if (assignee.options.length === 0) {
    try {
      const users = await api('/users');
      assignee.innerHTML = users.map(u => `<option value="${u.id}">${escHtml(u.full_name)} (${u.role})</option>`).join('');
    } catch (e) {
      assignee.innerHTML = `<option value="">Không tải được user</option>`;
    }
  }

  if (project.options.length <= 1) {
    try {
      const projects = await api('/projects');
      projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name;
        project.appendChild(opt);
        if (ragProject) {
          const ragOpt = document.createElement('option');
          ragOpt.value = p.id;
          ragOpt.textContent = p.name;
          ragProject.appendChild(ragOpt);
        }
      });
    } catch (_) {}
  }
}

function getRagOptions() {
  return {
    useRag: document.getElementById('aiUseRag')?.checked !== false,
    ragQuery: document.getElementById('aiRagQuery')?.value.trim() || '',
  };
}

async function generateAiTasksFromText() {
  if (!canDo('aiGenerate')) {
    toast('Ban khong co quyen tao AI task', 'error');
    return;
  }
  const text = document.getElementById('aiRequirementText').value.trim();
  const maxTasks = Number(document.getElementById('aiMaxTasks').value || 8);
  const { useRag, ragQuery } = getRagOptions();
  if (text.length < 10) {
    toast('Vui lòng nhập requirements dài hơn 10 ký tự', 'error');
    return;
  }
  await generateAiTasks(() => api('/ai/task-breakdown', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, max_tasks: maxTasks, use_rag: useRag, rag_query: ragQuery }),
  }));
}

async function generateAiTasksFromDocx() {
  if (!canDo('aiGenerate')) {
    toast('Ban khong co quyen tao AI task', 'error');
    return;
  }
  const file = document.getElementById('aiDocxFile').files[0];
  const maxTasks = Number(document.getElementById('aiMaxTasks').value || 8);
  const { useRag, ragQuery } = getRagOptions();
  if (!file) {
    toast('Vui lòng chọn file .docx', 'error');
    return;
  }
  const form = new FormData();
  form.append('file', file);
  form.append('max_tasks', String(maxTasks));
  form.append('use_rag', String(useRag));
  if (ragQuery) {
    form.append('rag_query', ragQuery);
  }
  await generateAiTasks(() => api('/ai/task-breakdown/docx', {
    method: 'POST',
    body: form,
  }));
}

async function generateAiTasks(loader) {
  const preview = document.getElementById('aiTaskPreview');
  preview.innerHTML = '<div class="skeleton" style="height:160px"></div>';
  try {
    const result = await loader();
    state.aiItems = result.items || [];
    state.activeAiDraftId = result.ai_draft_id || null;
    state.activeAiDraft = state.activeAiDraftId ? { id: state.activeAiDraftId, status: result.status || 'draft', items: state.aiItems } : null;
    const ragMeta = result.retrieved_context_count ? ` · RAG: ${(result.retrieved_sources || []).join(', ')}` : '';
    document.getElementById('aiPreviewMeta').textContent = `${state.aiItems.length} task · nguồn: ${result.source}${ragMeta}`;
    document.getElementById('aiWarnings').textContent = (result.warnings || []).join(' ');
    await loadAiDrafts();
    renderAiPreview();
    toast('Đã tạo danh sách task đề xuất', 'success');
  } catch (e) {
    preview.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${escHtml(e.message)}</div>`;
    toast(e.message, 'error');
  }
}

function renderAiPreview() {
  const el = document.getElementById('aiTaskPreview');
  if (!el) return;
  if (!state.aiItems.length) {
    el.innerHTML = `<div class="empty-state"><div>AI</div>Dán requirements hoặc upload .docx để tạo task đề xuất</div>`;
    return;
  }
  el.innerHTML = `
    <table class="kpi-table ai-task-table">
      <thead>
        <tr>
          <th>Chọn</th><th>Task</th><th>Loại</th><th>SP</th><th>Deadline</th><th>Chi tiết</th>
        </tr>
      </thead>
      <tbody>
        ${state.aiItems.map((item, i) => `
          <tr>
            <td><input type="checkbox" ${item.selected !== false ? 'checked' : ''} onchange="toggleAiTask(${i}, this.checked)" /></td>
            <td>
              <strong>${escHtml(item.title)}</strong>
              <div class="text-sm text-muted">${escHtml(item.description || '')}</div>
            </td>
            <td><span class="tag">${escHtml(item.type || 'implementation')}</span></td>
            <td>${item.story_points}</td>
            <td>+${item.deadline_offset_days} ngày</td>
            <td><button type="button" class="btn btn-outline btn-sm" onclick="openAiItemDetail(${i})">Chi tiết</button></td>
          </tr>
        `).join('')}
      </tbody>
    </table>`;
}

function toggleAiTask(index, checked) {
  if (state.aiItems[index]) {
    state.aiItems[index] = { ...state.aiItems[index], selected: checked };
  }
}

function openAiItemDetail(index) {
  const item = state.aiItems[index];
  const overlay = document.getElementById('aiDraftOverlay');
  const title = document.getElementById('aiDraftDrawerTitle');
  const body = document.getElementById('aiDraftReviewBody');
  if (!item || !overlay || !body) return;
  overlay.classList.remove('hidden');
  if (title) title.textContent = item.title || 'AI task detail';
  body.innerHTML = `
    <div class="task-detail-section">
      <div class="task-detail-status-row">
        <span class="tag">${escHtml(item.type || 'implementation')}</span>
        <span class="badge badge-${item.difficulty}">${diffLabel(item.difficulty)}</span>
        <span class="tag">${Number(item.story_points || 3)} SP</span>
        <span class="tag">+${Number(item.deadline_offset_days || 7)} ngày</span>
      </div>
      <p class="task-detail-description">${escHtml(item.description || '')}</p>
      ${item.rationale ? `<p class="task-detail-description"><strong>Lý do:</strong> ${escHtml(item.rationale)}</p>` : ''}
    </div>
    ${taskAiDetailSection({ ...item, source_ai_draft_id: state.activeAiDraftId || '-' })}
    <div class="action-row">
      <button class="btn btn-outline" onclick="closeAiDraftReview()">Đóng</button>
    </div>`;
}

async function loadAiDrafts() {
  const el = document.getElementById('aiDraftsTable');
  if (!el) return;
  el.innerHTML = '<div class="skeleton" style="height:96px"></div>';
  try {
    const drafts = await api('/ai/task-breakdown/drafts');
    state.aiDrafts = drafts || [];
    renderAiDrafts();
  } catch (e) {
    el.innerHTML = `<div class="empty-state compact">${escHtml(e.message)}</div>`;
  }
}

function renderAiDrafts() {
  const el = document.getElementById('aiDraftsTable');
  if (!el) return;
  if (!state.aiDrafts.length) {
    el.innerHTML = '<div class="empty-state compact">Chưa có AI draft</div>';
    return;
  }
  const canReview = canDo('aiReview');
  const canImport = canDo('aiImport');
  el.innerHTML = `
    <table class="kpi-table ai-drafts-table">
      <thead>
        <tr><th>Batch</th><th>Nguồn</th><th>Task</th><th>Status</th><th>Tạo lúc</th><th>Reviewer</th><th></th></tr>
      </thead>
      <tbody>
        ${state.aiDrafts.map(d => `
          <tr>
            <td><strong>#${d.id}</strong><div class="text-sm text-muted">${escHtml(d.source_name || d.source_summary || '')}</div></td>
            <td>${aiSourceLabel(d.source_type)}</td>
            <td>${d.item_count || 0}</td>
            <td><span class="badge badge-${aiStatusClass(d.status)}">${aiStatusLabel(d.status)}</span></td>
            <td>${safeDate(d.created_at)}</td>
            <td>${d.reviewer_id ? `User ${d.reviewer_id}` : '-'}</td>
            <td>
              <div class="action-row compact-actions">
                ${canReview ? `<button class="btn btn-outline btn-sm" onclick="openAiDraftReview(${d.id})">Review</button>` : ''}
                ${canImport && d.status !== 'imported' ? `<button class="btn btn-primary btn-sm" onclick="importAiDraft(${d.id})">Import</button>` : ''}
              </div>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>`;
}

async function openAiDraftReview(draftId) {
  const overlay = document.getElementById('aiDraftOverlay');
  const body = document.getElementById('aiDraftReviewBody');
  if (!overlay || !body) return;
  overlay.classList.remove('hidden');
  body.innerHTML = '<div class="skeleton" style="height:180px"></div>';
  try {
    const draft = await api(`/ai/task-breakdown/drafts/${draftId}`);
    state.activeAiDraftId = draft.id;
    state.activeAiDraft = draft;
    state.aiItems = draft.items || [];
    document.getElementById('aiPreviewMeta').textContent = `${state.aiItems.length} task · draft #${draft.id} · ${aiStatusLabel(draft.status)}`;
    renderAiPreview();
    renderAiDraftReview(draft);
  } catch (e) {
    body.innerHTML = `<div class="empty-state compact">${escHtml(e.message)}</div>`;
  }
}

function closeAiDraftReview() {
  const overlay = document.getElementById('aiDraftOverlay');
  if (overlay) overlay.classList.add('hidden');
}

function renderAiDraftReview(draft) {
  const title = document.getElementById('aiDraftDrawerTitle');
  const body = document.getElementById('aiDraftReviewBody');
  if (!body) return;
  if (title) title.textContent = `AI Draft #${draft.id}`;
  const canReview = canDo('aiReview');
  const canImport = canDo('aiImport');
  body.innerHTML = `
    <div class="task-detail-section">
      <div class="task-detail-status-row">
        <span class="badge badge-${aiStatusClass(draft.status)}">${aiStatusLabel(draft.status)}</span>
        <span class="tag">${aiSourceLabel(draft.source_type)}</span>
      </div>
      <p class="task-detail-description">${escHtml(draft.source_summary || draft.source_name || '')}</p>
    </div>
    <div class="task-detail-section ai-review-items">
      ${(draft.items || []).map((item, i) => aiReviewItemRow(item, i)).join('')}
    </div>
    <div class="task-detail-section form-stack">
      <label class="field-label">Review note</label>
      <textarea id="aiReviewNote" class="textarea" rows="3">${escHtml(draft.review_note || '')}</textarea>
      <label class="field-label">Edit reason</label>
      <textarea id="aiEditReason" class="textarea" rows="3">${escHtml(draft.edit_reason || '')}</textarea>
      <div class="action-row">
        ${canReview ? `<button class="btn btn-primary" onclick="saveAiDraftReview(${draft.id})">Review</button>` : ''}
        ${canImport && draft.status !== 'imported' ? `<button class="btn btn-outline" onclick="importAiDraft(${draft.id})">Import</button>` : ''}
        <button class="btn btn-outline" onclick="closeAiDraftReview()">Close</button>
      </div>
    </div>`;
}

function aiReviewItemRow(item, i) {
  return `
    <div class="ai-review-item" data-ai-review-index="${i}">
      <label class="check-row">
        <input id="aiReviewSelected${i}" type="checkbox" ${item.selected !== false ? 'checked' : ''} />
        <span>Import</span>
      </label>
      <input id="aiReviewTitle${i}" class="input" type="text" value="${escHtml(item.title || '')}" />
      <input id="aiReviewType${i}" class="input" type="text" value="${escHtml(item.type || 'implementation')}" placeholder="Type" />
      <textarea id="aiReviewDesc${i}" class="textarea" rows="2">${escHtml(item.description || '')}</textarea>
      <textarea id="aiReviewBusinessGoal${i}" class="textarea" rows="2" placeholder="Business goal">${escHtml(item.business_goal || '')}</textarea>
      <div class="inline-fields">
        <select id="aiReviewDifficulty${i}" class="select">
          ${['easy', 'medium', 'hard'].map(d => `<option value="${d}" ${item.difficulty === d ? 'selected' : ''}>${diffLabel(d)}</option>`).join('')}
        </select>
        <input id="aiReviewPoints${i}" class="input" type="number" min="1" max="13" value="${Number(item.story_points || 3)}" />
        <input id="aiReviewOffset${i}" class="input" type="number" min="1" max="90" value="${Number(item.deadline_offset_days || 7)}" />
        <input id="aiReviewSuggestedRole${i}" class="input" type="text" value="${escHtml(item.suggested_role || '')}" placeholder="Suggested role" />
      </div>
      ${AI_LIST_FIELDS.map(field => `
        <label class="field-label">${AI_LIST_LABELS[field]}</label>
        <textarea id="aiReview${field}${i}" class="textarea" rows="2">${escHtml(listToLines(item[field]))}</textarea>
      `).join('')}
      <textarea id="aiReviewDemoValue${i}" class="textarea" rows="2" placeholder="Demo value">${escHtml(item.demo_value || '')}</textarea>
      <input id="aiReviewRationale${i}" class="input" type="text" value="${escHtml(item.rationale || '')}" />
    </div>`;
}

function collectAiReviewItems() {
  const rows = [...document.querySelectorAll('[data-ai-review-index]')];
  return rows.map(row => {
    const i = row.dataset.aiReviewIndex;
    return {
      title: document.getElementById(`aiReviewTitle${i}`).value.trim(),
      type: document.getElementById(`aiReviewType${i}`).value.trim() || 'implementation',
      description: document.getElementById(`aiReviewDesc${i}`).value.trim() || null,
      business_goal: document.getElementById(`aiReviewBusinessGoal${i}`).value.trim() || null,
      ...Object.fromEntries(AI_LIST_FIELDS.map(field => [
        field,
        linesToList(document.getElementById(`aiReview${field}${i}`).value),
      ])),
      demo_value: document.getElementById(`aiReviewDemoValue${i}`).value.trim() || null,
      suggested_role: document.getElementById(`aiReviewSuggestedRole${i}`).value.trim() || null,
      difficulty: document.getElementById(`aiReviewDifficulty${i}`).value,
      story_points: Number(document.getElementById(`aiReviewPoints${i}`).value || 3),
      deadline_offset_days: Number(document.getElementById(`aiReviewOffset${i}`).value || 7),
      rationale: document.getElementById(`aiReviewRationale${i}`).value.trim() || null,
      selected: document.getElementById(`aiReviewSelected${i}`).checked,
    };
  });
}

async function saveAiDraftReview(draftId) {
  if (!canDo('aiReview')) {
    toast('Ban khong co quyen review AI draft', 'error');
    return;
  }
  const items = collectAiReviewItems();
  if (!items.length || items.some(item => !item.title)) {
    toast('Vui lòng giữ ít nhất một task có tiêu đề', 'error');
    return;
  }
  try {
    const draft = await api(`/ai/task-breakdown/drafts/${draftId}/review`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items,
        review_note: document.getElementById('aiReviewNote').value.trim() || null,
        edit_reason: document.getElementById('aiEditReason').value.trim() || null,
      }),
    });
    state.aiItems = draft.items || [];
    state.activeAiDraft = draft;
    renderAiPreview();
    renderAiDraftReview(draft);
    await loadAiDrafts();
    toast('Đã review AI draft', 'success');
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function importAiDraft(draftId) {
  if (!canDo('aiImport')) {
    toast('Ban khong co quyen import AI task', 'error');
    return;
  }
  const assigneeId = Number(document.getElementById('aiAssigneeSelect').value);
  const projectRaw = document.getElementById('aiProjectSelect').value;
  if (!draftId) {
    toast('Chưa chọn AI draft để import', 'error');
    return;
  }
  if (!assigneeId) {
    toast('Vui lòng chọn người phụ trách', 'error');
    return;
  }
  try {
    const result = await api('/ai/task-breakdown/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ai_draft_id: draftId,
        assignee_id: assigneeId,
        project_id: projectRaw ? Number(projectRaw) : null,
        sprint_id: null,
      }),
    });
    toast(`Đã import ${result.created_count} task vào Kanban`, 'success');
    state.aiItems = [];
    state.activeAiDraftId = null;
    state.activeAiDraft = null;
    renderAiPreview();
    document.getElementById('aiPreviewMeta').textContent = 'Đã import xong';
    closeAiDraftReview();
    await loadAiDrafts();
  } catch (e) {
    toast(e.message, 'error');
  }
}

function aiStatusClass(status) {
  return { draft: 'draft', reviewed: 'reviewed', imported: 'imported' }[status] || 'todo';
}

function aiStatusLabel(status) {
  return { draft: 'Draft', reviewed: 'Reviewed', imported: 'Imported' }[status] || status;
}

function aiSourceLabel(source) {
  return source === 'docx' ? 'DOCX' : 'Text';
}

async function importSelectedAiTasks() {
  await importAiDraft(state.activeAiDraftId);
}
