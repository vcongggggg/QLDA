from datetime import datetime, timezone
from calendar import monthrange

DIFFICULTY_MULTIPLIER = {
    "easy": 1.0,
    "medium": 1.5,
    "hard": 2.0,
}


def parse_month(month: str) -> tuple[datetime, datetime]:
    year_str, month_str = month.split("-")
    year = int(year_str)
    month_num = int(month_str)
    start = datetime(year, month_num, 1, tzinfo=timezone.utc)
    last_day = monthrange(year, month_num)[1]
    end = datetime(year, month_num, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def compute_score(done_on_time: int, done_late: int, overdue_unfinished: int) -> float:
    return float(done_on_time * 10 + done_late * 5 - overdue_unfinished * 5)


def _to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def calculate_monthly_kpi(tasks: list[dict], month: str, adjustments: list[dict] | None = None) -> dict[int, dict]:
    start, end = parse_month(month)
    report: dict[int, dict] = {}

    for task in tasks:
        deadline = _to_dt(task["deadline"])
        if deadline is None or deadline < start or deadline > end:
            continue

        user_id = int(task["assignee_id"])
        user_name = task.get("assignee_name", "Unknown")
        difficulty = task.get("difficulty", "easy")
        multiplier = DIFFICULTY_MULTIPLIER.get(difficulty, 1.0)

        if user_id not in report:
            report[user_id] = {
                "user_id": user_id,
                "user_name": user_name,
                "month": month,
                "done_on_time": 0,
                "done_late": 0,
                "overdue_unfinished": 0,
                "score": 0.0,
            }

        status = task["status"]
        completed_at = _to_dt(task.get("completed_at"))

        if status == "done" and completed_at is not None:
            if completed_at <= deadline:
                report[user_id]["done_on_time"] += 1
                report[user_id]["score"] += 10.0 * multiplier
            else:
                report[user_id]["done_late"] += 1
                report[user_id]["score"] += 5.0 * multiplier
        elif status != "done" and deadline <= end:
            report[user_id]["overdue_unfinished"] += 1
            report[user_id]["score"] -= 5.0 * multiplier

    for item in report.values():
        item["score"] = round(item["score"], 2)

    if adjustments:
        for adj in adjustments:
            user_id = int(adj["user_id"])
            if user_id not in report:
                report[user_id] = {
                    "user_id": user_id,
                    "user_name": adj.get("user_name", "Unknown"),
                    "month": month,
                    "done_on_time": 0,
                    "done_late": 0,
                    "overdue_unfinished": 0,
                    "score": 0.0,
                }
            report[user_id]["score"] = round(float(report[user_id]["score"]) + float(adj["points"]), 2)

    return report


def compute_dashboard_metrics(tasks: list[dict], monthly_kpi: dict[int, dict], month: str) -> dict:
    now = datetime.now(timezone.utc)
    total_tasks = len(tasks)
    todo_tasks = sum(1 for t in tasks if t["status"] == "todo")
    doing_tasks = sum(1 for t in tasks if t["status"] == "doing")
    done_tasks = sum(1 for t in tasks if t["status"] == "done")
    overdue_tasks = 0
    for task in tasks:
        deadline = _to_dt(task["deadline"])
        if deadline and task["status"] != "done" and deadline < now:
            overdue_tasks += 1

    kpi_scores = [item["score"] for item in monthly_kpi.values()]
    avg_kpi_score = round(sum(kpi_scores) / len(kpi_scores), 2) if kpi_scores else 0.0

    return {
        "month": month,
        "total_tasks": total_tasks,
        "todo_tasks": todo_tasks,
        "doing_tasks": doing_tasks,
        "done_tasks": done_tasks,
        "overdue_tasks": overdue_tasks,
        "avg_kpi_score": avg_kpi_score,
    }
