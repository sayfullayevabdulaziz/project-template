---
name: ui-component
description: Add or change a UI component (shadcn/ui primitives or app components) in this frontend with accessibility and tests. Use when building or editing components under src/components.
---

# UI component

## Add a shadcn primitive

- Run `pnpm dlx shadcn@latest add <name>` (config: `components.json`). Output goes to `src/components/ui/`.
- Existing primitives: alert-dialog, badge, button, card, checkbox, dropdown-menu, field, input, label, select, separator, sheet, sidebar, skeleton, sonner, switch, table, tooltip. Reuse before adding.
- Do not restyle vendored files in `src/components/ui/` beyond design tokens (CSS variables in `src/index.css`). Compose variants in app components instead.
- Run `make fmt` after adding, because vendored output may not match Prettier.

## App components

- Live in `src/components/` (feature pieces such as `items-table.tsx`, `confirm-dialog.tsx`) and `src/components/data-table/` (generic table).
- Keep data fetching and mutations in components or hooks. Route files stay thin.
- Use `cn` from `@/lib/utils` for class merging and the `@/` alias for imports.

## Accessibility checklist

- Every input has a visible label (`FieldLabel` or `Label`), and errors use `FieldError`.
- Icon-only buttons have `aria-label`.
- Tab order follows visual order. Everything is reachable and operable by keyboard.
- Sortable headers expose `aria-sort` (see `data-table.tsx`).
- Dialogs trap focus, close on Escape, and return focus (use `alert-dialog`; see `confirm-dialog.tsx`).
- Text and controls meet WCAG AA contrast; do not use color alone to convey state.
- Async state is announced (toast via `sonner` or an `aria-live` region).

## Test

- Colocate `name.test.tsx` next to the component (see `item-form.test.tsx`, `data-table.test.tsx`).
- Use Testing Library: `getByRole`, `getByLabelText`, `userEvent`. Do not assert on class names, state, or internals.
- Run `pnpm test <file>`, then `make check`.
