# Diagrams

โค้ด Mermaid ของ diagram ในสไลด์ final วางลงใน https://mermaid.live แล้ว export เป็น PNG หรือ SVG ไปแปะในช่อง `[รูป: ...]` ของสไลด์

C4 Level 2 ใช้ภาพ architecture เดิมจากสไลด์ Deli 5

## use-cases

Use case diagram (Mermaid ไม่มี use case diagram โดยตรง จึงใช้ flowchart และวงรีแทน)

```mermaid
flowchart LR
    user(["User"])
    admin(["Admin"])
    google["Google OAuth"]
    mail["Email provider"]

    subgraph sys["Sub Glu Tee"]
        direction TB
        uc1(["UC1 Login ด้วย Google"])
        uc2(["UC2 จัดการ subscription"])
        uc3(["UC3 ดู Dashboard / Report"])
        uc4(["UC4 รับแจ้งเตือนก่อนตัดเงิน"])
        uc5(["ลบบัญชี (PDPA)"])
        uc6(["จัดการ role ผู้ใช้"])
    end

    user --- uc1 & uc2 & uc3 & uc4 & uc5
    admin --- uc1 & uc6
    uc1 --- google
    uc4 --- mail
```

## c4-l1

C4 Level 1: System Context

```mermaid
flowchart TB
    user["User<br/>ติดตาม subscription ดูค่าใช้จ่าย รับแจ้งเตือน"]
    admin["Admin<br/>ดูผู้ใช้และกำหนด role"]
    sgt["Sub Glu Tee<br/>[Software System]<br/>จัดการ subscription และแจ้งเตือนก่อนวันตัดเงิน"]
    google["Google OAuth<br/>[External System]<br/>ยืนยันตัวตน"]
    mail["Email provider (SMTP)<br/>[External System]<br/>ตอนนี้ใช้ MailHog"]

    user -- "ใช้งานผ่าน browser (HTTPS)" --> sgt
    admin -- "ใช้งานผ่าน browser (HTTPS)" --> sgt
    sgt -- "OAuth 2.0 login" --> google
    sgt -- "ส่งเมลแจ้งเตือน (SMTP)" --> mail
    mail -- "ส่งเมล" --> user

    classDef system fill:#7a2020,color:#f6f1e8,stroke:#7a2020
    classDef external fill:#e9dcc9,color:#2b2420,stroke:#a4524a
    classDef person fill:#fbf8f2,color:#2b2420,stroke:#2b2420
    class sgt system
    class google,mail external
    class user,admin person
```

## c4-l3

C4 Level 3: Component ของ subscription-service

```mermaid
flowchart TB
    gw["nginx API Gateway"]
    sched["scheduler<br/>ListDueReminders<br/>AdvanceBillingDates"]
    report["report-service<br/>GetSubscriptionsForReport"]
    usersvc["user-service<br/>DeleteSubscriptionsByUser"]
    db[("postgres-subscription")]

    subgraph svc["subscription-service"]
        direction LR
        routes["routes + JWT middleware<br/>(gin)"]
        ctl["SubscriptionController<br/>REST handlers"]
        grpcsrv["gRPC server<br/>SubscriptionService"]
        uc["SubscriptionUsecase<br/>business rules"]
        repo["SubscriptionRepository<br/>(interface)"]
        pg["SubscriptionPostgres<br/>SQL"]
        routes --> ctl
        ctl --> uc
        grpcsrv --> uc
        uc --> repo
        repo -. implemented by .-> pg
    end

    gw -- "REST /api/v1/subscriptions" --> routes
    sched -- "gRPC" --> grpcsrv
    report -- "gRPC" --> grpcsrv
    usersvc -- "gRPC" --> grpcsrv
    pg -- "pgx" --> db
```

## c4-l4

C4 Level 4: Code ของ use case สรุปค่าใช้จ่ายรายเดือน (`GET /api/v1/subscriptions/summary`)

```mermaid
classDiagram
    direction LR
    class SubscriptionController {
        -uc *SubscriptionUsecase
        +GetSummary(c *gin.Context)
    }
    class SubscriptionUsecase {
        -repo SubscriptionRepository
        -loc *time.Location
        +Summary(ctx, userID) SubscriptionSummary
    }
    class SubscriptionRepository {
        <<interface>>
        +Create(ctx, s) Subscription
        +FindByID(ctx, id, userID) Subscription
        +List(ctx, userID, p) []Subscription
        +Summary(ctx, userID) SubscriptionSummary
        +ListDueReminders(ctx, date) []DueReminder
    }
    class SubscriptionPostgres {
        -db *pgxpool.Pool
        +Summary(ctx, userID) SubscriptionSummary
    }
    class SubscriptionSummary {
        +Count int
        +MonthlyCost float64
    }

    SubscriptionController --> SubscriptionUsecase
    SubscriptionUsecase --> SubscriptionRepository
    SubscriptionRepository <|.. SubscriptionPostgres
    SubscriptionPostgres ..> SubscriptionSummary : returns
```

ใน `SubscriptionPostgres.Summary` ยอดรวมคำนวณใน SQL: `ROUND(SUM(CASE WHEN type = 'yearly' THEN cost / 12 ELSE cost END), 2)` บนคอลัมน์ `NUMERIC(10,2)`

## seq-login

```mermaid
sequenceDiagram
    autonumber
    actor U as User (browser)
    participant GW as nginx gateway
    participant A as auth-service
    participant G as Google OAuth
    participant US as user-service

    U->>GW: GET /api/v1/auth/google/login
    GW->>A: forward
    A-->>U: 302 ไป Google (พร้อม state cookie)
    U->>G: login + consent
    G-->>U: 302 กลับ /api/v1/auth/google/callback?code=...
    U->>GW: GET callback
    GW->>A: forward
    A->>G: แลก code เป็น profile
    G-->>A: email, google_sub
    A->>US: FindOrCreateUser (gRPC)
    US-->>A: user_id, role
    A-->>U: 302 ไป /auth/callback#35;access_token=... + Set-Cookie refresh token (HttpOnly)
    U->>GW: API request + Authorization: Bearer JWT
    Note over GW,US: แต่ละ service ตรวจ JWT เอง
```

## seq-reminder

```mermaid
sequenceDiagram
    autonumber
    participant S as scheduler (cron 09:00)
    participant SUB as subscription-service
    participant USR as user-service
    participant MQ as RabbitMQ
    participant N as noti-service
    participant DB as MongoDB (noti)
    participant M as SMTP (MailHog)

    S->>SUB: ListDueReminders(date) (gRPC)
    SUB-->>S: reminders ที่ครบกำหนด
    loop ทุก reminder
        S->>USR: GetUser(user_id) (gRPC)
        USR-->>S: email
        S->>MQ: publish email_notifications (reminder_id)
    end
    MQ->>N: deliver
    N->>DB: เช็ค reminder_id เคยส่งแล้วหรือยัง
    alt ส่งแล้ว
        N-->>MQ: Ack (ข้าม)
    else ยังไม่ส่ง
        N->>DB: บันทึก in_app_notifications
        N->>M: ส่งเมล
        alt สำเร็จ
            N->>DB: email_logs status=sent, sent_at
            N-->>MQ: Ack
        else ล้มเหลว
            N->>DB: email_logs status=failed
            N-->>MQ: Nack (requeue) แล้วลองใหม่
        end
    end
```

## deployment

Deployment Overview: EC2 เครื่องเดียว รันทุก container ด้วย Docker Compose

```mermaid
flowchart LR
    browser(["Browser"])
    google["Google OAuth"]
    ghcr["GitHub CI + GHCR<br/>image tag = commit sha"]

    subgraph ec2["AWS EC2 t3.small (Sydney) + Elastic IP: รันทุก container ด้วย Docker Compose"]
        direction LR
            caddy["Caddy<br/>HTTPS + HSTS"]
            gateway["nginx<br/>API Gateway"]
            envoy["Envoy<br/>gRPC-web"]
            frontend["frontend"]
            services["6 services<br/>auth, user, subscription,<br/>report, noti, scheduler<br/>(คุยกันด้วย gRPC)"]
            mq["RabbitMQ"]
            data[("PostgreSQL x3<br/>MongoDB")]
            mail["MailHog<br/>(SMTP)"]
        systemd["systemd timers<br/>autodeploy ทุก 2 นาที<br/>backup ทุกวัน 03:00"]
    end

    browser -- "HTTPS<br/>subglutee.duckdns.org" --> caddy
    caddy --> gateway
    gateway --> frontend
    gateway -- "REST" --> services
    gateway -- "gRPC-web" --> envoy
    envoy -- "gRPC" --> services
    services <--> mq
    services --> data
    services --> mail
    services -- "OAuth 2.0" --> google
    ghcr -. "pull image" .-> systemd

    classDef system fill:#7a2020,color:#f6f1e8,stroke:#7a2020
    classDef external fill:#e9dcc9,color:#2b2420,stroke:#a4524a
    classDef plain fill:#fbf8f2,color:#2b2420,stroke:#2b2420
    class caddy,gateway system
    class google,ghcr external
    class browser,frontend,envoy,services,mq,data,mail,systemd plain
    style ec2 fill:#fbf8f2,stroke:#7a2020
```
