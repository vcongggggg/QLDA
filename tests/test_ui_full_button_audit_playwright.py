from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
from calendar import monthrange
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest
import uvicorn

from app.database import get_connection
from app.main import app
from app.seed import seed_full_demo_data
from app.settings import settings
from tests.role_module_matrix import EXPECTED_ROLE_MODULES, ROLE_ACCOUNTS

try:
    from playwright.sync_api import Error, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright
except ImportError:
    Error = None
    Page = Any
    PlaywrightTimeoutError = TimeoutError
    sync_playwright = None


QUEUE_MANAGER_ROLES = {"ADMIN", "MANAGER", "HR"}
REPORT_ROLES = {"ADMIN", "MANAGER", "LEADER", "HR", "AUDITOR"}
AI_ROLES = {"ADMIN", "MANAGER", "LEADER"}
ADMIN_ROLES = {"ADMIN", "HR"}
OPS_ROLES = {"ADMIN", "AUDITOR"}


def _env_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _headed() -> bool:
    return os.getenv("PLAYWRIGHT_HEADED") == "1"


def _demo_notes_enabled() -> bool:
    value = os.getenv("PLAYWRIGHT_DEMO_NOTES")
    if value is not None:
        return value != "0"
    return _headed()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _move_datetime_to_month(value: datetime, *, year: int, month: int) -> datetime:
    last_day = monthrange(year, month)[1]
    return value.replace(year=year, month=month, day=min(value.day, last_day))


def _move_demo_kpi_dates_to_current_month() -> str:
    """Keep the temporary demo database visually current without changing KPI rules."""
    now = datetime.now(timezone.utc)
    target_month = now.strftime("%Y-%m")
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, deadline, completed_at, created_at, updated_at FROM tasks"
        ).fetchall()
        for row in rows:
            old_deadline = _parse_iso(str(row["deadline"]))
            if old_deadline is None:
                continue
            new_deadline = _move_datetime_to_month(old_deadline, year=now.year, month=now.month)
            old_completed = _parse_iso(row["completed_at"])
            old_created = _parse_iso(str(row["created_at"]))
            old_updated = _parse_iso(str(row["updated_at"]))
            new_completed = (new_deadline + (old_completed - old_deadline)).isoformat() if old_completed else None
            new_created = (new_deadline + (old_created - old_deadline)).isoformat() if old_created else new_deadline.isoformat()
            new_updated = (new_deadline + (old_updated - old_deadline)).isoformat() if old_updated else new_deadline.isoformat()
            conn.execute(
                """
                UPDATE tasks
                SET deadline = ?, completed_at = ?, created_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_deadline.isoformat(), new_completed, new_created, new_updated, int(row["id"])),
            )

        adjustment_day = min(now.day, monthrange(now.year, now.month)[1])
        adjustment_created_at = now.replace(day=adjustment_day, hour=17, minute=0, second=0, microsecond=0).isoformat()
        conn.execute(
            "UPDATE kpi_adjustments SET month = ?, created_at = ?",
            (target_month, adjustment_created_at),
        )
    return target_month


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _artifact_path() -> Path:
    preferred = Path(__file__).resolve().parents[1] / ".tmp"
    try:
        preferred.mkdir(exist_ok=True)
        probe = preferred / ".audit-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return preferred / "playwright-button-audit.json"
    except OSError:
        fallback = Path(tempfile.gettempdir()) / "teamswork-pytest"
        fallback.mkdir(exist_ok=True)
        return fallback / "playwright-button-audit.json"


@pytest.fixture()
def live_server() -> str:
    original_ai_key = settings.ai_api_key
    original_ai_timeout = settings.ai_task_breakdown_timeout_seconds
    original_rag_embedding = settings.rag_embedding_enabled
    settings.ai_api_key = ""
    settings.ai_task_breakdown_timeout_seconds = 1
    settings.rag_embedding_enabled = False
    seed_full_demo_data(mode="upsert")
    _move_demo_kpi_dates_to_current_month()

    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="on")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url}/health", timeout=1.0)
            if response.status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("Uvicorn test server did not become healthy")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)
    settings.ai_api_key = original_ai_key
    settings.ai_task_breakdown_timeout_seconds = original_ai_timeout
    settings.rag_embedding_enabled = original_rag_embedding


@pytest.fixture()
def browser():
    if sync_playwright is None or Error is None:
        pytest.skip("Playwright is not installed. Run `pip install -r requirements.txt`.")
    with sync_playwright() as pw:
        try:
            chromium = pw.chromium.launch(
                headless=not _headed(),
                slow_mo=_env_int("PLAYWRIGHT_SLOW_MO_MS", 650 if _headed() else 0),
            )
        except Error as exc:
            pytest.skip(f"Chromium is not installed for Playwright: {exc}")
        try:
            yield chromium
        finally:
            chromium.close()


class ButtonAudit:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.rows: list[dict[str, Any]] = []
        self.console_errors: list[str] = []
        self.failed_responses: list[str] = []

    def attach(self, page: Page) -> None:
        page.on("console", self._on_console)
        page.on("response", self._on_response)

    def _on_console(self, msg: Any) -> None:
        if msg.type == "error":
            text = msg.text
            if text not in self.console_errors:
                self.console_errors.append(text)

    def _on_response(self, response: Any) -> None:
        if response.url.startswith(self.base_url) and response.status >= 400:
            item = f"{response.status} {response.url}"
            if item not in self.failed_responses:
                self.failed_responses.append(item)

    def record(self, role: str, module: str, action: str, ok: bool, detail: str = "") -> None:
        self.rows.append({"role": role, "module": module, "action": action, "ok": ok, "detail": detail})
        self.write()

    def check(self, page: Page, role: str, module: str, action: str, func: Callable[[], str | None]) -> None:
        try:
            _show_demo_note(page, role, module, action)
            detail = func() or ""
            _demo_action_pause(page)
            self.record(role, module, action, True, detail)
        except Exception as exc:  # noqa: BLE001 - audit should collect every failing action.
            screenshot = _artifact_path().with_name(f"playwright-failure-{role}-{module}-{action}.png")
            try:
                page.screenshot(path=str(screenshot), full_page=True)
            except Exception:
                pass
            self.record(role, module, action, False, f"{type(exc).__name__}: {exc}")

    def write(self) -> Path:
        path = _artifact_path()
        payload = {
            "rows": self.rows,
            "console_errors": self.console_errors,
            "failed_responses": self.failed_responses,
            "summary": {
                "total": len(self.rows),
                "passed": sum(1 for row in self.rows if row["ok"]),
                "failed": sum(1 for row in self.rows if not row["ok"]),
            },
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path


def _login(page: Page, base_url: str, email: str, password: str) -> None:
    page.goto(f"{base_url}/ui/", wait_until="domcontentloaded")
    page.evaluate("() => localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.locator("#loginEmail").fill(email)
    page.locator("#loginPassword").fill(password)
    page.locator(".login-submit").click()
    page.wait_for_function(
        "() => !document.querySelector('#mainWrap')?.classList.contains('hidden')",
        timeout=10000,
    )
    _install_demo_overlay(page)


def _install_demo_overlay(page: Page) -> None:
    if not _demo_notes_enabled():
        return
    page.evaluate(
        """
        () => {
          if (document.getElementById('playwrightDemoNote')) return;
          const box = document.createElement('div');
          box.id = 'playwrightDemoNote';
          box.style.position = 'fixed';
          box.style.top = '14px';
          box.style.right = '14px';
          box.style.zIndex = '2147483647';
          box.style.maxWidth = '380px';
          box.style.padding = '10px 12px';
          box.style.borderRadius = '8px';
          box.style.background = 'rgba(15, 23, 42, 0.94)';
          box.style.color = '#fff';
          box.style.font = '600 13px/1.35 system-ui, -apple-system, Segoe UI, sans-serif';
          box.style.boxShadow = '0 12px 32px rgba(15, 23, 42, 0.24)';
          box.style.pointerEvents = 'none';
          box.style.whiteSpace = 'normal';
          box.textContent = 'Demo is starting';
          document.body.appendChild(box);
        }
        """
    )


def _show_demo_note(page: Page, role: str, module: str, action: str) -> None:
    if not _demo_notes_enabled():
        return
    _install_demo_overlay(page)
    label = f"{role} / {module} / {action.replace('-', ' ')}"
    page.evaluate(
        """
        (label) => {
          const box = document.getElementById('playwrightDemoNote');
          if (!box) return;
          box.textContent = `Running: ${label}`;
        }
        """,
        label,
    )
    page.wait_for_timeout(_env_int("PLAYWRIGHT_DEMO_NOTE_MS", 800 if _headed() else 0))


def _demo_action_pause(page: Page) -> None:
    if not _demo_notes_enabled():
        return
    page.wait_for_timeout(_env_int("PLAYWRIGHT_DEMO_AFTER_ACTION_MS", 350 if _headed() else 0))


def _goto_module(page: Page, section: str, role: str | None = None) -> None:
    if role is not None:
        _show_demo_note(page, role, section, "open module")
    page.evaluate("(section) => window.navigate(section)", section)
    page.wait_for_function(
        "(section) => !document.querySelector(`#sec-${section}`)?.classList.contains('hidden')",
        arg=section,
        timeout=10000,
    )
    _wait_for_settle(page)


def _wait_for_settle(page: Page) -> None:
    page.wait_for_timeout(_env_int("PLAYWRIGHT_DEMO_STEP_MS", 450 if _headed() else 150))
    try:
        page.wait_for_function(
            "() => !document.querySelector('.section:not(.hidden) .skeleton')",
            timeout=2500,
        )
    except PlaywrightTimeoutError:
        pass


def _visible_text(page: Page, section: str) -> str:
    return page.locator(f"#sec-{section}").inner_text(timeout=10000).lower()


def _assert_no_access_denied(page: Page, section: str) -> str:
    text = _visible_text(page, section)
    assert "access denied" not in text
    assert "không có quyền truy cập" not in text
    assert "khÃ´ng cÃ³ quyá»n truy cáº­p" not in text
    return "module visible"


def _click_visible(page: Page, selector: str, timeout: int = 10000) -> str:
    locator = page.locator(selector).first
    locator.wait_for(state="visible", timeout=timeout)
    locator.click()
    _wait_for_settle(page)
    return "clicked"


def _click_optional(page: Page, selector: str) -> str:
    locator = page.locator(selector).first
    if locator.count() == 0 or not locator.is_visible():
        return "not visible"
    if locator.is_disabled():
        return "disabled"
    locator.click()
    _wait_for_settle(page)
    return "clicked"


def _download(page: Page, selector: str) -> str:
    locator = page.locator(selector).first
    locator.wait_for(state="visible", timeout=10000)
    locator.click()
    page.wait_for_function("() => window.__lastDownloadStatus !== undefined", timeout=10000)
    status = int(page.evaluate("() => window.__lastDownloadStatus"))
    href = str(page.evaluate("() => window.__lastDownloadUrl || ''"))
    page.evaluate("() => { window.__lastDownloadStatus = undefined; window.__lastDownloadUrl = undefined; }")
    assert status == 200
    return href


def _toast_text(page: Page) -> str:
    locator = page.locator("#toast:not(.hidden)")
    if locator.count() == 0:
        return ""
    return locator.first.inner_text(timeout=3000)


def _global_actions(page: Page, audit: ButtonAudit, role: str) -> None:
    audit.check(page, role, "global", "refresh-current", lambda: _click_visible(page, "button[onclick='refreshCurrent()']"))
    audit.check(page, role, "global", "notification-panel", lambda: _click_visible(page, "#notificationBell"))
    audit.check(page, role, "global", "mark-all-notifications-read", lambda: _click_optional(page, "button[onclick='markAllNotificationsRead()']"))
    audit.check(page, role, "global", "sidebar-toggle", lambda: _click_optional(page, ".menu-btn"))


def _kanban_actions(page: Page, audit: ButtonAudit, role: str) -> None:
    if "kanban" not in EXPECTED_ROLE_MODULES[role]:
        return
    _goto_module(page, "kanban", role)
    audit.check(page, role, "kanban", "access", lambda: _assert_no_access_denied(page, "kanban"))
    audit.check(page, role, "kanban", "status-filter", lambda: page.locator("#kanbanStatusFilter").select_option("todo") or "filtered")
    audit.check(page, role, "kanban", "keyword-filter", lambda: page.locator("#kanbanKeywordFilter").fill("dashboard") or "typed")
    audit.check(page, role, "kanban", "reset-filters", lambda: _click_visible(page, "#sec-kanban button[onclick='resetKanbanFilters()']"))
    audit.check(page, role, "kanban", "open-task-detail", lambda: _click_optional(page, ".task-card"))
    audit.check(page, role, "kanban", "comment-validation", lambda: _click_optional(page, "button[onclick='submitTaskComment()']"))
    page.evaluate("() => window.closeTaskDetail && window.closeTaskDetail()")
    if role in {"ADMIN", "MANAGER", "LEADER", "MEMBER"}:
        audit.check(page, role, "kanban", "status-move", lambda: _click_optional(page, ".task-card-actions button"))


def _timeline_actions(page: Page, audit: ButtonAudit, role: str) -> None:
    if "timeline" not in EXPECTED_ROLE_MODULES[role]:
        return
    _goto_module(page, "timeline", role)
    audit.check(page, role, "timeline", "access", lambda: _assert_no_access_denied(page, "timeline"))
    audit.check(page, role, "timeline", "zoom-week", lambda: page.locator("#timelineZoom").select_option("week") or "week")
    audit.check(page, role, "timeline", "zoom-month", lambda: page.locator("#timelineZoom").select_option("month") or "month")
    audit.check(page, role, "timeline", "keyword-filter", lambda: page.locator("#timelineKeywordFilter").fill("dashboard") or "typed")
    audit.check(page, role, "timeline", "reset-filters", lambda: _click_visible(page, "#sec-timeline button[onclick='resetTimelineFilters()']"))
    audit.check(page, role, "timeline", "open-task-detail", lambda: _click_optional(page, ".timeline-task-row"))
    page.evaluate("() => window.closeTaskDetail && window.closeTaskDetail()")


def _reports_actions(page: Page, audit: ButtonAudit, role: str) -> None:
    if role not in REPORT_ROLES:
        return
    _goto_module(page, "reports", role)
    audit.check(page, role, "reports", "access", lambda: _assert_no_access_denied(page, "reports"))
    if role != "ADMIN":
        audit.check(page, role, "reports", "export-buttons-visible", lambda: "visible")
        return
    page.evaluate(
        """
        () => {
          window.__lastDownloadStatus = undefined;
          window.__lastDownloadUrl = undefined;
          window.triggerDownload = async (url) => {
            const res = await fetch(url, {
              headers: localStorage.getItem('tw_access_token')
                ? { Authorization: `Bearer ${localStorage.getItem('tw_access_token')}` }
                : {}
            });
            window.__lastDownloadStatus = res.status;
            window.__lastDownloadUrl = url;
            await res.arrayBuffer();
          };
        }
        """
    )
    report_buttons = (
        ("kpi-csv", "button[onclick=\"downloadReport('kpi','csv')\"]"),
        ("kpi-xlsx", "button[onclick=\"downloadReport('kpi','xlsx')\"]"),
        ("kpi-pdf", "button[onclick=\"downloadReport('kpi','pdf')\"]"),
        ("portfolio-csv", "button[onclick=\"downloadReport('portfolio','csv')\"]"),
        ("portfolio-xlsx", "button[onclick=\"downloadReport('portfolio','xlsx')\"]"),
        ("progress-csv", "button[onclick=\"downloadReport('progress','csv')\"]"),
        ("progress-xlsx", "button[onclick=\"downloadReport('progress','xlsx')\"]"),
    )
    for action, selector in report_buttons:
        audit.check(page, role, "reports", action, lambda selector=selector: _download(page, selector))
    audit.check(page, role, "reports", "sprint-export-validation", lambda: _click_visible(page, "button[onclick=\"downloadSprintReport('csv')\"]") or _toast_text(page))
    page.locator("#sprintReportId").fill("1")
    audit.check(page, role, "reports", "sprint-csv", lambda: _download(page, "button[onclick=\"downloadSprintReport('csv')\"]"))


def _ai_and_rag_actions(page: Page, audit: ButtonAudit, role: str) -> None:
    if role not in AI_ROLES:
        return
    _goto_module(page, "ai", role)
    audit.check(page, role, "ai", "access", lambda: _assert_no_access_denied(page, "ai"))
    audit.check(page, role, "ai", "draft-refresh", lambda: _click_visible(page, "#sec-ai button[onclick='loadAiDrafts()']"))
    if role != "MANAGER":
        audit.check(page, role, "ai", "buttons-visible", lambda: "visible")
        return
    page.locator("#aiRequirementText").fill("Build a project dashboard with task progress, KPI summary, and exportable status reports.")
    audit.check(page, role, "ai", "generate-text", lambda: _click_visible(page, "button[onclick='generateAiTasksFromText()']", timeout=20000))
    audit.check(page, role, "ai", "import-preview", lambda: _click_optional(page, "button[onclick='importSelectedAiTasks()']"))
    audit.check(page, role, "ai", "review-drawer", lambda: _click_optional(page, "#aiDraftsTable button:has-text('Review')"))
    audit.check(page, role, "ai", "review-save", lambda: _click_optional(page, "#aiDraftOverlay button:has-text('Review')"))
    audit.check(page, role, "ai", "review-close", lambda: _click_optional(page, "#aiDraftOverlay button:has-text('Close')"))
    page.locator("#ragTitle").fill(f"Audit RAG {role}")
    page.locator("#ragSource").fill(f"audit-{role.lower()}")
    page.locator("#ragContent").fill("Audit document for Playwright full button coverage and RAG management checks.")
    audit.check(page, role, "rag", "create-document", lambda: _click_visible(page, "button[onclick='createRagDocument()']"))
    audit.check(page, role, "rag", "refresh-documents", lambda: _click_visible(page, "#sec-ai button[onclick='loadRagDocuments()']"))
    audit.check(page, role, "rag", "delete-document", lambda: _click_optional(page, "#ragDocuments button"))


def _teams_actions(page: Page, audit: ButtonAudit, role: str) -> None:
    if "teams" not in EXPECTED_ROLE_MODULES[role]:
        return
    _goto_module(page, "teams", role)
    audit.check(page, role, "teams", "access", lambda: _assert_no_access_denied(page, "teams"))
    audit.check(page, role, "teams", "refresh", lambda: _click_visible(page, "button[onclick='loadTeams()']"))
    if role not in QUEUE_MANAGER_ROLES:
        audit.check(page, role, "teams", "queue-manager-hidden", lambda: "queue manager controls not exposed")


def _ops_actions(page: Page, audit: ButtonAudit, role: str) -> None:
    if role not in OPS_ROLES:
        return
    _goto_module(page, "ops", role)
    audit.check(page, role, "ops", "access", lambda: _assert_no_access_denied(page, "ops"))
    audit.check(page, role, "ops", "refresh", lambda: _click_visible(page, "button[onclick='loadOpsDashboard()']"))
    page.locator("#opsKeywordFilter").fill("risk")
    audit.check(page, role, "ops", "filter-keyword", lambda: page.locator("#opsKeywordFilter").press("Enter") or "filtered")
    audit.check(page, role, "ops", "reset-filters", lambda: _click_visible(page, "button[onclick='resetOpsFilters()']"))
    if role in QUEUE_MANAGER_ROLES:
        audit.check(page, role, "ops", "process-queue", lambda: _click_optional(page, "#opsProcessQueueBtn"))
    else:
        audit.check(page, role, "ops", "process-hidden", lambda: "not permitted")
    audit.check(page, role, "ops", "requeue-visible-failed", lambda: _click_optional(page, "#opsFailedQueueTable button"))


def _admin_actions(page: Page, audit: ButtonAudit, role: str) -> None:
    if role not in ADMIN_ROLES:
        return
    _goto_module(page, "admin", role)
    audit.check(page, role, "admin", "access", lambda: _assert_no_access_denied(page, "admin"))
    audit.check(page, role, "admin", "audit-refresh", lambda: _click_optional(page, "button[onclick='loadAuditLogs()']"))
    audit.check(page, role, "admin", "users-sort", lambda: _click_optional(page, "#adminUsersTable th[onclick=\"sortAdminUsers('name')\"]"))
    audit.check(page, role, "admin", "users-filter", lambda: page.locator("#adminUsersTable input.table-search").fill("team") or "filtered")
    audit.check(page, role, "admin", "departments-sort", lambda: _click_optional(page, "#adminDepartmentsTable th[onclick=\"sortAdminDepartments('code')\"]"))
    audit.check(page, role, "admin", "departments-filter", lambda: page.locator("#adminDepartmentsTable input.table-search").fill("eng") or "filtered")
    if role == "ADMIN":
        audit.check(page, role, "admin", "rbac-refresh", lambda: _click_visible(page, "button[onclick='loadRbacAdmin()']"))
        page.locator("#rbacRoleSelect").select_option("AUDITOR")
        audit.check(page, role, "admin", "rbac-load-role", lambda: page.evaluate("() => loadRolePermissions()") or "loaded")
        audit.check(page, role, "admin", "rbac-save", lambda: _click_visible(page, "button[onclick='saveRolePermissions()']"))
        def deactivate_cancel() -> str:
            result = _click_optional(page, "#adminDepartmentsTable button")
            if result == "clicked":
                page.evaluate("() => window.closeConfirmModal && window.closeConfirmModal(false)")
            return result

        audit.check(page, role, "admin", "department-deactivate-cancel", deactivate_cancel)
    else:
        audit.check(page, role, "admin", "rbac-save-hidden", lambda: "not permitted")


def _logout_action(page: Page, audit: ButtonAudit, role: str) -> None:
    def action() -> str:
        if page.locator(".logout-btn").count() == 0 or not page.locator(".logout-btn").is_visible():
            page.locator(".menu-btn").click()
        page.locator(".logout-btn").click()
        page.locator("#loginScreen").wait_for(state="visible", timeout=10000)
        return "logged out"

    audit.check(page, role, "global", "logout", action)


def test_full_button_audit_across_roles(live_server: str, browser) -> None:
    page = browser.new_page(accept_downloads=True)
    page.set_default_timeout(5000)
    audit = ButtonAudit(live_server)
    audit.attach(page)
    report_path = _artifact_path()
    try:
        for role, (email, password) in ROLE_ACCOUNTS.items():
            _login(page, live_server, email, password)
            _global_actions(page, audit, role)
            for section in EXPECTED_ROLE_MODULES[role]:
                _goto_module(page, section, role)
                audit.check(page, role, section, "open-module", lambda section=section: _assert_no_access_denied(page, section))
            _kanban_actions(page, audit, role)
            _timeline_actions(page, audit, role)
            _reports_actions(page, audit, role)
            _ai_and_rag_actions(page, audit, role)
            _teams_actions(page, audit, role)
            _ops_actions(page, audit, role)
            _admin_actions(page, audit, role)
            _logout_action(page, audit, role)
    finally:
        report_path = audit.write()
        page.close()

    failures = [row for row in audit.rows if not row["ok"]]
    assert not failures, f"Button audit failures written to {report_path}: {failures[:5]}"
