# Etapa 1: build de la SPA
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY index.html vite.config.js ./
COPY public/ public/
COPY src/ src/
RUN npm run build

# Etapa 2: nginx sirviendo estáticos + proxy /api → api:8000.
# Como plantilla (templates/): el entrypoint de nginx sustituye ${API_TOKEN}
# con envsubst al arrancar — el token no queda horneado en la imagen.
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

# 127.0.0.1 explícito: el wget de busybox resuelve localhost a ::1 y nginx escucha en IPv4
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
