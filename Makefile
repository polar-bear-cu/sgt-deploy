.PHONY: up up-dev down check logs

DEV = docker compose --env-file versions.dev.env --env-file .env
LOCAL = $(DEV) -f docker-compose.yaml -f docker-compose.local.yaml
CHECK = docker compose --env-file versions.dev.env --env-file .env.example

up:
	$(LOCAL) up -d --build

up-dev:
	$(DEV) up -d --pull always

down:
	$(LOCAL) down -v

check:
	$(CHECK) config -q
	$(CHECK) -f docker-compose.yaml -f docker-compose.local.yaml config -q

logs:
	$(LOCAL) logs -f
