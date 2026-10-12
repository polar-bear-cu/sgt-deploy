#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTGRES = {
    "postgres-subscription": "subscriptions",
    "postgres-user": "users",
    "postgres-auth": "auth",
}
MONGO_DB = "noti"

def log(msg):
    print(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {msg}", flush=True)

def container(project, service):
    out = subprocess.run(
        [
            "docker", "ps", "-q",
            "--filter", f"label=com.docker.compose.project={project}",
            "--filter", f"label=com.docker.compose.service={service}",
        ],
        check=True, capture_output=True, text=True,
    ).stdout.split()
    if len(out) != 1:
        raise RuntimeError(f"expected 1 running container for {service}, found {len(out)}")
    return out[0]

def dump(project, service, cmd, dest):
    tmp = dest.with_suffix(dest.suffix + ".part")
    with tmp.open("wb") as f:
        subprocess.run(["docker", "exec", container(project, service), *cmd], check=True, stdout=f)
    tmp.rename(dest)
    log(f"{service} -> {dest.name} ({dest.stat().st_size} bytes)")

def prune(base, keep):
    runs = sorted(p for p in base.iterdir() if p.is_dir() and not p.name.endswith(".part"))
    for old in runs[:-keep]:
        shutil.rmtree(old)
        log(f"pruned {old.name}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=ROOT.name)
    parser.add_argument("--out", default=str(ROOT / "backups"))
    parser.add_argument("--keep", type=int, default=7)
    args = parser.parse_args()
    os.umask(0o077)
    base = Path(args.out)
    base.mkdir(exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    work = base / f"{stamp}.part"
    work.mkdir()

    try:
        for service, db in POSTGRES.items():
            dump(args.project, service, ["pg_dump", "-U", "postgres", "-d", db, "-Fc"], work / f"{db}.dump")
        dump(args.project, "mongo", ["mongodump", "--db", MONGO_DB, "--archive", "--gzip", "--quiet"], work / f"{MONGO_DB}.archive.gz")
    except (subprocess.CalledProcessError, RuntimeError) as err:
        shutil.rmtree(work)
        log(f"backup FAILED: {err}")
        return 1

    work.rename(base / stamp)
    prune(base, args.keep)
    log(f"backup ok: {base / stamp}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
