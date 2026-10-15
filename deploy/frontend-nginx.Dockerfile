# Frontend clínico + Nginx (prod/staging en el host EMR).
# Contexto de build: raíz del repo. Referenciado por docker-compose.server.yml.
#
# Incluye location fijo del APK (/synesis-movil.apk → /srv/emr/public).
# El compose debe montar: /srv/emr/public:/srv/emr/public:ro

FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN if [ -f package-lock.json ]; then npm ci --legacy-peer-deps; else npm install --legacy-peer-deps; fi
COPY frontend/ ./
# Asegurar que el QR de public/ sea legible por nginx (evita 403 en el contenedor).
RUN chmod 644 public/qr-synesis-movil.png 2>/dev/null || true
ARG REACT_APP_API_URL=/api
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV CI=false
ENV DISABLE_ESLINT_PLUGIN=true
RUN npm run build

FROM nginx:1.27-alpine
# Conf con SPA + /api + APK persistente.
# (nginx.emr.test.conf = misma conf; nombre legacy del compose del host.)
COPY deploy/nginx/nginx.emr.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html
# Doble seguro: permisos de lectura en estáticos del login.
RUN chmod -R a+rX /usr/share/nginx/html \
    && chmod 644 /usr/share/nginx/html/qr-synesis-movil.png 2>/dev/null || true
EXPOSE 80
