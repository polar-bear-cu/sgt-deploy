.PHONY: up down check logs

up:
	docker compose up -d --build

down:
	docker compose down -v

check:
	docker compose config -q

logs:
	docker compose logs -f
