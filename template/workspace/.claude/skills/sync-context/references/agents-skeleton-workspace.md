# <project name>

Workspace root. Also loaded by Claude sessions inside `backend/`, `frontend/` and `mobile/`.

<!-- project-context:start -->
_Not generated yet. Fill PROJECT.md, then run /sync-context from the workspace root._
<!-- project-context:end -->

## Repo map

Each directory is its own git repo.

- `backend/`: API server, source of truth for the contract.
- `frontend/`: admin panel.
- `mobile/`: end-user app.

## Surface to client map

| Surface | Prefix | Client |
|---|---|---|
| `admin` | `/api/admin` | `frontend/` |
| `public` | `/api/v1` | `mobile/` |

## Contract-first rule

Backend `openapi/<surface>.json` is the source of truth. Never hand-edit a client's copied spec or generated API code.

## Change order

1. Change the backend and its OpenAPI spec.
2. Run `make sync-api` at the workspace root.
3. Update the clients.

Each repo commits separately.

## Session rule

Start Claude inside the repo you change. Start at the workspace root for cross-repo work and `/sync-context`. The root hook dispatches formatting to the repo that holds the edited file.
