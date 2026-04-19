from app.kpi import calculate_monthly_kpi


def test_kpi_done_on_time_and_late_and_overdue() -> None:
    tasks = [
        {
            "assignee_id": 1,
            "assignee_name": "User A",
            "difficulty": "easy",
            "status": "done",
            "deadline": "2026-04-10T10:00:00+00:00",
            "completed_at": "2026-04-09T10:00:00+00:00",
        },
        {
            "assignee_id": 1,
            "assignee_name": "User A",
            "difficulty": "hard",
            "status": "done",
            "deadline": "2026-04-10T10:00:00+00:00",
            "completed_at": "2026-04-12T10:00:00+00:00",
        },
        {
            "assignee_id": 1,
            "assignee_name": "User A",
            "difficulty": "medium",
            "status": "todo",
            "deadline": "2026-04-15T10:00:00+00:00",
            "completed_at": None,
        },
    ]

    report = calculate_monthly_kpi(tasks, "2026-04")
    result = report[1]

    assert result["done_on_time"] == 1
    assert result["done_late"] == 1
    assert result["overdue_unfinished"] == 1
    assert result["score"] == 12.5
