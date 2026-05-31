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
