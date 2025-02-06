[한국어](README.ko.md) | [English](README.md)

# teledrop
Private file sharing platform for self-hosted servers, powered by REST API.

## About
> _teledrop is a private file-sharing platform designed for self-hosted servers, providing secure and direct access to personal files from anywhere. Unlike cloud storage services such as Google Drive or Dropbox, teledrop eliminates the need to log in with sensitive accounts in potentially insecure environments._

## Installation
### 1. Prerequisites
* Docker

### 2. Hash User Password
1. The password must be hashed using the Argon2 algorithm.
> **Warning:** When setting environment variables in the `docker-compose.yml` file, make sure to replace `$` with `$$`. For example:  
> ```yaml
> WEB_PASSWORD: $$argon2id$$v=19$$m=65536,t=3,p=4$$0123456789ABCDEF$$abcdefghijklmnopqrstuvwxyz0123456789
> ```
> This ensures that the `$` symbol is correctly escaped and not interpreted by Docker Compose.
2. If a user account is not set, the default account credentials will be `admin/password`. 
**For security reasons, it is strongly recommended to set a custom username and password before running the application.**

### 3. Run teledrop
* Configure `docker-compose.yml` (Recommended)
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
      - WEB_PASSWORD=<YOUR_HASHED_LOGIN_PASSWORD>  # Use $$ instead of $ in docker-compose.yml
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
> # docker-compose.yml
> services:
>   teledrop:
>     ...
>     command: "--proxy-headers --forwarded-allow-ips *"
>     ...
> ``` 

* Running multiple worker processes
> To improve performance, specify the number of worker processes using the `--workers` option:
> ```yaml
> # docker-compose.yml
> services:
>   teledrop:
>     ...
>     command: "--workers <NUMBER_OF_PROCESSES>"
>     ...
> ```
> Set the `JWT_SECRET` environment variable to ensure token validation across worker processes:  
> ```yaml
> environment:
>   - JWT_SECRET=<YOUR_SECURE_RANDOM_SECRET>
> ```
> Example: Using OpenSSL to generate a secret key
> ```bash
> openssl rand -hex 32
> ```
> ***The generated key should be at least 32 bytes (256 bits) long. For enhanced security, you may use a longer key.***

## Build Docker image
Instead of using a pre-built Docker image, you can build your own:
```bash
docker build -t teledrop .
```
