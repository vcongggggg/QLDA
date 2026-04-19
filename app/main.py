from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import auth, kpi, monitoring, org, reports, sprints, tasks, teams, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="TeamsWork API",
    version="1.0.0",
    description="Hệ thống quản trị công việc & KPI nội bộ tích hợp Microsoft Teams",
    lifespan=lifespan,
)

# ── Static UI ──────────────────────────────────────────────────────────────────
_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(_static_dir), html=True), name="ui")


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/ui/")


# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(monitoring.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(org.router)
app.include_router(tasks.router)
app.include_router(sprints.router)
app.include_router(kpi.router)
app.include_router(reports.router)
app.include_router(teams.router)
