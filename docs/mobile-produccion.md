# SYNESIS movil: APK para pacientes (ICPL)

Usa **datos reales de producción**. Reservar, cancelar o reprogramar modifica turnos reales.
El APK abre sin Metro ni PC; requiere Internet y HTTPS válido.

## Estado vigente

- API pública: `https://emr.icpueblodeluis.com.ar:8080/api/movil`
- Certificado: Let's Encrypt (confiable en Android)
- Perfiles EAS `preview` y `production`: misma URL pública (sin Tailscale)
- Descarga estable prevista: `https://emr.icpueblodeluis.com.ar:8080/synesis-movil.apk`
- Push: deshabilitado hasta FCM/APNs

## 1. Verificar API

```bash
curl -sS "https://emr.icpueblodeluis.com.ar:8080/api/movil/institucion/"
# → {"code":"ICPL",...}
curl -sS -o /dev/null -w "%{http_code}\n" "https://emr.icpueblodeluis.com.ar:8080/api/movil/me/"
# → 401
```

En el server, `DJANGO_ALLOWED_HOSTS` debe incluir `emr.icpueblodeluis.com.ar`.

## 2. Actualizar backend (si hace falta)

```bash
ssh -p 2223 server@emr.sytes.net
cd /srv/emr/app
git fetch origin
git merge --no-edit origin/master
bash scripts/deploy_mobile_server.sh
```

Conservar la rama del server y los compose locales. Incluir `-f docker-compose.mobile.server.yml` en operaciones Compose del stack clínico.

## 3. Comprobar y construir el APK

Desde Ubuntu:

```bash
cd /home/diego/proyectos/emr/mobile
npm run check:production
npx eas-cli@latest build --profile production --platform android
```

`check:production` valida HTTPS, código ICPL y 401 en `/me/` sin sesión.
Usar la clave de firma EAS existente. Descargar el APK del build (no emulador).

## 4. Publicar APK + QR (pacientes)

### Enlace y QR (ya fijos en el código)

| Qué | Valor |
|-----|--------|
| URL | `https://emr.icpueblodeluis.com.ar:8080/synesis-movil.apk` |
| Login web | constante `MOVIL_APK_URL` + imagen `frontend/public/qr-synesis-movil.png` |
| QR imprimible | `mobile/assets/qr-instalacion-synesis-movil.png` |

No regenerar el QR ni cambiar la URL al publicar una versión nueva de la app.

### Por qué “se pierde” al regenerar

Si el APK se copia **dentro** del contenedor (`docker cp …:/usr/share/nginx/html/…`), al recrear/redeployar nginx el archivo desaparece. El QR sigue apuntando a la misma URL, pero el servidor responde 404.

**Solución:** el APK vive en el host en `/srv/emr/public/synesis-movil.apk` y nginx lo monta en solo lectura. Regenerar contenedores no lo borra.

### Una sola vez en el server (persistencia)

En el `docker-compose` real de prod (p. ej. `/srv/emr/app/docker-compose.server.yml`), servicio nginx:

```yaml
volumes:
  - /srv/emr/public:/srv/emr/public:ro
```

Incluir el location de `deploy/nginx/synesis-movil-apk.snippet.conf` en el `server { … }` del dominio clínico y recrear nginx:

```bash
sudo mkdir -p /srv/emr/public
# … editar compose + conf nginx …
docker compose -f docker-compose.server.yml up -d nginx   # o el compose real del host
```

### Cada vez que haya APK nuevo

```bash
# En el server — NO uses solo docker cp al html del contenedor
bash scripts/publish_movil_apk.sh /ruta/al/app-release.apk
curl -sSI 'https://emr.icpueblodeluis.com.ar:8080/synesis-movil.apk' | head -15
# Esperado: HTTP 200 y Content-Type application/vnd.android.package-archive
```

Cartel sugerido: «Android → escanear → permitir instalar → abrir SYNESIS → código ICPL → su usuario».

## 5. Prueba

Abrir SYNESIS móvil → **ICPL** → usuario paciente/médico de producción.
Acordar reservas de prueba: tocan la base real.

## 6. Pendientes posteriores

FCM/APNs; Play Store; iPhone (TestFlight/App Store); QR in-app para vincular clínica (distinto del QR de instalación).
