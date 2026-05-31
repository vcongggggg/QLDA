const TIMELINE_DAY_MS = 86400000;
let timelineDebounceTimer = null;

function loadTimelineDebounced() {
  clearTimeout(timelineDebounceTimer);
  timelineDebounceTimer = setTimeout(() => loadTimeline(), 250);
}

async function onTimelineProjectFilterChange() {
  await loadTimelineSprints();
  await loadTimeline();
}

async function loadTimeline() {
  const body = document.getElementById('timelineBody');
  const count = document.getElementById('timelineCount');
  if (!body) return;
  body.innerHTML = '<div class="skeleton" style="height:180px"></div>';
  if (count) count.textContent = '';

  try {
    await loadTimelineFilterOptions();
    const [tasks, context] = await Promise.all([
      api(buildTimelineTaskUrl()),
      loadTimelineContext(),
    ]);
    if (count) count.textContent = `${tasks.length} tasks`;
    renderTimeline(tasks, context);
  } catch (e) {
    body.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${escHtml(e.message)}</div>`;
  }
}

async function loadTimelineFilterOptions() {
  updateTimelineAssigneeVisibility();
  const project = document.getElementById('timelineProjectFilter');
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

  const assignee = document.getElementById('timelineAssigneeFilter');
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

  await loadTimelineSprints(false);
}

function updateTimelineAssigneeVisibility() {
  const assignee = document.getElementById('timelineAssigneeFilter');
  if (!assignee) return;
  assignee.style.display = isMemberRole() ? 'none' : '';
  assignee.disabled = isMemberRole();
  if (isMemberRole()) assignee.value = '';
}

async function loadTimelineSprints(resetValue = true) {
  const project = document.getElementById('timelineProjectFilter');
  const sprint = document.getElementById('timelineSprintFilter');
  if (!project || !sprint) return [];
  const previous = resetValue ? '' : sprint.value;
  sprint.innerHTML = '<option value="">All sprints</option>';
  sprint.disabled = true;
  if (!project.value) return [];

  try {
    const sprints = await api(`/projects/${project.value}/sprints`);
    sprints.forEach(item => {
      const option = document.createElement('option');
      option.value = item.id;
      option.textContent = item.name;
      option.dataset.startDate = item.start_date || '';
      option.dataset.endDate = item.end_date || '';
      sprint.appendChild(option);
    });
    sprint.disabled = false;
    if (previous && Array.from(sprint.options).some(option => option.value === previous)) {
      sprint.value = previous;
    }
    return sprints;
  } catch (_) {
    return [];
  }
}

async function loadTimelineContext() {
  const context = { projects: new Map(), users: new Map(), sprints: new Map() };
  const projectSelect = document.getElementById('timelineProjectFilter');
  const sprintSelect = document.getElementById('timelineSprintFilter');
  const assigneeSelect = document.getElementById('timelineAssigneeFilter');

  Array.from(projectSelect?.options || []).forEach(option => {
    if (option.value) context.projects.set(Number(option.value), { id: Number(option.value), name: option.textContent });
  });
  Array.from(sprintSelect?.options || []).forEach(option => {
    if (!option.value) return;
    context.sprints.set(Number(option.value), {
      id: Number(option.value),
      name: option.textContent,
      start_date: option.dataset.startDate || '',
      end_date: option.dataset.endDate || '',
    });
  });
  Array.from(assigneeSelect?.options || []).forEach(option => {
    if (option.value) context.users.set(Number(option.value), option.textContent);
  });

  return context;
}

function buildTimelineTaskUrl() {
  const params = new URLSearchParams();
  const projectId = document.getElementById('timelineProjectFilter')?.value;
  const sprintId = document.getElementById('timelineSprintFilter')?.value;
  const assignee = document.getElementById('timelineAssigneeFilter');
  const status = document.getElementById('timelineStatusFilter')?.value;
  const overdue = document.getElementById('timelineOverdueFilter')?.value;
  const keyword = document.getElementById('timelineKeywordFilter')?.value.trim();
  const deadlineFrom = document.getElementById('timelineDeadlineFromFilter')?.value;
  const deadlineTo = document.getElementById('timelineDeadlineToFilter')?.value;

  if (projectId) params.set('project_id', projectId);
  if (sprintId) params.set('sprint_id', sprintId);
  if (assignee && !assignee.disabled && assignee.value) params.set('assignee_id', assignee.value);
  if (status) params.set('status', status);
  if (overdue) params.set('overdue', overdue);
  if (keyword) params.set('keyword', keyword);
  if (deadlineFrom) params.set('deadline_from', new Date(`${deadlineFrom}T00:00:00Z`).toISOString());
  if (deadlineTo) params.set('deadline_to', new Date(`${deadlineTo}T23:59:59Z`).toISOString());

  const query = params.toString();
  return query ? `/tasks?${query}` : '/tasks';
}

function renderTimeline(tasks, context) {
  const body = document.getElementById('timelineBody');
  const range = document.getElementById('timelineRange');
  if (!body) return;
  if (!tasks.length) {
    if (range) range.textContent = '-';
    body.innerHTML = `<div class="empty-state"><div>${icon('calendar', 'empty-icon')}</div>No tasks match the timeline filters.</div>`;
    return;
  }

  const rows = tasks.map(task => timelineTaskRow(task, context));
  const bounds = timelineBounds(rows);
  const days = timelineDays(bounds.start, bounds.end);
  if (range) range.textContent = `${formatTimelineDate(bounds.start)} - ${formatTimelineDate(bounds.end)}`;
  const todayIndex = daysBetween(bounds.start, startOfDay(new Date()));

  body.innerHTML = `
    <div class="timeline-scroll" style="--timeline-days:${days.length}">
      <div class="timeline-grid timeline-grid-head">
        <div class="timeline-left timeline-left-head">Task</div>
        <div class="timeline-lane timeline-date-head">
          ${days.map(day => `<div class="timeline-day ${isWeekend(day) ? 'is-weekend' : ''}">${timelineDayLabel(day)}</div>`).join('')}
        </div>
      </div>
      ${timelineGroupedRows(rows, context, bounds, todayIndex)}
    </div>`;
}

function timelineTaskRow(task, context) {
  const sprint = task.sprint_id ? context.sprints.get(Number(task.sprint_id)) : null;
  const fallbackStart = parseTimelineDate(task.created_at) || parseTimelineDate(task.deadline) || new Date();
  const start = parseTimelineDate(sprint?.start_date) || fallbackStart;
  const end = parseTimelineDate(task.deadline) || start;
  return { task, start: startOfDay(start), end: startOfDay(end) };
}

function timelineBounds(rows) {
  const fromFilter = document.getElementById('timelineDeadlineFromFilter')?.value;
  const toFilter = document.getElementById('timelineDeadlineToFilter')?.value;
  const zoom = document.getElementById('timelineZoom')?.value || 'month';
  let start = fromFilter ? parseTimelineDate(`${fromFilter}T00:00:00Z`) : new Date(Math.min(...rows.map(row => row.start.getTime())));
  let end = toFilter ? parseTimelineDate(`${toFilter}T00:00:00Z`) : new Date(Math.max(...rows.map(row => row.end.getTime())));
  start = addDays(startOfDay(start), zoom === 'week' ? -2 : -7);
  end = addDays(startOfDay(end), zoom === 'week' ? 7 : 14);
  const maxDays = zoom === 'week' ? 28 : 90;
  if (daysBetween(start, end) > maxDays) end = addDays(start, maxDays);
  return { start, end };
}

function timelineDays(start, end) {
  const count = Math.max(1, daysBetween(start, end) + 1);
  return Array.from({ length: count }, (_, index) => addDays(start, index));
}

function timelineGroupedRows(rows, context, bounds, todayIndex) {
  const groups = new Map();
  rows.forEach(row => {
    const projectId = row.task.project_id == null ? 'none' : String(row.task.project_id);
    const projectName = context.projects.get(Number(row.task.project_id))?.name || 'No project';
    if (!groups.has(projectId)) groups.set(projectId, { name: projectName, rows: [] });
    groups.get(projectId).rows.push(row);
  });

  return Array.from(groups.values()).map(group => `
    <div class="timeline-group-row">
      <div class="timeline-left timeline-group-label">${escHtml(group.name)}</div>
      <div class="timeline-lane timeline-group-line"></div>
    </div>
    ${group.rows.map(row => timelineRowHtml(row, context, bounds, todayIndex)).join('')}
  `).join('');
}

function timelineRowHtml(row, context, bounds, todayIndex) {
  const task = row.task;
  const todayLine = todayIndex >= 0 && todayIndex <= daysBetween(bounds.start, bounds.end)
    ? `<div class="timeline-today" style="left:calc(${todayIndex} * var(--timeline-day-w) + var(--timeline-day-w) / 2)"></div>`
    : '';
  const clampedStart = new Date(Math.max(row.start.getTime(), bounds.start.getTime()));
  const clampedEnd = new Date(Math.min(row.end.getTime(), bounds.end.getTime()));
  const startIndex = Math.max(0, daysBetween(bounds.start, clampedStart));
  const span = Math.max(1, daysBetween(clampedStart, clampedEnd) + 1);
  const overdue = task.status !== 'done' && parseTimelineDate(task.deadline) < new Date();
  const assignee = context.users.get(Number(task.assignee_id)) || `User ${task.assignee_id}`;
  const sprint = context.sprints.get(Number(task.sprint_id));
  return `
    <div class="timeline-grid timeline-task-row" role="button" tabindex="0" data-task-id="${Number(task.id)}" onclick="openTaskDetail(${Number(task.id)})" onkeydown="if(event.key==='Enter')openTaskDetail(${Number(task.id)})">
      <div class="timeline-left timeline-task-label">
        <strong>${escHtml(task.title)}</strong>
        <span>${escHtml(assignee)}${sprint ? ` - ${escHtml(sprint.name)}` : ''}</span>
      </div>
      <div class="timeline-lane">
        ${todayLine}
        <div class="timeline-bar timeline-${escHtml(task.status)} ${overdue ? 'is-overdue' : ''}" style="grid-column:${startIndex + 1} / span ${span}">
          <span>${statusLabel(task.status)}</span>
          <small>${Number(task.story_points || 0)} SP</small>
        </div>
      </div>
    </div>`;
}

async function resetTimelineFilters() {
  ['timelineProjectFilter', 'timelineAssigneeFilter', 'timelineStatusFilter', 'timelineOverdueFilter'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  ['timelineKeywordFilter', 'timelineDeadlineFromFilter', 'timelineDeadlineToFilter'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  const zoom = document.getElementById('timelineZoom');
  if (zoom) zoom.value = 'month';
  await loadTimelineSprints();
  await loadTimeline();
}

function parseTimelineDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function startOfDay(date) {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
}

function addDays(date, days) {
  return new Date(date.getTime() + days * TIMELINE_DAY_MS);
}

function daysBetween(start, end) {
  return Math.round((startOfDay(end).getTime() - startOfDay(start).getTime()) / TIMELINE_DAY_MS);
}

function formatTimelineDate(date) {
  return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
}

function timelineDayLabel(date) {
  const zoom = document.getElementById('timelineZoom')?.value || 'month';
  if (zoom === 'week') return date.toLocaleDateString('vi-VN', { weekday: 'short', day: '2-digit' });
  return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
}

function isWeekend(date) {
  return [0, 6].includes(date.getUTCDay());
}
