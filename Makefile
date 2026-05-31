.PHONY: up down up-prod build logs shell-backend shell-db shell-cache migrate dev-reset pnpm-install vps-pull \
        frontend-install frontend-add frontend-add-dev frontend-remove frontend-shell

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

up-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

down-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

vps-pull:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --remove-orphans

migrate:
	docker compose exec -T backend alembic upgrade head

dev-reset:
	docker compose down -v
	docker compose build
	docker compose up -d
	@echo "Esperando que la DB esté lista..."
	@until docker compose exec -T db pg_isready -U $${POSTGRES_USER:-arbitrage_user} > /dev/null 2>&1; do sleep 1; done
	@echo "Esperando que el backend esté listo..."
	@until docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" > /dev/null 2>&1; do sleep 2; done
	$(MAKE) migrate

pnpm-install:
	docker run --rm \
		-v "$(shell pwd)/frontend/package.json:/work/package.json:ro" \
		-v "$(shell pwd)/frontend/pnpm-workspace.yaml:/work/pnpm-workspace.yaml:ro" \
		-v "pnpm-work-modules:/work/node_modules" \
		-v "$(shell pwd)/frontend:/out" \
		node:26.2.0-alpine3.23 \
		sh -c "cd /work && npm install -g pnpm --quiet 2>/dev/null && pnpm install && cp pnpm-lock.yaml /out/ && chown $(shell id -u):$(shell id -g) /out/pnpm-lock.yaml"
	docker volume rm pnpm-work-modules 2>/dev/null || true

frontend-install:
	docker compose exec frontend pnpm install

frontend-add:
	@test -n "$(PKG)" || (echo "Uso: make frontend-add PKG=nombre-paquete" && exit 1)
	docker compose exec frontend pnpm add $(PKG)

frontend-add-dev:
	@test -n "$(PKG)" || (echo "Uso: make frontend-add-dev PKG=nombre-paquete" && exit 1)
	docker compose exec frontend pnpm add -D $(PKG)

frontend-remove:
	@test -n "$(PKG)" || (echo "Uso: make frontend-remove PKG=nombre-paquete" && exit 1)
	docker compose exec frontend pnpm remove $(PKG)

frontend-shell:
	docker compose exec frontend sh

shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec db psql -U $${POSTGRES_USER:-arbitrage_user} -d $${POSTGRES_DB:-arbitrage_db}

shell-cache:
	docker compose exec cache redis-cli
