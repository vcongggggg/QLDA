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
  ADMIN:   ['dashboard', 'projects', 'kanban', 'timeline', 'teams', 'teams-simulator', 'kpi', 'reports', 'ai', 'ops', 'admin'],
  MANAGER: ['dashboard', 'projects', 'kanban', 'timeline', 'teams', 'teams-simulator', 'kpi', 'reports', 'ai'],
  LEADER:  ['dashboard', 'projects', 'kanban', 'timeline', 'teams', 'kpi', 'reports', 'ai'],
  MEMBER:  ['dashboard', 'kanban', 'timeline', 'kpi'],
  HR:      ['dashboard', 'admin', 'kpi', 'reports', 'teams', 'teams-simulator'],
  AUDITOR: ['dashboard', 'reports', 'ops'],
};

const ROLE_NAV_LABELS = {
  MEMBER: { kanban: 'My Tasks', timeline: 'My Timeline', kpi: 'My KPI' },
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
  timeline: ['KANBAN_VIEW'],
  projects: ['PROJECT_VIEW'],
  kpi: ['KPI_VIEW_OWN', 'KPI_VIEW_TEAM', 'KPI_VIEW_ALL'],
  reports: ['REPORT_VIEW_TEAM', 'REPORT_VIEW_ALL'],
  ai: ['AI_TASK_VIEW'],
  teams: ['TEAM_VIEW'],
  'teams-simulator': ['TEAM_VIEW'],
  ops: ['AUDIT_VIEW', 'OPS_VIEW'],
  admin: ['USER_VIEW', 'ROLE_VIEW', 'DEPARTMENT_VIEW'],
};

const ACTION_PERMISSIONS = {
  taskUpdate: ['KANBAN_UPDATE_OWN_TASK', 'KANBAN_MANAGE_TEAM', 'KANBAN_MANAGE_ALL', 'tasks.update_own', 'tasks.update_any'],
  taskDeadlineExtend: ['KANBAN_MANAGE_TEAM', 'KANBAN_MANAGE_ALL', 'tasks.update_any'],
  reportExport: ['REPORT_EXPORT', 'reports.export'],
  aiGenerate: ['AI_TASK_GENERATE', 'ai.preview'],
  aiReview: ['AI_TASK_REVIEW', 'ai.import'],
  aiImport: ['AI_TASK_IMPORT', 'ai.import'],
  ragManage: ['rag.manage'],
  opsManage: ['OPS_MANAGE', 'monitoring.admin', 'teams.manage'],
  seed: ['monitoring.admin'],
  roleManage: ['ROLE_MANAGE', 'roles.manage'],
};

const AI_LIST_FIELDS = [
  'subtasks',
  'acceptance_criteria',
  'data_requirements',
  'ui_components',
  'test_cases',
  'dependencies',
  'risks',
];

const AI_LIST_LABELS = {
  subtasks: 'Subtasks',
  acceptance_criteria: 'Acceptance criteria',
  data_requirements: 'Data requirements',
  ui_components: 'UI components',
  test_cases: 'Test cases',
  dependencies: 'Dependencies',
  risks: 'Risks',
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
  timeline:  'Timeline',
  kanban:    'Kanban – Bảng công việc',
  projects:  'Dự án',
  kpi:       'KPI – Chỉ số hiệu suất',
  reports:   'Báo cáo',
  ai:        'AI – Phân rã yêu cầu thành task',
  teams:     'Teams-ready Simulation',
  'teams-simulator': 'Teams Simulation Mode',
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
    case 'timeline':  loadTimeline();  break;
    case 'projects':  loadProjects();  break;
    case 'kpi':       loadKPI();       break;
    case 'reports':   setupReports();  break;
    case 'ai':        loadAI();        break;
    case 'teams':     loadTeams();     break;
    case 'teams-simulator': loadTeamsSimulator(); break;
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
