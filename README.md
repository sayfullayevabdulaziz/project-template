# project-template

Copier template for a four-repo project: a workspace root plus `backend/` (FastAPI), `frontend/` (React admin) and `mobile/` (Flutter). Each directory is its own git repo with its own `.copier-answers.yml`.

## Generate

```sh
copier copy --trust gh:<user>/project-template my-app
# or, from a local checkout (absolute path required):
copier copy --trust /abs/path/to/project-template my-app
```

Requires Copier >= 9.0.0, `git` and `uv`; `pnpm` for the frontend; `flutter` is optional.

The template must be committed before you generate from a local checkout. The workspace copies each component with the committed `_commit` of the template, so uncommitted edits are not picked up. A relative template path is rejected.

## What you get

```
my-app/            workspace root: PROJECT.md, AGENTS.md, CLAUDE.md, Makefile, compose.yaml, .claude/
  backend/         FastAPI + Postgres + Redis + taskiq (own git repo)
  frontend/        React admin panel (own git repo)
  mobile/          Flutter app (own git repo)
```

Each repo gets an initial commit. Lockfiles are generated at copy time and are not part of the template.

## Fill `PROJECT.md`, then run `/sync-context`

Edit `my-app/PROJECT.md` (purpose, roles, clients, entities, integrations). Then start Claude at the workspace root and run `/sync-context` to refresh the context blocks in every repo's `AGENTS.md` and `CLAUDE.md`.

## Session rule

Start Claude inside the repo you change: its hooks, permissions and skills load only from the start folder. Start at the workspace root for cross-repo work and `/sync-context`.

## Create remotes and push

```sh
cd my-app
gh repo create <org>/my-app --private --source . --push
gh repo create <org>/my-app-backend --private --source backend --push
gh repo create <org>/my-app-frontend --private --source frontend --push
gh repo create <org>/my-app-mobile --private --source mobile --push
```

## Update

Run in each repo you want to update, in any order (each repo records its own answers):

```sh
cd my-app/backend && copier update --trust
cd my-app/frontend && copier update --trust
cd my-app/mobile && copier update --trust
cd my-app && copier update --trust
```

Copier does not manage lockfiles. After updating, re-lock: `uv lock` (backend), `pnpm install` (frontend), `flutter pub get` (mobile).

## Develop

Components live in `template/<component>/` and are developed and tested in place. Only files that need answers carry the `.jinja` suffix.

```sh
make test            # pytest suite for the template
make test-template   # generate from this checkout into a scratch dir and run every repo's `make check`
```

`make test-template` refuses a dirty or untracked tree: commit first. Options: `OUT=<dir>` (default: a fresh temp dir) and `REPOS="backend frontend"` (default: all three; mobile is skipped when `flutter` is not on PATH).

## Release

Releases are git tags in PEP 440 form so `copier update` can see versions:

```sh
git tag v0.1.0
git push --tags
```

## Known limits

- Flutter is not required at copy time. Without it, generation succeeds and mobile prints a warning to run `make bootstrap` later.
- The mobile repo is not verified locally; CI covers it only when the generated `mobile/` has a `pubspec.yaml`.
