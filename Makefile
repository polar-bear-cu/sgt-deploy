.PHONY: up up-dev up-prod-smoke up-prod down down-prod-smoke down-prod clean check logs logs-prod loadtest

COMPOSE = docker compose --env-file versions.dev.env --env-file .env
DEV = $(COMPOSE) -f docker-compose.yaml -f docker-compose.tools.yaml
LOCAL = $(DEV) -f docker-compose.local.yaml
SMOKE = docker compose -p sgt-prod-smoke --env-file versions.prod.env --env-file .env -f docker-compose.yaml -f docker-compose.smoke.yaml
PROD_VERSIONS ?= versions.prod.env
PROD = docker compose --env-file $(PROD_VERSIONS) --env-file .env -f docker-compose.yaml -f docker-compose.prod.yaml
CHECK = docker compose --env-file versions.dev.env --env-file .env.example
CHECK_PROD = docker compose --env-file versions.prod.env --env-file .env.example
BASE_URL ?= http://host.docker.internal:8000
T ?= smoke
K6 = docker run --rm -v "$(CURDIR)/tests:/scripts" -e BASE_URL=$(BASE_URL) grafana/k6:2.3.0

export MSYS_NO_PATHCONV := 1

up:
	$(LOCAL) up -d --build

up-dev:
	$(DEV) up -d --pull always

up-prod-smoke:
	$(SMOKE) up -d --pull always

up-prod:
	$(PROD) up -d --pull always

down:
	$(LOCAL) down

down-prod-smoke:
	$(SMOKE) down

down-prod:
	$(PROD) down

clean:
	$(LOCAL) down -v

check:
	$(CHECK) -f docker-compose.yaml config -q
	$(CHECK) -f docker-compose.yaml -f docker-compose.tools.yaml config -q
	$(CHECK) -f docker-compose.yaml -f docker-compose.tools.yaml -f docker-compose.local.yaml config -q
	$(CHECK_PROD) -f docker-compose.yaml -f docker-compose.smoke.yaml config -q
	$(CHECK_PROD) -f docker-compose.yaml -f docker-compose.prod.yaml config -q

logs:
	$(LOCAL) logs -f

logs-prod:
	$(PROD) logs -f

loadtest:
	$(K6) run /scripts/$(T).ts