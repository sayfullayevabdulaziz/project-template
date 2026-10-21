---
name: sync-context
description: Refresh the generated context blocks in every repo's AGENTS.md and CLAUDE.md from PROJECT.md. Use after filling PROJECT.md, or when a repo's Makefile, skills, agents, MCP servers or plugins changed. Run from the workspace root.
disable-model-invocation: true
---

# sync-context

Regenerate the managed parts of the context files from `PROJECT.md` and what each repo actually contains. Run from the workspace root. Manual only.

Managed regions are delimited by these exact marker lines:

- `<!-- project-context:start -->` and `<!-- project-context:end -->` in each `AGENTS.md`.
- `<!-- claude-tools:start -->` and `<!-- claude-tools:end -->` in each `CLAUDE.md`.

## Rules

- Edit only text between a start and end marker pair. The one exception is the `## Commands` section of a repo's `AGENTS.md`: fix it to match the Makefile (command targets from the skeleton only).
- Never change any other text outside the markers.
- Derive block content only from files you read. No timestamps, no dates, no counts that change. Use stable ordering (alphabetical) so a rerun is byte-identical.
- Skip repos that are not present (`backend/`, `frontend/`, `mobile/`).

## Procedure

1. Read `PROJECT.md` at the workspace root. For each present repo, read:
   - the manifest: `pyproject.toml`, `package.json` or `pubspec.yaml`;
   - `Makefile`;
   - the top-level directory tree;
   - `.claude/skills/` and `.claude/agents/`;
   - `.mcp.json`;
   - the plugins listed in `.claude/settings.json`;
   - for the backend, also `src/app/api/surfaces.py`.
2. In each `<repo>/AGENTS.md`, rewrite only the text between `<!-- project-context:start -->` and `<!-- project-context:end -->`. Cover:
   - what this repo is for in this product;
   - the entities, roles and glossary terms that matter to this repo;
   - the API surface it serves or consumes;
   - the sibling repos;
   - where the contract lives (`backend/openapi/<surface>.json`).

   Then fix the `## Commands` section so it lists only the command targets from the skeleton's Commands list that exist in the repo's Makefile. Never add file targets or helper targets. This is the only text outside the markers you may edit.
3. In each `<repo>/CLAUDE.md`, rewrite only the text between `<!-- claude-tools:start -->` and `<!-- claude-tools:end -->`: which skill, agent or MCP server to use for which task, taken from what step 1 found.
4. Finish:
   - If a repo's `AGENTS.md` or `CLAUDE.md` is missing, create it from `references/agents-skeleton-<stack>.md` or `references/claude-skeleton-<stack>.md` (stacks: `workspace`, `backend`, `frontend`, `mobile`). Replace `<project name>` with the project name from `PROJECT.md`, then fill the blocks as in steps 2 and 3.
   - Refresh the workspace root's own `AGENTS.md` and `CLAUDE.md` blocks the same way, using the `workspace` skeletons if they are missing.
   - Make the run idempotent: a second run must produce no diff.
   - Print a per-file summary: created, updated or unchanged.
