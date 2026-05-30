/* ══════════════════════════════════════════════
   TeamsWork – Client Application
   ══════════════════════════════════════════════ */

// ── State ──────────────────────────────────────
const state = {
  userId: localStorage.getItem('tw_uid') || '1',
  accessToken: localStorage.getItem('tw_access_token') || '',
  currentUser: null,
  permissions: new Set(),
  month: new Date().toISOString().slice(0, 7),
  currentSection: 'dashboard',
  currentUserRole: null,
  charts: {},
  aiItems: [],
  aiDrafts: [],
  activeAiDraftId: null,
  activeAiDraft: null,
  rbac: { roles: [], permissions: [], selectedKeys: new Set() },
  activeTaskId: null,
  draggingTaskId: null,
  notificationsOpen: false,
  loginMessage: '',
  adminUsers: { rows: [], search: '', role: '', department: '', status: '', sort: 'name', dir: 'asc', page: 1, pageSize: 8 },
  adminDepartments: { rows: [], search: '', status: '', sort: 'name', dir: 'asc', page: 1, pageSize: 8 },
};

const ROLE_NAV_POLICY = {
  ADMIN:   ['dashboard', 'projects', 'kanban', 'teams', 'kpi', 'reports', 'ai', 'ops', 'admin'],
  MANAGER: ['dashboard', 'projects', 'kanban', 'teams', 'kpi', 'reports', 'ai'],
  LEADER:  ['dashboard', 'projects', 'kanban', 'teams', 'kpi', 'reports', 'ai'],
  MEMBER:  ['dashboard', 'kanban', 'kpi'],
  HR:      ['dashboard', 'admin', 'kpi', 'reports', 'teams'],
  AUDITOR: ['dashboard', 'reports', 'ops'],
};

const ROLE_NAV_LABELS = {
  MEMBER: { kanban: 'My Tasks', kpi: 'My KPI' },
  ADMIN: { admin: 'Quản trị' },
};

const ROLE_COLORS = {
  ADMIN: 'role-admin',
  MANAGER: 'role-manager',
  LEADER: 'role-leader',
  MEMBER: 'role-member',
  HR: 'role-hr',
  AUDITOR: 'role-auditor',
};

const MODULE_VIEW_PERMISSIONS = {
  dashboard: ['DASHBOARD_VIEW'],
  kanban: ['KANBAN_VIEW'],
  projects: ['PROJECT_VIEW'],
  kpi: ['KPI_VIEW_OWN', 'KPI_VIEW_TEAM', 'KPI_VIEW_ALL'],
  reports: ['REPORT_VIEW_TEAM', 'REPORT_VIEW_ALL'],
  ai: ['AI_TASK_VIEW'],
  teams: ['TEAM_VIEW'],
  ops: ['AUDIT_VIEW', 'OPS_VIEW'],
  admin: ['USER_VIEW', 'ROLE_VIEW', 'DEPARTMENT_VIEW'],
};

const ACTION_PERMISSIONS = {
  taskUpdate: ['KANBAN_UPDATE_OWN_TASK', 'KANBAN_MANAGE_TEAM', 'KANBAN_MANAGE_ALL', 'tasks.update_own', 'tasks.update_any'],
  reportExport: ['REPORT_EXPORT', 'reports.export'],
  aiGenerate: ['AI_TASK_GENERATE', 'ai.preview'],
  aiReview: ['AI_TASK_REVIEW', 'ai.import'],
  aiImport: ['AI_TASK_IMPORT', 'ai.import'],
  ragManage: ['rag.manage'],
  opsManage: ['OPS_MANAGE', 'monitoring.admin', 'teams.manage'],
  seed: ['monitoring.admin'],
  roleManage: ['ROLE_MANAGE', 'roles.manage'],
};

function icon(name, className = 'ui-icon') {
  return `<svg class="${className}" aria-hidden="true"><use href="#i-${name}"></use></svg>`;
}

// ── Init ───────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  const mp = document.getElementById('monthPicker');
  if (mp) mp.value = state.month;

  const userInput = document.getElementById('userIdInput');
  if (userInput) userInput.value = state.userId;
  const devSwitcher = document.getElementById('devUserSwitcher');
  if (devSwitcher && isDevAuthEnabled()) devSwitcher.classList.remove('hidden');
  await bootAuth();
  initKanbanDragDrop();

  document.addEventListener('click', (e) => {
    const wrap = document.querySelector('.notification-wrap');
    if (state.notificationsOpen && wrap && !wrap.contains(e.target)) {
      closeNotificationPanel();
    }
  });
});

window.addEventListener('hashchange', () => {
  if (!state.currentUser) return;
  navigate(requestedSectionFromUrl() || firstAllowedSection() || 'dashboard', { replace: true });
});

// ── API Helper ─────────────────────────────────
async function api(path, opts = {}) {
  const headers = { ...opts.headers };
  if (state.accessToken) headers.Authorization = `Bearer ${state.accessToken}`;
  else if (isDevAuthEnabled()) headers['X-User-Id'] = state.userId;
  try {
    const res = await fetch(path, { ...opts, headers });
    if (res.status === 401 && state.currentUser) {
      logout({ expired: true });
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      const message = res.status === 403
        ? 'Bạn không có quyền truy cập chức năng này.'
        : (err.detail || `HTTP ${res.status}`);
      const error = new Error(message);
      error.status = res.status;
      throw error;
    }
    return await res.json();
  } catch (e) {
    throw e;
  }
}

function isDevAuthEnabled() {
  return window.VITE_ENABLE_DEV_AUTH === true || localStorage.getItem('VITE_ENABLE_DEV_AUTH') === 'true';
}

function roleCode(value = state.currentUserRole) {
  const raw = String(value || '').trim();
  const aliases = { admin: 'ADMIN', manager: 'MANAGER', leader: 'LEADER', staff: 'MEMBER', member: 'MEMBER', hr: 'HR', auditor: 'AUDITOR' };
  return aliases[raw.toLowerCase()] || raw.toUpperCase() || 'MEMBER';
}

function currentRoleCode() {
  return roleCode(state.currentUserRole || state.currentUser?.role?.code || state.currentUser?.role_code || state.currentUser?.role);
}

function isMemberRole() {
  return currentRoleCode() === 'MEMBER';
}

function roleAllowsSection(section) {
  const allowed = ROLE_NAV_POLICY[currentRoleCode()] || ROLE_NAV_POLICY.MEMBER;
  return allowed.includes(section);
}

function navLabel(section) {
  return (ROLE_NAV_LABELS[currentRoleCode()] || {})[section] || TITLES[section] || section;
}

// ── Toast ──────────────────────────────────────
function toast(msg, type = 'info') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type}`;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add('hidden'), 3500);
}

// ── User ───────────────────────────────────────
function setCurrentUserDisplay({ name, role, avatar, department }) {
  document.getElementById('userName').textContent = name;
  const roleEl = document.getElementById('userRole');
  const code = roleCode(role);
  if (roleEl) {
    roleEl.textContent = department ? `${roleName(code)} • ${department}` : roleName(code);
    roleEl.className = `user-role role-pill ${ROLE_COLORS[code] || 'role-member'}`;
  }
  document.getElementById('userAvatar').textContent = avatar;
  const dep = document.getElementById('userDepartment');
  if (dep) dep.textContent = '';
}

function roleName(code) {
  return { ADMIN: 'Admin', MANAGER: 'Manager', LEADER: 'Leader', MEMBER: 'Member', HR: 'HR', AUDITOR: 'Auditor' }[roleCode(code)] || code;
}

async function bootAuth() {
  if (!state.accessToken && !isDevAuthEnabled()) {
    showLogin();
    return;
  }
  try {
    await loadCurrentUser();
    showApp();
    applyPermissionNavigation();
    loadNotificationCount();
    navigate(requestedSectionFromUrl() || firstAllowedSection() || 'dashboard', { replace: true });
  } catch (_) {
    state.accessToken = '';
    localStorage.removeItem('tw_access_token');
    showLogin();
  }
}

function showLogin() {
  document.getElementById('loginScreen')?.classList.remove('hidden');
  document.getElementById('sidebar')?.classList.add('hidden');
  document.getElementById('mainWrap')?.classList.add('hidden');
  if (state.loginMessage) {
    const error = document.getElementById('loginError');
    if (error) {
      error.textContent = state.loginMessage;
      error.classList.remove('hidden');
    }
    state.loginMessage = '';
  }
}

function showApp() {
  document.getElementById('loginScreen')?.classList.add('hidden');
  document.getElementById('sidebar')?.classList.remove('hidden');
  document.getElementById('mainWrap')?.classList.remove('hidden');
}

async function login(event) {
  if (event) event.preventDefault();
  const error = document.getElementById('loginError');
  const btn = document.querySelector('.login-submit');
  const originalText = btn?.textContent || 'Đăng nhập';
  if (error) error.classList.add('hidden');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Signing in...';
  }
  try {
    const payload = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        usernameOrEmail: document.getElementById('loginEmail').value,
        password: document.getElementById('loginPassword').value,
      }),
    }).then(async res => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Dang nhap that bai');
      }
      return res.json();
    });
    state.accessToken = payload.accessToken;
    localStorage.setItem('tw_access_token', state.accessToken);
    await bootAuth();
  } catch (e) {
    if (error) {
      error.textContent = e.message;
      error.classList.remove('hidden');
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }
}

function logout(options = {}) {
  state.accessToken = '';
  state.currentUser = null;
  state.permissions = new Set();
  state.currentUserRole = null;
  state.currentSection = 'dashboard';
  closeNotificationPanel();
  localStorage.removeItem('tw_access_token');
  if (options.expired) {
    state.loginMessage = 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.';
    toast(state.loginMessage, 'error');
  }
  if (window.history) {
    window.history.replaceState(null, '', window.location.pathname);
  }
  showLogin();
}

async function loadCurrentUser() {
  try {
    const me = await api(state.accessToken ? '/auth/me' : '/users/me');
    const fullName = me.fullName || me.full_name;
    const role = me.role?.code || me.role_code || me.role || me.role_detail?.code || 'MEMBER';
    const department = me.department?.name || me.department_detail?.name || me.department || '';
    state.currentUserRole = roleCode(role);
    setCurrentUserDisplay({
      name: fullName,
      role,
      department,
      avatar: fullName.charAt(0).toUpperCase(),
    });
    state.currentUser = me;
    state.permissions = new Set(me.permissions || []);
    updateKanbanAssigneeVisibility();
  } catch (_) {
    setCurrentUserDisplay({
      name: `User ${state.userId}`,
      role: 'Unknown',
      avatar: 'U',
    });
    state.currentUserRole = null;
    updateKanbanAssigneeVisibility();
  }
}

async function changeUserId(val) {
  state.userId = String(val);
  localStorage.setItem('tw_uid', state.userId);
  await loadCurrentUser();
  applyPermissionNavigation();
  loadNotificationCount();
  closeNotificationPanel();
  navigate(requestedSectionFromUrl() || firstAllowedSection() || 'dashboard', { replace: true });
}

function hasPermission(key) {
  return state.permissions.has(key);
}

function hasAnyPermission(keys) {
  return (keys || []).some(key => state.permissions.has(key));
}

function canViewModule(module) {
  return roleAllowsSection(module) && hasAnyPermission(MODULE_VIEW_PERMISSIONS[module] || []);
}

function canDo(action) {
  return hasAnyPermission(ACTION_PERMISSIONS[action] || []);
}

function navAllowed(el) {
  const section = el.dataset.section;
  if (section && !roleAllowsSection(section)) return false;
  if (section && !canViewModule(section)) return false;
  const one = el.dataset.permission;
  const any = el.dataset.anyPermission;
  if (one && !hasPermission(one)) return false;
  if (any && !hasAnyPermission(any.split(',').map(x => x.trim()))) return false;
  return true;
}

function applyPermissionNavigation() {
  document.querySelectorAll('.nav-item').forEach(el => {
    const section = el.dataset.section;
    const label = section ? navLabel(section) : '';
    const span = el.querySelector('span');
    if (span && label) span.textContent = label;
    el.classList.toggle('hidden', !navAllowed(el));
  });
  applyPermissionVisibility();
}

function applyPermissionVisibility(root = document) {
  root.querySelectorAll('[data-requires-permission]').forEach(el => {
    el.classList.toggle('hidden', !hasPermission(el.dataset.requiresPermission));
  });
  root.querySelectorAll('[data-requires-any-permission]').forEach(el => {
    const keys = el.dataset.requiresAnyPermission.split(',').map(x => x.trim()).filter(Boolean);
    el.classList.toggle('hidden', !hasAnyPermission(keys));
  });
}

function firstAllowedSection() {
  const item = Array.from(document.querySelectorAll('.nav-item')).find(navAllowed);
  return item?.dataset.section;
}

function requestedSectionFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const querySection = params.get('section');
  const hashSection = window.location.hash.replace(/^#\/?/, '');
  const section = (querySection || hashSection || '').trim();
  return MODULE_VIEW_PERMISSIONS[section] ? section : null;
}

// ── Navigation ─────────────────────────────────
const TITLES = {
  dashboard: 'Dashboard',
  kanban:    'Kanban – Bảng công việc',
  projects:  'Dự án',
  kpi:       'KPI – Chỉ số hiệu suất',
  reports:   'Báo cáo',
  ai:        'AI – Phân rã yêu cầu thành task',
  teams:     'Tích hợp Microsoft Teams',
  ops:       'Audit & Ops',
  admin:     'Quản trị hệ thống',
};

function navigate(section, options = {}) {
  if (!MODULE_VIEW_PERMISSIONS[section]) {
    section = firstAllowedSection() || 'dashboard';
  }
  if (!canViewModule(section)) {
    showAccessDenied(section, options);
    return;
  }
  const nav = document.querySelector(`.nav-item[data-section="${section}"]`);
  if (nav && !navAllowed(nav)) {
    showAccessDenied(section, options);
    return;
  }
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.section === section);
  });
  document.querySelectorAll('.section').forEach(el => el.classList.add('hidden'));
  const sec = document.getElementById(`sec-${section}`);
  if (sec) sec.classList.remove('hidden');

  state.currentSection = section;
  document.getElementById('pageTitle').textContent = navLabel(section);
  syncSectionUrl(section, options);
  loadSection(section);
  applyPermissionVisibility();
}

function showAccessDenied(section, options = {}) {
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.section').forEach(el => el.classList.add('hidden'));
  const sec = document.getElementById('sec-access-denied');
  if (sec) sec.classList.remove('hidden');
  const title = document.getElementById('pageTitle');
  if (title) title.textContent = 'Access Denied';
  const requested = document.getElementById('accessDeniedTarget');
  if (requested) requested.textContent = TITLES[section] || section || '-';
  state.currentSection = 'access-denied';
  syncSectionUrl(section || 'access-denied', options);
}

function backToDashboard() {
  navigate(firstAllowedSection() || 'dashboard', { replace: true });
}

function syncSectionUrl(section, options = {}) {
  if (!window.history || options.skipUrl) return;
  const targetHash = `#${section}`;
  if (window.location.hash === targetHash) return;
  const nextUrl = `${window.location.pathname}${window.location.search}${targetHash}`;
  if (options.replace) window.history.replaceState(null, '', nextUrl);
  else window.history.pushState(null, '', nextUrl);
}

function refreshCurrent() {
  if (state.currentSection === 'access-denied') return;
  loadSection(state.currentSection);
}

function loadSection(section) {
  switch (section) {
    case 'dashboard': loadDashboard(); break;
    case 'kanban':    loadKanban();    break;
    case 'projects':  loadProjects();  break;
    case 'kpi':       loadKPI();       break;
    case 'reports':   setupReports();  break;
    case 'ai':        loadAI();        break;
    case 'teams':     loadTeams();     break;
    case 'ops':       loadOpsDashboard(); break;
    case 'admin':     loadAdmin();     break;
  }
}

function onMonthChange(val) {
  state.month = val;
  document.getElementById('kpiMonth').textContent = val;
  document.getElementById('kpiTableMonth').textContent = val;
  if (state.currentSection === 'dashboard') loadDashboard();
  if (state.currentSection === 'kpi') loadKPI();
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

async function loadNotificationCount() {
  const badge = document.getElementById('notificationCount');
  if (!badge) return;
  try {
    const result = await api('/notifications/unread-count');
    const count = Number(result.unread_count || 0);
    badge.textContent = String(count);
    badge.classList.toggle('hidden', count === 0);
  } catch (_) {
    badge.classList.add('hidden');
  }
}

async function toggleNotificationPanel(event) {
  if (event) event.stopPropagation();
  if (state.notificationsOpen) {
    closeNotificationPanel();
    return;
  }
  state.notificationsOpen = true;
  const panel = document.getElementById('notificationPanel');
  if (panel) panel.classList.remove('hidden');
  await loadNotifications();
}

function closeNotificationPanel() {
  state.notificationsOpen = false;
  const panel = document.getElementById('notificationPanel');
  if (panel) panel.classList.add('hidden');
}

async function loadNotifications() {
  const list = document.getElementById('notificationList');
  if (!list) return;
  list.innerHTML = '<div class="skeleton" style="height:80px"></div>';
  try {
    const rows = await api('/notifications?limit=20');
    if (!rows.length) {
      list.innerHTML = '<div class="empty-state compact">Bạn chưa có thông báo mới.</div>';
      return;
    }
    list.innerHTML = rows.map(notificationItem).join('');
  } catch (e) {
    list.innerHTML = `<div class="empty-state compact">${escHtml(e.message)}</div>`;
  }
}

function notificationItem(n) {
  const taskAction = n.entity_type === 'task'
    ? `<button type="button" class="btn-mini" onclick="event.stopPropagation();openNotificationTask(${n.id}, ${n.entity_id})">View task</button>`
    : '';
  const readAction = n.is_read
    ? ''
    : `<button type="button" class="btn-mini" onclick="event.stopPropagation();markNotificationRead(${n.id})">Mark read</button>`;
  return `
    <div class="notification-item ${n.is_read ? '' : 'unread'}" onclick="openNotificationTask(${n.id}, ${n.entity_id})">
      <div class="notification-item-head">
        <strong>${escHtml(n.title)}</strong>
        <time>${fmtDateTime(n.created_at)}</time>
      </div>
      <div class="notification-message">${escHtml(n.message)}</div>
      <div class="notification-actions">
        <span class="text-sm text-muted">${escHtml(n.entity_type)} #${n.entity_id}</span>
        <span>${taskAction}${readAction}</span>
      </div>
    </div>`;
}

async function markNotificationRead(notificationId) {
  try {
    await api(`/notifications/${notificationId}/read`, { method: 'PATCH' });
    await Promise.all([loadNotificationCount(), loadNotifications()]);
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function markAllNotificationsRead() {
  try {
    await api('/notifications/read-all', { method: 'PATCH' });
    await Promise.all([loadNotificationCount(), loadNotifications()]);
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function openNotificationTask(notificationId, taskId) {
  try {
    await api(`/notifications/${notificationId}/read`, { method: 'PATCH' });
  } catch (_) {}
  closeNotificationPanel();
  await loadNotificationCount();
  openTaskDetail(Number(taskId));
}

// ════════════════════════════════ DASHBOARD ════

async function loadDashboard() {
  await Promise.all([loadDashStats(), loadKpiRank(), loadProjectOverview()]);
}

async function loadDashStats() {
  const container = document.getElementById('dashStats');
  container.innerHTML = '';
  try {
    const d = await api(`/dashboard/summary?month=${state.month}`);

    const cards = [
      { icon: 'list-checks', label: 'Tổng công việc',   value: d.total_tasks   ?? 0, change: '' },
      { icon: 'check-circle', label: 'Hoàn thành',        value: d.done_tasks    ?? 0, cls: 'up',      change: pct(d.done_tasks, d.total_tasks) },
      { icon: 'alert-triangle', label: 'Quá hạn',           value: d.overdue_tasks ?? 0, cls: 'down',    change: d.overdue_tasks > 0 ? `${d.overdue_tasks} task cần xử lý` : 'Tốt!' },
      { icon: 'target', label: 'KPI trung bình',    value: (d.avg_kpi_score ?? 0).toFixed(1), cls: kpiCls(d.avg_kpi_score), change: kpiTier(d.avg_kpi_score) },
    ];

    container.innerHTML = cards.map(c => `
      <div class="stat-card">
        <div class="stat-icon">${icon(c.icon, 'stat-svg')}</div>
        <div class="stat-value">${c.value}</div>
        <div class="stat-label">${c.label}</div>
        ${c.change ? `<div class="stat-change ${c.cls || 'neutral'}">${c.change}</div>` : ''}
      </div>
    `).join('');

    // Task status doughnut chart
    renderTaskChart(d.total_tasks ?? 0, d.done_tasks ?? 0,
      (d.total_tasks ?? 0) - (d.done_tasks ?? 0) - (d.overdue_tasks ?? 0),
      d.overdue_tasks ?? 0);

  } catch (e) {
    container.innerHTML = `<div class="stat-card"><div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>Không tải được dữ liệu<br><small>${e.message}</small></div></div>`;
  }
}

function pct(num, total) {
  if (!total) return '–';
  return `${Math.round(num * 100 / total)}%`;
}

function kpiCls(score) {
  if (!score) return 'neutral';
  if (score >= 90) return 'up';
  if (score >= 50) return 'neutral';
  return 'down';
}

function kpiTier(score) {
  if (!score) return '–';
  if (score >= 90) return `${icon('star', 'text-icon')} Xuất sắc`;
  if (score >= 70) return `${icon('thumbs-up', 'text-icon')} Tốt`;
  if (score >= 50) return `${icon('check-circle', 'text-icon')} Đạt`;
  return `${icon('alert-triangle', 'text-icon')} Cần cải thiện`;
}

function renderTaskChart(total, done, doing, overdue) {
  const ctx = document.getElementById('taskChart');
  if (!ctx) return;
  if (state.charts.taskChart) state.charts.taskChart.destroy();
  state.charts.taskChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Hoàn thành', 'Đang làm', 'Quá hạn'],
      datasets: [{
        data: [done, doing < 0 ? 0 : doing, overdue],
        backgroundColor: ['#10B981', '#F59E0B', '#EF4444'],
        borderWidth: 2,
        borderColor: '#fff',
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 12 }, padding: 12 } }
      },
      cutout: '65%',
    }
  });
}

async function loadKpiRank() {
  const el = document.getElementById('kpiRankTable');
  const monthEl = document.getElementById('kpiMonth');
  if (monthEl) monthEl.textContent = state.month;
  try {
    const rows = await api(`/kpi/monthly?month=${state.month}`);
    if (!rows.length) {
      el.innerHTML = `<div class="empty-state"><div>${icon('bar-chart', 'empty-icon')}</div>Chưa có dữ liệu KPI tháng này</div>`;
      return;
    }
    el.innerHTML = `
      <table class="rank-table">
        <thead><tr><th>#</th><th>Nhân sự</th><th>Điểm KPI</th><th>Xếp loại</th></tr></thead>
        <tbody>
          ${rows.slice(0, 8).map((r, i) => `
            <tr>
              <td><span class="rank-badge rank-${i < 3 ? i+1 : 'other'}">${i+1}</span></td>
              <td><strong>${r.user_name || `User ${r.user_id}`}</strong></td>
              <td><strong style="color:var(--brand)">${(r.score || 0).toFixed(1)}</strong></td>
              <td><span class="tier ${tierClass(r.score)}">${tierLabel(r.score)}</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  } catch (e) {
    el.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${e.message}</div>`;
  }
}

async function loadProjectOverview() {
  const el = document.getElementById('projectOverview');
  try {
    const projects = await api('/projects');
    if (!projects.length) {
      el.innerHTML = `<div class="empty-state"><div>${icon('folder', 'empty-icon')}</div>Chưa có dự án nào</div>`;
      return;
    }
    const rows = await Promise.all(
      projects.slice(0, 6).map(async p => {
        try {
          const progress = await api(`/projects/${p.id}/progress`);
          return { ...p, progress };
        } catch {
          return { ...p, progress: { total_tasks: 0, done_tasks: 0, completion_rate: 0 } };
        }
      })
    );
    el.innerHTML = rows.map(p => {
      const pct = p.progress?.completion_rate ?? 0;
      const fillCls = pct >= 80 ? 'done' : pct < 30 ? 'warning' : '';
      return `
        <div class="project-row">
          <div class="project-row-name">${p.name}</div>
          <span class="badge badge-${p.status}">${statusLabel(p.status)}</span>
          <div class="project-row-bar">
            <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-3);margin-bottom:3px">
              <span>${p.progress?.done_tasks ?? 0}/${p.progress?.total_tasks ?? 0} tasks</span>
              <span>${pct.toFixed(0)}%</span>
            </div>
            <div class="progress-bar"><div class="progress-fill ${fillCls}" style="width:${pct}%"></div></div>
          </div>
        </div>`;
    }).join('');
  } catch (e) {
    el.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${e.message}</div>`;
  }
}

/** Một lần: gắn dropzone + delegation (3 cột giữ id cố định, chỉ nội dung con thay đổi) */
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

async function loadKanban() {
  const cols = {
    todo:  document.getElementById('col-todo'),
    doing: document.getElementById('col-doing'),
    done:  document.getElementById('col-done'),
  };

  Object.values(cols).forEach(c => { c.innerHTML = '<div class="skeleton" style="height:64px;margin:4px 0"></div>'; });

  try {
    await loadKanbanFilterOptions();
    const url = buildKanbanTaskUrl();
    const tasks = await api(url);
    await loadWorkloadWarnings();
    const grouped = { todo: [], doing: [], done: [] };
    tasks.forEach(t => { if (grouped[t.status]) grouped[t.status].push(t); });

    document.getElementById('cnt-todo').textContent  = grouped.todo.length;
    document.getElementById('cnt-doing').textContent = grouped.doing.length;
    document.getElementById('cnt-done').textContent  = grouped.done.length;
    document.getElementById('kanbanCount').textContent = `${tasks.length} công việc`;

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
  }
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

async function loadProjects() {
  const grid = document.getElementById('projectGrid');
  const statusFilter = document.getElementById('projectStatusFilter').value;
  grid.innerHTML = '<div class="skeleton" style="height:160px"></div>'.repeat(3);

  let url = '/projects';
  if (statusFilter) url += `?status=${statusFilter}`;

  try {
    const projects = await api(url);
    document.getElementById('projectCount').textContent = `${projects.length} dự án`;

    if (!projects.length) {
      grid.innerHTML = `<div class="card" style="grid-column:1/-1"><div class="empty-state"><div>${icon('folder', 'empty-icon')}</div>Không có dự án nào</div></div>`;
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
          <span>Tiến độ</span>
          <strong>${pct.toFixed(0)}%</strong>
        </div>
        <div class="progress-bar">
          <div class="progress-fill ${fillCls}" style="width:${pct}%"></div>
        </div>
      </div>
      <div class="project-footer">
        <span>${icon('list-checks', 'text-icon')} ${p.progress?.done_tasks ?? 0}/${p.progress?.total_tasks ?? 0} tasks</span>
        <span>${icon('calendar', 'text-icon')} ${start} → ${end}</span>
      </div>
    </div>`;
}

// ════════════════════════════════ KPI ══════════

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
      el.innerHTML = `<div class="empty-state"><div>${icon('bar-chart', 'empty-icon')}</div>Chưa có dữ liệu KPI tháng ${state.month}</div>`;
      return;
    }
    el.innerHTML = `
      <table class="kpi-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Nhân sự</th>
            <th>Điểm KPI</th>
            <th>Xếp loại</th>
            <th>Done</th>
            <th>Quá hạn</th>
            <th>Tổng SP</th>
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
          label: 'Điểm KPI',
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
              label: ctx => `KPI: ${ctx.raw} điểm`
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

// ════════════════════════════════ REPORTS ══════

function setupReports() {
  // Nothing to load – buttons use onclick handlers
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
  if (!id) { toast('Vui lòng nhập Sprint ID', 'error'); return; }
  triggerDownload(`/reports/sprints/${id}/review.${fmt}`);
}

function triggerDownload(url) {
  const a = document.createElement('a');
  a.href = url;
  a.click();
}

// ════════════════════════════════ AI TASKS ═════

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
          <th>Chọn</th><th>Task</th><th>Độ khó</th><th>SP</th><th>Deadline</th><th>Lý do</th>
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
            <td><span class="badge badge-${item.difficulty}">${diffLabel(item.difficulty)}</span></td>
            <td>${item.story_points}</td>
            <td>+${item.deadline_offset_days} ngày</td>
            <td class="text-sm text-muted">${escHtml(item.rationale || '')}</td>
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

async function importSelectedAiTasks() {
  const selected = state.aiItems.filter(item => item.selected !== false);
  const assigneeId = Number(document.getElementById('aiAssigneeSelect').value);
  const projectRaw = document.getElementById('aiProjectSelect').value;
  if (!selected.length) {
    toast('Chưa chọn task nào để import', 'error');
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
        assignee_id: assigneeId,
        project_id: projectRaw ? Number(projectRaw) : null,
        sprint_id: null,
        items: selected,
      }),
    });
    toast(`Đã import ${result.created_count} task vào Kanban`, 'success');
    state.aiItems = [];
    renderAiPreview();
    document.getElementById('aiPreviewMeta').textContent = 'Đã import xong';
  } catch (e) {
    toast(e.message, 'error');
  }
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
      <textarea id="aiReviewDesc${i}" class="textarea" rows="2">${escHtml(item.description || '')}</textarea>
      <div class="inline-fields">
        <select id="aiReviewDifficulty${i}" class="select">
          ${['easy', 'medium', 'hard'].map(d => `<option value="${d}" ${item.difficulty === d ? 'selected' : ''}>${diffLabel(d)}</option>`).join('')}
        </select>
        <input id="aiReviewPoints${i}" class="input" type="number" min="1" max="13" value="${Number(item.story_points || 3)}" />
        <input id="aiReviewOffset${i}" class="input" type="number" min="1" max="90" value="${Number(item.deadline_offset_days || 7)}" />
      </div>
      <input id="aiReviewRationale${i}" class="input" type="text" value="${escHtml(item.rationale || '')}" />
    </div>`;
}

function collectAiReviewItems() {
  const rows = [...document.querySelectorAll('[data-ai-review-index]')];
  return rows.map(row => {
    const i = row.dataset.aiReviewIndex;
    return {
      title: document.getElementById(`aiReviewTitle${i}`).value.trim(),
      description: document.getElementById(`aiReviewDesc${i}`).value.trim() || null,
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

  const query = params.toString();
  return query ? `/tasks?${query}` : '/tasks';
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

async function loadAdmin() {
  const jobs = [loadPlanCompletion()];
  if (hasPermission('USER_VIEW')) jobs.push(loadAdminUsers());
  if (hasPermission('DEPARTMENT_VIEW')) jobs.push(loadAdminDepartments());
  if (hasPermission('AUDIT_VIEW')) jobs.push(loadAuditLogs());
  if (hasPermission('ROLE_VIEW') || hasPermission('roles.view')) jobs.push(loadRbacAdmin());
  await Promise.all(jobs);
}

async function loadAdminUsers() {
  const el = document.getElementById('adminUsersTable');
  if (!el) return;
  el.innerHTML = '<div class="skeleton" style="height:100px"></div>';
  try {
    const rows = await api('/users');
    el.innerHTML = `
      <table class="audit-table">
        <thead><tr><th>Ten</th><th>Email</th><th>Role</th><th>Department</th><th>Status</th></tr></thead>
        <tbody>
          ${rows.map(u => `
            <tr>
              <td>${escHtml(u.full_name)}</td>
              <td>${escHtml(u.email)}</td>
              <td>${escHtml(u.role_detail?.name || u.role_code || u.role)}</td>
              <td>${escHtml(u.department_detail?.name || u.department || '-')}</td>
              <td><span class="tag">${u.is_active ? 'Active' : 'Inactive'}</span></td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  } catch (e) {
    el.innerHTML = `<div class="empty-state compact">${escHtml(e.message)}</div>`;
  }
}

async function loadAdminDepartments() {
  const el = document.getElementById('adminDepartmentsTable');
  if (!el) return;
  el.innerHTML = '<div class="skeleton" style="height:100px"></div>';
  try {
    const rows = await api('/departments');
    el.innerHTML = `
      <table class="audit-table">
        <thead><tr><th>Code</th><th>Name</th><th>Manager</th><th>Members</th></tr></thead>
        <tbody>
          ${rows.map(d => `
            <tr>
              <td><span class="tag">${escHtml(d.code)}</span></td>
              <td>${escHtml(d.name)}</td>
              <td>${escHtml(d.manager_name || '-')}</td>
              <td>${escHtml(d.member_count ?? 0)}</td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  } catch (e) {
    el.innerHTML = `<div class="empty-state compact">${escHtml(e.message)}</div>`;
  }
}

async function loadRbacAdmin() {
  const roleSelect = document.getElementById('rbacRoleSelect');
  const table = document.getElementById('rbacPermissionTable');
  if (!roleSelect || !table) return;
  table.innerHTML = '<div class="skeleton" style="height:120px"></div>';
  try {
    const [roles, permissions] = await Promise.all([api('/rbac/roles'), api('/rbac/permissions')]);
    state.rbac.roles = roles;
    state.rbac.permissions = permissions;
    roleSelect.innerHTML = roles.map(r => `<option value="${escHtml(r.slug)}">${escHtml(r.name)} (${escHtml(r.slug)})</option>`).join('');
    await loadRolePermissions();
  } catch (e) {
    table.innerHTML = `<div class="empty-state compact">${escHtml(e.message)}</div>`;
  }
}

async function loadRolePermissions() {
  const roleSelect = document.getElementById('rbacRoleSelect');
  const table = document.getElementById('rbacPermissionTable');
  if (!roleSelect || !table || !roleSelect.value) return;
  table.innerHTML = '<div class="skeleton" style="height:120px"></div>';
  try {
    const result = await api(`/rbac/roles/${encodeURIComponent(roleSelect.value)}/permissions`);
    state.rbac.selectedKeys = new Set((result.permissions || []).map(p => p.key));
    renderPermissionTable();
  } catch (e) {
    table.innerHTML = `<div class="empty-state compact">${escHtml(e.message)}</div>`;
  }
}

function renderPermissionTable() {
  const table = document.getElementById('rbacPermissionTable');
  const permissions = state.rbac.permissions || [];
  if (!permissions.length) {
    table.innerHTML = '<div class="empty-state compact">Chưa có permission</div>';
    return;
  }
  table.innerHTML = `
    <table class="audit-table">
      <thead><tr><th>Cho phép</th><th>Permission</th><th>Nhóm</th></tr></thead>
      <tbody>
        ${permissions.map(p => `
          <tr>
            <td><input type="checkbox" ${state.rbac.selectedKeys.has(p.key) ? 'checked' : ''} onchange="togglePermissionKey('${escHtml(p.key)}', this.checked)" /></td>
            <td><strong>${escHtml(p.name)}</strong><div class="text-sm text-muted">${escHtml(p.key)}</div></td>
            <td><span class="tag">${escHtml(p.category)}</span></td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

function togglePermissionKey(key, checked) {
  if (checked) state.rbac.selectedKeys.add(key);
  else state.rbac.selectedKeys.delete(key);
}

async function saveRolePermissions() {
  if (!canDo('roleManage')) {
    toast('Ban khong co quyen luu phan quyen', 'error');
    return;
  }
  const role = document.getElementById('rbacRoleSelect')?.value;
  if (!role) return;
  try {
    await api(`/rbac/roles/${encodeURIComponent(role)}/permissions`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ permission_keys: Array.from(state.rbac.selectedKeys).sort() }),
    });
    toast('Đã lưu phân quyền', 'success');
    await loadRolePermissions();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function loadPlanCompletion() {
  const el = document.getElementById('planCompletion');
  try {
    const plan = await api('/plan/completion');
    const completionPercent = plan.completion_percent ?? 0;
    const items = plan.items ?? [];
    el.innerHTML = `
      <div style="margin-bottom:12px">
        <div class="progress-label">
          <span>Tổng tiến độ</span>
          <strong>${completionPercent}%</strong>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${completionPercent}%"></div></div>
      </div>
      <div class="plan-list">
        ${items.map(item => `
          <div class="plan-item">
            <span class="plan-check">${icon(item.done ? 'check-circle' : 'square', 'text-icon')}</span>
            <span style="color:${item.done ? 'var(--success)' : 'var(--text-2)'}">${escHtml(item.title || formatPlanKey(item.key || ''))}</span>
          </div>`).join('')}
      </div>`;
  } catch (e) {
    el.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${e.message}</div>`;
  }
}

async function loadAuditLogs() {
  const el = document.getElementById('auditTable');
  el.innerHTML = '<div class="skeleton" style="height:120px"></div>';
  try {
    const logs = await api('/audit/logs?limit=50');
    if (!logs.length) {
      el.innerHTML = `<div class="empty-state"><div>${icon('list-checks', 'empty-icon')}</div>Chưa có nhật ký hoạt động</div>`;
      return;
    }
    el.innerHTML = `
      <table class="audit-table">
        <thead><tr><th>Thời gian</th><th>Người dùng</th><th>Hành động</th><th>Đối tượng</th><th>Chi tiết</th></tr></thead>
        <tbody>
          ${logs.map(l => `
            <tr>
              <td style="white-space:nowrap">${new Date(l.created_at).toLocaleString('vi-VN')}</td>
              <td>User ${l.actor_user_id || '–'}</td>
              <td><code>${l.action}</code></td>
              <td><code>${l.entity}${l.entity_id ? ' #' + l.entity_id : ''}</code></td>
              <td style="color:var(--text-2)">${l.detail || '–'}</td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  } catch (e) {
    el.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${e.message}</div>`;
  }
}

async function runSeed() {
  if (!canDo('seed')) {
    toast('Ban khong co quyen khoi tao seed', 'error');
    return;
  }
  const btn = document.getElementById('seedBtn');
  const result = document.getElementById('seedResult');
  btn.disabled = true;
  btn.textContent = 'Đang khởi tạo...';
  try {
    const res = await api('/seed/init', { method: 'POST' });
    const count = Object.entries(res)
      .filter(([k, v]) => typeof v === 'number')
      .map(([k, v]) => `${k}: ${v}`)
      .join(', ');
    result.innerHTML = `<div class="inline-status" style="color:var(--success);font-size:13px">${icon('check-circle', 'text-icon')} Khởi tạo thành công! ${count}</div>`;
    toast('Dữ liệu mẫu đã được khởi tạo', 'success');
  } catch (e) {
    result.innerHTML = `<div class="inline-status" style="color:var(--danger);font-size:13px">${icon('x-circle', 'text-icon')} ${e.message}</div>`;
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Khởi tạo dữ liệu mẫu';
  }
}

// ════════════════════════════════ HELPERS ══════

function fmtDateTime(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString('vi-VN');
}

function dueStateLabel(value) {
  return { on_time: 'Đúng hạn', late: 'Trễ hạn', overdue: 'Quá hạn' }[value] || value || '-';
}

function dueStateClass(value) {
  return { on_time: 'due-on-time', late: 'due-late', overdue: 'due-overdue' }[value] || 'due-on-time';
}

function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function statusLabel(s) {
  const m = { active: 'Hoạt động', on_hold: 'Tạm dừng', done: 'Hoàn thành', archived: 'Lưu trữ', todo: 'Chưa làm', doing: 'Đang làm' };
  return m[s] || s;
}

function diffLabel(d) {
  return { easy: 'Dễ', medium: 'Trung bình', hard: 'Khó' }[d] || d;
}

function tierClass(score) {
  if (!score) return 'tier-D';
  if (score >= 90) return 'tier-A';
  if (score >= 70) return 'tier-B';
  if (score >= 50) return 'tier-C';
  return 'tier-D';
}

function tierLabel(score) {
  if (!score) return 'Chưa có dữ liệu';
  if (score >= 90) return 'Xuất sắc';
  if (score >= 70) return 'Tốt';
  if (score >= 50) return 'Đạt';
  return 'Cần cải thiện';
}

function scoreColor(score) {
  if (!score) return '#94A3B8';
  if (score >= 90) return '#059669';
  if (score >= 70) return '#2563EB';
  if (score >= 50) return '#D97706';
  return '#DC2626';
}

function formatPlanKey(key) {
  const m = {
    task_crud:               'Task CRUD (tạo/sửa/xóa)',
    kpi_engine:              'KPI Engine',
    sprint_management:       'Quản lý Sprint',
    project_management:      'Quản lý Dự án',
    csv_xlsx_reports:        'Báo cáo CSV/XLSX',
    pdf_reports:             'Báo cáo PDF',
    teams_tab_integration:   'Teams Tab tích hợp',
    teams_bot_scaffold:      'Teams Bot scaffold',
    azure_ad_sso:            'Azure AD SSO (production)',
    full_backlog_coverage:   'Toàn bộ backlog',
    docker_deployment:       'Docker deployment',
    ci_pipeline:             'CI/CD Pipeline',
  };
  return m[key] || key.replace(/_/g, ' ');
}

// Role-aware dashboard overrides. Function declarations are intentionally placed
// after the original MVP dashboard functions so these are the active versions.
function setDashboardShell() {
  const sec = document.getElementById('sec-dashboard');
  if (!sec) return;
  const role = currentRoleCode();
  const titles = {
    MEMBER: { kpi: 'KPI cá nhân', chart: 'Progress cá nhân', overview: 'Task của tôi' },
    ADMIN: { kpi: 'Global analytics', chart: 'Task toàn hệ thống', overview: 'System health & audit' },
    AUDITOR: { kpi: 'Báo cáo hệ thống', chart: 'Task toàn hệ thống', overview: 'Audit gần đây' },
    HR: { kpi: 'KPI nhân sự', chart: 'Tổng quan task', overview: 'Nhân sự & phòng ban' },
  };
  const copy = titles[role] || { kpi: 'KPI team', chart: 'Sprint progress', overview: 'Team workload' };
  sec.innerHTML = `
    <div class="stat-grid" id="dashStats">
      <div class="stat-card skeleton"></div>
      <div class="stat-card skeleton"></div>
      <div class="stat-card skeleton"></div>
      <div class="stat-card skeleton"></div>
    </div>
    <div class="two-col">
      <div class="card">
        <div class="card-header">
          <h3>${icon('trophy', 'heading-icon')}${copy.kpi}</h3>
          <span class="tag" id="kpiMonth">${state.month}</span>
        </div>
        <div id="kpiRankTable"></div>
      </div>
      <div class="card">
        <div class="card-header"><h3>${icon('bar-chart', 'heading-icon')}${copy.chart}</h3></div>
        <div class="chart-wrap"><canvas id="taskChart"></canvas></div>
      </div>
    </div>
    <div class="card mt-16">
      <div class="card-header"><h3>${icon(role === 'MEMBER' ? 'list-checks' : 'folder', 'heading-icon')}${copy.overview}</h3></div>
      <div id="projectOverview"></div>
    </div>`;
}

async function loadDashboard() {
  setDashboardShell();
  await Promise.all([loadDashStats(), loadKpiRank(), loadProjectOverview()]);
}

async function loadDashStats() {
  const container = document.getElementById('dashStats');
  container.innerHTML = '';
  try {
    const d = await api(`/dashboard/summary?month=${state.month}`);
    const role = currentRoleCode();
    let cards;
    if (role === 'ADMIN') {
      const metrics = await api('/monitoring/metrics').catch(() => null);
      cards = [
        { icon: 'list-checks', label: 'Users', value: metrics?.users ?? '-', change: 'Tài khoản hệ thống' },
        { icon: 'folder', label: 'Projects', value: metrics?.projects ?? 0, change: 'Danh mục đang theo dõi' },
        { icon: 'alert-triangle', label: 'Overdue', value: metrics?.overdue_tasks ?? d.overdue_tasks ?? 0, cls: 'down', change: 'Cần xử lý' },
        { icon: 'activity', label: 'Health', value: (metrics?.failed_notifications ?? 0) > 0 ? 'Warn' : 'OK', cls: (metrics?.failed_notifications ?? 0) > 0 ? 'down' : 'up', change: 'System health' },
      ];
    } else if (role === 'MEMBER') {
      cards = [
        { icon: 'list-checks', label: 'Task của tôi', value: d.total_tasks ?? 0, change: '' },
        { icon: 'calendar', label: 'Đang làm', value: d.doing_tasks ?? 0, cls: 'neutral', change: 'Cần cập nhật tiến độ' },
        { icon: 'alert-triangle', label: 'Deadline gần', value: d.overdue_tasks ?? 0, cls: d.overdue_tasks > 0 ? 'down' : 'up', change: d.overdue_tasks > 0 ? 'Có task quá hạn' : 'Không có quá hạn' },
        { icon: 'target', label: 'KPI cá nhân', value: (d.avg_kpi_score ?? 0).toFixed(1), cls: kpiCls(d.avg_kpi_score), change: kpiTier(d.avg_kpi_score) },
      ];
    } else {
      cards = [
        { icon: 'list-checks', label: role === 'AUDITOR' ? 'Total tasks' : 'Team workload', value: d.total_tasks ?? 0, change: '' },
        { icon: 'check-circle', label: 'Hoàn thành', value: d.done_tasks ?? 0, cls: 'up', change: pct(d.done_tasks, d.total_tasks) },
        { icon: 'alert-triangle', label: 'Overdue tasks', value: d.overdue_tasks ?? 0, cls: 'down', change: d.overdue_tasks > 0 ? `${d.overdue_tasks} task cần xử lý` : 'Tốt' },
        { icon: 'target', label: role === 'HR' ? 'KPI nhân sự' : 'KPI team', value: (d.avg_kpi_score ?? 0).toFixed(1), cls: kpiCls(d.avg_kpi_score), change: kpiTier(d.avg_kpi_score) },
      ];
    }
    container.innerHTML = cards.map(c => `
      <div class="stat-card">
        <div class="stat-icon">${icon(c.icon, 'stat-svg')}</div>
        <div class="stat-value">${escHtml(c.value)}</div>
        <div class="stat-label">${escHtml(c.label)}</div>
        ${c.change ? `<div class="stat-change ${c.cls || 'neutral'}">${c.change}</div>` : ''}
      </div>
    `).join('');
    renderTaskChart(d.total_tasks ?? 0, d.done_tasks ?? 0, (d.total_tasks ?? 0) - (d.done_tasks ?? 0) - (d.overdue_tasks ?? 0), d.overdue_tasks ?? 0);
  } catch (e) {
    container.innerHTML = `<div class="stat-card"><div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>Không tải được dashboard<br><small>${escHtml(e.message)}</small></div></div>`;
  }
}

async function loadKpiRank() {
  const el = document.getElementById('kpiRankTable');
  const monthEl = document.getElementById('kpiMonth');
  if (monthEl) monthEl.textContent = state.month;
  try {
    const rows = await api(`/kpi/monthly?month=${state.month}`);
    if (!rows.length) {
      el.innerHTML = `<div class="empty-state"><div>${icon('bar-chart', 'empty-icon')}</div>Chưa có KPI trong tháng này.</div>`;
      return;
    }
    if (isMemberRole()) {
      const r = rows[0];
      el.innerHTML = `
        <div class="personal-kpi">
          <div class="personal-kpi-score" style="color:${scoreColor(r.score)}">${(r.score || 0).toFixed(1)}</div>
          <div><span class="tier ${tierClass(r.score)}">${tierLabel(r.score)}</span></div>
          <div class="text-sm text-muted">Hoàn thành đúng hạn: ${r.done_on_time ?? 0} • Quá hạn: ${r.overdue_unfinished ?? r.overdue ?? 0}</div>
        </div>`;
      return;
    }
    el.innerHTML = `
      <table class="rank-table">
        <thead><tr><th>#</th><th>Nhân sự</th><th>Điểm KPI</th><th>Xếp loại</th></tr></thead>
        <tbody>
          ${rows.slice(0, 8).map((r, i) => `
            <tr>
              <td><span class="rank-badge rank-${i < 3 ? i+1 : 'other'}">${i+1}</span></td>
              <td><strong>${escHtml(r.user_name || `User ${r.user_id}`)}</strong></td>
              <td><strong style="color:var(--brand)">${(r.score || 0).toFixed(1)}</strong></td>
              <td><span class="tier ${tierClass(r.score)}">${tierLabel(r.score)}</span></td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  } catch (e) {
    el.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${escHtml(e.message)}</div>`;
  }
}

async function loadProjectOverview() {
  const el = document.getElementById('projectOverview');
  try {
    if (isMemberRole()) {
      const tasks = await api('/tasks');
      if (!tasks.length) {
        el.innerHTML = `<div class="empty-state"><div>${icon('list-checks', 'empty-icon')}</div>Bạn chưa có task nào được giao.</div>`;
        return;
      }
      el.innerHTML = tasks.slice().sort((a, b) => new Date(a.deadline) - new Date(b.deadline)).slice(0, 6).map(t => `
        <div class="project-row">
          <div class="project-row-name">${escHtml(t.title)}</div>
          <span class="badge badge-${escHtml(t.status)}">${statusLabel(t.status)}</span>
          <span class="text-sm text-muted">${new Date(t.deadline).toLocaleDateString('vi-VN')}</span>
        </div>`).join('');
      return;
    }
    if (currentRoleCode() === 'LEADER') {
      const tasks = await api('/tasks');
      if (!tasks.length) {
        el.innerHTML = `<div class="empty-state"><div>${icon('list-checks', 'empty-icon')}</div>Chua co task nao trong workload.</div>`;
        return;
      }
      el.innerHTML = tasks.slice().sort((a, b) => new Date(a.deadline) - new Date(b.deadline)).slice(0, 6).map(t => `
        <div class="project-row">
          <div class="project-row-name">${escHtml(t.title)}</div>
          <span class="badge badge-${escHtml(t.status)}">${statusLabel(t.status)}</span>
          <span class="text-sm text-muted">${new Date(t.deadline).toLocaleDateString('vi-VN')}</span>
        </div>`).join('');
      return;
    }
    if (currentRoleCode() === 'AUDITOR') {
      const logs = await api('/audit/logs?limit=6').catch(() => []);
      if (!logs.length) {
        el.innerHTML = `<div class="empty-state"><div>${icon('list-checks', 'empty-icon')}</div>Chưa có nhật ký audit trong khoảng thời gian này.</div>`;
        return;
      }
      el.innerHTML = logs.map(l => `
        <div class="project-row">
          <div class="project-row-name">${escHtml(l.action)} <span class="text-sm text-muted">${escHtml(l.entity)}</span></div>
          <span class="text-sm text-muted">${fmtDateTime(l.created_at)}</span>
        </div>`).join('');
      return;
    }
    const projects = await api('/projects');
    if (!projects.length) {
      el.innerHTML = `<div class="empty-state"><div>${icon('folder', 'empty-icon')}</div>Chưa có dự án nào.</div>`;
      return;
    }
    const rows = await Promise.all(projects.slice(0, 6).map(async p => {
      try {
        const progress = await api(`/projects/${p.id}/progress`);
        return { ...p, progress };
      } catch {
        return { ...p, progress: { total_tasks: 0, done_tasks: 0, completion_rate: 0 } };
      }
    }));
    el.innerHTML = rows.map(p => {
      const done = p.progress?.done_tasks ?? 0;
      const total = p.progress?.total_tasks ?? 0;
      const completion = p.progress?.completion_rate ?? 0;
      const fillCls = completion >= 80 ? 'done' : completion < 30 ? 'warning' : '';
      return `
        <div class="project-row">
          <div class="project-row-name">${escHtml(p.name)}</div>
          <span class="badge badge-${escHtml(p.status)}">${statusLabel(p.status)}</span>
          <div class="project-row-bar">
            <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-3);margin-bottom:3px">
              <span>${done}/${total} tasks</span><span>${completion.toFixed(0)}%</span>
            </div>
            <div class="progress-bar"><div class="progress-fill ${fillCls}" style="width:${completion}%"></div></div>
          </div>
        </div>`;
    }).join('');
  } catch (e) {
    el.innerHTML = `<div class="empty-state"><div>${icon('alert-triangle', 'empty-icon')}</div>${escHtml(e.message)}</div>`;
  }
}

function renderRoleBadge(role) {
  const code = roleCode(role?.code || role?.slug || role);
  return `<span class="role-badge ${ROLE_COLORS[code] || 'role-member'}">${roleName(code)}</span>`;
}

function statusBadge(active) {
  return `<span class="status-badge ${active ? 'active' : 'inactive'}"><span class="status-dot"></span>${active ? 'Active' : 'Inactive'}</span>`;
}

function sortRows(rows, sort, dir, getValue) {
  const direction = dir === 'desc' ? -1 : 1;
  return rows.slice().sort((a, b) => String(getValue(a, sort) ?? '').localeCompare(String(getValue(b, sort) ?? ''), 'vi') * direction);
}

function paginateRows(rows, page, pageSize) {
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  const safePage = Math.min(Math.max(1, page), totalPages);
  return { totalPages, safePage, rows: rows.slice((safePage - 1) * pageSize, safePage * pageSize) };
}

function pagerHtml(kind, page, totalPages) {
  return `
    <div class="table-pager">
      <button class="btn btn-outline btn-sm" ${page <= 1 ? 'disabled' : ''} onclick="${kind}Page(${page - 1})">Prev</button>
      <span class="text-sm text-muted">Page ${page}/${totalPages}</span>
      <button class="btn btn-outline btn-sm" ${page >= totalPages ? 'disabled' : ''} onclick="${kind}Page(${page + 1})">Next</button>
    </div>`;
}

async function confirmAction(title, message) {
  const modal = document.getElementById('confirmModal');
  if (!modal) return window.confirm(`${title}\n${message}`);
  return new Promise(resolve => {
    document.getElementById('confirmTitle').textContent = title;
    document.getElementById('confirmMessage').textContent = message;
    modal.classList.remove('hidden');
    window.__confirmResolve = resolve;
  });
}

function closeConfirmModal(result) {
  const modal = document.getElementById('confirmModal');
  if (modal) modal.classList.add('hidden');
  if (window.__confirmResolve) window.__confirmResolve(Boolean(result));
  window.__confirmResolve = null;
}

async function loadAdminUsers() {
  const el = document.getElementById('adminUsersTable');
  if (!el) return;
  el.innerHTML = '<div class="skeleton" style="height:100px"></div>';
  try {
    state.adminUsers.rows = await api('/users');
    state.adminUsers.page = 1;
    renderAdminUsers();
  } catch (e) {
    el.innerHTML = `<div class="empty-state compact">${escHtml(e.message)}</div>`;
  }
}

function adminUserValue(row, sort) {
  if (sort === 'role') return row.role_detail?.name || row.role_code || row.role;
  if (sort === 'department') return row.department_detail?.name || row.department || '';
  if (sort === 'status') return row.is_active ? 'active' : 'inactive';
  return row.full_name || '';
}

function renderAdminUsers() {
  const el = document.getElementById('adminUsersTable');
  const s = state.adminUsers;
  const roles = Array.from(new Set(s.rows.map(u => roleCode(u.role_detail?.code || u.role_code || u.role)))).sort();
  const departments = Array.from(new Set(s.rows.map(u => u.department_detail?.name || u.department || '').filter(Boolean))).sort();
  const term = s.search.toLowerCase();
  let rows = s.rows.filter(u => {
    const haystack = `${u.full_name} ${u.email} ${u.role_code || ''} ${u.department_detail?.name || u.department || ''}`.toLowerCase();
    if (term && !haystack.includes(term)) return false;
    if (s.role && roleCode(u.role_detail?.code || u.role_code || u.role) !== s.role) return false;
    if (s.department && (u.department_detail?.name || u.department || '') !== s.department) return false;
    if (s.status && String(Boolean(u.is_active)) !== s.status) return false;
    return true;
  });
  rows = sortRows(rows, s.sort, s.dir, adminUserValue);
  const page = paginateRows(rows, s.page, s.pageSize);
  s.page = page.safePage;
  el.innerHTML = `
    <div class="table-toolbar">
      <input class="input table-search" type="search" placeholder="Search users" value="${escHtml(s.search)}" oninput="adminUsersFilter('search', this.value)" />
      <select class="select" onchange="adminUsersFilter('role', this.value)"><option value="">All roles</option>${roles.map(r => `<option value="${r}" ${s.role === r ? 'selected' : ''}>${roleName(r)}</option>`).join('')}</select>
      <select class="select" onchange="adminUsersFilter('department', this.value)"><option value="">All departments</option>${departments.map(d => `<option value="${escHtml(d)}" ${s.department === d ? 'selected' : ''}>${escHtml(d)}</option>`).join('')}</select>
      <select class="select" onchange="adminUsersFilter('status', this.value)"><option value="">All status</option><option value="true" ${s.status === 'true' ? 'selected' : ''}>Active</option><option value="false" ${s.status === 'false' ? 'selected' : ''}>Inactive</option></select>
    </div>
    ${!rows.length ? '<div class="empty-state compact">Không có user phù hợp với bộ lọc.</div>' : `
    <div class="responsive-table">
      <table class="audit-table enterprise-table">
        <thead><tr>
          <th onclick="sortAdminUsers('name')">Name</th>
          <th>Email</th>
          <th onclick="sortAdminUsers('role')">Role</th>
          <th onclick="sortAdminUsers('department')">Department</th>
          <th onclick="sortAdminUsers('status')">Status</th>
          <th>Actions</th>
        </tr></thead>
        <tbody>${page.rows.map(u => `
          <tr>
            <td><strong>${escHtml(u.full_name)}</strong></td>
            <td>${escHtml(u.email)}</td>
            <td>${renderRoleBadge(u.role_detail || u.role_code || u.role)}</td>
            <td>${escHtml(u.department_detail?.name || u.department || '-')}</td>
            <td>${statusBadge(Boolean(u.is_active))}</td>
            <td>
              <select class="select action-select" onchange="handleUserAction(${Number(u.id)}, this.value); this.value=''">
                <option value="">Actions</option>
                <option value="${u.is_active ? 'deactivate' : 'activate'}">${u.is_active ? 'Deactivate' : 'Activate'}</option>
                <option value="reset">Reset password</option>
              </select>
            </td>
          </tr>`).join('')}</tbody>
      </table>
    </div>
    ${pagerHtml('adminUsers', page.safePage, page.totalPages)}`}
  `;
}

function adminUsersFilter(key, value) {
  state.adminUsers[key] = value;
  state.adminUsers.page = 1;
  renderAdminUsers();
}

function sortAdminUsers(sort) {
  const s = state.adminUsers;
  s.dir = s.sort === sort && s.dir === 'asc' ? 'desc' : 'asc';
  s.sort = sort;
  renderAdminUsers();
}

function adminUsersPage(page) {
  state.adminUsers.page = page;
  renderAdminUsers();
}

async function handleUserAction(userId, action) {
  if (!action) return;
  try {
    if (action === 'deactivate' || action === 'activate') {
      const active = action === 'activate';
      if (!(await confirmAction(active ? 'Activate user' : 'Deactivate user', active ? 'User này sẽ đăng nhập lại được.' : 'User này sẽ không thể đăng nhập cho tới khi được kích hoạt lại.'))) return;
      await api(`/users/${userId}/active`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ is_active: active }) });
      toast(active ? 'User activated successfully' : 'User deactivated successfully', 'success');
    }
    if (action === 'reset') {
      const password = window.prompt('Nhập mật khẩu mới (tối thiểu 8 ký tự)');
      if (!password) return;
      if (!(await confirmAction('Reset password', 'Mật khẩu hiện tại của user sẽ bị thay thế.'))) return;
      await api(`/users/${userId}/reset-password`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }) });
      toast('Password reset successfully', 'success');
    }
    await loadAdminUsers();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function loadAdminDepartments() {
  const el = document.getElementById('adminDepartmentsTable');
  if (!el) return;
  el.innerHTML = '<div class="skeleton" style="height:100px"></div>';
  try {
    state.adminDepartments.rows = await api('/departments');
    state.adminDepartments.page = 1;
    renderAdminDepartments();
  } catch (e) {
    el.innerHTML = `<div class="empty-state compact">${escHtml(e.message)}</div>`;
  }
}

function renderAdminDepartments() {
  const el = document.getElementById('adminDepartmentsTable');
  const s = state.adminDepartments;
  const term = s.search.toLowerCase();
  let rows = s.rows.filter(d => {
    const haystack = `${d.code} ${d.name} ${d.manager_name || ''}`.toLowerCase();
    if (term && !haystack.includes(term)) return false;
    if (s.status && String(Boolean(d.is_active)) !== s.status) return false;
    return true;
  });
  rows = sortRows(rows, s.sort, s.dir, (d, sort) => sort === 'members' ? Number(d.member_count || 0) : d[sort] || '');
  const page = paginateRows(rows, s.page, s.pageSize);
  s.page = page.safePage;
  el.innerHTML = `
    <div class="table-toolbar">
      <input class="input table-search" type="search" placeholder="Search departments" value="${escHtml(s.search)}" oninput="adminDepartmentsFilter('search', this.value)" />
      <select class="select" onchange="adminDepartmentsFilter('status', this.value)"><option value="">All status</option><option value="true" ${s.status === 'true' ? 'selected' : ''}>Active</option><option value="false" ${s.status === 'false' ? 'selected' : ''}>Inactive</option></select>
    </div>
    ${!rows.length ? '<div class="empty-state compact">Không có phòng ban phù hợp với bộ lọc.</div>' : `
    <div class="responsive-table">
      <table class="audit-table enterprise-table">
        <thead><tr><th onclick="sortAdminDepartments('code')">Code</th><th onclick="sortAdminDepartments('name')">Name</th><th>Manager</th><th onclick="sortAdminDepartments('members')">Members</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>${page.rows.map(d => `
          <tr>
            <td><span class="tag">${escHtml(d.code)}</span></td>
            <td><strong>${escHtml(d.name)}</strong></td>
            <td>${escHtml(d.manager_name || '-')}</td>
            <td>${escHtml(d.member_count ?? 0)}</td>
            <td>${statusBadge(Boolean(d.is_active))}</td>
            <td><button class="btn btn-outline btn-sm" onclick="deactivateDepartment(${Number(d.id)})" ${!d.is_active ? 'disabled' : ''}>Deactivate</button></td>
          </tr>`).join('')}</tbody>
      </table>
    </div>
    ${pagerHtml('adminDepartments', page.safePage, page.totalPages)}`}
  `;
}

function adminDepartmentsFilter(key, value) {
  state.adminDepartments[key] = value;
  state.adminDepartments.page = 1;
  renderAdminDepartments();
}

function sortAdminDepartments(sort) {
  const s = state.adminDepartments;
  s.dir = s.sort === sort && s.dir === 'asc' ? 'desc' : 'asc';
  s.sort = sort;
  renderAdminDepartments();
}

function adminDepartmentsPage(page) {
  state.adminDepartments.page = page;
  renderAdminDepartments();
}

async function deactivateDepartment(id) {
  try {
    if (!(await confirmAction('Deactivate department', 'Phòng ban sẽ bị chuyển sang trạng thái inactive.'))) return;
    await api(`/departments/${id}`, { method: 'DELETE' });
    toast('Department deactivated', 'success');
    await loadAdminDepartments();
  } catch (e) {
    toast(e.message, 'error');
  }
}
