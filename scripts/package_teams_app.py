from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from urllib.parse import urlparse

REQUIRED_FILES = ["manifest.json", "color.png", "outline.png"]
PLACEHOLDER_HOST = "REPLACE_WITH_PUBLIC_HOST"
PLACEHOLDER_CLIENT_ID = "REPLACE_WITH_AAD_APP_CLIENT_ID"


def _read_env(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _host_from_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.netloc:
        return parsed.netloc
    return base_url.replace("https://", "").replace("http://", "").strip("/")


def _render_manifest(template: str, host: str | None, client_id: str | None) -> str:
    rendered = template
    if host:
        rendered = rendered.replace(PLACEHOLDER_HOST, host)
    if client_id:
        rendered = rendered.replace(PLACEHOLDER_CLIENT_ID, client_id)

    remaining = [value for value in (PLACEHOLDER_HOST, PLACEHOLDER_CLIENT_ID) if value in rendered]
    if remaining:
        raise ValueError(
            "Missing values for manifest placeholders: "
            + ", ".join(remaining)
            + ". Pass --host/--client-id or set APP_BASE_URL/TEAMS_CLIENT_ID in .env."
        )
    return rendered


def package_teams_app(
    source_dir: Path,
    out_zip: Path,
    *,
    host: str | None = None,
    client_id: str | None = None,
    env_path: Path = Path(".env"),
) -> None:
    missing = [name for name in REQUIRED_FILES if not (source_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing required files in {source_dir}: {', '.join(missing)}"
        )

    env = _read_env(env_path)
    host = host or _host_from_base_url(env.get("APP_BASE_URL", ""))
    client_id = client_id or env.get("TEAMS_CLIENT_ID")
    manifest = _render_manifest(
        (source_dir / "manifest.json").read_text(encoding="utf-8"),
        host=host,
        client_id=client_id,
    )

    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", manifest)
        for name in ("color.png", "outline.png"):
            zf.write(source_dir / name, arcname=name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package Teams app manifest and icons into zip")
    parser.add_argument("--source", default="teams-app", help="Folder containing manifest and icons")
    parser.add_argument("--out", default="teams-app-package.zip", help="Output zip path")
    parser.add_argument("--env", default=".env", help="Environment file used to fill manifest placeholders")
    parser.add_argument("--host", help="Public HTTPS host without protocol, e.g. example.ngrok-free.dev")
    parser.add_argument("--client-id", help="Azure App Registration client ID")
    args = parser.parse_args()

    source = Path(args.source)
    out = Path(args.out)
    package_teams_app(
        source,
        out,
        env_path=Path(args.env),
        host=args.host,
        client_id=args.client_id,
    )
    print(f"Packaged Teams app to: {out.resolve()}")
