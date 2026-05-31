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

/** Một lần: gắn dropzone + delegation (3 cột giữ id cố định, chỉ nội dung con thay đổi) */
