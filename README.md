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
2. If a user account is not set, the default account credentials will be `admin/password`.  
**In prod mode, the default `admin/password` combination is blocked. Set custom credentials before running.**

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
> `APP_MODE` defaults to `prod`.
> In `prod`, `SESSION_COOKIE_SECURE` defaults to `true` (if not explicitly set).
> If `SESSION_COOKIE_SAMESITE=none`, `SESSION_COOKIE_SECURE=true` is required.

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
