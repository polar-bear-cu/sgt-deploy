# Subglutee Project - Deploy

รวมทุก service ของ Subglutee ขึ้น docker network เดียว จำลอง production topology (gateway เป็นทางเข้าเดียว)

### Modes

| คำสั่ง | image มาจาก | ใช้ตอน |
| --- | --- | --- |
| `make up` | build จาก `../sgt-*` | เขียนโค้ด (ต้อง clone ทุก repo) |
| `make up-dev` | `ghcr.io/polar-bear-cu/sgt-*:dev` | รันทั้งระบบโดยไม่ต้องมี source |
| `make up-prod-smoke` | sha ใน `versions.prod.env` | ลองชุด prod บนเครื่องตัวเองก่อนขึ้น VM (gateway ที่ http://localhost:8100) |
| `make up-prod` | sha ใน `versions.prod.env` + Caddy | บน VM จริง (HTTPS) |

### Prerequisite

- Docker
- `make up`: clone repo ทั้งหมดเป็น sibling directory เดียวกัน

```
final-proj/
  sgt-deploy/
  sgt-gateway/
  sgt-frontend/
  sgt-auth-service/
  sgt-user-service/
  sgt-subscription-service/
  sgt-report-service/
  sgt-noti-service/
  sgt-scheduler/
```

- `make up-dev` / `make up-prod-smoke`: ถ้า package บน GHCR เป็น private ต้อง `docker login ghcr.io` ด้วย PAT ที่มีสิทธิ์ `read:packages` ก่อน

### Setup

```terminal
git clone https://github.com/polar-bear-cu/sgt-deploy.git
cd sgt-deploy
cp .env.example .env   # ใส่ GOOGLE_CLIENT_ID/SECRET จริงถ้าจะเทส login
make up
```

ตัวแปรใน `.env` เป็น required ทั้งหมด ถ้า `.env` เก่าขาดตัวแปร compose จะขึ้น `required variable X is missing a value` ให้ copy บรรทัดที่ขาดมาจาก `.env.example`

ค่าใน `.env.example` ใช้ได้แค่บนเครื่องตัวเอง บน prod ต้องสุ่มค่าใหม่ทุกตัว (เช่น `openssl rand -hex 24`) และใช้ Google OAuth client แยกจาก dev

### Files

```
docker-compose.yaml         base: ทุก service, ไม่ publish port, image จาก GHCR ตาม <NAME>_TAG
docker-compose.local.yaml   build จาก ../sgt-* (make up)
docker-compose.tools.yaml   port บน 127.0.0.1 + pgweb / mongo-express (ใช้บน laptop เท่านั้น)
docker-compose.smoke.yaml   publish แค่ gateway ที่ 127.0.0.1:8100 (make up-prod-smoke)
docker-compose.prod.yaml    Caddy (HTTPS) หน้า gateway + จำกัด cache ของ mongo (make up-prod)
Caddyfile                   reverse proxy ไป gateway พร้อม HSTS
versions.dev.env            tag ของแต่ละ service ฝั่ง dev
versions.prod.env           sha ของ main ที่ deploy บน prod (สร้างตอน release)
.env                        secret + config ต่อเครื่อง (gitignored)
tests/                      k6 load test (smoke / seed / load / stress), ผลอยู่ใน tests/reports/
scripts/mint_tokens.py      สร้าง JWT ของ user ทดสอบจาก JWT_SECRET ใน .env (make tokens)
```

### Ports

ทุก port bind ที่ `127.0.0.1` เข้าได้จากเครื่องตัวเองเท่านั้น

- gateway: http://localhost:8000
- rabbitmq management ui: http://localhost:15672 (user/password ตาม `RABBITMQ_USER` / `RABBITMQ_PASSWORD`)
- mailhog ui: http://localhost:8025
- mongo-express ui: http://localhost:8089
- pgweb: subscription http://localhost:8081, user http://localhost:8083, auth http://localhost:8085
- postgres: subscription 5433, user 5434, auth 5435
- service ตรง: subscription 8080, user 8082, auth 8084, report 8086, noti 8088, scheduler 8090, envoy 8091

ถ้า `make up` ขึ้น `ports are not available ... 127.0.0.1:<port>` แปลว่ามีโปรแกรมอื่นจับ port นั้นอยู่ (เช่น Firestore emulator ใช้ 8080) ให้ปิดโปรแกรมนั้นก่อน

### Structure

```
postgres-subscription / postgres-user / postgres-auth   แยก DB ต่อ service
migrate-subscription / migrate-user / migrate-auth      one-shot migration job (image sgt-<name>-migrate tag เดียวกับ service)
rabbitmq / mongo / mailhog                               shared infra (noti + scheduler ใช้ queue เดียวกัน)
subscription-service / auth-service                      REST + gRPC
user-service                                              gRPC only, เข้าผ่าน gateway to envoy (grpc-web bridge)
report-service / noti-service / scheduler                 gRPC client / consumer, ไม่มี DB เอง
envoy                                                      bridge grpc-web ไป gRPC ใน user-service
gateway                                                    ทางเข้าเดียว, route ไป frontend + REST + grpc-web (envoy)
frontend                                                  SPA, เข้าผ่าน gateway เท่านั้น
```

### Useful Commands

```terminal
make up               # build จาก source แล้วรัน (build เฉพาะที่เปลี่ยน)
make up-dev           # pull image :dev ล่าสุดแล้วรัน
make up-prod-smoke    # รันชุด prod (project แยก sgt-prod-smoke) รันพร้อม make up ได้
make down             # หยุดและลบ container แต่เก็บ volume (ข้อมูลยังอยู่)
make down-prod-smoke  # หยุดชุด prod smoke
make up-prod          # บน VM: pull image ตาม versions.prod.env แล้วรันพร้อม Caddy
make down-prod        # บน VM: หยุด (เก็บ volume)
make logs-prod        # บน VM: logs -f
make clean            # down -v ลบ volume ด้วย (DB/queue data หาย)
make logs             # logs -f
make check            # ตรวจ compose ทุกโหมด (CI ใช้ตัวนี้)
```

### Production (EC2)

เครื่อง: AWS EC2 `t3.small` (Ubuntu 24.04, ap-southeast-2) + Elastic IP + DuckDNS เปิดแค่ 80/443 ส่วน SSH เปิดเฉพาะ IP ของทีม ต้องมี Docker และ swap 2 GB ก่อน

ครั้งแรก

```terminal
git clone https://github.com/polar-bear-cu/sgt-deploy.git
cd sgt-deploy
umask 077
cat > .env <<EOF
DOMAIN=<domain>
PUBLIC_URL=https://<domain>
COOKIE_SECURE=true
JWT_SECRET=$(openssl rand -hex 32)
GOOGLE_CLIENT_ID=<prod client id>
GOOGLE_CLIENT_SECRET=<prod client secret>
SUBSCRIPTION_DB_PASSWORD=$(openssl rand -hex 24)
USER_DB_PASSWORD=$(openssl rand -hex 24)
AUTH_DB_PASSWORD=$(openssl rand -hex 24)
RABBITMQ_USER=sgt
RABBITMQ_PASSWORD=$(openssl rand -hex 24)
EOF
make up-prod
```

- `umask 077` ทำให้ `.env` อ่านได้แค่เจ้าของไฟล์ และห้ามใช้ค่าจาก `.env.example` บน prod
- password ต้องเป็น hex (URL-safe) เพราะถูกใส่ใน connection string
- Caddy ออก cert จาก Let's Encrypt เองเมื่อ DNS ชี้มาที่เครื่องและเปิด 80/443 แล้ว เช็คด้วย `curl https://<domain>/healthz`
- Google OAuth ของ prod ต้องเพิ่ม redirect URI `https://<domain>/api/v1/auth/google/callback`

#### Auto deploy

VM ดึงอัปเดตเองทุก 2 นาทีด้วย systemd timer (`scripts/autodeploy.py`)

- sgt-deploy: ถ้า `main` มี commit ใหม่และ CI เขียว -> `git merge --ff-only`
- แต่ละ service: ถ้า sha ล่าสุดของ `main` ต่างจากที่รันอยู่และ CI ของ sha นั้นเขียว (push image สำเร็จ) -> ใช้ sha ใหม่
- มีอะไรเปลี่ยน -> เขียน `versions.live.env` (ไม่อยู่ใน git) แล้ว `make up-prod PROD_VERSIONS=versions.live.env`
- deploy ล้มจะไม่ลองชุดเดิมซ้ำจนกว่าจะมี commit ใหม่

ติดตั้งครั้งแรกบน VM

```terminal
sudo cp systemd/sgt-autodeploy.service systemd/sgt-autodeploy.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sgt-autodeploy.timer
```

```terminal
systemctl list-timers sgt-autodeploy.timer    # รอบถัดไป
journalctl -u sgt-autodeploy -n 50            # log
cat versions.live.env                         # sha ที่รันอยู่
touch .autodeploy-paused                      # หยุด auto deploy ชั่วคราว (ลบไฟล์เพื่อเปิดต่อ)
```

rollback: หยุด auto deploy ก่อน แล้วแก้ sha ใน `versions.live.env` เป็นตัวก่อนหน้า แล้ว `make up-prod PROD_VERSIONS=versions.live.env` จากนั้นแก้ที่ต้นเหตุใน `main` ก่อนเปิด auto deploy อีกครั้ง

ดู mailhog ของ prod ผ่าน SSH tunnel แล้วเปิด http://localhost:8025

```terminal
ssh -L 8025:127.0.0.1:8025 -i <key.pem> ubuntu@<domain>
```

เช็คเครดิตที่เหลือใน AWS Settings ทุกสัปดาห์ ถ้าเครดิตหมด account จะปิดและข้อมูลหาย

### Load test (k6)

k6 รันผ่าน docker (`grafana/k6:2.3.0`) ไม่ต้องติดตั้ง ส่วน `tests/package.json` มีแค่ `@types/k6` ไว้ให้ editor (`cd tests && npm ci`)

```
smoke    1 VU 10 วินาที ยิง /healthz เช็คว่า script และ network ใช้ได้
seed     สร้าง subscription ให้ user ทดสอบคนละ N_SUB_PER_USER รายการ
load     ตาม NFR-2: 50 VU 5 นาที, list / detail / summary p95 < 2s, error < 1%
stress   ขั้นบันได 50 -> 100 -> 200 -> 300 VU หาจุดที่ระบบเริ่มช้า
```

```terminal
make tokens N_USERS=50           # JWT ของ user ทดสอบ (sub = uuid สุ่ม, อายุ 2 ชม.) -> tests/tokens.json
make seed N_SUB_PER_USER=100
make load
make stress
```

- ผลอยู่ใน `tests/reports/<target>.html` (gitignored)
- ยิงที่อื่นด้วย `BASE_URL=` เช่น `make load BASE_URL=https://<domain>` ค่า default คือ gateway บน laptop
- อย่า mint token ใหม่ระหว่างรอบ เพราะข้อมูลที่ seed ไว้ผูกกับ `sub` ชุดเดิม ถ้า token หมดอายุให้ลบข้อมูลแล้วเริ่มใหม่ทั้งชุด
- ข้อมูลทดสอบชื่อ `loadtest-*` และวันบิลอยู่ในเดือนธันวาคม 2027 เพื่อไม่ให้ scheduler ส่ง reminder หา user ที่ไม่มีอยู่จริง

ยิง prod

- mint token บน VM เท่านั้น (`JWT_SECRET` ห้ามออกจากเครื่อง) แล้ว scp `tokens.json` กลับมา ไฟล์นี้เป็น credential ห้ามแชร์
- บน VM ให้ `touch .autodeploy-paused` ก่อนยิง และเช็ค CPU credit balance ในแท็บ Monitoring ของ EC2 ให้เหลือพอ (โหมด standard จะโดนลดเหลือ 20% เมื่อ credit หมด)
- ลบข้อมูลทดสอบหลังเสร็จ แล้วลบ `.autodeploy-paused`

### Branch และ Release

- ทุก repo รวม sgt-deploy ใช้ flow เดียวกัน: feature -> `dev` -> `main`
- release = PR `dev` -> `main` แบบ merge commit (ห้าม squash) ไล่ตามลำดับ proto -> services -> frontend -> gateway -> deploy
- CI ของ `dev` / `main` push `ghcr.io/polar-bear-cu/sgt-<name>:<branch>` และ `:<sha>` (subscription / user / auth มี `sgt-<name>-migrate` ด้วย)
- prod pin image ด้วย sha ใน `versions.prod.env` rollback = revert commit ที่แก้ไฟล์นั้น
- hotfix บน `main` ต้อง merge กลับเข้า `dev` ด้วยทุกครั้ง
