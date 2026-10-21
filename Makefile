# Template-repo dev targets (not shipped: copier only renders template/<component>/).
OUT ?=
REPOS ?= backend frontend mobile

.PHONY: test test-template

test:
	uv run --with pytest --with pyyaml pytest tests/

# Generate the workspace from this checkout into a scratch dir and run each repo's `make check`.
# Nested component copies pin the committed _commit, so the tree must be committed first.
test-template:
	@if ! git -C "$(CURDIR)" diff --quiet HEAD || [ -n "$$(git -C "$(CURDIR)" ls-files --others --exclude-standard)" ]; then \
	  echo "ERROR: commit all changes first; nested copies use the committed _commit" >&2; exit 1; \
	fi
	@set -e; \
	out="$(OUT)"; [ -n "$$out" ] || out=$$(mktemp -d); \
	copier copy --trust --defaults --vcs-ref HEAD -d project_name="Test App" "$(CURDIR)" "$$out/app"; \
	for d in app app/backend app/frontend app/mobile; do \
	  [ -d "$$out/$$d/.git" ] || { echo "ERROR: missing $$out/$$d/.git" >&2; exit 1; }; \
	  [ -f "$$out/$$d/.copier-answers.yml" ] || { echo "ERROR: missing $$out/$$d/.copier-answers.yml" >&2; exit 1; }; \
	done; \
	for r in $(REPOS); do \
	  if [ ! -f "$$out/app/$$r/Makefile" ]; then echo "skip: $$r/Makefile absent"; continue; fi; \
	  if [ "$$r" = mobile ] && ! command -v flutter >/dev/null 2>&1; then echo "skip: mobile (flutter not on PATH)"; continue; fi; \
	  $(MAKE) -C "$$out/app/$$r" check; \
	done; \
	$(MAKE) -C "$$out/app" -n check >/dev/null; \
	echo "OUT=$$out"
