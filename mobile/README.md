# SYNESIS movil

Aplicación Android/iOS de turnos para pacientes y médicos, conectada al EMR existente.
Nombre visible: **SYNESIS movil**. Fuente React Native / Expo Router en `src/app`.

## Qué incluye

- Acceso con usuarios existentes del EMR (paciente/médico), sesión revocable de 30 días y token en SecureStore.
- Paciente: calendario, elección de médico y consulta/estudio, disponibilidad real en bloques de 20 minutos, reserva, confirmación de asistencia, cancelación y reprogramación.
- Médico: sus propios turnos, calendario, respuesta de asistencia del paciente y gestión de sus turnos.
- La app no permite configurar franjas de atención: corresponde a secretaría/administración desde el EMR.
- El paciente no selecciona consultorio ni prioridad. El servidor determina esos datos.
- Recordatorio push alrededor de 24 horas antes, con enlace al turno; requiere iniciar sesión y activar avisos.
- Confirmar asistencia no equivale a la confirmación administrativa del turno. No responder no cancela automáticamente.

## Estado y pendientes externos

Código y migraciones preparados localmente; no publicado ni desplegado en producción.
La exportación de JavaScript para ambas plataformas no es un APK/AAB/IPA firmado ni una prueba en celulares.
Los íconos son provisionales del proyecto Expo; reemplazarlos antes de publicar.
Faltan cuentas de Google Play, Apple Developer y proyecto Expo/EAS; credenciales FCM/APNs; política de privacidad, ficha de tiendas y prueba real de instalación/notificaciones.
Los identificadores `net.sytes.emr.synesismovil` son provisionales: confirmar titular e identificadores antes de la primera publicación.

## Preparar desarrollo

Desde `/home/diego/proyectos/emr/mobile`, con Node compatible con Expo 57:

```bash
npm ci
cp .env.example .env
```

Editar `.env`: `EXPO_PUBLIC_API_URL` debe apuntar a un backend de prueba con estas migraciones y HTTPS confiable.
No usar `localhost` para acceder desde un teléfono: representa al propio teléfono.
El ejemplo de producción es `https://emr.sytes.net:8080/api/movil`; no utilizarlo para crear turnos de prueba de pacientes reales.
Nunca colocar contraseñas, claves privadas ni credenciales del proveedor en variables `EXPO_PUBLIC_*`.

```bash
npm run typecheck
npm run lint
npm test
npx expo export --platform android --platform ios
```

## Backend y recordatorios

La nueva API se monta en `/api/movil/`. Usa Bearer móvil independiente del acceso web.
El backend guarda solamente un hash del token. Cerrar sesión revoca la sesión y desactiva sus dispositivos.

Antes de actualizar producción: respaldar la base, desplegar el código completo de agenda de 20 minutos y móvil, construir la imagen backend y ejecutar migraciones en esa imagen.
En el servidor conocido, una vez reconstruido el servicio:

```bash
cd /srv/emr/app
docker exec emr_backend_server python manage.py migrate
docker exec emr_backend_server python manage.py check
```

No basta hacer `git pull`: el contenedor debe contener el nuevo código. El archivo Compose del servidor se mantiene allí; usar su configuración real para reconstruir, sin reemplazarlo por el Compose de demo.

Configurar en el entorno del backend:

```dotenv
MOBILE_PUSH_ENABLED=true
EXPO_ACCESS_TOKEN=valor_privado_si_el_proyecto_usa_push_security
```

El envío está desactivado por defecto. Habilitarlo después de configurar credenciales y probar con usuarios de prueba.
Programar en el servidor un único cron cada cinco minutos (usuario con acceso a Docker), con archivo de log y rotación:

```cron
*/5 * * * * /usr/bin/flock -n /tmp/synesis-movil-recordatorios.lock /usr/bin/docker exec emr_backend_server python manage.py recordatorios_turnos >> /srv/emr/recordatorios.log 2>&1
```

Verificar previamente rutas de docker/flock y permisos del log. Una alternativa es el programador de tareas ya utilizado por la infraestructura.
Se procesan hasta 100 envíos y 100 recibos por ejecución: monitorear retrasos y ajustar capacidad si crece el volumen.
Monitorear salida y estados ERROR/pendientes antiguos en RecordatorioTurno; no registrar tokens ni datos clínicos.

El proceso vuelve a comprobar estado, fecha, sesión y asistencia antes del envío. Una reprogramación descarta el aviso anterior y reinicia la confirmación de asistencia.
Reservas hechas con menos de 24 horas reciben el aviso en el siguiente ciclo.
Hay reintentos acotados y deduplicación por turno/dispositivo/fecha. Un timeout después de aceptar el proveedor puede producir un duplicado: no se garantiza entrega exactamente una vez.
ACEPTADO significa que Expo aceptó el envío; ENTREGADO significa aceptación por FCM/APNs, no lectura ni entrega comprobada al teléfono.
Los avisos muestran texto genérico sin nombre del paciente, médico ni información clínica.

## Construcción y tiendas

Luego de crear las cuentas bajo la titularidad del responsable de la app:

1. Iniciar sesión en Expo y crear/vincular el proyecto:
   `npx eas-cli@latest login`, luego `npx eas-cli@latest init`.
2. Completar `EXPO_PUBLIC_EAS_PROJECT_ID`, identificadores definitivos y credenciales push siguiendo la documentación oficial. Configurar también variables del entorno EAS de cada perfil; no asumir que el archivo local estará en el build remoto.
3. Preparar Android FCM y Apple APNs mediante EAS. El archivo `google-services.json` se referencia con `GOOGLE_SERVICES_JSON`; mantenerlo fuera de Git.
4. Crear builds de desarrollo:
   `npx eas-cli@latest build --profile development --platform android` y su equivalente `--platform ios`.
5. Instalar en teléfonos de prueba y ejecutar `npx expo start --dev-client`.
6. Probar acceso, reserva concurrente, cancelación, reprogramación, permisos denegados, sesión vencida y avisos con app abierta/cerrada. Comprobar que abrir una notificación exige la sesión correcta.
7. Después de validar: `npx eas-cli@latest build --profile production --platform all`.
8. Revisar las fichas, privacidad, capturas y requisitos de las tiendas antes de enviar builds con EAS Submit. Esta documentación no publica automáticamente.

Documentación oficial:
- [Expo SDK 57](https://docs.expo.dev/versions/v57.0.0/)
- [Configuración de push y builds de desarrollo](https://docs.expo.dev/push-notifications/push-notifications-setup/)
- [Envío y recibos de notificaciones](https://docs.expo.dev/push-notifications/sending-notifications/)

## Pruebas del backend

Desde la raíz del repositorio, usando base aislada:

```bash
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: .venv/bin/python -m pytest movil/tests medicos/tests/test_agenda_reservas.py turnos/tests/test_permissions_mutations.py -q
```

Estas pruebas comprueban permisos, expiración y revocación, reserva/reprogramación, confirmación de asistencia y recordatorios simulados. No envían push reales.
Antes del lanzamiento también deben verificarse concurrencia y bloqueos con PostgreSQL, además de los dispositivos físicos.

## Prueba Android por Wi-Fi (desarrollo local)

La API local verificada está en `http://192.168.1.94:8000/api/movil`.
`mobile/.env` (excluido de Git) contiene esa URL y `EXPO_PUBLIC_ALLOW_LOCAL_HTTP=true`.
Esta excepción funciona solamente con `__DEV__` y direcciones IPv4 privadas.
El perfil EAS `development` habilita tráfico HTTP Android; los perfiles de distribución conservan HTTPS.
Usar usuarios y datos ficticios durante esta prueba HTTP en una red de confianza.
Si cambia la IP de Windows, actualizar `.env` y `EMR_DEV_ALLOWED_HOSTS` del backend local.

Desde `mobile`, generar el instalador con:

```bash
npx eas-cli@latest build --profile development --platform android
```

Instalar el APK que proporciona EAS. Después iniciar Metro con `npx expo start --dev-client`.
En WSL, el celular también debe alcanzar el puerto de Metro: que funcione el backend en 8000 no garantiza que 8081/8082 esté accesible.
Se puede usar el túnel de Expo para Metro (`npx expo start --dev-client --tunnel --port 8082`); la API seguirá usando el Wi-Fi local.
Las notificaciones push reales quedan pendientes de configurar FCM y habilitar el backend.

## Instituciones: vinculación por código

Al abrir la app se ingresa un código de clínica. Para la prueba local: **ICPL**.
Se verifica `/api/movil/institucion/` antes de habilitar el acceso. La institución aparece en todas las pantallas; ICPL utiliza su logo existente del EMR.
En Mi cuenta → Cambiar clínica se revoca primero la sesión anterior (incluidos dispositivos push). Si el servidor no responde, el cambio se detiene para no dejar notificaciones activas de una sesión abandonada.
La app recuerda la institución; las credenciales están guardadas por código y vinculadas a la URL exacta. No se reutilizan tokens antiguos sin institución.

Cada clínica debe tener su propio despliegue y base. No se habilita una base compartida ni acceso cruzado. El código es público, no otorga permisos: se exige usuario de la institución.

En cada backend configurar:

```dotenv
MOBILE_INSTITUTION_CODE=ICPL
MOBILE_INSTITUTION_NAME=Instituto de Cardiología Pueblo de Luis
```

En producción no hay institución por defecto. Configurar el catálogo autorizado de la app en `EXPO_PUBLIC_CLINICS_JSON` (JSON en una sola línea), por ejemplo:

```json
[{"code":"ICPL","name":"Instituto de Cardiología Pueblo de Luis","apiUrl":"https://servidor-de-la-clinica.example/api/movil","logoUrl":"https://servidor-de-la-clinica.example/logo.png"}]
```

Sustituir las URLs de ejemplo por las reales. El editor de la app administra ese catálogo; no se aceptan URLs introducidas por pacientes. Los endpoints y logos de producción requieren HTTPS. El catálogo es público, sin secretos. Cambiar el catálogo requiere distribuir una actualización de la app; el directorio remoto y los QR quedan para otra etapa.
Las notificaciones ahora incluyen el código de institución; se ignoran enlaces de notificaciones antiguas o de otra institución para no confundir IDs de turnos.

Validación manual: vincular ICPL, verificar su logo/nombre, ingresar, reservar, cambiar clínica y confirmar nuevo acceso. Para validar dos instituciones reales se necesita un segundo backend separado y su entrada en el catálogo.
