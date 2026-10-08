.PHONY: up up-dev down check logs

COMPOSE = docker compose --env-file versions.dev.env --env-file .env
DEV = $(COMPOSE) -f docker-compose.yaml -f docker-compose.tools.yaml
LOCAL = $(DEV) -f docker-compose.local.yaml
CHECK = docker compose --env-file versions.dev.env --env-file .env.example

up:
	$(LOCAL) up -d --build

up-dev:
	$(DEV) up -d --pull always

down:
	$(LOCAL) down -v

check:
	$(CHECK) -f docker-compose.yaml config -q
	$(CHECK) -f docker-compose.yaml -f docker-compose.tools.yaml config -q
	$(CHECK) -f docker-compose.yaml -f docker-compose.tools.yaml -f docker-compose.local.yaml config -q

logs:
	$(LOCAL) logs -f
