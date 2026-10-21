# Project brief

Fill every section. `/sync-context` reads this file to write each repo's context block.

## Purpose

<!-- What the product does, for whom, and why it exists. Two or three sentences. -->

## Users and roles

<!-- Each kind of user, their role names, and what each may do. -->

## Clients and the surface each uses

<!-- Which client talks to which API surface. Default: admin panel (frontend/) uses admin, /api/admin; mobile app (mobile/) uses public, /api/v1. -->

## Glossary

<!-- Domain terms with one-line definitions. Use these exact words in code and UI. -->

## Core entities and rules

<!-- The main entities, how they relate, and the business rules and invariants that always hold. -->

## Integrations

<!-- Third-party services (payments, email, push, storage): what each does and who owns the account. -->

## Environments

<!-- dev, staging, production: URLs, how each is deployed, where secrets live. -->

## Cross-repo conventions

<!-- Rules every repo follows. Add or change as needed. -->

- All timestamps are UTC.
- Money is stored and sent as integer minor units (for example cents).
- IDs are UUIDv7.
