#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path

from backup import ROOT, container, log

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=ROOT.name)
    parser.add_argument("--tokens", default=str(ROOT / "tests" / "tokens.json"))
    parser.add_argument("--any-user", action="store_true")
    args = parser.parse_args()

    where = "name LIKE 'loadtest-%'"
    if not args.any_user:
        users = json.loads(Path(args.tokens).read_text(encoding="utf-8"))
        subs = ",".join(f"'{uuid.UUID(u['sub'])}'" for u in users)
        where += f" AND user_id IN ({subs})"
    sql = f"WITH deleted AS (DELETE FROM subscriptions WHERE {where} RETURNING 1) SELECT count(*) FROM deleted"

    try:
        out = subprocess.run(
            [
                "docker", "exec", container(args.project, "postgres-subscription"),
                "psql", "-U", "postgres", "-d", "subscriptions", "-v", "ON_ERROR_STOP=1", "-tA", "-c", sql,
            ],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as err:
        log(f"cleanup FAILED: {err.stderr.strip()}")
        return 1
    except RuntimeError as err:
        log(f"cleanup FAILED: {err}")
        return 1

    log(f"deleted {out} loadtest subscriptions")
    return 0

if __name__ == "__main__":
    sys.exit(main())
