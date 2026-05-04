from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import psycopg2


TABLES_IN_ORDER = [
    "users",
    "departments",
    "projects",
    "project_members",
    "sprints",
    "tasks",
    "sprint_capacity_plans",
    "project_risks",
    "weekly_status_updates",
    "teams_conversation_refs",
    "notification_queue",
    "audit_logs",
    "kpi_adjustments",
]


def read_sqlite_rows(sqlite_path: Path, table: str) -> tuple[list[str], list[tuple]]:
    with sqlite3.connect(sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    out: list[tuple] = []
    for r in rows:
        values: list[object] = []
        for c in cols:
            val = r[c]
            if isinstance(val, str) and c == "payload":
                try:
                    json.loads(val)
                except Exception:
                    pass
            values.append(val)
        out.append(tuple(values))
    return cols, out


def copy_table(pg_conn, sqlite_path: Path, table: str) -> int:
    cols, rows = read_sqlite_rows(sqlite_path, table)
    if not rows:
        return 0

    with pg_conn.cursor() as cur:
        col_sql = ", ".join(cols)
        placeholders = ", ".join(["%s"] * len(cols))
        insert_sql = f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        cur.executemany(insert_sql, rows)
    return len(rows)


def sync_table_sequence(pg_conn, table: str) -> None:
    with pg_conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT setval(
                pg_get_serial_sequence('{table}', 'id'),
                COALESCE(MAX(id), 1),
                COALESCE(MAX(id) IS NOT NULL, FALSE)
            )
            FROM {table}
            """
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate TeamsWork data from SQLite to PostgreSQL")
    parser.add_argument("--sqlite", default="teamswork.db", help="Path to SQLite DB file")
    parser.add_argument("--postgres-dsn", required=True, help="PostgreSQL DSN")
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite).resolve()
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite DB not found: {sqlite_path}")

    pg_conn = psycopg2.connect(args.postgres_dsn)
    try:
        total = 0
        for table in TABLES_IN_ORDER:
            try:
                copied = copy_table(pg_conn, sqlite_path, table)
                sync_table_sequence(pg_conn, table)
                total += copied
                print(f"{table}: copied {copied} rows")
            except Exception as exc:
                pg_conn.rollback()
                print(f"{table}: failed - {exc}")
                raise
            else:
                pg_conn.commit()

        print(f"Done. Total copied rows: {total}")
    finally:
        pg_conn.close()


if __name__ == "__main__":
    main()
