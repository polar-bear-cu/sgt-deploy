# NFR Verification

วิธีเช็ค NFR ทีละข้อ สำหรับคนในทีมที่รู้จักระบบแต่ไม่เคยทำฝั่ง ops ทำตามจากบนลงล่างได้เลย แต่ละข้อบอกว่าต้องเปิดอะไร พิมพ์อะไร เห็นอะไรถึงผ่าน และถ้าไม่ผ่านให้ดูอะไร

## สรุปสถานะ (ตรวจ 2026-11-02)

| NFR | สถานะ | ทำที่ |
|---|---|---|
| 1.1 Timeliness 100 reminders | ผ่าน: 100/100 ภายใน 203 ms | PC |
| 1.2 Timestamps | ผ่านแบบมีข้อจำกัด: ใช้ config + `sent_at` | VM |
| 2.1, 2.2 Response time / error rate | ผ่าน: p95 ไม่เกิน 298.16 ms, error 0% | PC ยิง prod |
| 3.1 Uptime 99% | กำลังวัด: CloudWatch status check 0 fail ตั้งแต่ 10-09, UptimeRobot เริ่ม 11-02 | browser |
| 4.1, 4.2 Backup / restore | ผ่าน | VM, PC |
| 5.1 Determinism | ผ่าน: API 3 ครั้ง = SQL | browser, PC |
| 6.1 HTTPS | ผ่าน | PC |
| 6.2 No secrets in code/logs | ผ่าน | PC, VM |
| 7.1 PDPA | ผ่าน | browser, PC |
| 8.1-8.3 Mobile 360 px | ผ่าน | browser |
| 9.1 Browsers | ผ่านแบบมีข้อจำกัด: ไม่ได้ทดสอบ Safari บน macOS | browser |
| 10.1, 10.3 Reminder records / attempts | ผ่าน: failed 11 ครั้ง แล้ว sent | VM, PC |
| 10.2 Check time + acceptance time | ผ่านแบบมีข้อจำกัด: เหมือน 1.2 | VM |
| 10.4 Logs 90 วัน | ผ่าน | VM |
| 10.5 No email bodies in logs | ผ่าน | VM |

---

## ก่อนเริ่ม

### กฎ 3 ข้อ

1. คำสั่งที่มี `INSERT`, `DELETE`, `pg_restore`, `mongorestore`, `docker stop` ให้รันบน **PC เท่านั้น** ห้ามรันบน VM เพราะ VM คือ prod ที่มีข้อมูลผู้ใช้จริง
2. ห้าม `cat .env` และห้ามให้อีเมลผู้ใช้จริงขึ้นจอ ถ้าอัดคลิปหรือแคปจอ (คำสั่งในไฟล์นี้ตัด `to` ออกให้แล้ว)
3. ทำไม่ได้หรือผลไม่ตรง ให้หยุดแล้วถามในทีม อย่าเดาแก้บน VM

### ป้ายบอกที่รัน

ทุก code block มีป้ายบอกว่าต้องพิมพ์ที่ไหน

| ป้าย | หมายถึง |
|---|---|
| **[PC cmd]** | Command Prompt บน Windows ในโฟลเดอร์ `sgt-deploy` |
| **[VM bash]** | หลัง SSH เข้า EC2 แล้ว อยู่ในโฟลเดอร์ `~/sgt-deploy` |
| **[browser]** | Chrome บน PC |

คำสั่ง `[PC cmd]` ห้ามเอาไปรันใน Git Bash หรือ PowerShell เพราะ quote และ `findstr` ใช้ไม่ได้

### เตรียมเครื่อง PC (ทำครั้งเดียว)

1. ติดตั้ง Docker Desktop แล้วเปิดไว้
2. clone `sgt-deploy` แล้วทำตาม [README หัวข้อ Setup](../README.md#setup) ให้มีไฟล์ `.env` (ขอค่า `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` ของ dev จากทีม)
3. เปิดระบบ

   **[PC cmd]**
   ```cmd
   make up-dev
   ```

   ถ้าขึ้น `ports are not available ... 127.0.0.1:8080` หรือ `8000` แปลว่ามีโปรแกรมอื่นใช้ port อยู่ (เช่น Firestore emulator ใช้ 8080, Kong ใช้ 8000) ให้ปิดโปรแกรมนั้นก่อนแล้วรันใหม่

4. เช็คว่าขึ้นครบ

   **[PC cmd]**
   ```cmd
   docker ps --format "{{.Names}}" | findstr /i "scheduler mailhog postgres mongo noti"
   ```

   ต้องเห็น `sgt-deploy-scheduler-1`, `sgt-deploy-mailhog-1`, `sgt-deploy-postgres-subscription-1`, `sgt-deploy-postgres-user-1`, `sgt-deploy-mongo-1`, `sgt-deploy-noti-service-1`

5. เปิด http://localhost:8000 แล้ว login ด้วย Google 1 ครั้ง
6. หน้าเว็บอื่นบน PC ที่ใช้ในไฟล์นี้: mailhog (กล่องเมลปลอม) http://localhost:8025

### หา user_id ของตัวเองบน PC

หลายข้อต้องใช้ `user_id` ของ user ที่ **login อยู่ใน browser ตอนนั้น** ถ้าใช้ผิดคน ผลจะเป็น 0

**[PC cmd]** ใส่อีเมลที่ login
```cmd
docker exec sgt-deploy-postgres-user-1 psql -U postgres -d users -tAc "SELECT id FROM users WHERE email = '<อีเมลที่ login>'"
```

ได้ UUID 1 ตัว เช่น `8d33d3d7-1c47-43c0-a712-a6f6892e2431` จดไว้ ในไฟล์นี้เรียกว่า `<USER_ID>` ถ้าได้ค่าว่าง แปลว่ายังไม่เคย login บน PC ด้วยอีเมลนั้น

### เข้า VM (เฉพาะข้อที่ป้าย [VM bash])

ต้องมี 2 อย่าง ขอจากคนดูแล VM ในทีม

- ไฟล์ key `.pem` (เป็น credential ห้ามแชร์ต่อหรือ commit)
- IP บ้านของเราต้องอยู่ใน security group ของ EC2 (AWS Console > EC2 > Security Groups > inbound rule SSH > Source "My IP") ถ้า SSH ค้างจน timeout ส่วนใหญ่เป็นเพราะ IP บ้านเปลี่ยน

**[PC cmd]**
```cmd
ssh -i <path ของ key.pem> ubuntu@subglutee.duckdns.org
cd ~/sgt-deploy
```

---

## NFR-1 Notification timeliness

### 1.1 reminder 100 รายการ ต้องส่งถึง mail server อย่างน้อย 95% ภายใน 3 นาที

ทำบน PC เท่านั้น แนวคิดคือ สร้าง subscription 100 รายการที่ "ครบกำหนดแจ้งเตือนวันนี้" ให้ user ของเรา รอ scheduler รัน แล้ววัดว่าเมลออกช้ากว่าเวลา check เท่าไร เมลทั้งหมดเข้า mailhog ไม่ได้ส่งออกจริง

ต้องใช้ user จริงที่ login แล้ว (user ปลอมจาก `make tokens` ใช้ไม่ได้ เพราะ scheduler ต้องหาอีเมลจาก user-service)

1. สร้าง 100 รายการ ชื่อ `nfr11-1` ถึง `nfr11-100` วันบิล = พรุ่งนี้ แจ้งล่วงหน้า 1 วัน

   **[PC cmd]** แทน `<USER_ID>`
   ```cmd
   docker exec sgt-deploy-postgres-subscription-1 psql -U postgres -d subscriptions -c "INSERT INTO subscriptions (user_id, name, cost, type, category, next_billing_date, billing_day, reminder_time_in_advanced, status) SELECT '<USER_ID>', 'nfr11-' || g, 100, 'monthly', 'streaming', (((now() AT TIME ZONE 'Asia/Bangkok')::date + 1)::timestamp AT TIME ZONE 'Asia/Bangkok'), EXTRACT(DAY FROM (now() AT TIME ZONE 'Asia/Bangkok')::date + 1)::smallint, 1, 'active' FROM generate_series(1, 100) g"
   ```

   ต้องได้ `INSERT 0 100`

2. ให้ scheduler รัน
   - ดูค่าใน `.env` ของ PC บรรทัด `REMINDER_CRON`
   - ถ้าเป็น `@every 1m` ไม่ต้องทำอะไร รอไม่เกิน 1 นาที
   - ถ้าเป็นแบบ `0 9 * * *` ให้แก้เป็นเวลาอีก 3 นาทีข้างหน้า (เวลาไทย รูปแบบ `นาที ชั่วโมง * * *` เช่น 14:30 คือ `30 14 * * *`) แล้วรัน `make up-dev` อีกครั้ง และรอให้ถึงเวลา

3. ดูว่า scheduler เจอและส่งครบ

   **[PC cmd]**
   ```cmd
   docker logs sgt-deploy-scheduler-1 --since 10m | findstr "due=100"
   ```

   ต้องเห็นบรรทัดแบบ `2026/11/02 05:05:12 reminder check: date=2026-11-02 due=100 published=100 failed=0` จดเวลาหน้าบรรทัด (`05:05:12`) นี่คือ check time

4. วัดผล แก้ check time ใน `ISODate('...+07:00')` ให้ตรงกับที่จด (วันที่และเวลาไทย ไม่ต้องแปลงเป็น UTC)

   **[PC cmd]**
   ```cmd
   docker exec sgt-deploy-mongo-1 mongosh --quiet noti --eval "const t = ISODate('2026-11-02T05:05:12+07:00'); db.email_logs.aggregate([{$match: {created_at: {$gte: t}, reminder_id: /:billing:/}}, {$group: {_id: '$status', total: {$sum: 1}, within3m: {$sum: {$cond: [{$lte: [{$subtract: ['$sent_at', t]}, 180000]}, 1, 0]}}, minMs: {$min: {$subtract: ['$sent_at', t]}}, maxMs: {$max: {$subtract: ['$sent_at', t]}}}}]).toArray()"
   ```

   ผ่านเมื่อแถว `_id: 'sent'` มี `total: 100` และ `within3m` อย่างน้อย 95 (`maxMs` = รายการที่ช้าที่สุด หน่วย ms, 180000 ms = 3 นาที)

5. เก็บหลักฐาน: แคปผลข้อ 3, ผลข้อ 4 และหน้า mailhog ที่มีเมลเข้า 100 ฉบับ
6. ทำ 10.1/10.3 กรณี failed ต่อได้เลย (ด้านล่าง) แล้วค่อย cleanup

**ถ้าไม่ผ่าน**

- ข้อ 3 ไม่เจอ `due=100`: ดู `docker logs sgt-deploy-scheduler-1 --since 10m` ทั้งหมด ถ้า `due=0` แปลว่าวันที่ในข้อ 1 ไม่ตรง เช็คด้วย `... -tAc "SELECT count(*), min(next_billing_date AT TIME ZONE 'Asia/Bangkok') FROM subscriptions WHERE name LIKE 'nfr11-%'"` ต้องเป็นวันพรุ่งนี้ 00:00
- ข้อ 3 `failed` มากกว่า 0: มักเป็นเพราะ user ไม่มีในระบบ เช็ค `<USER_ID>` อีกรอบ
- ข้อ 4 ได้ `[]`: check time ผิด ลองเลื่อนให้เร็วขึ้น 1 นาที

**cleanup (ต้องทำทุกครั้ง)**

**[PC cmd]**
```cmd
docker exec sgt-deploy-postgres-subscription-1 psql -U postgres -d subscriptions -c "DELETE FROM subscriptions WHERE name LIKE 'nfr11-%'"
```

ถ้าแก้ `REMINDER_CRON` ในข้อ 2 ให้แก้กลับเป็นค่าเดิมแล้ว `make up-dev`

ผลทดสอบ 2026-11-02 (PC, check time 05:05:12): `due=100 published=100 failed=0`, `sent` 100/100 ภายใน 3 นาที เร็วสุด 47 ms ช้าสุด 203 ms

### 1.2 มีเวลาพอวัดระยะจาก check time ถึงตอน mail server รับ

ระบบไม่ได้เก็บ check time ลงฐานข้อมูล (ทีมเลือกทางนี้) แต่คำนวณได้จาก

- check time = ค่า `REMINDER_CRON` ของ prod คือ 09:00 เวลาไทยทุกวัน
- วันที่ = วันใน `created_at`
- เวลาที่ mail server รับ = `sent_at`

**[VM bash]**
```bash
grep REMINDER_CRON .env
docker exec sgt-deploy-mongo-1 mongosh --quiet noti --eval 'db.email_logs.find({}, {_id:0, to:0}).sort({created_at:-1}).limit(1).toArray()'
```

ถ้าบรรทัดแรกไม่มีผล แปลว่าใช้ค่า default `0 9 * * *` (09:00)

ตัวอย่างจาก prod: `created_at 2026-10-20T02:00:00.315Z` (09:00 ไทย), `sent_at 02:00:00.335Z` ห่างกัน 0.3 วินาที

ข้อจำกัด: ถ้าวันหนึ่งเปลี่ยน `REMINDER_CRON` ข้อมูลเก่าจะไม่มีบันทึกว่าตอนนั้นใช้เวลาไหน ทางแก้ในอนาคตคือให้ scheduler ส่ง `check_time` มาเก็บด้วย

---

## NFR-2 Response time

ทดสอบแล้วบน prod ด้วย k6 (50 users x 100 subscriptions, 50 VU 5 นาที) ไม่ต้องรันซ้ำ เพราะการยิง prod ต้องเตรียมหลายขั้นและกิน CPU credit ของ EC2 ถ้าจำเป็นต้องรันใหม่ ให้คนดูแล VM ทำตาม [README หัวข้อ Load test](../README.md#load-test-k6)

ดูผล: เปิดไฟล์ใน `tests/reports/` ด้วย browser (ไฟล์อยู่บนเครื่องที่รัน ไม่ได้อยู่ใน git ขอจากคนที่รัน)

| ไฟล์ | ใช้ตอบ |
|---|---|
| `load.html`, `load-summary.txt` | 2.1, 2.2 |
| `stress.html`, `stress-summary.txt` | ข้อมูลเสริม: ระบบทนได้แค่ไหน |

ผล

ผลรอบล่าสุด (2026-10-21)

- 2.1 ผ่าน: p95 list 298.16 ms, detail 294.61 ms, summary 295.48 ms (เกณฑ์ 2 วินาที)
- 2.2 ผ่าน: error 0% (0 จาก 17,223 request, เกณฑ์ไม่เกิน 1%)
- stress 300 VU: p95 307.13 ms, error 0 จาก 120,555 request (154 req/s)
- request ที่เร็วที่สุดใช้ประมาณ 280 ms ซึ่งเกือบทั้งหมดคือระยะทางเน็ตจากกรุงเทพฯ ไป Sydney ฝั่ง server ใช้ราว 10 ms

เช็คก่อนใช้: ใน `load.html` ค่า p95 ต้องประมาณ 295-298 ms ถ้าเห็นประมาณ 3 ms คือไฟล์ที่ซ้อมบน PC ไม่ใช่ของ prod

---

## NFR-3 Availability

### 3.1 uptime อย่างน้อย 99% (กำลังวัด)

มีหลักฐาน 2 ส่วน: ย้อนหลังจาก CloudWatch และวัดต่อจากนี้ด้วย UptimeRobot

#### ย้อนหลัง: CloudWatch StatusCheckFailed

**[browser]**

1. AWS Console เลือก region Sydney (ap-southeast-2)
2. CloudWatch → Metrics → All metrics → EC2 → Per-Instance Metrics → ติ๊ก `StatusCheckFailed` ของ instance prod
3. ช่วงเวลา Custom → Absolute `2026-10-09 00:00` ถึงวันที่ต้องการ เลือก UTC
4. แท็บ Graphed metrics: Statistic `Maximum`, Period `5 minutes`

ผ่านถ้าเส้นแบนที่ 0 ตลอด ต้องใช้ Maximum เพราะ Average จะกลบความล้มเหลวสั้น ๆ จนมองไม่เห็น

ผล 2026-11-02: 0 ตลอดตั้งแต่ 2026-10-09 19:20 UTC (เครื่องเริ่มทำงาน) ถึง 2026-11-01

ข้อจำกัด: วัดแค่ว่า AWS ติดต่อเครื่องได้ ไม่นับช่วงที่ reboot เอง ช่วง autodeploy สร้าง container ใหม่ หรือ service ข้างในล่มขณะที่เครื่องยังเปิด

#### ต่อจากนี้: UptimeRobot

ตั้ง monitor แล้วเมื่อ 2026-11-02 ประมาณ 08:08 เวลาไทย: HTTP(s) ยิง `https://subglutee.duckdns.org/healthz` ทุก 5 นาที (แผนฟรี) บัญชีอยู่กับคนที่ตั้ง ขอดูผลจากคนนั้น

**[browser]** อ่านผล

1. เข้า UptimeRobot → Monitoring → `subglutee.duckdns.org`
2. ดูการ์ด Last 7 days และ Last 30 days: ตัวเลข % คือ uptime และบรรทัดใต้ตัวเลขคือจำนวน incident กับเวลาที่ล่มรวม
3. ถ้า % ต่ำกว่า 99 ให้เลื่อนลงไปดูรายการ incident ว่าล่มช่วงไหน แล้วเทียบกับ autodeploy log หรือการ reboot

ผ่านถ้า uptime ในช่วงที่วัดได้ไม่ต่ำกว่า 99%

อ่านผลให้ถูก:

- นับเฉพาะช่วงหลังวันที่ตั้ง monitor ถึงแม้แถบ Last 24 hours จะขึ้นเขียวเต็มตั้งแต่วันแรกก็ตาม
- `/healthz` เป็น nginx ตอบเอง (`sgt-gateway/nginx.conf`) จึงวัดได้แค่ VM + Caddy + gateway ถ้า backend ตัวใดล่มแต่ nginx ยังอยู่ ตรงนี้จะยังเป็น Up
- response time ที่ UptimeRobot แสดงวัดจาก region Europe ไปถึง Sydney ใช้เทียบกับ NFR-2 ไม่ได้
- ช่วงที่วัดได้ก่อนนำเสนอมีแค่ไม่กี่วัน เกณฑ์ 99% ปกติวัดกันเป็นเดือน ให้บอกตรง ๆ ว่าเป็นผลเบื้องต้น

เช็คว่าตอนนี้ระบบตอบอยู่

**[PC cmd]**
```cmd
curl -s -o NUL -w "%{http_code}\n" https://subglutee.duckdns.org/healthz
```

ต้องได้ `200`

---

## NFR-4 Recoverability

### 4.1 backup ทุกวัน

backup รันเองทุกวัน 03:00 เวลาไทย เก็บ 7 ชุดล่าสุด

**[VM bash]**
```bash
systemctl list-timers sgt-backup.timer
ls ~/sgt-deploy/backups | tail -3
```

ผ่านเมื่อ

- คอลัมน์ `LAST` เป็นเมื่อไม่เกิน 24 ชั่วโมง และ `NEXT` เป็นภายใน 24 ชั่วโมงข้างหน้า (แสดงเป็น UTC: 20:00 UTC = 03:00 ไทย)
- มีโฟลเดอร์ชื่อวันล่าสุด เช่น `2026-11-01_200048`

ถ้าไม่ผ่าน: ดูสาเหตุด้วย `journalctl -u sgt-backup -n 20` แล้วส่งผลให้คนดูแล VM

ตรวจ 2026-11-02: LAST 2026-11-01 20:00 UTC มีครบทุกวัน

### 4.2 restore จาก backup ล่าสุดได้

ซ้อมบน PC เท่านั้น ข้อมูลใน DB ของ PC จะถูกแทนที่ด้วยข้อมูลจาก backup

1. ดึงชุด backup ล่าสุดจาก VM มาไว้ **นอกโฟลเดอร์ repo** (มีข้อมูลส่วนตัวผู้ใช้จริง ห้าม commit ห้ามแชร์)

   **[PC cmd]** แทน `<ชุด>` ด้วยชื่อโฟลเดอร์จาก 4.1 เช่น `2026-11-01_200048`
   ```cmd
   mkdir C:\sgt-restore-test
   scp -r -i <path ของ key.pem> ubuntu@subglutee.duckdns.org:/home/ubuntu/sgt-deploy/backups/<ชุด> C:\sgt-restore-test\
   ```

2. นับจำนวนแถวก่อน restore

   **[PC cmd]**
   ```cmd
   docker exec sgt-deploy-postgres-subscription-1 psql -U postgres -d subscriptions -tAc "SELECT count(*) FROM subscriptions"
   ```

3. restore

   **[PC cmd]**
   ```cmd
   docker exec -i sgt-deploy-postgres-subscription-1 pg_restore -U postgres -d subscriptions --clean --if-exists --no-owner < C:\sgt-restore-test\<ชุด>\subscriptions.dump
   docker exec -i sgt-deploy-mongo-1 mongorestore --archive --gzip --drop < C:\sgt-restore-test\<ชุด>\noti.archive.gz
   ```

4. นับอีกครั้งด้วยคำสั่งข้อ 2 ต้องได้เท่ากับจำนวนแถวบน prod ตอนที่ backup
5. ลบ `C:\sgt-restore-test` ทิ้งทันทีหลังซ้อม

ผลซ้อมเดิม: 5004/5004 แถว migration version ตรงกัน ใช้เวลา 4 วินาที

---

## NFR-5 Determinism

### 5.1 input เดิม ต้องได้ผลคำนวณเดิม

ทำไมผ่านในโค้ด: ยอดรวมต่อเดือนคำนวณใน SQL ทั้งหมด (`sgt-subscription-service/repositories/subscription.go` ฟังก์ชัน `Summary`) ราคาเก็บเป็น `NUMERIC(10,2)` ไม่ใช่ float ปัดเศษด้วย `ROUND(..., 2)` ใน Postgres และไม่มีค่าเวลาปัจจุบันเข้ามาเกี่ยว

1. ถ้า user ยังไม่มี subscription ให้เพิ่มผ่านหน้าเว็บ 2-3 รายการ ควรมีแบบรายปี 1 รายการ (ราคารายปีถูกหาร 12 เป็นจุดที่ทดสอบการปัดเศษ)
2. **[browser]** เปิด http://localhost:8000/home กด F12 > แท็บ Network > ช่อง Filter พิมพ์ `summary`
3. กด F5 3 ครั้ง คลิก request `summary` แต่ละอัน > แท็บ Response ต้องเหมือนกันทั้ง 3 เช่น `{"count":4,"monthlyCost":463}`
4. รัน SQL เดียวกับที่ service ใช้ 2 ครั้ง

   **[PC cmd]** แทน `<USER_ID>` (ต้องเป็น user ที่ login อยู่ในข้อ 2)
   ```cmd
   docker exec sgt-deploy-postgres-subscription-1 psql -U postgres -d subscriptions -tAc "SELECT COUNT(*), ROUND(COALESCE(SUM(CASE WHEN type = 'yearly' THEN cost / 12 ELSE cost END), 0), 2) FROM subscriptions WHERE user_id = '<USER_ID>' AND status IN ('active', 'free_trial')"
   ```

ผ่านเมื่อ API 3 ครั้งและ SQL 2 ครั้งได้ค่าเดียวกันหมด เช่น `4|463.00`

ถ้า SQL ได้ `0|0.00` แต่ API ไม่ใช่ 0: ใช้ `<USER_ID>` ผิดคน ดู user ทุกคนที่มีข้อมูล

**[PC cmd]**
```cmd
docker exec sgt-deploy-postgres-subscription-1 psql -U postgres -d subscriptions -tAc "SELECT user_id, COUNT(*) FROM subscriptions GROUP BY user_id"
```

ผลทดสอบ 2026-11-02: API `{"count":4,"monthlyCost":463}` 3 ครั้ง, SQL `4|463.00`

---

## NFR-6 Access control and data protection

### 6.1 HTTPS

**[PC cmd]**
```cmd
curl -sI http://subglutee.duckdns.org
curl -sI https://subglutee.duckdns.org | findstr /i strict
```

ผ่านเมื่อ

- คำสั่งแรกขึ้น `HTTP/1.1 308 Permanent Redirect` และ `Location: https://subglutee.duckdns.org/` (เข้าแบบ http จะถูกส่งไป https)
- คำสั่งที่สองขึ้น `strict-transport-security: max-age=31536000` (browser จะบังคับ https ต่อ 1 ปี)

ทำงานอย่างไร: Caddy บน VM ขอ certificate จาก Let's Encrypt เองและใส่ header ตาม `Caddyfile`

### 6.2 ไม่มี secret ใน source code และใน log

ส่วน source code

**[PC cmd]**
```cmd
git check-ignore .env
```

ต้องได้ `.env` แปลว่าไฟล์ที่มี secret ไม่ถูก commit secret ทุกตัวอ่านจาก environment variable

ส่วน log

**[VM bash]**
```bash
sudo journalctl -o cat --no-pager | grep -cE 'eyJ[A-Za-z0-9_-]{20,}|Bearer [A-Za-z0-9]|password=|JWT_SECRET|GOCSPX-'
```

ต้องได้ `0` (คำสั่งนี้นับอย่างเดียว ไม่พิมพ์บรรทัดที่เจอ กัน secret ขึ้นจอ ถ้าได้มากกว่า 0 อย่าเปิดดูเอง แจ้งคนดูแล VM)

ค้นหาอะไร: `eyJ...` = JWT token, `Bearer` = header ที่ส่ง token, `password=` และ `JWT_SECRET` = ชื่อตัวแปร secret, `GOCSPX-` = Google client secret

ข้อจำกัด: ตรวจได้เฉพาะรูปแบบที่รู้จัก ตรวจ 2026-11-02 ได้ 0

---

## NFR-7 PDPA

### 7.1 มีฐานทางกฎหมายในการเก็บข้อมูล และลบข้อมูลเมื่อผู้ใช้ลบบัญชี

ฐานทางกฎหมาย

**[browser]** เปิด https://subglutee.duckdns.org/privacy โดยไม่ต้อง login ต้องเห็นนโยบายความเป็นส่วนตัว

ลบข้อมูลเมื่อลบบัญชี (ทำบน PC ด้วยอีเมลที่ไม่เสียดายข้อมูล)

1. login ที่ http://localhost:8000 เพิ่ม subscription 1 รายการ แล้วจด `<USER_ID>` (ดู "ก่อนเริ่ม")
2. **[browser]** ไปหน้า Profile > กด Delete account > ยืนยัน
3. เช็คว่าไม่เหลือข้อมูล

   **[PC cmd]** แทน `<USER_ID>`
   ```cmd
   docker exec sgt-deploy-postgres-user-1 psql -U postgres -d users -tAc "SELECT count(*) FROM users WHERE id = '<USER_ID>'"
   docker exec sgt-deploy-postgres-subscription-1 psql -U postgres -d subscriptions -tAc "SELECT count(*) FROM subscriptions WHERE user_id = '<USER_ID>'"
   docker exec sgt-deploy-mongo-1 mongosh --quiet noti --eval "db.in_app_notifications.countDocuments({user_id: '<USER_ID>'})"
   docker logs sgt-deploy-noti-service-1 --since 5m | findstr user_deleted
   ```

ผ่านเมื่อ 3 บรรทัดแรกได้ `0` ทุกตัว และบรรทัดสุดท้ายไม่มีคำว่า `failed`

ทำงานอย่างไร: user-service ลบ user แล้วส่งข้อความ `user_deleted` เข้า RabbitMQ, noti-service รับแล้วลบการแจ้งเตือนในแอปและประวัติเมลของ user นั้น (`sgt-noti-service/consumer/user_deleted.go`)

---

## NFR-8 Usability (ผ่านแล้ว 2026-11-02)

**[browser]**

1. เปิด http://localhost:8000 แล้ว login กด F12 > ไอคอนมือถือ (Toggle device toolbar) > เลือก Responsive > ใส่ความกว้าง `360`
2. เปิดทุกหน้า: Login, Home (`/home`), Report (`/report`), Notifications (`/notifications`), Profile (`/profile`) รวมฟอร์มเพิ่ม/แก้ subscription
3. แต่ละหน้าเช็ค
   - 8.1 กด กรอก บันทึกได้ครบ
   - 8.2 ไม่มีช่องกรอกหรือปุ่มสำคัญถูกซ่อนหรือตกขอบ
   - 8.3 ไม่ต้องเลื่อนซ้ายขวา เช็คได้แน่นอนโดยพิมพ์ในแท็บ Console:

     ```js
     document.documentElement.scrollWidth <= window.innerWidth
     ```

     ต้องได้ `true`
4. แคปจอทุกหน้าไว้เป็นหลักฐาน

---

## NFR-9 Compatibility (ผ่านแล้ว 2026-11-02)

ทดสอบ flow หลักบนแต่ละ browser: login, เพิ่ม/แก้/ลบ subscription, ดู Home และ Report, เปิด Notifications, logout

| Browser | อุปกรณ์ | ผล |
|---|---|---|
| Chrome | Windows | ผ่าน |
| Edge | Windows | ผ่าน |
| Firefox | Windows | ผ่าน |
| Safari | iPhone (iOS) | ผ่าน |
| Safari | macOS | ไม่ได้ทดสอบ (ทีมไม่มี Mac) |

จดเวอร์ชัน browser ตอนทดสอบด้วย (Chrome/Edge: Settings > About, iPhone: Settings > General > About > iOS Version)

ข้อจำกัด: Safari บน iOS และ macOS ใช้ engine WebKit ตัวเดียวกัน แต่ยังไม่ได้ทดสอบบน Mac จริง

---

## NFR-10 Operational traceability

### 10.1, 10.3 รู้ว่า reminder ถูกสร้าง พยายามส่ง สำเร็จ หรือล้มเหลว และมีประวัติ retry

เก็บไว้ 2 ที่

- ถูกสร้าง: log ของ scheduler `reminder check: date=... due=... published=... failed=...`
- พยายามส่ง / สำเร็จ / ล้มเหลว: collection `email_logs` ใน Mongo DB `noti` การส่ง 1 ครั้ง = 1 document มี `reminder_id`, `status` (`sent` หรือ `failed`), `created_at`, `sent_at`

ดูภาพรวมบน prod

**[VM bash]**
```bash
docker exec sgt-deploy-mongo-1 mongosh --quiet noti --eval 'db.email_logs.aggregate([{$group:{_id:"$status",n:{$sum:1}}}]).toArray()'
journalctl CONTAINER_NAME=sgt-deploy-scheduler-1 --since "7 days ago" | grep "reminder check"
```

ทดสอบกรณีส่งไม่สำเร็จแล้ว retry (PC เท่านั้น ใช้ `REMINDER_CRON=@every 1m` จะง่ายที่สุด ดู 1.1 ข้อ 2)

1. ปิดกล่องเมลปลอม

   **[PC cmd]**
   ```cmd
   docker stop sgt-deploy-mailhog-1
   ```

2. สร้าง reminder ใหม่ 1 รายการชื่อ `nfr11-fail`

   **[PC cmd]** แทน `<USER_ID>`
   ```cmd
   docker exec sgt-deploy-postgres-subscription-1 psql -U postgres -d subscriptions -c "INSERT INTO subscriptions (user_id, name, cost, type, category, next_billing_date, billing_day, reminder_time_in_advanced, status) SELECT '<USER_ID>', 'nfr11-fail', 100, 'monthly', 'streaming', (((now() AT TIME ZONE 'Asia/Bangkok')::date + 1)::timestamp AT TIME ZONE 'Asia/Bangkok'), EXTRACT(DAY FROM (now() AT TIME ZONE 'Asia/Bangkok')::date + 1)::smallint, 1, 'active'"
   ```

3. รอให้ scheduler รัน (ไม่เกิน 1 นาที) แล้วรออีกประมาณ 10-30 วินาที จากนั้นเปิดกล่องเมลกลับ

   **[PC cmd]**
   ```cmd
   docker start sgt-deploy-mailhog-1
   ```

4. ดูทุกครั้งที่พยายามส่งของ reminder นี้

   **[PC cmd]**
   ```cmd
   docker exec sgt-deploy-mongo-1 mongosh --quiet noti --eval "db.email_logs.aggregate([{$match: {created_at: {$gte: new Date(Date.now() - 600000)}, status: {$in: ['failed', 'sent']}}}, {$group: {_id: {r: '$reminder_id', s: '$status'}, n: {$sum: 1}, first: {$min: '$created_at'}, last: {$max: '$created_at'}}}, {$sort: {first: 1}}]).toArray()"
   docker logs sgt-deploy-noti-service-1 --since 10m | findstr "send failed"
   ```

   ผ่านเมื่อ `reminder_id` เดียวกันมีทั้ง `failed` (หลายครั้ง) และ `sent` 1 ครั้งที่เวลาหลังสุด

5. cleanup ด้วยคำสั่งเดียวกับ 1.1 (`DELETE ... LIKE 'nfr11-%'`)

ถ้าไม่เห็น `failed`: mailhog ถูกเปิดกลับเร็วเกินไป หรือ scheduler ยังไม่รัน ทำข้อ 1-4 ใหม่ด้วยชื่ออื่น เช่น `nfr11-fail2`

ผลทดสอบ 2026-11-02: `failed` 11 ครั้ง (05:07:12 ถึง 05:07:44, error `lookup mailhog ... no such host`) แล้ว `sent` 1 ครั้งตอน 05:07:47 หลังเปิด mailhog

ข้อสังเกต (ใส่ใน risk matrix): ในโค้ดไม่มีการรอระหว่าง retry (`Nack` แล้วเข้าคิวใหม่ทันที) รอบนี้ห่างกันราว 3 วินาทีเพราะการหา DNS ที่ล้มใช้เวลาเอง ถ้า mail server ตอบ error ทันที จะวนถี่กว่านี้มาก

### 10.2 เก็บ check time และเวลาที่ mail server รับ ของแต่ละ reminder

ใช้วิธีเดียวกับ 1.2 และมีข้อจำกัดเดียวกัน

### 10.4 เก็บ log อย่างน้อย 90 วัน

log ของทุก container บน prod ถูกส่งเข้า journald ของ VM ตั้งให้เก็บ 100 วัน หรือไม่เกิน 4 GB

**[VM bash]**
```bash
cat /etc/systemd/journald.conf.d/journald-sgt.conf
journalctl --disk-usage
journalctl -o short-iso --no-pager | head -1
```

ผ่านเมื่อ

- บรรทัดแรกเห็น `MaxRetentionSec=100day` และ `SystemMaxUse=4G`
- บรรทัดที่สองไม่เกิน 4G (ตรวจ 2026-11-02: 1.2G)
- บรรทัดสุดท้ายคือวันที่ของ log เก่าสุดที่ยังอยู่

ข้อจำกัด: ถ้าใช้ครบ 4 GB ก่อน 100 วัน log เก่าจะถูกลบก่อน คนดูแล VM ควรเช็ค `df -h` และ `journalctl --disk-usage` เดือนละครั้ง

### 10.5 ไม่บันทึกเนื้อหาเมลเต็ม

- โค้ด: `sgt-noti-service/models/email_notification.go` มีแค่ `ReminderID`, `To`, `Title`, `Status`, `CreatedAt`, `SentAt` ไม่มีเนื้อหาเมล
- ข้อมูลจริง

  **[VM bash]**
  ```bash
  docker exec sgt-deploy-mongo-1 mongosh --quiet noti --eval 'db.email_logs.countDocuments({content: {$exists: true}})'
  ```

  ต้องได้ `0`
- log ของ noti มีแค่ `reminder_id` และข้อความ error ไม่มีเนื้อหาเมล
