# Production image for the ops dashboard (static build + nginx).
# Context is the REPO ROOT. VITE_API_URL bakes the API origin in at build time;
# leave it empty for same-origin serving behind the nginx /api proxy below.
# Build: docker build -f frontend/Dockerfile -t smart-erp-frontend .
ARG VITE_API_URL=""

FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
