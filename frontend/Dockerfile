# Stage 1: dev — Vite con hot-reloading
FROM node:26.2.0-alpine3.23 AS dev
RUN apk add --no-cache tzdata && npm install -g pnpm
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc* ./
RUN pnpm install
EXPOSE 5173
CMD ["pnpm", "dev", "--host"]

# Stage 2: build-stage — hereda node_modules del stage dev
FROM dev AS build-stage
COPY . .
RUN pnpm build

# Stage 3: prod — imagen mínima con Nginx sirviendo archivos estáticos
FROM nginx:1.30.1-alpine3.23 AS prod
RUN apk add --no-cache tzdata
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
