ARG UV_VERSION=0.11.7

# 1. node base for building tailwind css
FROM node:24-alpine AS node_builder
WORKDIR /app
COPY ui-build/package.json ui-build/package-lock.json ./ui-build/
COPY ui-build/scripts ./ui-build/scripts
COPY app/interfaces/web/static ./app/interfaces/web/static
COPY app/interfaces/web/templates ./app/interfaces/web/templates
WORKDIR /app/ui-build
RUN npm ci
RUN npm run build

# python base image
FROM python:3.14-alpine AS python_base

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# 2. dependencies install
FROM python_base AS dependency_builder
COPY --from=uv /uv /bin/uv
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

# copy teledrop sources 
COPY ./main.py .
COPY ./app ./app
COPY ./scripts/docker-entrypoint.sh ./scripts/docker-entrypoint.sh
# Copy built css from node_builder
COPY --from=node_builder /app/app/interfaces/web/static/gen/output.css ./app/interfaces/web/static/gen/output.css
COPY --from=node_builder /app/app/interfaces/web/static/vendor ./app/interfaces/web/static/vendor

# set path
ENV PATH="/teledrop/.venv/bin:$PATH"

RUN chmod +x ./scripts/docker-entrypoint.sh

# run
EXPOSE 8000/tcp
ENTRYPOINT ["./scripts/docker-entrypoint.sh"]
