# 1. web build
FROM node:20-alpine AS builder

# set workdir
WORKDIR /web

# install packages
COPY ./web/package.json ./
RUN npm install

# copy web sources
COPY ./web ./

# set arguments and env variables for vite
ARG HOST_DOMAIN=localhost
ARG PREFIX_API_BASE=/api

ENV VITE_API_HOST=$HOST_DOMAIN
ENV VITE_API_BASE=$PREFIX_API_BASE

# build
RUN npm run build


# 2. run server
FROM python:3.12-alpine
ENV PYTHONUNBUFFERED=1

# set workdir
WORKDIR /teledrop

# install packages
COPY ./requirements.txt ./
RUN pip install -r requirements.txt

# copy server sources -- exclude in .dockerignore
COPY ./main.py .
COPY ./api ./api

# copy builded web
COPY --from=builder /web/build ./web/build
EXPOSE 8000/tcp
CMD ["fastapi", "run"]