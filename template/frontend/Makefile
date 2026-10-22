.PHONY: dev test lint fmt gen-api check

dev:
	@pnpm dev

test:
	pnpm test

lint:
	pnpm lint

fmt:
	pnpm fmt

gen-api:
	pnpm gen-api

check: lint
	pnpm typecheck
	pnpm test
	pnpm build
