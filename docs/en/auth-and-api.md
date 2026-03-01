# Authentication and API

## Authentication
* Password login only
* Configure credentials with `WEB_USERNAME` and `WEB_PASSWORD`

Drop link password policy:
* `drop_password` is currently stored and compared as plain text.
* Treat it as a lightweight sharing guard, not an account-grade secret.
* Do not reuse account passwords as drop passwords.

Useful auth endpoints:
* `POST /api/auth/login`
* `GET /api/auth/me`
* `POST /api/auth/logout` (recommended)
* `GET /api/auth/logout` (compatible)

## Breaking Drop API (Reworked)
* `GET /api/drop?page=1&page_size=50&sort=created_at|title|size_bytes&order=asc|desc`
* `POST /api/drop` (multipart: `file`, `slug?`, `title?`, `description?`, `access_scope`, `drop_password?`)
* `GET /api/drop/{slug}/meta?drop_password=...`
* `GET /api/drop/{slug}?disposition=attachment|inline&drop_password=...` (Range supported)
* `PATCH /api/drop/{slug}` (JSON body: `title?`, `description?`, `access_scope?`, `is_favorite?`, `new_password?`, `current_password?`)
* `DELETE /api/drop/{slug}?current_password=...`
* `GET /api/drop/availability/{slug}`

## Web Action Paths (HTMX Forms)
* `POST /actions/auth/login`
* `POST /actions/auth/logout`
* `POST /actions/drop/upload`
* `POST /actions/drop/{slug}/open`
* `POST /actions/drop/{slug}/detail`
* `POST /actions/drop/{slug}/favorite`
* `POST /actions/drop/{slug}/access`
* `POST /actions/drop/{slug}/password`
* `POST /actions/drop/{slug}/delete`

## HTMX SSR Preview UI
* `GET /` (login + upload/list/detail management panel)
* `GET /<FILE_SLUG>` (dashboard preview view)
* UI write actions use CSRF-protected form submissions.
* After deploying a new `CSRF_SECRET_KEY`, previously rendered form tokens are expected to fail (403).
