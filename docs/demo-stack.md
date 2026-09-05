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
3. `.env.demo` con hosts/CSRF `http://dsachubut.sytes.net:8081` y secreto fuerte.
4. Mismo `up --build` + seeds.
5. URL: `http://dsachubut.sytes.net:8081/demo`

**Prohibido:** `seed_demo_marketing` en el backend clínico; reutilizar volumen `postgres_data` / `postgres_data_prod`; `down -v` del proyecto clínico.

## Archivos

- `docker-compose.demo.yml`
- `deploy/Dockerfile.demo-nginx` (build React `REACT_APP_API_URL=/api` + nginx)
- `deploy/nginx/nginx.demo.conf`
- `.env.demo.example`
