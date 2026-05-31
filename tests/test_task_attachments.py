from datetime import datetime, timedelta, timezone
from io import BytesIO
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.repository import create_task, create_user

client = TestClient(app)

def _hdr(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}

def _unique(prefix: str) -> str:
    return f"{prefix}.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

def test_task_attachments_upload_delete_and_validation() -> None:
    init_db()
    manager = create_user("Attachment Manager", f"{_unique('att.manager')}@example.com", "manager", "PMO")
    staff = create_user("Attachment Staff", f"{_unique('att.staff')}@example.com", "staff", "Engineering")
    outsider = create_user("Attachment Outsider", f"{_unique('att.outsider')}@example.com", "staff", "Engineering")
    
    deadline = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    task = create_task(
        "Attachment testing task",
        "Verification for US071",
        int(staff["id"]),
        None,
        None,
        2,
        "medium",
        deadline,
    )
    task_id = int(task["id"])

    # 1. Happy path: Upload attachment as manager
    file_content = b"Fake PDF file contents"
    response = client.post(
        f"/tasks/{task_id}/attachments",
        headers=_hdr(int(manager["id"])),
        files={"file": ("spec.pdf", BytesIO(file_content), "application/pdf")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["attachment_metadata"]) == 1
    att = payload["attachment_metadata"][0]
    assert att["name"] == "spec.pdf"
    assert att["content_type"] == "application/pdf"
    assert att["size"] == len(file_content)
    assert att["url"].startswith("/ui/uploads/")

    # 2. Permissions boundary: Outsider staff cannot upload
    outsider_upload = client.post(
        f"/tasks/{task_id}/attachments",
        headers=_hdr(int(outsider["id"])),
        files={"file": ("hack.exe", BytesIO(b"evil"), "application/octet-stream")},
    )
    assert outsider_upload.status_code == 403

    # 3. Happy path: Upload attachment as assigned staff (owner)
    another_file = b"Fake Image contents"
    response2 = client.post(
        f"/tasks/{task_id}/attachments",
        headers=_hdr(int(staff["id"])),
        files={"file": ("screenshot.png", BytesIO(another_file), "image/png")},
    )
    assert response2.status_code == 200
    assert len(response2.json()["attachment_metadata"]) == 2

    # 4. Upload size limit validation: > 50MB (50MB + 1 byte)
    huge_content = b"a" * (50 * 1024 * 1024 + 1)
    huge_upload = client.post(
        f"/tasks/{task_id}/attachments",
        headers=_hdr(int(staff["id"])),
        files={"file": ("huge.zip", BytesIO(huge_content), "application/zip")},
    )
    assert huge_upload.status_code == 400
    assert "exceeds 50MB" in huge_upload.json()["detail"]

    # 5. Happy path: Delete attachment as staff
    url_to_delete = att["url"]
    delete_resp = client.request(
        "DELETE",
        f"/tasks/{task_id}/attachments",
        headers=_hdr(int(staff["id"])),
        json={"url": url_to_delete},
    )
    assert delete_resp.status_code == 200
    assert len(delete_resp.json()["attachment_metadata"]) == 1
    assert delete_resp.json()["attachment_metadata"][0]["name"] == "screenshot.png"

    # 6. Delete validation: non-existent URL
    delete_non_existent = client.request(
        "DELETE",
        f"/tasks/{task_id}/attachments",
        headers=_hdr(int(staff["id"])),
        json={"url": "/ui/uploads/doesnotexist.txt"},
    )
    assert delete_non_existent.status_code == 400
