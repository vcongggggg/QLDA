from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import init_db
from app.seed import seed_full_demo_data, seed_rag_demo_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed TeamsWork full demo data and RAG demo documents.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--upsert", action="store_true", help="Idempotently upsert full demo data. This is the default.")
    mode.add_argument("--reset-demo", action="store_true", help="Reset demo-scoped data before reseeding. Local/dev/demo only.")
    parser.add_argument("--rag-only", action="store_true", help="Seed only RAG demo documents and required parent records.")
    parser.add_argument("--force", action="store_true", help="Override reset guard. Dangerous outside local/dev/demo.")
    args = parser.parse_args()

    seed_mode = "reset" if args.reset_demo else "upsert"
    init_db()
    if args.rag_only:
        summary = seed_rag_demo_data(mode=seed_mode, force=args.force)
    else:
        summary = seed_full_demo_data(mode=seed_mode, force=args.force)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
