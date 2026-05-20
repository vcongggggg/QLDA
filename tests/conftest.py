import os
import tempfile
from pathlib import Path


_TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
_TEST_TEMP_ROOT.mkdir(exist_ok=True)

for _name in ("TMPDIR", "TEMP", "TMP"):
    os.environ[_name] = str(_TEST_TEMP_ROOT)

tempfile.tempdir = str(_TEST_TEMP_ROOT)
