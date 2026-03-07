[한국어](../ko/README.md) | [English](README.md)

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
2. If a user account is not set, the default account credentials will be `admin/password`.  
Set custom credentials before running any deployment exposed to other users.

### 3. Run teledrop
* Configure `compose.yml` (Recommended)
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
      - TZ=Asia/Seoul
      - WEB_USERNAME=<YOUR_LOGIN_USERNAME>
      - WEB_PASSWORD=<YOUR_HASHED_LOGIN_PASSWORD>  # Use $$ instead of $ in compose.yml
```
```bash
docker compose up -d
```

* Run in the command line
```bash
docker run --detach \
   --name teledrop \
   -p 80:8000 \
   --env WEB_USERNAME=<YOUR_LOGIN_USERNAME> \
   --env WEB_PASSWORD=<YOUR_HASHED_LOGIN_PASSWORD> \
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
> Protected REST API endpoints accept either a session cookie or `X-API-Key`.
> API key management (create/revoke/delete) is available only in the authenticated web UI:
> `/settings/api-keys`
> Example request:
> ```bash
> curl -H "X-API-Key: tdpk_<public_id>_<secret>" http://localhost:8000/api/drop
> ```
> API key values are shown once at creation time and cannot be retrieved again.
> `created_by_username` is stored as an audit snapshot field.

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
> Session authentication is stored in the database.  
> If you run multiple instances/workers, all instances must share the same database and file storage.

* Direct app startup outside the Docker entrypoint
> teledrop validates the database schema at startup but does not create tables automatically.
> Apply Alembic migrations before launching `uvicorn` directly:
> ```bash
> uv run alembic -c alembic.ini upgrade head
> ```

## Documentation
* [Authentication and API](auth-and-api.md)
* [Slug Word Pools](slug-word-pools.md)
* [Migration Notes](migration.md)
* [Local Development and Tests](local-dev-and-test.md)

## Build Docker image
Instead of using a pre-built Docker image, you can build your own:
```bash
docker build -t teledrop .
```
