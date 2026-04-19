from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.auth import get_current_user, require_roles
from app.kpi import calculate_monthly_kpi
from app.reporting import (
    build_kpi_csv,
    build_kpi_pdf,
    build_kpi_xlsx,
    build_portfolio_csv,
    build_portfolio_xlsx,
    build_project_progress_csv,
    build_project_progress_xlsx,
    build_sprint_review_csv,
    build_sprint_review_xlsx,
)
from app.repository import (
    all_tasks_with_users,
    list_kpi_adjustments_by_month,
    list_projects,
    portfolio_summary,
    project_progress,
    sprint_exists,
    sprint_review_summary,
)
from fastapi import HTTPException

router = APIRouter(prefix="/reports", tags=["reports"])


def _kpi_rows(month: str, current_user: dict) -> list[dict]:
    tasks = all_tasks_with_users()
    if current_user["role"] == "staff":
        tasks = [t for t in tasks if int(t["assignee_id"]) == int(current_user["id"])]
    report = calculate_monthly_kpi(tasks, month, adjustments=list_kpi_adjustments_by_month(month))
    return sorted(report.values(), key=lambda r: r["score"], reverse=True)


@router.get("/kpi.csv")
def kpi_report_csv(month: str = Query(description="YYYY-MM"), current_user: dict = Depends(get_current_user)) -> Response:
    require_roles(current_user, {"admin", "manager", "hr"})
    content = build_kpi_csv(_kpi_rows(month, current_user))
    return Response(content=content, media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=teamswork-kpi-{month}.csv"})


@router.get("/kpi.xlsx")
def kpi_report_xlsx(month: str = Query(description="YYYY-MM"), current_user: dict = Depends(get_current_user)) -> Response:
    require_roles(current_user, {"admin", "manager", "hr"})
    content = build_kpi_xlsx(_kpi_rows(month, current_user))
    return Response(content=content,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=teamswork-kpi-{month}.xlsx"})


@router.get("/kpi.pdf")
def kpi_report_pdf(month: str = Query(description="YYYY-MM"), current_user: dict = Depends(get_current_user)) -> Response:
    require_roles(current_user, {"admin", "manager", "hr"})
    content = build_kpi_pdf(_kpi_rows(month, current_user), month)
    return Response(content=content, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=teamswork-kpi-{month}.pdf"})


@router.get("/portfolio/summary.csv")
def portfolio_csv(current_user: dict = Depends(get_current_user)) -> Response:
    require_roles(current_user, {"admin", "manager", "hr"})
    content = build_portfolio_csv(portfolio_summary())
    return Response(content=content, media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=teamswork-portfolio-summary.csv"})


@router.get("/portfolio/summary.xlsx")
def portfolio_xlsx(current_user: dict = Depends(get_current_user)) -> Response:
    require_roles(current_user, {"admin", "manager", "hr"})
    content = build_portfolio_xlsx(portfolio_summary())
    return Response(content=content,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=teamswork-portfolio-summary.xlsx"})


@router.get("/projects/progress.csv")
def project_progress_csv(current_user: dict = Depends(get_current_user)) -> Response:
    require_roles(current_user, {"admin", "manager", "hr"})
    rows = [project_progress(p["id"]) for p in list_projects()]
    content = build_project_progress_csv(rows)
    return Response(content=content, media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=teamswork-project-progress.csv"})


@router.get("/projects/progress.xlsx")
def project_progress_xlsx(current_user: dict = Depends(get_current_user)) -> Response:
    require_roles(current_user, {"admin", "manager", "hr"})
    rows = [project_progress(p["id"]) for p in list_projects()]
    content = build_project_progress_xlsx(rows)
    return Response(content=content,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=teamswork-project-progress.xlsx"})


@router.get("/sprints/{sprint_id}/review.csv")
def sprint_review_csv(sprint_id: int, current_user: dict = Depends(get_current_user)) -> Response:
    require_roles(current_user, {"admin", "manager", "hr"})
    if not sprint_exists(sprint_id):
        raise HTTPException(status_code=404, detail="sprint not found")
    content = build_sprint_review_csv(sprint_review_summary(sprint_id))
    return Response(content=content, media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=teamswork-sprint-{sprint_id}-review.csv"})


@router.get("/sprints/{sprint_id}/review.xlsx")
def sprint_review_xlsx(sprint_id: int, current_user: dict = Depends(get_current_user)) -> Response:
    require_roles(current_user, {"admin", "manager", "hr"})
    if not sprint_exists(sprint_id):
        raise HTTPException(status_code=404, detail="sprint not found")
    content = build_sprint_review_xlsx(sprint_review_summary(sprint_id))
    return Response(content=content,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=teamswork-sprint-{sprint_id}-review.xlsx"})
