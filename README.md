[한국어](docs/ko/README.md) | [English](README.md)

# teledrop
Private file sharing platform for self-hosted servers, powered by REST API.

## About
> _teledrop is a private file-sharing platform designed for self-hosted servers, providing secure and direct access to personal files from anywhere. Unlike cloud storage services such as Google Drive or Dropbox, teledrop eliminates the need to log in with sensitive accounts in potentially insecure environments._

## Installation
### 1. Prerequisites
* Docker

### 2. Hash User Password
1. The password must be hashed using the Argon2 algorithm.
> **Warning:** When setting environment variables in the `compose.yml` file, make sure to replace `$` with `$$`. For example:
> ```yaml
> WEB_PASSWORD: $$argon2id$$v=19$$m=65536,t=3,p=4$$0123456789ABCDEF$$abcdefghijklmnopqrstuvwxyz0123456789
> ```
> This ensures that the `$` symbol is correctly escaped and not interpreted by Docker Compose.
2. `WEB_USERNAME` and `WEB_PASSWORD` are bootstrap-only values. On first startup with an empty database, teledrop creates the initial web user from those values. `WEB_PASSWORD` must be a valid Argon2 hash.
3. If the bootstrap values are omitted on an empty database, the initial user is created with `admin/password` only when `BOOTSTRAP_ALLOW_INSECURE_DEFAULTS=true`.
Set custom credentials and `BOOTSTRAP_ALLOW_INSECURE_DEFAULTS=false` before running any deployment exposed to other users. With that flag disabled, startup fails on an empty database if the credentials are missing, invalid, or still resolve to `admin/password`.

### 3. Run teledrop
* Configure `compose.yml` (Recommended)
Create `.env` next to `compose.yml` or export these variables before running Compose:
```dotenv
WEB_USERNAME=<YOUR_LOGIN_USERNAME>
WEB_PASSWORD='$argon2id$v=19$m=65536,t=3,p=4$...'
```

```yaml
services:
  teledrop:
    image: ghcr.io/onejajae/teledrop:latest
    container_name: teledrop
    restart: unless-stopped
    ports:
      - 80:8000/tcp
    volumes:
      - <YOUR_SHARE_DIRECTORY_OR_DOCKER_VOLUME>:/teledrop/share
    environment:
      TZ: Asia/Seoul
      WEB_USERNAME: ${WEB_USERNAME:?Set WEB_USERNAME before running docker compose}
      WEB_PASSWORD: ${WEB_PASSWORD:?Set WEB_PASSWORD to a valid Argon2 hash}
      BOOTSTRAP_ALLOW_INSECURE_DEFAULTS: "false"
```
```bash
docker compose up -d
```

* Run in the command line
```bash
docker run --detach \
   --name teledrop \
   -p 80:8000 \
   --env WEB_USERNAME \
   --env WEB_PASSWORD \
   --env BOOTSTRAP_ALLOW_INSECURE_DEFAULTS=false \
   --restart unless-stopped \
   --volume <YOUR_SHARE_DIRECTORY_OR_DOCKER_VOLUME>:/teledrop/share \
   ghcr.io/onejajae/teledrop:latest
```

### 4. Options
* Running behind a reverse proxy
> If teledrop is running behind a reverse proxy, add the following options to properly log the actual client IP addresses:
> ```yaml
> # compose.yml
> services:
>   teledrop:
>     ...
>     command: "--proxy-headers --forwarded-allow-ips *"
>     ...
	> ```

* Shared `CSRF_SECRET_KEY` for multiple workers/instances
> `CSRF_SECRET_KEY` defaults to a per-process random value.
> Set a shared value when running multiple workers/instances so CSRF validation remains consistent.
> ```yaml
> # compose.yml
> services:
>   teledrop:
>     environment:
>       - CSRF_SECRET_KEY=<YOUR_CSRF_SECRET>
> ```
> If you run with `docker run`, add:
> ```bash
> --env CSRF_SECRET_KEY=<YOUR_CSRF_SECRET> \
> ```

* Cookie security defaults
> `SESSION_COOKIE_SECURE` defaults to `true`.
> If `SESSION_COOKIE_SAMESITE=none`, `SESSION_COOKIE_SECURE=true` is required.
> `APP_MODE` is not supported. If it exists in `.env`, startup fails.
> Deployments exposed to users should run over HTTPS.
> HTTP is supported for local development or trusted internal networks by setting:
> ```yaml
> environment:
>   - SESSION_COOKIE_SECURE=false
>   - API_DOCS_ENABLED=true
>   - CORS_ALLOW_ALL=true
> ```

* API key auth for external clients
> REST API read endpoints accept either a session cookie or `X-API-Key`.
> REST API mutation endpoints (`POST/PATCH/DELETE /api/drop...`) require `X-API-Key`.
> API key management (create/revoke/delete) is available only in the authenticated web UI:
> `/settings/api-keys`
> Example request:
> ```bash
> curl -H "X-API-Key: tdpk_<public_id>_<secret>" http://localhost:8000/api/drop
> ```
> API key values are shown once at creation time and cannot be retrieved again.
> The API key page only lists keys owned by the current signed-in user.

* Upload and download security
> `MAX_UPLOAD_BYTES` defaults to 1073741824 bytes (1 GiB) and is enforced before and during file writes.
> File downloads always use `Content-Disposition: attachment`; `disposition=inline` is accepted only for compatibility and is ignored.
> Drop link passwords are stored as Argon2id hashes. Legacy plaintext protected drops are incompatible; back up and recreate the database before using this version.

* Running multiple worker processes
> To improve performance, specify the number of worker processes using the `--workers` option:
> ```yaml
> # compose.yml
> services:
>   teledrop:
>     ...
>     command: "--workers <NUMBER_OF_PROCESSES>"
>     ...
> ```
> Users, sessions, API keys, and drop ownership are stored in the database.
> If you run multiple instances/workers, all instances must share the same database and file storage.

* Direct app startup outside the Docker entrypoint
> teledrop creates the current database schema automatically at startup when the database is empty.
> Existing Alembic/legacy databases are not migrated automatically; back up and remove `share/database.db` before starting this version.

## Documentation
* [Authentication and API](docs/en/auth-and-api.md)
* [Slug Word Pools](docs/en/slug-word-pools.md)
* [Migration Notes](docs/en/migration.md)
* [Local Development and Tests](docs/en/local-dev-and-test.md)

## Build Docker image
Instead of using a pre-built Docker image, you can build your own:
```bash
docker build -t teledrop .
```
