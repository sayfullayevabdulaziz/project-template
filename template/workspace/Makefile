REPOS := backend frontend mobile
ADMIN_SPEC := backend/openapi/admin.json
PUBLIC_SPEC := backend/openapi/public.json
# One variable per client: which backend surface spec it consumes.
FRONTEND_SPEC_SRC := $(ADMIN_SPEC)
MOBILE_SPEC_SRC := $(PUBLIC_SPEC)

.PHONY: up down sync-api check check-specs

up:
	docker compose up -d

down:
	docker compose down

sync-api:
	@if [ -f "backend/Makefile" ]; then $(MAKE) -C "backend" openapi; else echo "skip: backend/Makefile absent"; fi
	@if [ -f "frontend/Makefile" ]; then cp "$(FRONTEND_SPEC_SRC)" "frontend/openapi.json" && $(MAKE) -C "frontend" gen-api; else echo "skip: frontend/Makefile absent"; fi
	@if [ -f "mobile/Makefile" ]; then cp "$(MOBILE_SPEC_SRC)" "mobile/openapi.json" && $(MAKE) -C "mobile" gen-api; else echo "skip: mobile/Makefile absent"; fi

check-specs:
	@rc=0; \
	for pair in "frontend:$(FRONTEND_SPEC_SRC)" "mobile:$(MOBILE_SPEC_SRC)"; do \
	  c=$${pair%%:*}; src=$${pair#*:}; \
	  if [ -f "$$src" ] && [ -f "$$c/openapi.json" ] && ! cmp -s "$$src" "$$c/openapi.json"; then \
	    echo "stale client: $$c/openapi.json differs from $$src; run make sync-api"; rc=1; \
	  fi; \
	done; \
	exit $$rc

check: check-specs
	@for r in $(REPOS); do \
	  if [ -f "$$r/Makefile" ]; then $(MAKE) -C "$$r" check || exit 1; else echo "skip: $$r/Makefile absent"; fi; \
	done
