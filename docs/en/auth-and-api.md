# Authentication and API

## Authentication
* Password login is required for web UI access
* `WEB_USERNAME` and `WEB_PASSWORD` are used only to bootstrap the first database-backed web user on an empty database
* Protected REST API endpoints accept:
  * session cookie authentication
  * `X-API-Key: tdpk_<public_id>_<secret>`
* API key management is web-login only (`/settings/api-keys`)
* The API key management page only shows the current user's keys
* Authentication failures for protected REST API return `401` with:
  * `WWW-Authenticate: Session, ApiKey`

Runtime defaults and scaling notes:
* `SESSION_COOKIE_SECURE` defaults to `true`
* If `SESSION_COOKIE_SAMESITE=none`, `SESSION_COOKIE_SECURE=true` is required
* `APP_MODE` is not supported; if present in `.env`, startup fails
* HTTP is for local/internal use (`SESSION_COOKIE_SECURE=false`); production should use HTTPS
* `API_DOCS_ENABLED` defaults to `false` (enable in local/dev only)
* `CORS_ALLOW_ALL` defaults to `false` (enable in local/dev only)
* `CSRF_SECRET_KEY` defaults to a per-process random value
* For multiple workers/instances, set a shared `CSRF_SECRET_KEY`
* The same shared secret is also used to sign drop-unlock grant cookies for password-protected links

Drop link password policy:
* `drop_password` is currently stored and compared as plain text.
* Treat it as a lightweight sharing guard, not an account-grade secret.
* Do not reuse account passwords as drop passwords.
* Web UI no longer carries drop passwords in the URL. A successful unlock sets a signed HttpOnly grant cookie instead.

Useful auth endpoints:
* `POST /api/auth/login`
* `GET /api/auth/me` (session or API key)
* `POST /api/auth/logout` (recommended)
* `GET /api/auth/logout` (compatible)

## Breaking Drop API (Reworked)
* `GET /api/drop?page=1&page_size=50&sort=created_at|title|size_bytes&order=asc|desc`
* `POST /api/drop` (multipart: `file`, `slug?`, `title?`, `description?`, `access_scope`, `drop_password?`)
* `GET /api/drop/{slug}/meta` (`X-Drop-Password` header for protected drops)
* `GET /api/drop/{slug}?disposition=attachment|inline` (`X-Drop-Password` header for protected drops, Range supported)
* `PATCH /api/drop/{slug}` (JSON body: `title?`, `description?`, `access_scope?`, `is_favorite?`, `new_password?`, `current_password?`)
* `DELETE /api/drop/{slug}` (`X-Drop-Password` header for protected drops)
* `GET /api/drop/availability/{slug}`

Ownership and masking rules:
* New drops are created for the currently authenticated user
* Private drops are visible only to their owner
* Private non-owner access is masked as `404` in both API and web UI

## Web Action Paths (HTMX Forms)
* `POST /actions/auth/login`
* `POST /actions/auth/logout`
* `POST /actions/auth/api-keys/create`
* `POST /actions/auth/api-keys/{public_id}/revoke`
* `POST /actions/auth/api-keys/{public_id}/delete`
* `POST /actions/drop/upload`
* `POST /actions/drop/{slug}/open`
* `POST /actions/drop/{slug}/detail`
* `POST /actions/drop/{slug}/unlock`
* `POST /actions/drop/{slug}/favorite`
* `POST /actions/drop/{slug}/access`
* `POST /actions/drop/{slug}/password`
* `POST /actions/drop/{slug}/delete`

## HTMX SSR Preview UI
* `GET /` (login + upload/list/detail management panel)
* `GET /<FILE_SLUG>` (dashboard preview view)
* `GET /settings/api-keys` (web API key management page; login required; shows only the current user's keys)
* UI write actions use CSRF-protected form submissions.
* Unlocking a password-protected drop redirects back to the clean URL without exposing the password in query parameters.
* After deploying a new `CSRF_SECRET_KEY`, previously rendered form tokens are expected to fail (403).
