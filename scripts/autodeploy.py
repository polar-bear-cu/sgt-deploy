#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ORG = "polar-bear-cu"
DEPLOY_REPO = "sgt-deploy"
SERVICES = {
    "SUBSCRIPTION_TAG": "sgt-subscription-service",
    "USER_TAG": "sgt-user-service",
    "AUTH_TAG": "sgt-auth-service",
    "REPORT_TAG": "sgt-report-service",
    "NOTI_TAG": "sgt-noti-service",
    "SCHEDULER_TAG": "sgt-scheduler",
    "FRONTEND_TAG": "sgt-frontend",
    "GATEWAY_TAG": "sgt-gateway",
}

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "versions.prod.env"
LIVE = ROOT / "versions.live.env"
PAUSE = ROOT / ".autodeploy-paused"
STATE = ROOT / ".autodeploy-state.json"


def log(msg):
    print(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {msg}", flush=True)


def run(*cmd):
    return subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def read_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and not key.startswith("#"):
            values[key] = value
    return values


def write_env(path, values):
    path.write_text("".join(f"{k}={values[k]}\n" for k in SERVICES), encoding="utf-8")


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"failed_ci": {}, "failed_deploy": ""}


def save_state(state):
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def remote_main(repo):
    out = run("git", "ls-remote", f"https://github.com/{ORG}/{repo}.git", "refs/heads/main")
    return out.split()[0]


def ci_status(repo, sha):
    url = f"https://api.github.com/repos/{ORG}/{repo}/actions/runs?head_sha={sha}&event=push"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "sgt-autodeploy"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        runs = json.load(resp)["workflow_runs"]
    if not runs or any(r["status"] != "completed" for r in runs):
        return "pending"
    return "success" if all(r["conclusion"] == "success" for r in runs) else "failure"


def ready(repo, sha, state):
    if state["failed_ci"].get(repo) == sha:
        return False
    status = ci_status(repo, sha)
    if status == "failure":
        state["failed_ci"][repo] = sha
        log(f"{repo} {sha[:7]} CI failed, skipping until main moves")
    elif status == "pending":
        log(f"{repo} {sha[:7]} CI pending")
    return status == "success"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if PAUSE.exists():
        return 0

    state = load_state()
    notes = []

    run("git", "fetch", "-q", "origin", "main")
    head, target = run("git", "rev-parse", "HEAD"), run("git", "rev-parse", "origin/main")
    deploy_ready = head != target and ready(DEPLOY_REPO, target, state)
    if deploy_ready:
        notes.append(f"{DEPLOY_REPO} {head[:7]}->{target[:7]}")

    live = read_env(LIVE) if LIVE.exists() else read_env(BASE)
    new = dict(live)
    for var, repo in SERVICES.items():
        sha = remote_main(repo)
        if sha != live.get(var) and ready(repo, sha, state):
            new[var] = sha
            notes.append(f"{repo} {live.get(var, '')[:7]}->{sha[:7]}")

    save_state(state)
    if not notes and LIVE.exists():
        return 0

    signature = json.dumps([target if deploy_ready else head, new], sort_keys=True)
    if state["failed_deploy"] == signature:
        return 0

    log("deploying: " + (", ".join(notes) or "initial live versions"))
    if args.dry_run:
        return 0

    if deploy_ready:
        run("git", "merge", "--ff-only", "-q", "origin/main")
    write_env(LIVE, new)
    try:
        run("make", "up-prod", "PROD_VERSIONS=versions.live.env")
    except subprocess.CalledProcessError as err:
        state["failed_deploy"] = signature
        save_state(state)
        log("deploy FAILED: " + (err.stderr or err.stdout)[-800:])
        return 1

    state["failed_deploy"] = ""
    save_state(state)
    log("deploy ok")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.HTTPError as err:
        log(f"GitHub API error {err.code}, retry next run")
        sys.exit(0)
    except (urllib.error.URLError, subprocess.CalledProcessError) as err:
        log(f"error: {err}, retry next run")
        sys.exit(0)
