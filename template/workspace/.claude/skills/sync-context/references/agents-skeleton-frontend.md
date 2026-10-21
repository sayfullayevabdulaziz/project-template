# <project name> admin panel

<!-- project-context:start -->
_Not generated yet. Fill PROJECT.md, then run /sync-context from the workspace root._
<!-- project-context:end -->

## Stack

Vite, React 19, TypeScript strict, TanStack Router + Query + Table, `@hey-api/openapi-ts` generated client, Tailwind v4 + shadcn/ui, react-hook-form + zod, ESLint + Prettier, Vitest + Testing Library + MSW. The package manager is pnpm; `make` wraps it.

## Commands

- `make dev`: run the Vite dev server.
- `make test`: run Vitest.
- `make lint`: ESLint and the type check.
- `make fmt`: format with Prettier.
- `make check`: lint, tests and a production build.
- `make gen-api`: regenerate `src/client/` from `openapi.json`.

## Architecture map

- `src/routes/`: file-based TanStack Router routes. The `beforeLoad` guard allows admins only.
- `src/client/`: generated API client. Never edit.
- `src/components/`: shared UI, including shadcn/ui primitives.
- `src/features/<name>/`: screens, forms and queries per domain feature.
- `openapi.json`: copy of the backend `admin` spec, written by `make sync-api` at the workspace root.

## Conventions

- Call the API only through `src/client/` and its TanStack Query helpers.
- Forms use react-hook-form with zod schemas.
- Use the glossary words from PROJECT.md in code and UI.
- Accessible by default: labelled controls, keyboard support, jsx-a11y clean.
- The API base URL comes from runtime config, not hard-coded.

## Testing

- Vitest with Testing Library; mock the API with MSW.
- Test behavior a user sees, not implementation details.
- Add a test with every screen or form you add.

## Definition of done

- `make check` is green.
- The client is regenerated after any spec change (`make gen-api`).
- The UI works for loading, empty and error states.

## Never

- Edit generated code in `src/client/`.
- Hand-edit `openapi.json`; change the backend and run `make sync-api`.
- Commit secrets.
- Put business rules in components; the backend enforces them.
- Call `/api/v1` from this app; it uses `/api/admin` only.
