[한국어](README.ko.md) | [English](README.md)

# teledrop
Private file sharing platform for self-hosted servers, powered by REST API.

## About

> _teledrop is a private file-sharing platform designed for self-hosted servers, providing secure and direct access to personal files from anywhere. Unlike cloud storage services such as Google Drive or Dropbox, teledrop eliminates the need to log in with sensitive accounts in potentially insecure environments._

## Installation

### 1. Prerequisites

* Docker

### 2. Hash User Password

1. Generate an Argon2id hash using the image's `hash-password` command.

```bash
docker run --rm -it ghcr.io/onejajae/teledrop:latest hash-password
```

Enter the password twice with hidden input. The command prints the hash and exits without requiring server settings or volumes. If the published image does not include the command yet, see [Build Docker image](#build-docker-image) below.

> **Warning:** Replace every `$` with `$$` when writing the hash directly in `compose.yml`.
>
> ```yaml
> WEB_PASSWORD: '$$argon2id$$v=19$$m=65536,t=3,p=1$$<salt>$$<hash>'
> ```
>
> This is a format example; use your complete generated hash. With `docker run --env`, keep single `$` characters and enclose the value in single quotes.

2. `WEB_USERNAME` and `WEB_PASSWORD` are required. The server refuses to start without them. Usernames are case-sensitive.

### 3. Run teledrop

* Configure `compose.yml` (Recommended)

```yaml
services:
  teledrop:
    image: ghcr.io/onejajae/teledrop:latest
    container_name: teledrop
    restart: unless-stopped
    ports:
      - 80:8080/tcp
    volumes:
      - <YOUR_SHARE_DIRECTORY_OR_DOCKER_VOLUME>:/app/share
    environment:
      - TZ=Asia/Seoul
      - WEB_USERNAME=<YOUR_LOGIN_USERNAME>
      - WEB_PASSWORD=<YOUR_HASHED_LOGIN_PASSWORD>  # Use $$ instead of $ in compose.yml
      - SHARE_DIRECTORY=/app/share
```

```bash
docker compose up -d
```

* Run in the command line

```bash
docker run --detach \
   --name teledrop \
   -p 80:8080 \
   --env WEB_USERNAME='<YOUR_LOGIN_USERNAME>' \
   --env WEB_PASSWORD='<YOUR_HASHED_LOGIN_PASSWORD>' \
   --env SHARE_DIRECTORY='/app/share' \
   --restart unless-stopped \
   --volume '<YOUR_SHARE_DIRECTORY_OR_DOCKER_VOLUME>:/app/share' \
   ghcr.io/onejajae/teledrop:latest
```

### 4. Options

* Running behind a reverse proxy

> Add this entry to the existing environment variable list in `compose.yml` to preserve the original client IP and request scheme.
>
> ```yaml
> environment:
>   - ASPNETCORE_FORWARDEDHEADERS_ENABLED=true
> ```
>
> Disabled by default. When enabled, it trusts `X-Forwarded-For` and `X-Forwarded-Proto` from all proxies. Make the application reachable only through your proxy, and configure the proxy to set forwarded headers correctly.

* Enabling API uploads

> Configure an authentication key to use API uploads.
>
> ```yaml
> environment:
>   - TELEDROP_API_KEY=<YOUR_API_KEY>
> ```
>
> Send the same key in the `X-API-Key` header of `/api/upload` requests. If unset, API uploads return 401; web uploads remain available.

* Changing the upload size limit

> The default is `1073741824` bytes (1 GiB). Set a positive byte value.
>
> ```yaml
> environment:
>   - MAX_UPLOAD_BYTES=1073741824
> ```
>
> The limit applies to both the file and the entire request body. Multipart overhead counts toward the limit, so the effective maximum file size is smaller.

* Automating password hash generation

> `--stdin` reads the first input line without confirmation and outputs only the hash. Do not pass passwords as command-line arguments.
>
> ```bash
> docker run --rm -i ghcr.io/onejajae/teledrop:latest hash-password --stdin < /path/to/password.txt
> ```
>
> After configuring Compose, use `docker compose run --rm --no-deps teledrop hash-password` for interactive hidden input as well.

Apply environment variable changes by recreating the container with `docker compose up -d`.

## Build Docker image

Build an image from the current source:

```bash
docker build -t teledrop:local .
docker run --rm -it teledrop:local hash-password
```

Replace the image name in the run examples with `teledrop:local`.
