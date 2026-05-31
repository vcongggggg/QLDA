from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_phase5_mobile_accessibility_i18n_shell_hooks_are_present() -> None:
    html = _read("app/static/index.html")
    layout_css = _read("app/static/css/layout.css")
    base_css = _read("app/static/css/base.css")
    shell_js = _read("app/static/js/core-shell.js")
    manifest = _read("app/static/app.js")

    assert 'class="skip-link"' in html
    assert 'id="appContent" tabindex="-1"' in html
    assert 'id="mobileBottomNav" aria-label="Mobile primary navigation"' in html
    assert 'id="languageToggle"' in html

    assert ".mobile-bottom-nav" in layout_css
    assert "@media (max-width: 768px)" in layout_css
    assert "grid-template-columns: repeat(var(--mobile-nav-count" in layout_css
    assert ".nav-item[aria-current=\"page\"]" in layout_css
    assert ".skip-link:focus" in base_css
    assert ":focus-visible" in base_css
    assert "prefers-reduced-motion" in base_css

    assert "MOBILE_NAV_PRIORITY" in shell_js
    assert "function renderMobileNav()" in shell_js
    assert "function toggleLanguage()" in shell_js
    assert "localStorage.setItem('tw_lang'" in shell_js
    assert "document.documentElement.lang" in shell_js
    assert "performance.measure?.('tw:navigate'" in shell_js
    assert "aria-current" in shell_js

    assert "mobile-bottom-nav" in manifest
    assert "skip-link" in manifest
    assert "toggleLanguage" in manifest
