from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import ai, auth, kpi, monitoring, notifications, org, phase6, rag, rbac, reports, sprints, tasks, teams, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app.settings import settings

    settings.validate_production_safety()
    init_db()
    yield


app = FastAPI(
    title="TeamsWork API",
    version="1.0.0",
    description="Hệ thống quản trị công việc & KPI nội bộ tích hợp Microsoft Teams",
    lifespan=lifespan,
)

# ── Static UI ──────────────────────────────────────────────────────────────────
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    from app.settings import settings

    response = await call_next(request)
    script_sources = ["'self'", "'unsafe-inline'", "https://res.cdn.office.net", "https://cdn.jsdelivr.net"]
    if settings.app_env != "production":
        script_sources.append("'unsafe-eval'")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    if not request.url.path.startswith("/teams/tab"):
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'self' https://teams.microsoft.com https://*.teams.microsoft.com; "
        f"script-src {' '.join(script_sources)}; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'",
    )
    if settings.app_env == "production" and getattr(settings, "security_hsts_enabled", False):
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(_static_dir), html=True), name="ui")


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/ui/")


# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(monitoring.router)
app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(rbac.router)
app.include_router(rag.router)
app.include_router(users.router)
app.include_router(org.router)
app.include_router(tasks.router)
app.include_router(notifications.router)
app.include_router(sprints.router)
app.include_router(kpi.router)
app.include_router(reports.router)
app.include_router(teams.router)
app.include_router(phase6.router)
