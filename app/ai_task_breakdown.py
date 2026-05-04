from __future__ import annotations

import io
import json
import re
import time
from dataclasses import dataclass

import httpx
from docx import Document

from app.schemas import TaskBreakdownItem
from app.settings import settings


MAX_DOCX_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class BreakdownResult:
    source: str
    items: list[TaskBreakdownItem]
    warnings: list[str]


def extract_docx_text(data: bytes) -> str:
    if len(data) > MAX_DOCX_BYTES:
        raise ValueError("docx file is too large; max size is 2MB")
    doc = Document(io.BytesIO(data))
    parts: list[str] = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts).strip()


def normalize_breakdown_items(raw_items: list[dict], max_tasks: int) -> list[TaskBreakdownItem]:
    output: list[TaskBreakdownItem] = []
    for index, raw in enumerate(raw_items[:max_tasks], start=1):
        title = str(raw.get("title") or raw.get("name") or "").strip()
        if not title:
            continue
        difficulty = str(raw.get("difficulty") or "medium").strip().lower()
        if difficulty not in {"easy", "medium", "hard"}:
            difficulty = "medium"
        try:
            story_points = int(raw.get("story_points", 3))
        except (TypeError, ValueError):
            story_points = 3
        try:
            offset = int(raw.get("deadline_offset_days", 7 + index))
        except (TypeError, ValueError):
            offset = 7 + index
        output.append(
            TaskBreakdownItem(
                title=title[:200],
                description=(str(raw.get("description") or "").strip() or None),
                story_points=max(1, min(story_points, 13)),
                difficulty=difficulty,
                deadline_offset_days=max(1, min(offset, 90)),
                rationale=(str(raw.get("rationale") or "").strip() or None),
                selected=bool(raw.get("selected", True)),
            )
        )
    return output


def breakdown_requirements_locally(text: str, max_tasks: int = 8) -> list[TaskBreakdownItem]:
    candidates = _candidate_sentences(text)
    if not candidates:
        candidates = [text.strip()]
    raw_items: list[dict] = []
    for index, sentence in enumerate(candidates[:max_tasks], start=1):
        title = _title_from_sentence(sentence)
        raw_items.append(
            {
                "title": title,
                "description": sentence.strip(),
                "story_points": _estimate_story_points(sentence),
                "difficulty": _estimate_difficulty(sentence),
                "deadline_offset_days": min(90, 5 + index * 2),
                "rationale": "Sinh tự động từ yêu cầu/tài liệu bằng heuristic fallback.",
            }
        )
    return normalize_breakdown_items(raw_items, max_tasks=max_tasks)


def breakdown_requirements(text: str, project_context: str | None = None, max_tasks: int = 8) -> BreakdownResult:
    warnings: list[str] = []
    if settings.ai_provider == "openai_compatible" and settings.ai_api_key:
        last_exc: Exception | None = None
        models = [settings.ai_model]
        if settings.ai_fallback_model and settings.ai_fallback_model not in models:
            models.append(settings.ai_fallback_model)

        for model_index, model in enumerate(models):
            for attempt in range(1, 4):
                try:
                    items = _breakdown_with_openai_compatible(text, project_context, max_tasks, model=model)
                    if items:
                        return BreakdownResult(source="openai_compatible", items=items, warnings=warnings)
                    warnings.append(f"AI model {model} returned no tasks.")
                    break
                except httpx.HTTPStatusError as exc:
                    last_exc = exc
                    if exc.response.status_code == 429 and attempt < 3:
                        warnings.append(f"Rate limit on {model} (attempt {attempt}/3), retrying in {attempt * 3}s...")
                        time.sleep(attempt * 3)
                        continue
                    break
                except Exception as exc:  # noqa: BLE001 - fallback must be robust for demos
                    last_exc = exc
                    break
            if model_index < len(models) - 1:
                warnings.append(f"AI model {model} failed; trying fallback model {models[-1]}.")
                continue
        if last_exc is not None:
            warnings.append(f"AI provider failed; used local fallback: {last_exc}")
    else:
        warnings.append("AI_API_KEY is not configured; used local fallback.")
    return BreakdownResult(source="heuristic", items=breakdown_requirements_locally(text, max_tasks), warnings=warnings)


def _breakdown_with_openai_compatible(
    text: str,
    project_context: str | None,
    max_tasks: int,
    model: str | None = None,
) -> list[TaskBreakdownItem]:
    base_url = settings.ai_base_url.rstrip("/")
    prompt = {
        "role": "system",
        "content": (
            "You are a senior project manager. Break Vietnamese requirements into actionable software tasks. "
            "Return only JSON with key 'tasks'. Each task must have title, description, story_points "
            "(1,2,3,5,8,13), difficulty (easy|medium|hard), deadline_offset_days, rationale."
        ),
    }
    user_content = {
        "project_context": project_context or "TeamsWork task/KPI management system integrated with Microsoft Teams",
        "max_tasks": max_tasks,
        "requirements": text[:50000],
    }
    with httpx.Client(timeout=settings.ai_task_breakdown_timeout_seconds) as client:
        response = client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.ai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model or settings.ai_model,
                "messages": [prompt, {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)}],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    payload = json.loads(content)
    raw_tasks = payload.get("tasks", payload if isinstance(payload, list) else [])
    if not isinstance(raw_tasks, list):
        return []
    return normalize_breakdown_items(raw_tasks, max_tasks=max_tasks)


def _candidate_sentences(text: str) -> list[str]:
    lines = [line.strip(" -•\t") for line in text.splitlines() if line.strip()]
    chunks: list[str] = []
    for line in lines:
        if len(line) <= 180:
            chunks.append(line)
        else:
            chunks.extend(part.strip() for part in re.split(r"(?<=[.!?。])\s+", line) if part.strip())
    keywords = ("cần", "cho phép", "quản lý", "tạo", "xem", "cập nhật", "xuất", "tích hợp", "đăng nhập", "phân quyền")
    prioritized = [chunk for chunk in chunks if any(keyword in chunk.lower() for keyword in keywords)]
    return prioritized or chunks


def _title_from_sentence(sentence: str) -> str:
    cleaned = re.sub(r"\s+", " ", sentence).strip(" .,:;")
    cleaned = re.sub(r"^(hệ thống|người dùng|admin|manager|quản lý)\s+", "", cleaned, flags=re.IGNORECASE)
    if len(cleaned) > 72:
        cleaned = cleaned[:69].rstrip() + "..."
    if not cleaned:
        return "Phân tích và triển khai yêu cầu"
    return cleaned[0].upper() + cleaned[1:]


def _estimate_difficulty(sentence: str) -> str:
    lower = sentence.lower()
    hard_markers = ("tích hợp", "sso", "azure", "teams", "báo cáo", "ai", "phân rã", "đồng bộ")
    easy_markers = ("hiển thị", "xem", "lọc", "danh sách")
    if any(marker in lower for marker in hard_markers):
        return "hard"
    if any(marker in lower for marker in easy_markers):
        return "easy"
    return "medium"


def _estimate_story_points(sentence: str) -> int:
    difficulty = _estimate_difficulty(sentence)
    if difficulty == "hard":
        return 8
    if difficulty == "easy":
        return 2
    return 5
