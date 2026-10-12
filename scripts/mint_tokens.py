#!/usr/bin/env python3
import argparse
import base64
import hashlib
import hmac
import json
import time
import uuid
from pathlib import Path

def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def read_secret(env_path):
    for line in Path(env_path).read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key == "JWT_SECRET":
            return value.strip().strip("\"'")
    raise SystemExit(f"JWT_SECRET not found in {env_path}")

def sign(secret, sub, ttl):
    now = int(time.time())
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = b64url(json.dumps({"sub": sub, "iat": now, "exp": now + ttl}).encode())
    signature = hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{b64url(signature)}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=".env")
    parser.add_argument("--users", type=int, default=50)
    parser.add_argument("--ttl", type=int, default=7200)
    parser.add_argument("--out", default="tests/tokens.json")
    args = parser.parse_args()

    secret = read_secret(args.env)
    users = []
    for _ in range(args.users):
        # generate token สำหรับสื่อว่าเป็น user คนละคนกันตามค่า --users ที่กำหนด
        sub = str(uuid.uuid4())
        users.append({"sub": sub, "token": sign(secret, sub, args.ttl)})

    Path(args.out).write_text(json.dumps(users, indent=2), encoding="utf-8")
    print(f"wrote {len(users)} tokens to {args.out}, expires in {args.ttl}s")

if __name__ == "__main__":
    main()
