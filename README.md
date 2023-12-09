# teledrop
Instant file cloud for device-to-device file sharing
## Installation
### 1. Prerequisites
* Python 3.11+
* nodejs 20+
* docker
### 2. Write your environments
1. `teledrop/.env.prod` for api server
2. `teledrop/web/.env.production` for web server
### 3. Build
1. Frontend Build
```
teledrop$ cd web/
teledrop/web$ npm i
teledrop/web$ npm run build
```
2. Docker Image Build
```
teledrop$ docker compose build
```
## Run
```
teledrop$ docker compose up
```