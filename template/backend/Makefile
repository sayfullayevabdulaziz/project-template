.PHONY: dev lint fmt test check openapi up down migrate migration create-admin

dev:
	uv run uvicorn app.main:create_app --factory --reload --port 8000

lint:
	uv run ruff check . && uv run ruff format --check . && uv run ty check

fmt:
	uv run ruff format . && uv run ruff check --fix .

test:
	uv run pytest

check: lint test

openapi:
	uv run python scripts/export_openapi.py

up:
	docker compose up -d --build --wait

down:
	docker compose down

migrate:
	uv run alembic upgrade head

migration:
	$(if $(m),,$(error m is required: make migration m="message"))
	uv run alembic revision --autogenerate -m "$(m)"

create-admin:
	docker compose run --rm api create-admin $(ARGS)
