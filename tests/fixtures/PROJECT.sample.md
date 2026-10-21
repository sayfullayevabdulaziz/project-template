# Project brief

## Purpose

Acme Shop sells small household goods online. Customers browse the catalogue and order from their phone; staff manage the catalogue and orders from a web admin panel.

## Users and roles

- `admin`: staff. Manage the whole catalogue, users and orders in the admin panel.
- `user`: customer. Browse published items and manage their own account in the mobile app.

## Clients and the surface each uses

- Admin panel (`frontend/`) uses the `admin` surface, `/api/admin`.
- Mobile app (`mobile/`) uses the `public` surface, `/api/v1`.

## Glossary

- Item: a product in the catalogue.
- Catalogue: the set of all items.
- Published: an item customers can see.

## Core entities and rules

- Item: name, description, price in minor units, `is_published`.
- User: email (unique), role `admin` or `user`, `is_active`.
- Customers see published items only. Only admins create, edit or delete items.
- A deactivated user cannot log in.

## Integrations

- Email provider: welcome emails. Owned by the shop owner.
- Payments: not integrated yet.

## Environments

- dev: local, `make up`.
- production: one VPS behind a reverse proxy; secrets in the host environment.

## Cross-repo conventions

- All timestamps are UTC.
- Money is stored and sent as integer minor units (for example cents).
- IDs are UUIDv7.
