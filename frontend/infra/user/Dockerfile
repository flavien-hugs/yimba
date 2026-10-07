# syntax=docker/dockerfile:1
#
# Image of the user app: Node builds, nginx (unprivileged, port 8080) serves the static files and forwards /api to
# the backend (same origin: no CORS). The context is the frontend/ directory (the workspace):
#
#   docker build -f infra/user/Dockerfile -t yimba-frontend-user .      # from frontend/
#
# Its own builder: only this app and the packages it uses are installed and compiled, and the context
# (infra/user/Dockerfile.dockerignore) holds nothing of the other app, so a change there does not rebuild this image.

ARG NODE_VERSION=24
ARG NGINX_VERSION=1.30

# ---- dependencies: downloaded from the lockfile ---------------------------------------------------------------------
FROM node:${NODE_VERSION}-alpine AS deps
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
WORKDIR /app
# pnpm at the version of "packageManager" in package.json.
RUN corepack enable
# Only the manifests: this layer is reused as long as they and the lockfile do not change.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY apps/user/package.json apps/user/
COPY packages/api/package.json packages/api/
COPY packages/ui/package.json packages/ui/
RUN --mount=type=cache,id=pnpm-store,target=/pnpm-store pnpm fetch --store-dir /pnpm-store

# ----  ---------------------------------------------------------------------------------------------------------
FROM deps AS build
# Where the user app sends to the administration ("Administration" in the settings): its address, from the outside.
ARG VITE_ADMIN_URL=/admin/
ENV VITE_ADMIN_URL=${VITE_ADMIN_URL}
COPY packages packages
COPY apps/user apps/user
RUN --mount=type=cache,id=pnpm-store,target=/pnpm-store \
    pnpm install --offline --frozen-lockfile --filter @yimba/user... --store-dir /pnpm-store \
    && pnpm --filter @yimba/user build \
    # nginx serves the gzip files (gzip_static); it has no brotli module, so the .br files would only weigh.
    && find apps/user/build -name '*.br' -delete

# ---- image -----------------------------------------------------------------------------------------------------------
FROM nginxinc/nginx-unprivileged:${NGINX_VERSION}-alpine-slim
# Where /api goes (host:port). The entrypoint writes the configuration from the template at start, fills
# NGINX_LOCAL_RESOLVERS from /etc/resolv.conf (Docker or Kubernetes DNS), and starts one worker per CPU granted to
# the container rather than per CPU of the host.
ENV API_UPSTREAM=api:8800 \
    NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1 \
    NGINX_ENTRYPOINT_WORKER_PROCESSES_AUTOTUNE=1
COPY infra/security-headers.conf /etc/nginx/security-headers.conf
COPY infra/user/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/apps/user/build /usr/share/nginx/html
EXPOSE 8080
