from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _request(base_url: str, path: str, *, user_id: int | None = None) -> tuple[int, str, str]:
    headers = {}
    if user_id is not None:
        headers["X-User-Id"] = str(user_id)
    request = Request(f"{base_url.rstrip('/')}{path}", headers=headers)
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, response.headers.get("content-type", ""), body
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, exc.headers.get("content-type", ""), body


def _expect(name: str, ok: bool, detail: str) -> bool:
    status = "PASS" if ok else "FAIL"
    print(f"{status} {name}: {detail}")
    return ok


def run_smoke_checks(base_url: str, user_id: int, expect_production_auth: bool) -> int:
    failures = 0
    month = datetime.now(timezone.utc).strftime("%Y-%m")

    status, _content_type, body = _request(base_url, "/health")
    failures += not _expect("health", status == 200 and '"ok"' in body, f"HTTP {status}")

    status, _content_type, body = _request(base_url, "/monitoring/readiness")
    failures += not _expect("readiness", status == 200 and "ready" in body, f"HTTP {status}")

    status, _content_type, body = _request(base_url, "/teams/tab/prod")
    failures += not _expect("teams_tab_prod", status == 200 and "TeamsWork Production Tab" in body, f"HTTP {status}")

    status, content_type, body = _request(base_url, f"/reports/kpi.csv?month={month}", user_id=user_id)
    failures += not _expect(
        "kpi_csv_export",
        status == 200 and "text/csv" in content_type and "user_id,user_name,month" in body,
        f"HTTP {status} {content_type}",
    )

    status, content_type, body = _request(base_url, "/monitoring/metrics", user_id=user_id)
    metrics_ok = status == 200 and "application/json" in content_type
    if metrics_ok:
        metrics_ok = "users" in json.loads(body)
    failures += not _expect("monitoring_metrics", metrics_ok, f"HTTP {status} {content_type}")

    status, _content_type, _body = _request(base_url, "/monitoring/metrics")
    expected_status = 401 if expect_production_auth else 200
    failures += not _expect(
        "auth_without_header",
        status == expected_status,
        f"HTTP {status}, expected {expected_status}",
    )

    return int(failures)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run TeamsWork deployment smoke checks.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--expect-production-auth", action="store_true")
    args = parser.parse_args()

    try:
        return run_smoke_checks(args.base_url, args.user_id, args.expect_production_auth)
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"FAIL smoke_check: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
