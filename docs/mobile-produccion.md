# SYNESIS movil: APK independiente conectado a ICPL

Este perfil usa **datos reales de producción**, no una base de ensayo. Reservar, cancelar o reprogramar modifica turnos reales. El APK abre sin Metro, Wi-Fi compartido ni computadora encendida; requiere Internet y un servidor con HTTPS válido.

## Estado comprobado al preparar esta entrega

- API configurada: `https://emr.sytes.net:8080/api/movil`.
- El certificado público actual es autofirmado: la app lo rechaza correctamente.
- SSH desde el entorno de desarrollo es rechazado por la clave pública; la actualización debe ejecutarse con el acceso del operador.
- El perfil `preview` genera un APK firmado independiente, sin publicar en Play Store.
- Push permanece deshabilitado hasta configurar FCM/APNs y el programador.

## 1. Integrar GitHub en el servidor

Desde la computadora, conectarse con el mecanismo SSH habitual. Ya en el servidor:

```bash
cd /srv/emr/app
git status --short
git fetch origin
git log -1 --oneline origin/master
```

Si hay cambios locales, detenerse y revisarlos; no usar reset ni borrar archivos del servidor.
La rama clínica conocida es `cursor/fix-barcode-scanner-hyphen-df6e`; conservarla e integrar:

```bash
git merge origin/master
```

Si hay conflictos, resolverlos antes del despliegue. No reemplazar el Compose del servidor por el Compose local o de demo.

## 2. Actualizar backend y agenda web

El script preparado exige los archivos reales `docker-compose.server.yml` y `.env.server`, y verifica las etiquetas de los contenedores `emr_backend_server`, `emr_nginx_server`, `emr_postgres_server`.
Revisar que el Compose real tenga los servicios `backend` y `nginx`. Si los nombres difieren, adaptar después de inspeccionar; no adivinarlos.

```bash
cd /srv/emr/app
bash scripts/deploy_mobile_server.sh
```

Construye las imágenes, respalda PostgreSQL usando el usuario/base efectivos de Django y verifica el archivo del respaldo. Luego aplica migraciones y recrea solo backend/nginx en el mismo proyecto, sin tocar volúmenes ni levantar la demo. Puede haber una breve interrupción durante la recreación. El complemento `docker-compose.mobile.server.yml` configura ICPL y desactiva seed y push.
**No fue ejecutado remotamente desde el entorno de desarrollo.**

Para futuros comandos de Compose incluir también `-f docker-compose.mobile.server.yml`, o trasladar esas variables a la configuración efectiva del backend; omitir el complemento puede perder la identidad institucional.
Los respaldos y referencias de imágenes previas quedan en `/srv/emr/backups/mobile-FECHA/`, con permisos privados. Si falla antes de recrear los servicios, conservar los contenedores actuales e investigar. No restaurar la base automáticamente: las migraciones son aditivas y una restauración borraría operaciones posteriores al respaldo.

## 3. HTTPS sin abrir el puerto 80

El certificado debe ser confiable para Android/iOS y corresponder al dominio. No usar `curl -k` ni desactivar validación en la app como solución.
Como no se puede habilitar el 80, verificar una de estas opciones antes de emitir un certificado:

- DNS-01: control del TXT `_acme-challenge.emr.sytes.net` o un dominio propio con API DNS. No requiere entrada por 80. Automatizar renovación y recarga de Nginx.
- TLS-ALPN-01: requiere puerto público 443 y configurar un cliente compatible sin interrumpir el HTTPS existente.

No-IP gratuito no permite TXT; verificar el plan/control del nombre antes de elegir DNS-01. Si se usa otro dominio, actualizar hosts Django, proxy/certificado y el catálogo de `mobile/eas.json` antes de compilar.
El certificado emitido se puede servir por 8080. El despliegue conocido monta `/srv/emr/https-test/certs` en `emr_https_test`; su Nginx lee `emr.crt` y `emr.key`. No sobrescribirlos hasta tener el certificado correcto y respaldo de ambos. Instalar cadena completa, proteger clave privada, ejecutar `nginx -t` y recargar Nginx. Configurar renovación; la emisión manual sin renovación no constituye un despliegue terminado.

Referencias: [Let's Encrypt: validación](https://letsencrypt.org/docs/challenge-types/), [No-IP: limitaciones](https://www.noip.com/support/knowledgebase/free-enhanced-limitations).

## 4. Comprobar y construir el APK

Después de actualizar el backend e instalar el certificado, desde Ubuntu en la computadora:

```bash
cd /home/diego/proyectos/emr/mobile
npm run check:production
```

Debe verificar HTTPS, código ICPL y respuesta 401 del endpoint privado sin sesión. No usa contraseñas ni crea turnos.
Solo si pasa:

```bash
npx eas-cli@latest build --profile preview --platform android
```

Usar la clave de firma existente cuando EAS pregunte. No instalar en emulador: descargar el APK desde el enlace del build en el Android.
El perfil preview fija el catálogo de ICPL y deshabilita HTTP local; el `.env` de desarrollo no define el destino de ese perfil.
No publicar en Play Store todavía. La publicación es una acción distinta del build interno.

Abrir SYNESIS movil → código **ICPL** → usuario de producción. Verificar primero consulta de agenda con una cuenta autorizada. Acordar explícitamente cualquier reserva de comprobación, porque esta versión modifica la base real. La configuración de franjas sigue siendo exclusiva de secretaría/administración.

## 5. Pendientes posteriores

FCM/APNs y recordatorios reales; revisión en dispositivos Android/iPhone; arte y ficha de tiendas; segundo backend para incorporar otra clínica. El código QR no está implementado aún.
