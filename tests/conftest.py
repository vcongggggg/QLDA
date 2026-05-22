import os
import tempfile
from pathlib import Path

import pytest

from app.database import init_db
from app.settings import settings


_TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
_TEST_TEMP_ROOT.mkdir(exist_ok=True)

for _name in ("TMPDIR", "TEMP", "TMP"):
    os.environ[_name] = str(_TEST_TEMP_ROOT)

tempfile.tempdir = str(_TEST_TEMP_ROOT)


@pytest.fixture(autouse=True)
def isolated_test_database(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    init_db()
    yield
