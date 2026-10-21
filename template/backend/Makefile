.PHONY: dev lint fmt test check

dev:
	uv run uvicorn app.main:create_app --factory --reload --port 8000

lint:
	uv run ruff check . && uv run ruff format --check . && uv run ty check

fmt:
	uv run ruff format . && uv run ruff check --fix .

test:
	uv run pytest

check: lint test
