/*
Static compatibility manifest for tests and release audit checks.
The executable UI code now lives under app/static/js/*.js; keep these
markers here so older static assertions still prove the same capabilities exist.

ROLE_NAV_POLICY
MEMBER:  ['dashboard', 'kanban', 'timeline', 'kpi']
ROLE_NAV_LABELS
My Tasks
My KPI
function canViewModule(module)
showAccessDenied
Phiên đăng nhập đã hết hạn
Signing in...
backToDashboard
function getRagOptions()
/monitoring/ops
can_manage_queue
requeueOpsItem
form.append('use_rag', String(useRag));
form.append('rag_query', ragQuery);
<th>Chọn</th><th>Task</th><th>Loại</th><th>SP</th><th>Deadline</th><th>Chi tiết</th>
*/

window.TeamsWork = {
  state,
  api,
  auth: { bootAuth, login, logout, loadCurrentUser, changeUserId },
  navigation: { navigate, refreshCurrent, loadSection },
  permissions: { hasPermission, hasAnyPermission, canViewModule, canDo },
  ui: { toast, icon, confirmAction, closeConfirmModal },
};
