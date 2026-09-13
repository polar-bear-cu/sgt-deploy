# Subglutee Project - Deploy

รวมทุก service ของ Subglutee ขึ้น docker network เดียว จำลอง production topology (gateway เป็นทางเข้าเดียว)

### Prerequisite

clone repo ทั้งหมดเป็น sibling directory เดียวกัน (ชื่อ container ต้องตรงกับที่ `sgt-gateway/nginx.conf` อ้างถึง):

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

- Docker

### Setup

```terminal
git clone https://github.com/polar-bear-cu/sgt-deploy.git
cd sgt-deploy
cp .env.example .env   # ใส่ GOOGLE_CLIENT_ID/SECRET จริงถ้าจะเทส login
make up
```

- gateway: http://localhost:8000
- rabbitmq management ui: http://localhost:15672 (guest/guest)
- mailhog ui: http://localhost:8025
- pgweb (subscription db): http://localhost:8081
- pgweb (user db): http://localhost:8083
- pgweb (auth db): http://localhost:8085

### Structure

```
postgres-subscription / postgres-user / postgres-auth   แยก DB ต่อ service
migrate-subscription / migrate-user / migrate-auth      one-shot migration job, รันก่อน service ที่เกี่ยวข้อง
rabbitmq / mongo / mailhog                               shared infra (noti + scheduler ใช้ queue เดียวกัน)
subscription-service / user-service / auth-service       REST + gRPC
report-service / noti-service / scheduler                gRPC client / consumer, ไม่มี DB เอง
gateway                                                   ทางเข้าเดียว (:8000), route ไป frontend + REST
frontend                                                  SPA, เข้าผ่าน gateway เท่านั้น (ไม่ publish port ตรง)
```

### Useful Commands

```terminal
make up       # docker compose up -d --build
make down     # docker compose down -v (ลบ volume, DB/queue data หาย)
make logs     # docker compose logs -f
make check    # docker compose config -q (CI ใช้ตัวนี้)
```

rebuild/restart service เดียว: `docker compose up -d --build <name>`
