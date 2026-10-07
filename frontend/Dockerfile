# syntax=docker/dockerfile:1
#
# One image per app, each with its own builder: `--target user` (the user app, on /) and `--target admin` (the
# administration, on /admin). Node only builds; an image holds static files and nginx (unprivileged, port 8080), and
# forwards /api to the backend (same origin: no CORS).
#
#   docker build --target user  -t yimba-frontend-user  .
#   docker build --target admin -t yimba-frontend-admin .
#
# The builders share the dependency download (`deps`) but not their sources: a change in the admin app does not rebuild
# the user app, and each installs and compiles only its own app and the packages it uses.

ARG NODE_VERSION=24
ARG NGINX_VERSION=1.30

# ---- deps: every package of the lockfile, downloaded once ------------------------------------------------------------
FROM node:${NODE_VERSION}-alpine AS deps
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
WORKDIR /app
# pnpm at the version of "packageManager" in package.json.
RUN corepack enable
# Only the manifests: this layer is reused as long as they and the lockfile do not change.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY apps/user/package.json apps/user/
COPY apps/admin/package.json apps/admin/
COPY packages/api/package.json packages/api/
COPY packages/ui/package.json packages/ui/
RUN --mount=type=cache,id=pnpm-store,target=/pnpm-store pnpm fetch --store-dir /pnpm-store

# ---- builder of the user app -----------------------------------------------------------------------------------------
FROM deps AS build-user
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

# ---- builder of the administration -----------------------------------------------------------------------------------
FROM deps AS build-admin
# Where the administration sends to the user app ("Aller sur Yimba"): its address, from the outside.
ARG VITE_USER_URL=/
ENV VITE_USER_URL=${VITE_USER_URL}
COPY packages packages
COPY apps/admin apps/admin
RUN --mount=type=cache,id=pnpm-store,target=/pnpm-store \
    pnpm install --offline --frozen-lockfile --filter @yimba/admin... --store-dir /pnpm-store \
    && pnpm --filter @yimba/admin build \
    && find apps/admin/build -name '*.br' -delete

# ---- nginx, common to both images ------------------------------------------------------------------------------------
FROM nginxinc/nginx-unprivileged:${NGINX_VERSION}-alpine-slim AS serve
# Where /api goes (host:port). The entrypoint writes the configuration from the template at start, fills
# NGINX_LOCAL_RESOLVERS from /etc/resolv.conf (Docker or Kubernetes DNS), and starts one worker per CPU granted to
# the container rather than per CPU of the host.
ENV API_UPSTREAM=api:8800 \
    NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1 \
    NGINX_ENTRYPOINT_WORKER_PROCESSES_AUTOTUNE=1
COPY nginx/security-headers.conf /etc/nginx/security-headers.conf
EXPOSE 8080

# ---- the administration image ----------------------------------------------------------------------------------------
FROM serve AS admin
COPY nginx/admin.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build-admin /app/apps/admin/build /usr/share/nginx/html/admin

# ---- the user image (last: the default target) -----------------------------------------------------------------------
FROM serve AS user
COPY nginx/user.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build-user /app/apps/user/build /usr/share/nginx/html
