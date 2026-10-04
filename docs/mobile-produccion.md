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

En el server, una sola vez (nginx) y cada vez que haya APK nuevo:

```bash
# En el server — ver scripts/publish_movil_apk.sh y deploy/nginx/synesis-movil-apk.snippet.conf
sudo mkdir -p /srv/emr/public
# Copiar el APK descargado de EAS:
sudo cp /ruta/al/app-release.apk /srv/emr/public/synesis-movil.apk
sudo chmod 644 /srv/emr/public/synesis-movil.apk
```

Incluir el snippet de nginx en el `server { ... }` que atiende `:8080` HTTPS y recargar nginx.

URL fija: `https://emr.icpueblodeluis.com.ar:8080/synesis-movil.apk`  
QR imprimible: `mobile/assets/qr-instalacion-synesis-movil.png` (apunta a esa URL).

Cartel sugerido: «Android → escanear → permitir instalar → abrir SYNESIS → código ICPL → su usuario».

Al actualizar la app: reemplazar solo el archivo `.apk`; el QR impreso no cambia.

## 5. Prueba

Abrir SYNESIS móvil → **ICPL** → usuario paciente/médico de producción.
Acordar reservas de prueba: tocan la base real.

## 6. Pendientes posteriores

FCM/APNs; Play Store; iPhone (TestFlight/App Store); QR in-app para vincular clínica (distinto del QR de instalación).
