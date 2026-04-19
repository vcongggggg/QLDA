from io import BytesIO
from datetime import datetime

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def build_kpi_csv(rows: list[dict]) -> str:
    lines = ["user_id,user_name,month,done_on_time,done_late,overdue_unfinished,score"]
    for r in rows:
        lines.append(
            f"{r['user_id']},{r['user_name']},{r['month']},{r['done_on_time']},{r['done_late']},{r['overdue_unfinished']},{r['score']}"
        )
    return "\n".join(lines)


def build_kpi_xlsx(rows: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "KPI"
    ws.append(["user_id", "user_name", "month", "done_on_time", "done_late", "overdue_unfinished", "score"])
    for r in rows:
        ws.append(
            [
                r["user_id"],
                r["user_name"],
                r["month"],
                r["done_on_time"],
                r["done_late"],
                r["overdue_unfinished"],
                r["score"],
            ]
        )
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def build_kpi_pdf(rows: list[dict], month: str) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, f"TeamsWork KPI Report - {month}")
    y -= 24
    pdf.setFont("Helvetica", 9)
    pdf.drawString(40, y, f"Generated at: {datetime.utcnow().isoformat()}Z")
    y -= 24
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(40, y, "User")
    pdf.drawString(220, y, "On-time")
    pdf.drawString(280, y, "Late")
    pdf.drawString(330, y, "Overdue")
    pdf.drawString(400, y, "Score")
    y -= 16
    pdf.setFont("Helvetica", 9)

    for row in rows:
        if y < 50:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 9)
        pdf.drawString(40, y, str(row["user_name"])[:28])
        pdf.drawString(220, y, str(row["done_on_time"]))
        pdf.drawString(280, y, str(row["done_late"]))
        pdf.drawString(330, y, str(row["overdue_unfinished"]))
        pdf.drawString(400, y, str(row["score"]))
        y -= 14

    pdf.save()
    return buffer.getvalue()


def build_project_progress_csv(rows: list[dict]) -> str:
    lines = [
        "project_id,total_tasks,done_tasks,overdue_tasks,completion_rate,total_story_points,completed_story_points"
    ]
    for r in rows:
        lines.append(
            f"{r['project_id']},{r['total_tasks']},{r['done_tasks']},{r['overdue_tasks']},{r['completion_rate']},{r['total_story_points']},{r['completed_story_points']}"
        )
    return "\n".join(lines)


def build_project_progress_xlsx(rows: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "ProjectProgress"
    ws.append(
        [
            "project_id",
            "total_tasks",
            "done_tasks",
            "overdue_tasks",
            "completion_rate",
            "total_story_points",
            "completed_story_points",
        ]
    )
    for r in rows:
        ws.append(
            [
                r["project_id"],
                r["total_tasks"],
                r["done_tasks"],
                r["overdue_tasks"],
                r["completion_rate"],
                r["total_story_points"],
                r["completed_story_points"],
            ]
        )
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def build_sprint_review_csv(summary: dict) -> str:
    headers = [
        "sprint_id",
        "project_id",
        "sprint_name",
        "status",
        "total_tasks",
        "done_tasks",
        "unfinished_tasks",
        "planned_story_points",
        "completed_story_points",
        "completion_rate",
    ]
    values = [str(summary.get(h, "")) for h in headers]
    return ",".join(headers) + "\n" + ",".join(values)


def build_sprint_review_xlsx(summary: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "SprintReview"
    for k, v in summary.items():
        ws.append([k, v])
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def build_portfolio_csv(rows: list[dict]) -> str:
    headers = [
        "project_id",
        "project_name",
        "status",
        "completion_rate",
        "total_tasks",
        "overdue_tasks",
        "completed_story_points",
        "total_story_points",
    ]
    lines = [",".join(headers)]
    for r in rows:
        lines.append(
            ",".join(
                [
                    str(r.get("project_id", "")),
                    str(r.get("project_name", "")),
                    str(r.get("status", "")),
                    str(r.get("completion_rate", "")),
                    str(r.get("total_tasks", "")),
                    str(r.get("overdue_tasks", "")),
                    str(r.get("completed_story_points", "")),
                    str(r.get("total_story_points", "")),
                ]
            )
        )
    return "\n".join(lines)


def build_portfolio_xlsx(rows: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Portfolio"
    ws.append(
        [
            "project_id",
            "project_name",
            "status",
            "completion_rate",
            "total_tasks",
            "overdue_tasks",
            "completed_story_points",
            "total_story_points",
        ]
    )
    for r in rows:
        ws.append(
            [
                r.get("project_id"),
                r.get("project_name"),
                r.get("status"),
                r.get("completion_rate"),
                r.get("total_tasks"),
                r.get("overdue_tasks"),
                r.get("completed_story_points"),
                r.get("total_story_points"),
            ]
        )
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
