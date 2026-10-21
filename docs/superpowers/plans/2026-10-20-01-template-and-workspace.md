# Template Mechanics and Workspace Root Implementation Plan (plan 01 of 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Copier template shell (`copier.yml`, per-component answers files, template README/Makefile/CI, pytest suite) and the full `template/workspace/` component, so `copier copy` produces a workspace plus nested component repos.

**Architecture:** One Copier template; `_subdirectory: "template/{{ component }}"` selects the component. The workspace component runs nested `copier copy` per component from the committed `_src_path`/`_commit`. Every task is gated on `_copier_operation == 'copy'`. Behavior is tested by pytest driving `copier` via subprocess against throwaway git copies of the template (so injected junk and stub Makefiles never touch the real tree).

**Tech Stack:** Copier 9.19, Jinja, GNU make, bash, jq-or-python3, pytest (run with `uv run --with pytest --with pyyaml pytest tests/`), GitHub Actions.

**Spec:** `/Users/abdulaziz/Code/project-template/docs/superpowers/specs/2026-10-20-project-template-design.md` (sections 5, 6.1, 6.2, 6.7, 6.8, 6.10, 8, 9). Other plans: 02 backend, 03 admin, 04 mobile; execution order 01, then 02, then 03 and 04. This plan must work while component dirs hold only their answers file.

## Global Constraints

- Template root `/Users/abdulaziz/Code/project-template` is not a git repo and has no `copier`. `git init` and every commit need user approval ("No scaffolding, installs, or code until the user approves"); `uv tool install copier` needs approval. Do not install Flutter.
- `_subdirectory: "template/{{ component }}"`; each `template/<component>/` has its own `{{ _copier_conf.answers_file }}.jinja`.
- Every `_tasks` entry has `when: "{{ _copier_operation == 'copy' }}"` (tasks run up to 3x on update).
- Nested copies: `{{ _copier_python }} -m copier copy --trust --defaults --vcs-ref {{ _copier_answers._commit }} -d component=<c> -d project_name=… -d project_slug=… -d project_description=… -d org_domain=… -d author_name=… -d author_email=… {{ _copier_answers._src_path }} <c>`. Never `_copier_conf.src_path`. Fail fast if `_copier_answers._src_path` is relative.
- Mobile: run `make bootstrap` only if `flutter` is on PATH, else print a warning to run `make bootstrap` later. Other components unaffected.
- `_message_after_update` reminds to re-lock (`uv lock` / `pnpm install` / `flutter pub get`). No lockfiles shipped.
- `_exclude` keeps out: `.venv`, `node_modules`, `uv.lock`, `pnpm-lock.yaml`, `pubspec.lock`, `.dart_tool`, `build`, `dist`, caches. Only files needing answers get `.jinja`.
- Marker lines exactly: `<!-- project-context:start -->`, `<!-- project-context:end -->`, `<!-- claude-tools:start -->`, `<!-- claude-tools:end -->`.
- Each repo's `.claude/hooks/format.sh` reads hook JSON on stdin; root `format-dispatch.sh` passes the same stdin to `<repo>/.claude/hooks/format.sh`; always exit 0; prefer `jq`, else `python3`.
- Root `Makefile` targets: `up`, `down`, `sync-api`, `check`. Per-repo targets: `dev|test|lint|fmt|check`; clients add `gen-api`; backend adds `openapi`, `up`, `down`, `migrate`, `migration`, `create-admin`; mobile adds `bootstrap`.
- `sync-api`: `make -C backend openapi`; copy `backend/openapi/admin.json` to `frontend/openapi.json` and `backend/openapi/public.json` to `mobile/openapi.json` (surface-to-client mapping = one variable per client); run each client's `make gen-api`.
- Ports: API 8000, admin dev 5173. Admin dev container (spec 5 item 17): `node` running `pnpm dev --host`, repo bind-mounted.
- AGENTS.md ~100 to 150 lines; order: project-context block, Stack, Commands, Architecture map, Conventions, Testing, Definition of done, Never list. CLAUDE.md = `@AGENTS.md` + `claude-tools` block.
- Conventional Commits. Commit paths are relative to the template repo root. Commits only after user approval (Task 1).

## Review Focus

1. `project_name` with apostrophes/quotes/unicode/spaces (`O'Brien's Shop`, `Café 2024`): slug and nested `-d` args must survive; test in Task 4.
2. Destination path containing spaces: nested copies and `make` recipes must quote paths; test in Task 4.
3. No global git identity (empty `HOME`, `GIT_CONFIG_GLOBAL=/dev/null`): initial commits must still succeed (identity comes from `-c user.name/user.email` using answers); test in Task 3.
4. Dirty or uncommitted template repo when running `make test-template`: refuse with a clear message instead of silently testing stale `HEAD`; test in Task 9.
5. `copier update` at workspace level must not touch nested repos' files, and a `project-context` block filled by the user survives; tests in Task 5 and Task 10.

---

### Task 1: Approval gate, repo init, pytest harness

**Files:**
- Create: `.gitignore`, `tests/conftest.py`, `tests/test_harness.py`
- Create (empty placeholders so `template/<c>/` exist): none yet (Task 2 adds answers files)

**Interfaces:**
- Produces (`tests/conftest.py`):
  - `REPO: Path` repo root.
  - `COMMON_ANSWERS: dict[str,str]` = `project_name="Acme Shop"`, `project_slug="acme-shop"`, `project_description="Demo"`, `org_domain="com.example"`, `author_name="Ada Dev"`, `author_email="ada@example.com"`.
  - `make_template(tmp_path: Path, overlay: dict[str,str] | None = None, tag: str | None = None) -> Path`: copies `copier.yml` + `template/` (skipping `.venv`, `node_modules`, `__pycache__`) to `tmp_path/"tpl"`, writes `overlay` (relative path -> text; applied after copy), `git init -b main`, commits with `-c user.name=t -c user.email=t@t`, optional `git tag`; returns the absolute path.
  - `run_copier(args: list[str], cwd: Path, path_prepend: list[Path] | None = None, no_git_identity: bool = True) -> subprocess.CompletedProcess` (text, captured; env has `HOME=<tmp>`, `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null` when `no_git_identity`; PATH prepended).
  - `generate(tpl: Path, dest: Path, component: str = "workspace", extra: dict[str,str] | None = None, **kw) -> CompletedProcess`: `copier copy --trust --defaults --vcs-ref HEAD` + `-d k=v` for `COMMON_ANSWERS | {"component": component} | extra`.
  - fixture `ws(tmp_path_factory)` session-scoped: `generate()` of a pristine `make_template()` into a tmp dir; returns generated workspace `Path`.

- [ ] **Step 1: Ask the user for approval** to (a) `git init` the template repo and commit per task, (b) `uv tool install copier`. Do not proceed to step 2 without a yes. If commits are declined, skip every "Commit" step in this plan and leave work uncommitted (note: `make test-template` then cannot run, since it needs a committed tree).
- [ ] **Step 2: `git init -b main` in `/Users/abdulaziz/Code/project-template`; `uv tool install copier`; verify `copier --version` prints 9.x.** Re-check Copier version and that task `when:` plus `regex_replace` filter exist (verify at build start).
- [ ] **Step 3: Write failing test** `tests/test_harness.py::test_make_template_is_a_git_repo_with_tag`: `make_template(tmp_path, overlay={"template/x/f.txt":"hi"}, tag="v0.1.0")` -> `git -C tpl describe --tags` == `v0.1.0`, and `tpl/template/x/f.txt` reads `hi`.
- [ ] **Step 4: Run** `uv run --with pytest --with pyyaml pytest tests/test_harness.py -v`. Expected: FAIL (conftest missing).
- [ ] **Step 5: Implement `tests/conftest.py`** per Interfaces. `.gitignore`: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.DS_Store`.
- [ ] **Step 6: Run again.** Expected: PASS.
- [ ] **Step 7: Commit** `git add .gitignore tests docs && git commit -m "chore: init template repo and pytest harness"`.

---

### Task 2: `copier.yml` questions, `_exclude`, answers files

**Files:**
- Create: `copier.yml`, `template/{workspace,backend,frontend,mobile}/{{ _copier_conf.answers_file }}.jinja`
- Test: `tests/test_questions.py`

**Interfaces:**
- Produces: questions `component` (choices workspace|backend|frontend|mobile, default `workspace`), `project_name` (default `My App`), `project_slug`, `package_name`, `project_description`, `org_domain` (default `com.example`), `author_name`, `author_email`. All have defaults so `--defaults` works. Component-specific questions use `when: "{{ component == '<c>' }}"`; none are needed in plan 01 (plans 02-04 may add; convention documented in a `copier.yml` comment).
- `project_slug` and `package_name` are ordinary questions with derived `default` (NOT `when: false`), because `when: false` answers are not written to the answers file and cannot be overridden by `-d`; acceptance 1 requires `project_slug` recorded. Slug default: `{{ project_name | lower | regex_replace('[^a-z0-9]+','-') | trim('-') }}`; `package_name` default `{{ project_slug | replace('-','_') }}`. Validators: `project_slug` matches `^[a-z][a-z0-9-]*$` (valid kebab, valid Dart package after `-`->`_`), `org_domain` matches `^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*)+$` (reverse DNS). Error text must name the field.
- `_subdirectory: "template/{{ component }}"`. `_exclude` (replaces Copier defaults, so repeat `.git`, `.DS_Store`): `.git`, `.DS_Store`, `.venv`, `node_modules`, `uv.lock`, `pnpm-lock.yaml`, `pubspec.lock`, `.dart_tool`, `build`, `dist`, `__pycache__`, `*.pyc`, `.pytest_cache`, `.ruff_cache`, `.ty_cache` (verify ty cache dir name), `.mypy_cache`, `coverage`.
- Answers file `.jinja` content in each dir: `{{ _copier_answers|to_nice_yaml -}}` (standard Copier idiom).

- [ ] **Step 1: Write failing tests**
  - `test_workspace_answers_file_records_component_and_shared_answers`: `generate(make_template(tmp_path), dest)`; load `dest/.copier-answers.yml`; assert `component == "workspace"` and all six `COMMON_ANSWERS` keys equal; `package_name == "acme_shop"`; `_src_path` is absolute (`Path(v).is_absolute()`).
  - `test_each_component_answers_file_has_its_component` (parametrized backend/frontend/mobile): generate that component alone; answers `component == c`; dest contains `.copier-answers.yml` only (plus nothing else yet; assert `.copier-answers.yml` exists).
  - `test_slug_derived_from_name_when_not_given`: `copier copy --defaults -d project_name="Café 2024!"` (no slug) -> answers `project_slug == "caf-2024"`, `package_name == "caf_2024"`.
  - `test_invalid_slug_rejected`: `-d project_slug=Bad_Slug` exits nonzero, stderr names `project_slug`.
  - `test_invalid_org_domain_rejected`: `-d org_domain=nodots` exits nonzero.
  - `test_exclude_drops_dev_artifacts`: overlay `template/backend/.venv/x`, `template/backend/uv.lock`, `template/frontend/node_modules/y`, `template/frontend/pnpm-lock.yaml`, `template/mobile/pubspec.lock`, `template/mobile/.dart_tool/z`, `template/backend/dist/a`, plus a kept `template/backend/keep.txt`; generate each; assert none of the excluded exist, `keep.txt` exists.
  - `test_component_question_gating`: overlay a question `backend_only` (`when: "{{ component == 'backend' }}"`) appended to `copier.yml` text; generating `frontend` has no `backend_only` key in answers, generating `backend` with `-d backend_only=x` has it.
- [ ] **Step 2: Run** `pytest tests/test_questions.py -v`. Expected: FAIL (no copier.yml).
- [ ] **Step 3: Implement `copier.yml` and the four answers-file templates.** Component repos get task-free output in this task (tasks come in Task 3).
- [ ] **Step 4: Run.** Expected: PASS. If `regex_replace` or `_src_path` absolute behavior differs, adjust (verify at build start).
- [ ] **Step 5: Commit** `git add copier.yml template tests && git commit -m "feat: add copier questions, excludes and answers files"`.

---

### Task 3: Component tasks (git init, commit, mobile bootstrap) with copy-only gating

**Files:**
- Modify: `copier.yml` (add `_tasks`)
- Test: `tests/test_tasks.py`

**Interfaces:**
- Produces `_tasks` for `component in (backend, frontend, mobile)`, each entry `when: "{{ _copier_operation == 'copy' and component == '<c>' }}"` (list form commands so Jinja renders per element, no shell quoting issues):
  1. `["git","init","-b","main"]`.
  2. Backend: `["uv","lock"]` only if `pyproject.toml` exists (`["sh","-c","[ ! -f pyproject.toml ] || uv lock"]`); frontend: same with `package.json` and `pnpm install`. These guards let plan-01-only runs pass.
  3. Mobile: `["sh","-c","if command -v flutter >/dev/null 2>&1 && [ -f Makefile ]; then make bootstrap; else echo 'WARNING: flutter not found (or no Makefile); run make bootstrap in mobile/ later'; fi"]`. Contains the literal `make bootstrap`.
  4. Initial commit: `git add -A` then `["git","-c","user.name={{ author_name }}","-c","user.email={{ author_email }}","commit","--allow-empty","-m","chore: initial commit"]`.
  Gating covers `update`: no task runs on update.

- [ ] **Step 1: Write failing tests**
  - `test_component_is_own_git_repo_with_one_commit` (backend/frontend/mobile): `git -C dest rev-list --count HEAD` == `1`; `git -C dest status --porcelain` empty; commit author email `ada@example.com`.
  - `test_commit_works_without_global_git_identity`: `run_copier(..., no_git_identity=True)` (default) succeeds; same assertion. (Review Focus 3.)
  - `test_mobile_warns_without_flutter_and_still_succeeds`: PATH without flutter (assert `shutil.which("flutter")` None inside the run env by prepending an empty dir and filtering PATH only if needed); returncode 0; combined output contains `make bootstrap`.
  - `test_mobile_runs_make_bootstrap_when_flutter_on_path`: overlay `template/mobile/Makefile` = `bootstrap:\n\t@echo ran > bootstrapped.txt`; put a stub executable `flutter` on `path_prepend`; generated `mobile/bootstrapped.txt` exists and is committed (in `git ls-files`).
  - `test_other_components_unaffected_by_missing_flutter`: generate backend with flutter absent; returncode 0.
  - `test_tasks_do_not_run_on_update`: `make_template(tag="v0.1.0")`; generate `backend`; write `.git/marker`; record `rev-list --count`; add overlay file `template/backend/new.txt` to the template repo, commit, tag `v0.1.1`; run `copier update --trust --defaults --vcs-ref v0.1.1` in dest; assert `new.txt` appears, commit count unchanged (still 1), `.git/marker` still exists, no `uv lock` side effects (no `uv.lock`).
- [ ] **Step 2: Run** `pytest tests/test_tasks.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement the `_tasks`.** The workspace tasks come in Task 4 (same `_tasks` list, different `component` condition).
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `git add copier.yml tests && git commit -m "feat: add component git init, bootstrap and commit tasks"`.

---

### Task 4: Workspace tasks (nested copies, relative-src fail-fast, `_message_after_update`)

**Files:**
- Modify: `copier.yml`
- Create: `template/workspace/.gitignore`
- Test: `tests/test_workspace_tasks.py`

**Interfaces:**
- Consumes: Task 3 `_tasks` list, `make_template`, `generate`.
- Produces, in order, tasks gated `when: "{{ _copier_operation == 'copy' and component == 'workspace' }}"`:
  1. Fail-fast: `["sh","-c","case \"$1\" in /*|*://*|gh:*|git@*) ;; *) echo 'ERROR: template source must be an absolute path or URL, got: '\"$1\" >&2; exit 1;; esac","sh","{{ _copier_answers._src_path }}"]` (word-ordering of the sh args as needed; asserts only on behavior below).
  2. `["git","init","-b","main"]`.
  3. For each of `backend`, `frontend`, `mobile`: `["{{ _copier_python }}","-m","copier","copy","--trust","--defaults","--vcs-ref","{{ _copier_answers._commit }}","-d","component=<c>","-d","project_name={{ project_name }}","-d","project_slug={{ project_slug }}","-d","project_description={{ project_description }}","-d","org_domain={{ org_domain }}","-d","author_name={{ author_name }}","-d","author_email={{ author_email }}","{{ _copier_answers._src_path }}","<c>"]`.
  4. `git add -A`, then the initial commit (same `-c user.*` form as Task 3).
- `_message_after_update`: text containing `uv lock`, `pnpm install`, `flutter pub get`.
- `template/workspace/.gitignore`: `/backend`, `/frontend`, `/mobile`, `.DS_Store`, `.env` (spec 5 item 2: root excludes `/backend /frontend /mobile`).
- Runs only in the `component == 'workspace'` copy; `_copier_answers._commit` is the commit the outer copy used (must be committed; document in README).

- [ ] **Step 1: Write failing tests**
  - `test_workspace_generation_yields_four_git_repos`: dest and `dest/{backend,frontend,mobile}` each have `.git`; each has `.copier-answers.yml` with `component` equal to its name and the six shared answers; each repo has exactly 1 commit; workspace tracked files do not include any path under `backend/`, `frontend/`, `mobile/`.
  - `test_nested_answers_match_outer_answers_and_no_prompts`: generation returns 0 with stdin closed (`stdin=DEVNULL`), proving no re-prompt.
  - `test_nested_src_path_is_absolute_and_commit_matches`: nested `_src_path` equals outer `_src_path`; nested `_commit` equals outer `_commit`.
  - `test_relative_src_path_fails_fast`: `run_copier(["copier","copy","--trust","--defaults","--vcs-ref","HEAD", ...,"tpl","dest"], cwd=tpl.parent)` with the relative `tpl`; assert nonzero exit and stderr contains `absolute` OR (if Copier itself makes `_src_path` absolute for local paths, mark this test `xfail` with reason and keep the task: verify at build start whether Copier stores relative `_src_path`).
  - `test_awkward_names_survive` (Review Focus 1, 2): `project_name="O'Brien's Shop"`, slug `obriens-shop`, `author_name="Zoë O'Neil"`, dest `tmp/"my dir"/"app one"`; returncode 0; all four answers files record the exact `author_name`; `git log -1 --format=%an` in `backend` equals it.
  - `test_message_after_update_mentions_relocks`: load `copier.yml`, assert `_message_after_update` contains the three commands.
  - `test_workspace_update_does_not_touch_nested_repos` (Review Focus 5): `make_template(tag="v0.1.0")`, generate workspace; record `git -C backend rev-parse HEAD` and hash of every file under `backend/`; add overlay `template/workspace/NOTES.md`, tag `v0.1.1`; `copier update --trust --defaults` at workspace; assert `NOTES.md` present, backend HEAD and file hashes unchanged, workspace commit count unchanged (1).
- [ ] **Step 2: Run** `pytest tests/test_workspace_tasks.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** tasks, message and `.gitignore`.
- [ ] **Step 4: Run** `pytest tests -v`. Expected: PASS (Tasks 2-3 tests still green).
- [ ] **Step 5: Commit** `git add copier.yml template/workspace/.gitignore tests && git commit -m "feat: add workspace nested-copy tasks and update message"`.

---

### Task 5: Workspace docs: `PROJECT.md`, `AGENTS.md.jinja`, `CLAUDE.md.jinja`

**Files:**
- Create: `template/workspace/PROJECT.md`, `template/workspace/AGENTS.md.jinja`, `template/workspace/CLAUDE.md.jinja`
- Test: `tests/test_workspace_docs.py`

**Interfaces:**
- `PROJECT.md` (plain, no Jinja): `## ` sections in this order: Purpose, Users and roles, Clients and the surface each uses, Glossary, Core entities and rules, Integrations, Environments, Cross-repo conventions (prefilled bullets: UTC, money as integer minor units, ID format UUIDv7). Each section starts with an HTML-comment hint of what to write.
- `AGENTS.md.jinja` (short, <= 60 lines; also loaded inside sub-repos): title uses `{{ project_name }}`; the `project-context` marker block with placeholder line `_Not generated yet. Fill PROJECT.md, then run /sync-context from the workspace root._`; then sections: Repo map (backend/frontend/mobile, each its own git repo), Surface to client map (`admin` `/api/admin` -> `frontend/`; `public` `/api/v1` -> `mobile/`), Contract-first rule (backend `openapi/<surface>.json` is source of truth), Change order (backend, then `make sync-api`, then clients; each repo commits separately), Session rule (start Claude inside the repo you change; start at workspace root for cross-repo work and `/sync-context`; root hook dispatches formatting).
- `CLAUDE.md.jinja`: first line `@AGENTS.md`, then `## Claude` section with the `claude-tools` marker block (placeholder line) and a pointer to the `sync-context` skill.
- Marker lines appear exactly once each, on their own line.

- [ ] **Step 1: Write failing tests** (against `ws` fixture)
  - `test_agents_has_exact_context_markers_once`: file lines contain `<!-- project-context:start -->` and `<!-- project-context:end -->` exactly once each, start before end.
  - `test_claude_md_imports_agents_and_has_tool_markers`: first non-empty line `@AGENTS.md`; contains both `claude-tools` markers exactly once.
  - `test_agents_mentions_project_name_and_rules`: contains `Acme Shop`, `make sync-api`, `/api/admin`, `/api/v1`, `openapi/`.
  - `test_agents_length_within_target`: `len(lines) <= 150`.
  - `test_project_md_sections_in_order`: headings list equals the expected eight in order.
  - `test_no_unrendered_jinja_in_workspace`: no generated file under the workspace (excluding nested repos and `.git`) contains `{{` or `{%`, except files listed in an allowlist (starts empty).
  - `test_update_preserves_filled_project_context_block` (Review Focus 5): generate at `v0.1.0`; commit; edit text inside the `project-context` block in `AGENTS.md`; git commit; template change outside the block (overlay edits `AGENTS.md.jinja` Session-rule line), tag `v0.1.1`; `copier update --trust --defaults`; assert filled block text still present, and the new Session-rule line applied, no conflict markers (`<<<<<<<`) in file.
- [ ] **Step 2: Run** `pytest tests/test_workspace_docs.py -v`. Expected: FAIL.
- [ ] **Step 3: Write the three files.**
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `git add template/workspace tests && git commit -m "feat: add workspace PROJECT.md, AGENTS.md and CLAUDE.md"`.

---

### Task 6: Workspace `Makefile` and `compose.yaml`

**Files:**
- Create: `template/workspace/Makefile`, `template/workspace/compose.yaml`
- Test: `tests/test_workspace_make_compose.py`

**Interfaces:**
- `Makefile` (no Jinja; GNU make; `.PHONY`): variables `REPOS := backend frontend mobile`, `ADMIN_SPEC := backend/openapi/admin.json`, `PUBLIC_SPEC := backend/openapi/public.json`, `FRONTEND_SPEC_SRC := $(ADMIN_SPEC)`, `MOBILE_SPEC_SRC := $(PUBLIC_SPEC)` (one variable per client = the surface mapping). Targets:
  - `up`: `docker compose up -d`; `down`: `docker compose down`.
  - `sync-api`: `$(MAKE) -C backend openapi`; `cp $(FRONTEND_SPEC_SRC) frontend/openapi.json`; `cp $(MOBILE_SPEC_SRC) mobile/openapi.json`; `$(MAKE) -C frontend gen-api`; `$(MAKE) -C mobile gen-api`. Each client step skipped with a message if that dir is absent.
  - `check-specs`: for each client, if both files exist and `cmp -s` differs, print `stale client: <client>/openapi.json differs from <src>; run make sync-api` and exit 1; skip if either file absent.
  - `check`: depends on `check-specs`, then `$(MAKE) -C <repo> check` for each repo dir that exists (all paths quoted).
- `compose.yaml`: `include:` -> `backend/compose.yaml`; service `admin`: image `node:24`, `working_dir: /app`, `volumes: ["./frontend:/app", "/app/node_modules"]` (anonymous volume keeps host node_modules out), `ports: ["5173:5173"]`, `environment: API_PROXY_TARGET: http://api:8000` (see spec gap 3: frontend's `vite.config.ts` proxy target must read this variable; hand to plan 03), `command: sh -c "corepack enable && pnpm install && pnpm dev --host"`, `depends_on: [api]`. Backend compose service name `api` per spec 6.4 compose listing.

- [ ] **Step 1: Write failing tests**
  - `test_make_dry_run_targets_exist`: for `up down sync-api check check-specs`: `make -n <t>` in `ws` returns 0.
  - `test_check_specs_passes_when_equal_or_absent`: tmp copy of `ws`: no specs -> `make check-specs` 0; create `backend/openapi/admin.json` and identical `frontend/openapi.json` -> 0.
  - `test_check_specs_fails_when_client_spec_stale`: differing content -> returncode 1, output contains `stale client` and `frontend`; same for mobile vs `public.json`.
  - `test_check_runs_repo_checks_and_skips_missing`: stub `backend/Makefile` with `check:\n\t@echo BACKEND_CHECK`, no frontend/mobile dirs; `make check` output contains `BACKEND_CHECK`, returncode 0.
  - `test_check_fails_when_repo_check_fails`: stub `check:\n\t@exit 1` -> nonzero.
  - `test_sync_api_copies_and_calls_gen_api`: stubs: `backend/Makefile` `openapi:` writes the two spec files; `frontend/Makefile` and `mobile/Makefile` `gen-api:` echo `GEN_FRONTEND` / `GEN_MOBILE`; after `make sync-api`, `frontend/openapi.json == backend/openapi/admin.json`, `mobile/openapi.json == backend/openapi/public.json`, output has both markers.
  - `test_paths_with_spaces`: run the check tests inside a dir named `a b`.
  - `test_compose_shape` (pyyaml): `include` mentions `backend/compose.yaml`; `services.admin.image == "node:24"`; `"5173:5173"` in ports; `"./frontend:/app"` in volumes; command text contains `pnpm dev --host`; env has `API_PROXY_TARGET`.
  - `test_compose_config_validates_when_docker_and_backend_compose_present` (skipif no docker or no `backend/compose.yaml` in the *template*): in a generated tree run `docker compose config -q`. Skipped until plan 02 lands.
- [ ] **Step 2: Run** `pytest tests/test_workspace_make_compose.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the two files.
- [ ] **Step 4: Run.** Expected: PASS (compose-config test skipped).
- [ ] **Step 5: Commit** `git add template/workspace tests && git commit -m "feat: add workspace Makefile and compose"`.

---

### Task 7: Workspace `.claude/settings.json` and `format-dispatch.sh`

**Files:**
- Create: `template/workspace/.claude/settings.json`, `template/workspace/.claude/hooks/format-dispatch.sh` (mode 755; Copier preserves mode)
- Test: `tests/test_format_dispatch.py`

**Interfaces:**
- `settings.json`: `permissions.allow`: `Bash(make:*)`, `Bash(make -C:*)`, `Bash(docker compose:*)`, `Bash(git status:*)`, `Bash(git diff:*)`, `Bash(git log:*)`, `Bash(git show:*)`, `Bash(git branch:*)`, `Bash(git -C:*)` restricted to read verbs is not expressible, so omit it (verify permission-rule syntax at code.claude.com/docs at build start). `hooks.PostToolUse`: one entry, `matcher: "Edit|Write"`, command `"$CLAUDE_PROJECT_DIR"/.claude/hooks/format-dispatch.sh`.
- `format-dispatch.sh` (bash, `set -u`, no `-e`; ends `exit 0` on every path): reads stdin to a variable; extracts `tool_input.file_path` with `jq -r` if on PATH, else `python3 -c`; resolves the workspace root as the script's `../..`; canonicalizes the file path; for `repo` in `backend frontend mobile`, if the file lies under `$root/$repo/` and `$root/$repo/.claude/hooks/format.sh` is executable, pipes the original stdin into it. Relative `file_path` is resolved against `$root`. Anything unparsable or outside the repos is a silent no-op.

- [ ] **Step 1: Write failing tests** (script run with `subprocess.run(input=json)`, in a tmp workspace copy of `ws` with stub `backend/.claude/hooks/format.sh` that appends its stdin to `$ROOT/calls.log`; `frontend`/`mobile` stubs likewise)
  - `test_settings_json_valid_and_wired`: parses; hook command string contains `format-dispatch.sh`; matcher `Edit|Write`; allow list contains `Bash(make:*)` and `Bash(docker compose:*)`.
  - `test_dispatches_backend_file_with_same_stdin`: payload with `{"tool_input":{"file_path":"<root>/backend/src/app/x.py"}}` -> backend log has that exact payload, frontend/mobile logs empty; exit 0.
  - `test_dispatches_frontend_and_mobile_by_prefix`.
  - `test_sibling_prefix_not_matched`: file `<root>/backend-old/x.py` -> no calls.
  - `test_outside_repos_noop`: `<root>/PROJECT.md` and `/etc/hosts` -> no calls, exit 0.
  - `test_missing_format_script_noop`: delete backend stub -> exit 0.
  - `test_garbage_stdin_and_empty_stdin_exit_zero`.
  - `test_falls_back_to_python3_without_jq`: run with PATH restricted to a dir containing only `python3`, `bash`, `dirname`, `cat` symlinks (build in tmp); dispatch still works.
  - `test_failing_repo_formatter_does_not_propagate`: stub exits 7 -> dispatcher exits 0.
  - `test_relative_file_path_resolved_against_root`.
  - `test_script_is_executable_in_generated_tree`: `os.access(ws/.claude/hooks/format-dispatch.sh, os.X_OK)`.
- [ ] **Step 2: Run** `pytest tests/test_format_dispatch.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** both files.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `git add template/workspace/.claude tests && git commit -m "feat: add workspace claude settings and format dispatch hook"`.

---

### Task 8: `sync-context` skill and per-stack skeleton references

**Files:**
- Create: `template/workspace/.claude/skills/sync-context/SKILL.md`
- Create: `template/workspace/.claude/skills/sync-context/references/{agents,claude}-skeleton-{workspace,backend,frontend,mobile}.md` (8 files)
- Create: `tests/marker_diff.py`, `tests/fixtures/PROJECT.sample.md`
- Test: `tests/test_sync_context_assets.py`

**Interfaces:**
- `SKILL.md`: frontmatter `name: sync-context`, `description` (when to use: after filling `PROJECT.md`, or when repos' Makefile/skills/MCP changed), `disable-model-invocation: true` (manual only per spec 5 item 26; verify frontmatter keys at build start). Body is the spec 6.2 procedure, steps 1-4, written as imperative instructions:
  1. Read `PROJECT.md`; per present repo read manifest (`pyproject.toml`/`package.json`/`pubspec.yaml`), `Makefile`, top-level tree, `.claude/skills|agents`, `.mcp.json`, settings plugins; backend also `src/app/api/surfaces.py`.
  2. In `<repo>/AGENTS.md` rewrite only between `<!-- project-context:start -->` and `<!-- project-context:end -->` (what the repo is for in this product, relevant entities/roles/glossary, surface served or consumed, sibling repos, contract location). Fix the `## Commands` section to match the Makefile targets (the only text outside markers the skill may edit; see spec gap 1).
  3. In `<repo>/CLAUDE.md` refresh only the `claude-tools` block (which skill/agent/MCP to use when).
  4. Create missing files from the references skeleton; refresh the root's own blocks; idempotent (second run no diff); report a per-file summary; never touch text outside markers (except Commands). Content for blocks derives only from files read (no timestamps, stable ordering) so reruns are byte-identical.
- Skeletons: AGENTS skeleton has the 8 sections of spec 6.8 in order, both project-context markers, <= 150 lines, per-stack Commands list from the Global Constraints (backend: `dev test lint fmt check openapi up down migrate migration create-admin`; frontend/mobile: `dev test lint fmt check gen-api`, mobile + `bootstrap`; frontend `make` wraps pnpm; backend Architecture map = modules x surfaces `admin`/`public`, business logic only in `<module>/service.py`; Never list: edit generated code, edit applied migrations, commit secrets, put logic in surface files, break `/api/v1` in place). CLAUDE skeleton = `@AGENTS.md` + `claude-tools` block. Workspace skeletons mirror Task 5 files. Skeletons are plain (no Jinja); the skill substitutes project name from `PROJECT.md`.
- `tests/marker_diff.py`: `strip_managed(text: str) -> str` removes both marker blocks (inclusive of marker lines) and the `## Commands` section (up to next `## `); `same_outside_managed(a: str, b: str) -> bool`. Used by criterion 7's manual check.
- `tests/fixtures/PROJECT.sample.md`: a filled example (fictional "Acme Shop": roles admin/user, items catalogue, glossary, UTC/minor-units conventions) used for criterion 7.

- [ ] **Step 1: Write failing tests**
  - `test_skill_frontmatter`: name `sync-context`, description non-empty, body mentions all four exact marker lines and `PROJECT.md`.
  - `test_skeletons_have_exact_markers_once` (parametrized 4 stacks): each agents skeleton has both project-context lines exactly once; each claude skeleton has both claude-tools lines once and starts with `@AGENTS.md`.
  - `test_agents_skeleton_sections_in_order_and_short`: the headings subsequence equals Stack, Commands, Architecture map, Conventions, Testing, Definition of done, Never; `len <= 150`.
  - `test_skeleton_commands_match_contract`: backend skeleton lists every backend target; frontend/mobile contain `gen-api`; mobile contains `bootstrap`; no skeleton lists a target outside the contract set.
  - `tests/test_marker_diff.py::test_strip_managed_removes_blocks_and_commands`, `::test_same_outside_managed_detects_outside_edit`, `::test_marker_edit_inside_is_ignored`.
- [ ] **Step 2: Run** `pytest tests/test_sync_context_assets.py tests/test_marker_diff.py -v`. Expected: FAIL.
- [ ] **Step 3: Write the files.**
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `git add template/workspace/.claude/skills tests && git commit -m "feat: add sync-context skill, skeletons and marker diff helper"`.

---

### Task 9: Template README, `Makefile` (`test-template`) and CI

**Files:**
- Create: `README.md`, `Makefile`, `.github/workflows/ci.yml`
- Test: `tests/test_template_makefile.py`

**Interfaces:**
- `Makefile` targets: `test` (`uv run --with pytest --with pyyaml pytest tests/`) and `test-template`. Variables: `OUT` (default: fresh `mktemp -d`), `REPOS` (default `backend frontend mobile`). `test-template`:
  1. Refuse unless the tree is committed: `git diff --quiet HEAD && [ -z "$(git ls-files --others --exclude-standard)" ]`, else print `ERROR: commit all changes first; nested copies use the committed _commit` and exit 1 (Review Focus 4).
  2. `copier copy --trust --defaults --vcs-ref HEAD -d project_name="Test App" "$(CURDIR)" "$(OUT)/app"` (`$(CURDIR)` is absolute).
  3. Assert the four `.git` dirs and four `.copier-answers.yml` exist.
  4. For each repo in `REPOS` with a `Makefile` present: `make -C "$(OUT)/app/$$r" check`; mobile skipped with a notice when `flutter` is not on PATH.
  5. `make -C "$(OUT)/app" -n check` (workspace wiring sanity), print `$(OUT)`.
  Works with component dirs holding only answers files (no Makefile -> skipped).
- `README.md` sections: Generate (`copier copy --trust gh:<user>/project-template my-app` or absolute path; template must be committed), What you get, Fill `PROJECT.md` then run `/sync-context` from the workspace root, Session rule, Create remotes and push (per-repo `gh repo create … --source . --push` commands for the four repos), Update (`copier update --trust` per repo, any order; re-lock reminders), Develop (components live in `template/<c>/`, `make test`, `make test-template`), Release (git tag `vX.Y.Z`, PEP 440), Known limits (Flutter not required at copy time; mobile unverified locally).
- `ci.yml` (`on: push, pull_request`): job `test-template` on `ubuntu-latest`: `actions/checkout` with `fetch-depth: 0`; `astral-sh/setup-uv`; `uv tool install copier`; `actions/setup-node` (24) + `corepack enable`; step `make test` ; step `make test-template OUT="$RUNNER_TEMP/demo" REPOS="backend frontend"` (generation uses absolute `$GITHUB_WORKSPACE` via `$(CURDIR)`, `--vcs-ref HEAD`); then, guarded by `hashFiles` / `[ -f "$RUNNER_TEMP/demo/app/mobile/pubspec.yaml" ]`: `subosito/flutter-action` with `flutter-version-file: ${{ runner.temp }}/demo/app/mobile/pubspec.yaml`, then `make -C "$RUNNER_TEMP/demo/app/mobile" bootstrap check`. Git identity step: `git config --global user.name ci && user.email ci@example.com`. Pin each action to an exact released tag or SHA (verify at build start; confirm `flutter-version-file` input name).

- [ ] **Step 1: Write failing tests**
  - `test_make_test_template_refuses_dirty_tree`: create a tmp git clone of the repo files (copy repo minus `.git`, `git init`, commit), add an untracked file, run `make test-template` -> nonzero, stderr/stdout contains `commit all changes`. Skipped when `copier` missing.
  - `test_make_test_template_passes_on_committed_tree` (copier required): same clone, clean -> returncode 0, output contains the `OUT` path, `OUT/app/{backend,frontend,mobile}/.git` exist.
  - `test_ci_yaml_shape` (pyyaml): job `test-template` exists; steps text contains `--vcs-ref`-free call to `make test-template`, `GITHUB_WORKSPACE`-independent absolute path (assert `$(CURDIR)` in Makefile and `copier copy` line has `--vcs-ref HEAD`), `flutter-version-file`, `fetch-depth: 0`.
  - `test_readme_has_required_sections`: headings include Generate, Update, Develop, Release; contains `git tag` and `copier update --trust`.
- [ ] **Step 2: Run** `pytest tests/test_template_makefile.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the three files.
- [ ] **Step 4: Run** `make test`, then (tree committed after step 5 commit, re-run) `make test-template`. Expected: PASS.
- [ ] **Step 5: Commit** `git add README.md Makefile .github tests && git commit -m "feat: add template README, test-template target and CI"`; then re-run `make test-template` on the clean tree.

---

### Task 10: Update-path regression (acceptance 6, workspace scope)

**Files:**
- Test: `tests/test_update_path.py`

**Interfaces:**
- Consumes: `make_template(tag=...)`, `generate`, `run_copier`.

- [ ] **Step 1: Write the tests** (they should already pass; this task exists to pin criterion 6 so later plans cannot regress it)
  - `test_v010_to_v011_update_applies_cleanly_in_each_component` (parametrized workspace/backend/frontend/mobile): generate at `v0.1.0`; overlay a trivial change per component dir (`template/<c>/CHANGELOG-probe.txt`), tag `v0.1.1`; `copier update --trust --defaults --vcs-ref v0.1.1` in the generated component; exit 0, probe file present, no `<<<<<<<` anywhere, commit count unchanged, `git status --porcelain` lists only the probe as untracked.
  - `test_update_never_reprompts`: `stdin=DEVNULL`, `--defaults`; exit 0 (shared answers come from the answers file).
  - `test_update_keeps_user_edits_outside_template_changes`: user edits a line in `AGENTS.md` (workspace) not touched by the template change; survives.
- [ ] **Step 2: Run** `pytest tests/test_update_path.py -v`. Expected: PASS. If any fails, fix `copier.yml` (usually missing `when:` gating) rather than the test.
- [ ] **Step 3: Commit** `git add tests && git commit -m "test: pin copier update path"`.

---

### Task 11: Full generation run (RUN AFTER PLANS 02, 03 AND 04 ARE DONE)

**Files:** none created; fixes go in the files of whichever plan owns the failure.

- [ ] **Step 1: Commit everything** in the template repo (user-approved), so nested copies see it. `git status` clean.
- [ ] **Step 2: Acceptance 1.** `make test-template` (no `flutter` on this machine: mobile `make check` is skipped with a notice; mobile must still be generated and print the `make bootstrap` warning). Expected: four git repos, each answers file records `component` + six shared answers (`tests/test_workspace_tasks.py` green).
- [ ] **Step 3: Compose wiring.** In the generated workspace: `docker compose config -q` returns 0 (un-skips `test_compose_config_validates_when_docker_and_backend_compose_present`); `grep -n API_PROXY_TARGET frontend/vite.config.ts` finds the env read (spec gap 3); `make check` in the workspace passes (includes `check-specs`).
- [ ] **Step 4: Acceptance 6 on backend.** Commit, tag `v0.1.0`; make a trivial change under `template/backend/` (e.g. a comment in `README.md.jinja`), commit, tag `v0.1.1`. In a generated `backend/`: fill the `project-context` block in `AGENTS.md`, commit; run `copier update --trust --defaults --vcs-ref v0.1.1`. Expected: clean apply, no conflict markers, `git rev-list --count HEAD` unchanged (no task re-ran, no new `uv.lock` diff), filled block intact.
- [ ] **Step 5: Acceptance 7 (manual, in Claude Code).** Copy `tests/fixtures/PROJECT.sample.md` over the generated workspace's `PROJECT.md`; commit every repo (`git -C <r> add -A && git -C <r> commit -m wip` for workspace, backend, frontend, mobile). Start `claude` at the workspace root, run `/sync-context`. Then for each repo in `. backend frontend mobile` and each of `AGENTS.md`, `CLAUDE.md`:
  `python3 -c "import sys,subprocess; sys.path.insert(0,'<template>/tests'); from marker_diff import same_outside_managed as s; a=subprocess.check_output(['git','-C',r,'show','HEAD:'+f],text=True); b=open(r+'/'+f).read(); sys.exit(0 if s(a,b) else 1)"` -> exit 0 and both marker blocks filled (non-placeholder). Commit all repos, run `/sync-context` a second time, then `git -C <r> diff --exit-code` for the four repos -> exit 0 (no diff on rerun).
- [ ] **Step 6: Hook check.** From a Claude session started at the workspace root, ask it to edit `backend/src/app/main.py` adding badly formatted code (e.g. `x=1;y  =2`); `git -C backend diff` shows ruff-formatted output. Alternatively pipe `{"tool_input":{"file_path":"<abs>/backend/src/app/main.py"}}` into `.claude/hooks/format-dispatch.sh` after an unformatted edit and confirm the diff.
- [ ] **Step 7: Acceptance 8.** Report results and ask the user whether to commit and tag `v0.1.0`.

---

## Self-review notes

- Spec coverage: 6.1 -> Tasks 2-4, 9; 6.2 -> Tasks 5-8; 6.10 markers/format contract -> 5, 7, 8; criteria 1 -> 4, 9, 11; 6 -> 4, 10, 11; 7 -> 7, 8, 11; 8 -> 11.
- Task count: 11.

## Spec gaps (referenced above)

1. Spec 6.2 says `/sync-context` must "correct drift in the commands section to match the Makefile" and also "Never touch text outside markers". Plan resolves: only `## Commands` is editable outside markers.
2. Spec 6.1 says `project_slug`/`package_name` are "derived", yet 8.1 needs `project_slug` recorded in answers and passed via `-d`. Plan makes them normal questions with derived defaults (not `when: false`).
3. Admin dev container runs Vite inside Docker, but spec 6.5 proxies `/api` to the backend (localhost:8000 in the container is wrong). Plan 03 must read `API_PROXY_TARGET` (set to `http://api:8000` in root compose).
