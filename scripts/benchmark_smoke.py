from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import init_db
from app.main import app
from app.database import get_connection


def _admin_user_id() -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE role IN ('admin', 'ADMIN') OR role_id = 'ADMIN' ORDER BY id LIMIT 1"
        ).fetchone()
        if row:
            return int(row["id"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO users
            (full_name, email, role, department, role_id, is_active, created_at, updated_at)
            VALUES (?, ?, 'admin', 'IT', 'ADMIN', ?, ?, ?)
            """,
            (f"Benchmark Admin {stamp}", f"benchmark.admin.{stamp}@example.com", 1, now, now),
        )
    return int(cursor.lastrowid)


def run() -> dict:
    init_db()
    client = TestClient(app)
    admin_id = _admin_user_id()
    checks = [
        ("health", "GET", "/health", {}),
        ("readiness", "GET", "/monitoring/readiness", {}),
        ("metrics", "GET", "/monitoring/metrics", {"X-User-Id": str(admin_id)}),
        ("release_gate", "GET", "/monitoring/release-gate", {"X-User-Id": str(admin_id)}),
        ("release_acceptance", "GET", "/monitoring/release-acceptance", {"X-User-Id": str(admin_id)}),
    ]
    results = []
    for name, method, path, headers in checks:
        started = perf_counter()
        response = client.request(method, path, headers=headers)
        elapsed_ms = round((perf_counter() - started) * 1000, 2)
        results.append(
            {
                "name": name,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
                "ok": 200 <= response.status_code < 300,
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "local_testclient",
        "ok": all(item["ok"] for item in results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local Phase 6 benchmark smoke checks.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()
    payload = run()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for item in payload["results"]:
            status = "PASS" if item["ok"] else "FAIL"
            print(f"{status} {item['method']} {item['path']} {item['status_code']} {item['elapsed_ms']}ms")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
