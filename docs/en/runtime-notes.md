# Runtime Notes

## CSRF Secret Key
Set `CSRF_SECRET_KEY` when running teledrop.

Example in `docker-compose.yml`:
```yaml
services:
  teledrop:
    environment:
      - CSRF_SECRET_KEY=<YOUR_CSRF_SECRET>
```

Example in command line:
```bash
docker run --detach \
   --name teledrop \
   -p 80:8000 \
   --env WEB_USERNAME=<YOUR_LOGIN_USERNAME> \
   --env WEB_PASSWORD=<YOUR_HASHED_LOGIN_PASSWORD> \
   --env CSRF_SECRET_KEY=<YOUR_CSRF_SECRET> \
   --restart unless-stopped \
   --volume <YOUR_SHARE_DIRECTORY_OR_DOCKER_VOLUME>:/teledrop/share \
   ghcr.io/onejajae/teledrop:latest
```

## Running Multiple Worker Processes
Session authentication is stored in the database.  
If you run multiple instances/workers, all instances must share the same database and file storage.
