# Stack DEMO aislado (puerto 8081)

Segundo stack Docker **solo marketing/demo**, con Postgres y volumen propios.
No usa `emr_postgres` ni la BD clínica de producción.

| | Desarrollo habitual | Stack demo |
|--|---------------------|------------|
| Compose | `docker-compose.yml` / `./emrctl` | `docker-compose.demo.yml` |
| Proyecto | `emr` | `emr-demo` |
| Postgres | `emr_postgres` (:5432 host) | `emr_demo_postgres` (solo red interna; BD lógica `synesis_db` en **otro volumen**) |
| Volumen | `postgres_data` | `emr_demo_postgres_data` |
| URL | `:8000` / `:3000` | **http://localhost:8081** |
| Datos | QA + tu trabajo | `seed_data` + `seed_demo_marketing` |

## Local — arranque

```bash
cd /home/diego/proyectos/emr   # o tu ruta del repo
cp .env.demo.example .env.demo
# Editar secretos si querés; defaults sirven para local

docker compose -p emr-demo -f docker-compose.demo.yml --env-file .env.demo up -d --build

docker compose -p emr-demo -f docker-compose.demo.yml exec backend \
  python manage.py seed_data

docker compose -p emr-demo -f docker-compose.demo.yml exec backend \
  python manage.py seed_demo_marketing
```

Abrir: [http://localhost:8081/demo](http://localhost:8081/demo)

Usuarios: `medico1` / `medico123`, `laboratorio1` / `laboratorio123`,
`enfermeria1` / `enfermeria123`, `paciente1` / `paciente123`.

Comprobar que el stack de desarrollo sigue aparte:

```bash
docker ps --format '{{.Names}}' | grep -E 'emr_'
# Debe coexistir emr_postgres / emr_backend con emr_demo_*
```

## Parar solo el demo (sin tocar el clínico/dev)

```bash
docker compose -p emr-demo -f docker-compose.demo.yml down
# Datos demo persisten en volumen emr_demo_postgres_data
# Borrar datos demo: down -v  (SOLO el proyecto emr-demo)
```

## Producción (fase posterior)

1. NAT router: público **8081 → host EMR:8081** (clínico sigue en **8080**).
2. En el servidor (`ssh -p 2223`), directorio del repo o `/srv/emr-demo`.
3. `.env.demo` con hosts/CSRF `http://emr.sytes.net:8081` y secreto fuerte.
4. Mismo `up --build` + seeds.
5. URL: `http://emr.sytes.net:8081/demo`

**Prohibido:** `seed_demo_marketing` en el backend clínico; reutilizar volumen `postgres_data` / `postgres_data_prod`; `down -v` del proyecto clínico.

## Archivos

- `docker-compose.demo.yml`
- `deploy/Dockerfile.demo-nginx` (build React `REACT_APP_API_URL=/api` + nginx)
- `deploy/nginx/nginx.demo.conf`
- `.env.demo.example`

## Recorridos guiados por rol

La entrada `/demo` muestra el alcance y la cantidad de pasos de cada recorrido:

| Rol | Pasos | Contenido |
| --- | --- | --- |
| Médico | 15 | Agenda y filtros, pacientes, vista 360 y ficha detallada, atenciones, guardia, internación, laboratorio y estudios complementarios. |
| Laboratorio | 13 | Pendientes, etiquetas, recepción, órdenes, pestañas de muestras y resultados, validación por rol, informe finalizado, trazabilidad e inventario. |
| Enfermería | 13 | Camas, opciones del episodio y formularios, permisos de ingreso y alta, pacientes, historia, atenciones y laboratorio. |
| Paciente | 9 | Inicio, próximos turnos e historial, resultados liberados y PDF, documentos e historia. |

La guía navega entre pantallas y abre las pestañas de la orden LIMS. No ejecuta
recepciones, guarda resultados, valida informes ni envía documentos. Para explorar
las acciones manualmente se cierra la guía; el botón flotante permite reiniciarla.
Las explicaciones sobre las pestañas de internación indican cómo abrirlas manualmente.

Los pasos que necesitan un paciente u orden buscan coincidencias exactas con los
identificadores demo. Si falta el ejemplo, muestran un aviso y permiten continuar;
no abren el primer registro devuelto por la búsqueda. Si una sección no aparece
tras la espera de carga, también se informa en lugar de señalar otro elemento.

### Verificación del recorrido

- Entrar por `/demo` con cada rol y completar el recorrido, comprobando avance,
  retroceso, cierre, reinicio y cambio de rol.
- En laboratorio comprobar que se abren Resumen, Muestras y Resultados y que
  el ejemplo finalizado corresponde a `LAB-MKTG-00002`.
- Comprobar los recorridos con ejemplos ausentes y con pantalla angosta.
- Revisar que enfermería no presente alta médica y que laboratorio distinga
  carga de resultados de validación por bioquímico o administrador.

Pruebas automatizadas del controlador y la resolución de ejemplos:

```bash
cd frontend
CI=true npm test -- --watchAll=false --runInBand --runTestsByPath src/demo/DemoTourHost.test.tsx src/demo/demoResolve.test.ts
./node_modules/.bin/tsc --noEmit
```

## Identidad visual de ejemplo

La imagen demo se compila con `REACT_APP_DEMO_MODE=true`. Usa la identidad
**EMR DEMO · Entorno de ejemplo**, con un símbolo geométrico en versiones clara
 y oscura para menú, login y entrada del recorrido. El paso de build
`frontend/scripts/prepare-demo-branding.cjs` también adapta el título, favicon
 y manifiesto del demo. El logo institucional sigue disponible para el despliegue habitual.

### Demo dentro del mismo dominio que la clínica

En el frontend clínico, el logo institucional es el predeterminado. La entrada
`/demo` muestra la marca genérica y, al autenticar desde sus tarjetas, vincula
el modo demo al usuario autenticado. Terminar el recorrido conserva esa marca
para la exploración; **Salir del demo**, cerrar sesión o un ingreso normal
limpian la identidad demo. Las marcas antiguas del tour sin sesión identificada
no activan el logo genérico.

`REACT_APP_DEMO_MODE=true` se reserva para la imagen del stack exclusivamente demo
(`deploy/Dockerfile.demo-nginx`). No debe activarse en el build clínico que sirve
`emr_nginx_server`, aunque ese frontend también permita entrar a `/demo`.
