# syntax=docker/dockerfile:1
#
# The two single-page apps, served by nginx: the user app on /, the admin app on /admin, and /api forwarded to the
# backend (same origin: no CORS). Node only builds; the image holds static files and nginx (unprivileged, port 8080).

ARG NODE_VERSION=24
ARG NGINX_VERSION=1.30

FROM node:${NODE_VERSION}-alpine AS build
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
WORKDIR /app
# pnpm at the version of "packageManager" in package.json.
RUN corepack enable

# Dependencies first: this layer is reused as long as the manifests and the lockfile do not change.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY apps/user/package.json apps/user/
COPY apps/admin/package.json apps/admin/
COPY packages/api/package.json packages/api/
COPY packages/ui/package.json packages/ui/
RUN --mount=type=cache,id=pnpm-store,target=/pnpm-store \
    pnpm install --frozen-lockfile --store-dir /pnpm-store

COPY apps apps
COPY packages packages
# nginx serves the gzip files (gzip_static); it has no brotli module, so the .br files would only weigh on the image.
RUN pnpm build && find apps/*/build -name '*.br' -delete


FROM nginxinc/nginx-unprivileged:${NGINX_VERSION}-alpine-slim

# Where /api goes (host:port). The entrypoint writes the configuration from the template at start, fills
# NGINX_LOCAL_RESOLVERS from /etc/resolv.conf (Docker or Kubernetes DNS), and starts one worker per CPU granted to
# the container rather than per CPU of the host.
ENV API_UPSTREAM=api:8800 \
    NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1 \
    NGINX_ENTRYPOINT_WORKER_PROCESSES_AUTOTUNE=1

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY nginx/security-headers.conf /etc/nginx/security-headers.conf
COPY --from=build /app/apps/user/build /usr/share/nginx/html
COPY --from=build /app/apps/admin/build /usr/share/nginx/html/admin

EXPOSE 8080
