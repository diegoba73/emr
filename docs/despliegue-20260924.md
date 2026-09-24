# Actualización integral y catálogo de reactivos — 24/09/2026

Incluye resultados calculados, hemograma, microbiología y catálogos LabWin,
etiquetas, importadores y catálogo de reactivos e insumos. Requiere reconstruir
backend y frontend, y ejecutar todas las migraciones pendientes, incluidas
laboratorio 0049, 0051, 0052 y 0053. La 0050 ya existe en master.

## Comandos en producción

Usa la instalación documentada en `/srv/emr/app`, con `.env.server`,
`Dockerfile.server`, `docker-compose.server.yml` y contenedores
`emr_backend_server`, `emr_nginx_server`, `emr_postgres_server`.
Estos archivos específicos del servidor no están en el repositorio; comprobar
que conservan el montaje de media/static y el build de frontend actual.
Ejecutar cuando la publicación a GitHub esté confirmada y dentro de una ventana
de mantenimiento. El script detiene backend y nginx durante migración/importación.
Si existen otros procesos que escriben en la base, detenerlos durante esa ventana.

Desde tu computadora:

```bash
ssh -p 2223 server@emr.sytes.net
```

En el servidor, ejecutar este bloque completo. Se conserva la rama del servidor
y sus cambios de barcode mediante merge; no se reemplaza por master.

```bash
bash <<'BASH'
set -euo pipefail
cd /srv/emr/app
umask 077
git diff --quiet
git diff --cached --quiet
git rev-parse HEAD > /srv/emr/commit-antes-actualizacion-20260924.txt
git fetch origin
git merge --no-edit origin/master
bash scripts/actualizar_produccion_20260924.sh
BASH
```

Si hay cambios locales en archivos versionados o conflictos, el bloque se detiene:
resolverlos antes de ejecutar el script. El script conserva configuración,
exportaciones de los contenedores anteriores y un dump PostgreSQL comprobado con
`pg_restore --list` en una carpeta privada `/srv/emr/respaldo-20260924-*`.
Los rootfs no incluyen volúmenes; mantener los respaldos habituales de media.
Si falla después de detener los servicios, investigar antes de reabrirlos:
no se restaura automáticamente una base ni se ejecutan seeds de demostración.

## Reanudar si el respaldo falló con «role root does not exist»

Ese error ocurre antes de las migraciones y de la importación. El script corregido
toma usuario y base de la configuración de Django y comprueba la conexión antes
de detener servicios. Para este fallo concreto, si ambas imágenes ya se construyeron
y no cambió el código de la aplicación desde ese build, ejecutar en el servidor:

```bash
bash <<'BASH'
set -euo pipefail
cd /srv/emr/app
git fetch origin
git merge --no-edit origin/master
SKIP_BUILD=1 bash scripts/actualizar_produccion_20260924.sh
BASH
```

Se genera otro respaldo; el archivo incompleto de la ejecución fallida no se usa.
El script puede exportar los contenedores detenidos. Los servicios se levantan
al finalizar. No usar `SKIP_BUILD=1` si hay cambios posteriores de aplicación
que todavía no estén incorporados en las imágenes.

## Reactivos e insumos

Se usa `docs/Catalogo_reactivos.csv`: 56 filas, agrupadas en 53 productos.
El importador primero simula, aplica dentro de una transacción y vuelve a simular
para verificar que no queden cambios. Los tres informes quedan junto al respaldo.
Las cantidades creadas/actualizadas dependen del catálogo existente en producción.

Actualiza nombres y referencias comerciales y crea productos faltantes.
Conserva SKU existentes, equipos, proveedores, lotes, existencias y consumos.
Los productos nuevos quedan sin stock; controles, calibradores y limpieza se
registran como OTRO. No configura QC ni asigna equipos automáticamente.
Las referencias dudosas siguen pendientes de revisión. Para cargar existencias
reales se necesitan cantidades, unidades, lotes y vencimientos confirmados.

Las importaciones históricas LabWin y sus correcciones de escala son comandos
disponibles, pero no se ejecutan como parte de este despliegue. Los fixtures
mínimos de microbiología son solo para desarrollo, no para producción.

## Verificación al terminar

- Recargar la aplicación y comprobar login, una orden y carga de resultados.
- Abrir Inventario: buscar reactivos, controles y calibradores del CSV.
- Revisar microbiología e impresión/lectura de etiquetas con el flujo habitual.
- Confirmar que los servicios figuran activos; revisar logs si alguno reinicia.

## Validación local y límites conocidos

- Frontend: 63 suites, 318 pruebas aprobadas; build de producción correcto con
  advertencias ESLint. El build se generó en `/tmp` por permisos de la carpeta
  local `frontend/build`.
- Django: `makemigrations --check --dry-run` sin diferencias.
- Catálogo local: simulación con los 53 productos sin cambios pendientes.
- Verificación posterior de importadores LabWin, catálogo e inventario:
  54 pruebas aprobadas, incluidas las dos expectativas corregidas.
- La corrida general de laboratorio ejecutó 602 pruebas y detectó nueve fallos.
  Dos eran expectativas antiguas en pruebas nuevas de LabWin: exigir metadatos
  de escala antes de importar y mantener separados los códigos BACTE/NEMOTEC.
  Se actualizaron esas pruebas para comprobar las reglas documentadas.
- Los otros siete fallos se reprodujeron ejecutando las mismas pruebas contra
  el commit previo `1b8d455`: PDF de etiquetas, lookup inexistente (403/404),
  carga con muestra tomada, filtro por fecha de muestra, finalización con muestra
  tomada, orden del listado y validación del flujo crítico de microbiología.
  No se considera que la suite completa esté aprobada. Revisar estos flujos antes
  de usar el despliegue como una validación clínica; esta entrega publica el
  trabajo existente, no certifica esos circuitos.
- El script pasó `bash -n`. No se ejecutó contra el servidor de producción;
  sus archivos Docker específicos deben verificarse allí antes del despliegue.

Para futuras recreaciones conservar el override que desactiva seeds y migración
automática:

```bash
docker compose --env-file .env.server -f docker-compose.server.yml -f docker-compose.actualizacion-runtime.yml ps
docker compose --env-file .env.server -f docker-compose.server.yml -f docker-compose.actualizacion-runtime.yml logs --tail=100 backend nginx
```

No revertir solo el código después de cambios de esquema/datos sin evaluar
compatibilidad. El dump y la versión anterior permiten preparar una restauración
controlada; restaurar descarta escrituras posteriores al respaldo.
