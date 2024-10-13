# teledrop
Instant file cloud for device-to-device file sharing
## Installation
### 1. Prerequisites
* docker
### 2. Config your environments
1. Open `docker-compose.yml`
2. Set your host domain to `HOST_DOMAIN` to ARG
3. Mount your volume or directory to `/teledrop/share`
### 3. Run
```
teledrop$ docker compose up --build -d
```
