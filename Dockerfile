# 1. web build
FROM node:20-alpine AS web_builder

# set workdir
WORKDIR /web

# install packages
COPY ./web/package*.json ./
RUN npm install

# copy web sources
COPY ./web ./

# web build
RUN npm run build


# python base image
# FROM python:3.12-slim AS python_base
FROM python:3.12-alpine AS python_base

# 2. dependencies install
FROM python_base AS dependency_builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# set workdir
WORKDIR /teledrop

# install packages
COPY uv.lock pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev


# 3. deploy stage
FROM python_base
WORKDIR /teledrop

# copy dependencies
COPY --from=dependency_builder /teledrop ./

# copy built web
COPY --from=web_builder /web/build ./web/build

# copy teledrop sources 
COPY ./main.py .
COPY ./api ./api

# set path
ENV PATH="/teledrop/.venv/bin:$PATH"

# run
EXPOSE 8000/tcp
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--no-server-header"]
