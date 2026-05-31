async function loadAdmin() {
  const jobs = [loadPlanCompletion()];
  if (hasPermission('USER_VIEW')) jobs.push(loadAdminUsers());
  if (hasPermission('DEPARTMENT_VIEW')) jobs.push(loadAdminDepartments());
  if (hasPermission('AUDIT_VIEW')) jobs.push(loadAuditLogs());
  if (hasPermission('ROLE_VIEW') || hasPermission('roles.view')) jobs.push(loadRbacAdmin());
  await Promise.all(jobs);
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
