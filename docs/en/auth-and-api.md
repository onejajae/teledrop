# Authentication and API

## Authentication
* Password login is required for web UI access
* `WEB_USERNAME` and `WEB_PASSWORD` are used only to bootstrap the first database-backed web user on an empty database
* Web registration is available only when `ENABLE_REGISTRATION=true`; the default is `false`
* REST API read endpoints accept:
  * session cookie authentication
  * `X-API-Key: tdpk_<public_id>_<secret>`
* REST API mutation endpoints (`POST/PATCH/DELETE /api/drop...`) require `X-API-Key` and do not accept session-only authentication
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
* `MAX_UPLOAD_BYTES` defaults to `1073741824` (1 GiB) and is enforced before and during upload writes
* `ENABLE_REGISTRATION` defaults to `false`. When disabled, the registration UI is hidden and direct registration requests return `404`
* `BOOTSTRAP_ALLOW_INSECURE_DEFAULTS` defaults to `true` for local development
* Production deployments should set `BOOTSTRAP_ALLOW_INSECURE_DEFAULTS=false`; with an empty database, startup then fails if `WEB_USERNAME`/`WEB_PASSWORD` are missing, `WEB_PASSWORD` is not a valid Argon2 hash, or the credentials still resolve to `admin/password`
* `CSRF_SECRET_KEY` defaults to a per-process random value
* For multiple workers/instances, set a shared `CSRF_SECRET_KEY`
* The same shared secret is also used to sign drop-unlock grant cookies for password-protected links

Drop link password policy:
* `drop_password` is stored as an Argon2id hash.
* Treat it as a lightweight sharing guard, not an account-grade secret.
* Do not reuse account passwords as drop passwords.
* Web UI no longer carries drop passwords in the URL. A successful unlock sets a signed HttpOnly grant cookie instead.
* Grant cookies are signed from the stored password hash material, not the raw password.
* Plaintext protected drops from older releases are intentionally incompatible; back up and recreate the database before using this version.

Useful auth endpoints:
* `POST /api/auth/login`
* `GET /api/auth/me` (session or API key)
* `POST /api/auth/logout`

## Breaking Drop API (Reworked)
* `GET /api/drop?page=1&page_size=50&sort=created_at|title|size_bytes&order=asc|desc`
* `POST /api/drop` (API key only, multipart: `file`, `slug?`, `title?`, `description?`, `access_scope`, `drop_password?`)
* `GET /api/drop/{slug}/meta` (`X-Drop-Password` header for protected drops)
* `GET /api/drop/{slug}` (`X-Drop-Password` header for protected drops, Range supported)
* `PATCH /api/drop/{slug}` (API key only, JSON body: `title?`, `description?`, `access_scope?`, `is_favorite?`, `new_password?`)
* `DELETE /api/drop/{slug}` (API key only)
* `GET /api/drop/availability/{slug}`

Ownership and masking rules:
* New drops are created for the currently authenticated user
* Private drops are visible only to their owner
* Private non-owner access is masked as `404` in both API and web UI

Known residual risk:
* Concurrent delete/download races are not changed in this wave. If a delete stages the file before a concurrent download stream opens it, that download can fail; this is covered by a strict xfail test until a later storage-level concurrency design is implemented.

## Web Action Paths (HTMX Forms)
* `POST /actions/auth/login`
* `POST /actions/auth/register` (only when `ENABLE_REGISTRATION=true`)
* `POST /actions/auth/logout`
* `POST /actions/auth/api-keys/create`
* `POST /actions/auth/api-keys/{public_id}/revoke`
* `POST /actions/auth/api-keys/{public_id}/delete`
* `POST /actions/drop/upload`
* `POST /actions/drop/{slug}/detail`
* `POST /actions/drop/{slug}/unlock`
* `POST /actions/drop/{slug}/favorite`
* `POST /actions/drop/{slug}/access`
* `POST /actions/drop/{slug}/password`
* `POST /actions/drop/{slug}/delete`

## HTMX SSR Web UI
* `GET /` (login or upload entry page)
* `GET /register` (registration page, only when `ENABLE_REGISTRATION=true`)
* `GET /drops` (owned drop library)
* `GET /drops/{slug}` (owned drop management page)
* `GET /<FILE_SLUG>` (shared download view)
* `GET /settings/api-keys` (web API key management page; login required; shows only the current user's keys)
* UI write actions use CSRF-protected form submissions.
* Unlocking a password-protected drop redirects back to the clean URL without exposing the password in query parameters.
* After deploying a new `CSRF_SECRET_KEY`, previously rendered form tokens are expected to fail (403).
