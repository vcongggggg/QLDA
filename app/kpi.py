from datetime import datetime, timezone
from calendar import monthrange
from dataclasses import dataclass
import json


@dataclass(frozen=True)
class KPIPolicy:
    difficulty_multiplier: dict[str, float]
    on_time_points: float
    late_points: float
    overdue_unfinished_points: float
    fallback_difficulty: str = "easy"

    def multiplier_for(self, difficulty: str | None) -> float:
        fallback = self.difficulty_multiplier[self.fallback_difficulty]
        if difficulty is None:
            return fallback
        return self.difficulty_multiplier.get(difficulty, fallback)


DEFAULT_KPI_POLICY = KPIPolicy(
    difficulty_multiplier={
        "easy": 1.0,
        "medium": 1.5,
        "hard": 2.0,
    },
    on_time_points=10.0,
    late_points=5.0,
    overdue_unfinished_points=-5.0,
)

DIFFICULTY_MULTIPLIER = DEFAULT_KPI_POLICY.difficulty_multiplier


def policy_from_row(row: dict | None) -> KPIPolicy:
    if not row:
        return DEFAULT_KPI_POLICY
    raw_multiplier = row.get("difficulty_multiplier") or "{}"
    try:
        multiplier = json.loads(raw_multiplier) if isinstance(raw_multiplier, str) else dict(raw_multiplier)
    except (TypeError, ValueError):
        multiplier = dict(DEFAULT_KPI_POLICY.difficulty_multiplier)
    return KPIPolicy(
        difficulty_multiplier={
            "easy": float(multiplier.get("easy", DEFAULT_KPI_POLICY.difficulty_multiplier["easy"])),
            "medium": float(multiplier.get("medium", DEFAULT_KPI_POLICY.difficulty_multiplier["medium"])),
            "hard": float(multiplier.get("hard", DEFAULT_KPI_POLICY.difficulty_multiplier["hard"])),
        },
        on_time_points=float(row.get("on_time_points", DEFAULT_KPI_POLICY.on_time_points)),
        late_points=float(row.get("late_points", DEFAULT_KPI_POLICY.late_points)),
        overdue_unfinished_points=float(row.get("overdue_unfinished_points", DEFAULT_KPI_POLICY.overdue_unfinished_points)),
        fallback_difficulty=str(row.get("fallback_difficulty") or DEFAULT_KPI_POLICY.fallback_difficulty),
    )


def policy_to_dict(policy: KPIPolicy) -> dict:
    return {
        "difficulty_multiplier": dict(policy.difficulty_multiplier),
        "on_time_points": float(policy.on_time_points),
        "late_points": float(policy.late_points),
        "overdue_unfinished_points": float(policy.overdue_unfinished_points),
        "fallback_difficulty": policy.fallback_difficulty,
    }


def parse_month(month: str) -> tuple[datetime, datetime]:
    year_str, month_str = month.split("-")
    year = int(year_str)
    month_num = int(month_str)
    start = datetime(year, month_num, 1, tzinfo=timezone.utc)
    last_day = monthrange(year, month_num)[1]
    end = datetime(year, month_num, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def compute_score(
    done_on_time: int,
    done_late: int,
    overdue_unfinished: int,
    policy: KPIPolicy = DEFAULT_KPI_POLICY,
) -> float:
    return float(
        done_on_time * policy.on_time_points
        + done_late * policy.late_points
        + overdue_unfinished * policy.overdue_unfinished_points
    )


def _to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def calculate_monthly_kpi(
    tasks: list[dict],
    month: str,
    adjustments: list[dict] | None = None,
    policy: KPIPolicy = DEFAULT_KPI_POLICY,
) -> dict[int, dict]:
    start, end = parse_month(month)
    report: dict[int, dict] = {}

    for task in tasks:
        deadline = _to_dt(task["deadline"])
        if deadline is None or deadline < start or deadline > end:
            continue

        user_id = int(task["assignee_id"])
        user_name = task.get("assignee_name", "Unknown")
        difficulty = task.get("difficulty", policy.fallback_difficulty)
        multiplier = policy.multiplier_for(difficulty)

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
                report[user_id]["score"] += policy.on_time_points * multiplier
            else:
                report[user_id]["done_late"] += 1
                report[user_id]["score"] += policy.late_points * multiplier
        elif status != "done" and deadline <= end:
            report[user_id]["overdue_unfinished"] += 1
            report[user_id]["score"] += policy.overdue_unfinished_points * multiplier

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


def calculate_monthly_kpi_from_transactions(transactions: list[dict], month: str) -> dict[int, dict]:
    report: dict[int, dict] = {}
    for tx in transactions:
        if tx.get("status") != "active" or tx.get("month") != month:
            continue
        user_id = int(tx["user_id"])
        if user_id not in report:
            report[user_id] = {
                "user_id": user_id,
                "user_name": tx.get("user_name", "Unknown"),
                "month": month,
                "done_on_time": 0,
                "done_late": 0,
                "overdue_unfinished": 0,
                "score": 0.0,
            }
        source_type = str(tx.get("source_type") or "")
        reason = str(tx.get("reason") or "")
        if source_type == "task":
            if reason.startswith("done_on_time"):
                report[user_id]["done_on_time"] += 1
            elif reason.startswith("done_late"):
                report[user_id]["done_late"] += 1
            elif reason.startswith("overdue_unfinished"):
                report[user_id]["overdue_unfinished"] += 1
        report[user_id]["score"] = round(float(report[user_id]["score"]) + float(tx["points"]), 2)
    return report


def compute_dashboard_metrics(tasks: list[dict], monthly_kpi: dict[int, dict], month: str, as_of: datetime | None = None) -> dict:
    now = as_of or datetime.now(timezone.utc)
    total_tasks = len(tasks)
    todo_tasks = sum(1 for t in tasks if t["status"] == "todo")
    doing_tasks = sum(1 for t in tasks if t["status"] == "doing")
    done_tasks = sum(1 for t in tasks if t["status"] == "done")
    open_tasks = total_tasks - done_tasks
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
        "open_tasks": open_tasks,
        "overdue_tasks": overdue_tasks,
        "completion_rate": round((done_tasks / total_tasks) * 100, 2) if total_tasks else 0.0,
        "avg_kpi_score": avg_kpi_score,
    }
