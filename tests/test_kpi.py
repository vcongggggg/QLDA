from app.kpi import DEFAULT_KPI_POLICY, calculate_monthly_kpi


def _task(
    *,
    assignee_id: int = 1,
    assignee_name: str = "User A",
    difficulty: str = "easy",
    status: str = "done",
    deadline: str = "2026-04-10T10:00:00+00:00",
    completed_at: str | None = "2026-04-09T10:00:00+00:00",
) -> dict:
    return {
        "assignee_id": assignee_id,
        "assignee_name": assignee_name,
        "difficulty": difficulty,
        "status": status,
        "deadline": deadline,
        "completed_at": completed_at,
    }


def test_default_kpi_policy_matches_current_business_rules() -> None:
    assert DEFAULT_KPI_POLICY.difficulty_multiplier == {
        "easy": 1.0,
        "medium": 1.5,
        "hard": 2.0,
    }
    assert DEFAULT_KPI_POLICY.on_time_points == 10.0
    assert DEFAULT_KPI_POLICY.late_points == 5.0
    assert DEFAULT_KPI_POLICY.overdue_unfinished_points == -5.0
    assert DEFAULT_KPI_POLICY.fallback_difficulty == "easy"


def test_kpi_done_on_time_and_late_and_overdue() -> None:
    tasks = [
        _task(),
        _task(difficulty="hard", completed_at="2026-04-12T10:00:00+00:00"),
        _task(difficulty="medium", status="todo", deadline="2026-04-15T10:00:00+00:00", completed_at=None),
    ]

    report = calculate_monthly_kpi(tasks, "2026-04")
    result = report[1]

    assert result["done_on_time"] == 1
    assert result["done_late"] == 1
    assert result["overdue_unfinished"] == 1
    assert result["score"] == 12.5


def test_unknown_difficulty_falls_back_to_easy_multiplier() -> None:
    report = calculate_monthly_kpi([_task(difficulty="unknown")], "2026-04")

    assert report[1]["score"] == 10.0


def test_adjustments_are_applied_after_calculated_score() -> None:
    report = calculate_monthly_kpi(
        [_task()],
        "2026-04",
        adjustments=[
            {"user_id": 1, "user_name": "User A", "points": 2.5},
            {"user_id": 1, "user_name": "User A", "points": -1.0},
        ],
    )

    assert report[1]["score"] == 11.5


def test_adjustment_only_user_appears_in_report() -> None:
    report = calculate_monthly_kpi(
        [],
        "2026-04",
        adjustments=[
            {"user_id": 2, "user_name": "User B", "points": 3.0},
        ],
    )

    assert report[2]["score"] == 3.0
    assert report[2]["done_on_time"] == 0
