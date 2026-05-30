import os
import tempfile
from pathlib import Path
import uuid

import pytest

from app.database import init_db
from app.settings import settings


def _usable_temp_root() -> Path:
    preferred = Path(__file__).resolve().parents[1] / ".tmp"
    try:
        preferred.mkdir(exist_ok=True)
        probe = preferred / f".pytest-probe-{uuid.uuid4().hex}"
        probe.mkdir()
        probe.rmdir()
        pytest_root = preferred / f"pytest-of-{os.environ.get('USERNAME') or os.environ.get('USER') or ''}"
        if pytest_root.exists():
            list(pytest_root.iterdir())
        return preferred
    except OSError:
        fallback = Path(tempfile.gettempdir()) / "teamswork-pytest"
        fallback.mkdir(exist_ok=True)
        return fallback


_TEST_TEMP_ROOT = _usable_temp_root()

for _name in ("TMPDIR", "TEMP", "TMP"):
    os.environ[_name] = str(_TEST_TEMP_ROOT)

tempfile.tempdir = str(_TEST_TEMP_ROOT)


@pytest.fixture(autouse=True)
def isolated_test_database(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    init_db()
    yield
