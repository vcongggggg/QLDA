from __future__ import annotations

import socket
import threading
import time

import httpx
import pytest
import uvicorn

from app.main import app
from app.seed import seed_full_demo_data
from tests.role_module_matrix import EXPECTED_ROLE_MODULES, ROLE_ACCOUNTS

try:
    from playwright.sync_api import Error, sync_playwright
except ImportError:
    Error = None
    sync_playwright = None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def live_server() -> str:
    seed_full_demo_data(mode="upsert")
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


@pytest.fixture()
def browser():
    if sync_playwright is None or Error is None:
        pytest.skip("Playwright is not installed. Run `pip install -r requirements.txt`.")
    with sync_playwright() as pw:
        try:
            chromium = pw.chromium.launch(headless=True)
        except Error as exc:
            pytest.skip(f"Chromium is not installed for Playwright: {exc}")
        try:
            yield chromium
        finally:
            chromium.close()


def _login(page, base_url: str, email: str, password: str) -> None:
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


def _visible_sections(page) -> set[str]:
    return set(
        page.evaluate(
            """
            () => [...document.querySelectorAll('.nav-item')]
              .filter(el => getComputedStyle(el).display !== 'none' && !el.classList.contains('hidden'))
              .map(el => el.getAttribute('data-section'))
            """
        )
    )


def test_sidebar_modules_match_role_matrix(live_server: str, browser) -> None:
    page = browser.new_page()
    try:
        for role, (email, password) in ROLE_ACCOUNTS.items():
            _login(page, live_server, email, password)

            assert _visible_sections(page) == set(EXPECTED_ROLE_MODULES[role])
            assert page.locator("#userRole").inner_text().split(" ")[0].upper() == role
    finally:
        page.close()


def test_visible_modules_open_without_access_denied(live_server: str, browser) -> None:
    page = browser.new_page()
    try:
        for role, (email, password) in ROLE_ACCOUNTS.items():
            _login(page, live_server, email, password)

            for section in EXPECTED_ROLE_MODULES[role]:
                page.evaluate("(section) => window.navigate(section)", section)
                page.wait_for_function(
                    "(section) => !document.querySelector(`#sec-${section}`)?.classList.contains('hidden')",
                    arg=section,
                    timeout=10000,
                )
                text = page.locator(f"#sec-{section}").inner_text(timeout=10000).lower()
                assert "access denied" not in text, f"{role} {section}: {text}"
                assert "không có quyền truy cập" not in text, f"{role} {section}: {text}"
    finally:
        page.close()


def test_phase5_mobile_shell_i18n_and_accessibility_hooks(live_server: str, browser) -> None:
    page = browser.new_page(viewport={"width": 390, "height": 844})
    try:
        _login(page, live_server, *ROLE_ACCOUNTS["ADMIN"])

        mobile_nav = page.locator("#mobileBottomNav")
        mobile_nav.wait_for(state="visible", timeout=10000)
        assert 1 <= mobile_nav.locator("button").count() <= 5
        assert page.locator("#mobileBottomNav button[aria-current='page']").count() == 1

        page.locator(".skip-link").focus()
        assert page.evaluate("() => document.activeElement?.classList.contains('skip-link')") is True
        page.locator(".skip-link").click()
        assert page.evaluate("() => document.activeElement?.id") == "appContent"

        page.locator("#languageToggle").click()
        assert page.evaluate("() => document.documentElement.lang") == "en"
        assert page.locator("#pageTitle").inner_text() == "Dashboard"
        page.evaluate("() => window.navigate('reports')")
        page.wait_for_function("() => document.querySelector('#pageTitle')?.textContent === 'Reports'", timeout=10000)

        page.keyboard.press("Alt+M")
        assert page.locator("#sidebar.open").count() == 1
        page.keyboard.press("Escape")
        assert page.locator("#sidebar.open").count() == 0

        assert page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1") is True
    finally:
        page.close()
