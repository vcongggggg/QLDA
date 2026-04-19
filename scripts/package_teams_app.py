from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

REQUIRED_FILES = ["manifest.json", "color.png", "outline.png"]


def package_teams_app(source_dir: Path, out_zip: Path) -> None:
    missing = [name for name in REQUIRED_FILES if not (source_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing required files in {source_dir}: {', '.join(missing)}"
        )

    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in REQUIRED_FILES:
            zf.write(source_dir / name, arcname=name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package Teams app manifest and icons into zip")
    parser.add_argument("--source", default="teams-app", help="Folder containing manifest and icons")
    parser.add_argument("--out", default="teams-app-package.zip", help="Output zip path")
    args = parser.parse_args()

    source = Path(args.source)
    out = Path(args.out)
    package_teams_app(source, out)
    print(f"Packaged Teams app to: {out.resolve()}")
