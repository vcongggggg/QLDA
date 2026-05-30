from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:8000"

ROLE_ACCOUNTS = {
    "ADMIN": ("admin@teamswork.local", "Admin@123"),
    "MANAGER": ("manager@teamswork.local", "Manager@123"),
    "MEMBER": ("member@teamswork.local", "Member@123"),
    "AUDITOR": ("auditor@teamswork.local", "Auditor@123"),
}

CHART_JS_STUB = """
window.Chart = class {
  constructor() {}
  destroy() {}
  update() {}
};
"""

ADMIN_SECTIONS = (
    "dashboard",
    "projects",
    "kanban",
    "kpi",
    "reports",
    "ai",
    "teams",
    "ops",
    "admin",
)


def _artifact_root() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = ROOT / ".tmp" / "demo-evidence" / stamp
    (root / "screenshots").mkdir(parents=True, exist_ok=True)
    (root / "videos").mkdir(parents=True, exist_ok=True)
    return root


def _wait_for_health(base_url: str, timeout_seconds: int = 30) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{base_url.rstrip('/')}/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, URLError) as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {base_url}/health: {last_error}")


def _run_seed(reset_demo: bool) -> dict:
    cmd = [sys.executable, "scripts/seed_full_demo.py", "--reset-demo" if reset_demo else "--upsert"]
    completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    return json.loads(completed.stdout)


def _start_server(base_url: str) -> subprocess.Popen:
    if base_url != DEFAULT_BASE_URL:
        raise ValueError("--start-server currently supports the default http://127.0.0.1:8000 only")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _api_login(base_url: str, email: str, password: str) -> dict:
    payload = json.dumps({"usernameOrEmail": email, "password": password}).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last_error: Exception | None = None
    for _ in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"login failed for {email}: {last_error}")


def _new_context(browser, videos_dir: Path, payload: dict):
    user_id = int(payload["user"]["id"])
    token = payload["accessToken"]
    context = browser.new_context(
        viewport={"width": 1440, "height": 960},
        record_video_dir=str(videos_dir),
        record_video_size={"width": 1440, "height": 960},
    )
    context.route("https://cdn.jsdelivr.net/**", lambda route: route.fulfill(status=200, body=CHART_JS_STUB))
    context.add_init_script(
        f"""
        localStorage.setItem('tw_access_token', {json.dumps(token)});
        localStorage.setItem('tw_uid', {json.dumps(str(user_id))});
        """
    )
    return context


def _login(page, base_url: str, email: str, password: str) -> None:
    _ = (email, password)
    try:
        page.goto(f"{base_url.rstrip('/')}/ui/", wait_until="commit", timeout=10000)
    except Exception:
        # The static page may wait on external browser plumbing even after the
        # document is usable. Continue to the app-level readiness check below.
        pass
    page.wait_for_function(
        "() => !document.querySelector('#mainWrap')?.classList.contains('hidden')",
        timeout=15000,
    )


def _navigate_and_capture(page, section: str, path: Path) -> None:
    page.evaluate("(section) => window.navigate(section)", section)
    page.wait_for_function(
        """
        (section) => {
          const target = document.querySelector(`#sec-${section}`);
          const denied = document.querySelector('#sec-access-denied');
          return (target && !target.classList.contains('hidden')) ||
                 (denied && !denied.classList.contains('hidden'));
        }
        """,
        arg=section,
        timeout=15000,
    )
    page.wait_for_timeout(900)
    page.screenshot(path=str(path), full_page=True)


def _capture_ai_generation(page, screenshots_dir: Path) -> None:
    page.evaluate("(section) => window.navigate(section)", "ai")
    page.wait_for_selector("#aiRequirementText", timeout=15000)
    page.locator("#aiRequirementText").fill(
        "Manager can create a sprint plan, split requirements into tasks, "
        "track Kanban progress, calculate KPI, and export evidence reports."
    )
    page.locator("#aiMaxTasks").fill("4")
    page.evaluate(
        """
        async () => {
          const token = localStorage.getItem('tw_access_token') || '';
          const response = await fetch('/ai/task-breakdown', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              text: document.querySelector('#aiRequirementText').value,
              max_tasks: 4,
              use_rag: false
            })
          });
          if (!response.ok) {
            throw new Error(`AI draft capture failed: ${response.status}`);
          }
          const result = await response.json();
          document.querySelector('#aiPreviewMeta').textContent =
            `${result.items.length} task - source: ${result.source}`;
          if (window.loadAiDrafts) {
            await window.loadAiDrafts();
          }
        }
        """
    )
    page.wait_for_function(
        """
        () => {
          const meta = document.querySelector('#aiPreviewMeta')?.textContent || '';
          return meta.includes('task') && meta.includes('source');
        }
        """,
        timeout=20000,
    )
    page.wait_for_timeout(900)
    page.screenshot(path=str(screenshots_dir / "admin-ai-generated-draft.png"), full_page=True)


def capture(base_url: str, artifact_dir: Path, include_ai_generation: bool) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed. Run: pip install -r requirements.txt") from exc

    screenshots_dir = artifact_dir / "screenshots"
    videos_dir = artifact_dir / "videos"
    captured: list[str] = []
    errors: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            auth_payloads = {
                role: _api_login(base_url, email, password)
                for role, (email, password) in ROLE_ACCOUNTS.items()
            }

            admin_email, admin_password = ROLE_ACCOUNTS["ADMIN"]
            context = _new_context(browser, videos_dir, auth_payloads["ADMIN"])
            page = context.new_page()
            _login(page, base_url, admin_email, admin_password)
            for section in ADMIN_SECTIONS:
                target = screenshots_dir / f"admin-{section}.png"
                _navigate_and_capture(page, section, target)
                captured.append(str(target.relative_to(ROOT)))

            if include_ai_generation:
                target = screenshots_dir / "admin-ai-generated-draft.png"
                _capture_ai_generation(page, screenshots_dir)
                captured.append(str(target.relative_to(ROOT)))
            page.close()
            context.close()

            for role, forbidden_section in (("MEMBER", "projects"), ("AUDITOR", "ai")):
                email, password = ROLE_ACCOUNTS[role]
                context = None
                page = None
                try:
                    context = _new_context(browser, videos_dir, auth_payloads[role])
                    page = context.new_page()
                    _login(page, base_url, email, password)
                    target = screenshots_dir / f"{role.lower()}-access-denied-{forbidden_section}.png"
                    _navigate_and_capture(page, forbidden_section, target)
                    captured.append(str(target.relative_to(ROOT)))
                except Exception as exc:
                    errors.append(f"{role} {forbidden_section}: {exc}")
                finally:
                    if page is not None:
                        page.close()
                    if context is not None:
                        context.close()
        finally:
            browser.close()

    videos = [str(path.relative_to(ROOT)) for path in videos_dir.glob("*.webm")]
    return {"screenshots": captured, "videos": videos, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture TeamsWork local demo screenshots and video evidence.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--start-server", action="store_true", help="Start a temporary uvicorn server on port 8000.")
    parser.add_argument("--seed", action="store_true", help="Run the full demo seed before capture.")
    parser.add_argument("--reset-demo", action="store_true", help="Use --reset-demo when seeding. Local/dev/demo only.")
    parser.add_argument("--skip-ai-generation", action="store_true", help="Do not create an AI draft during capture.")
    args = parser.parse_args()

    artifact_dir = _artifact_root()
    server: subprocess.Popen | None = None
    seed_summary: dict | None = None
    try:
        if args.seed:
            seed_summary = _run_seed(reset_demo=args.reset_demo)
        if args.start_server:
            server = _start_server(args.base_url)
        _wait_for_health(args.base_url)
        result = capture(
            base_url=args.base_url,
            artifact_dir=artifact_dir,
            include_ai_generation=not args.skip_ai_generation,
        )
        summary = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "base_url": args.base_url,
            "artifact_dir": str(artifact_dir.relative_to(ROOT)),
            "seed_summary": seed_summary,
            **result,
        }
        summary_path = artifact_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
