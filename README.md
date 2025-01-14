# teledrop
Private file sharing platform for self-hosted servers, powered by REST API.
## Installation
### 1. Prerequisites
* Docker
### 2. Configure Build Environment
1. Open the `docker-compose.yml` file.
2. Set the `HOST_DOMAIN` argument to your desired host domain.
3. Mount your docker volume or directory to `/teledrop/share`.
### 3. Set Up User Account
1. Open the `docker-compose.yml` file.
2. Set the `WEB_USERNAME` environment variable to your desired username.
3. Set the `WEB_PASSWORD` environment variable to your desired password.  
   ***Note: The password must be hashed using the Argon2 algorithm.***  
4. If these parameters are not set, the default account credentials will be `admin/password`.  
> **Warning:** When setting environment variables in the `docker-compose.yml` file, make sure to replace `$` with `$$`. For example:  
> ```yaml
> WEB_PASSWORD: $$argon2hash$$
> ```
> This ensures that the `$` symbol is correctly escaped and not interpreted by Docker Compose.
### 4. Run
```bash
docker compose up --build -d
```
