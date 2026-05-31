from fastapi import APIRouter

from app.routers.task_routes import backlog_import, crud, detail_workflow, kanban, templates

router = APIRouter(tags=["tasks"])
for _module in (crud, kanban, backlog_import, templates, detail_workflow):
    router.include_router(_module.router)
