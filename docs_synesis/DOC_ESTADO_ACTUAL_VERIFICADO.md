# DOC_ESTADO_ACTUAL_VERIFICADO — Baseline operativo SYNESIS EMR + LIMS

**Fecha de verificación inicial:** 20 de junio de 2026  
**Cierre técnico filtro `?estudio_id=` (fail-closed HTTP 400):** 20 de junio de 2026  
**Infraestructura tests backend (pytest, SQLite, PostgreSQL):** 20 de junio de 2026  
**PostgreSQL smoke focal microbiología (CREATEDB validado en local):** 20 de junio de 2026  
**Método:** Inspección directa del código + ejecución de tests (prevalece sobre documentación histórica).

---

## Resultado de cierre — infraestructura tests backend (20 jun 2026)

| Ítem | Estado |
|------|--------|
| `pytest` / `pytest-django` declarados | **Sí** — sección *Desarrollo / tests* en `requirements.txt` |
| `python manage.py check` | **OK** |
| Tests SQLite in-memory (`laboratorio/`, `usuarios/`, `auditoria/`) | **OK** (ver tabla abajo) |
| PostgreSQL nativo — smoke focal (`manage.py test` filtro micro) | **OK** — `synesis_user` con `CREATEDB`; `test_synesis_db` creada/destruida |
| Suite PostgreSQL completa (`laboratorio/tests/`, `usuarios/`, `auditoria/` vía `manage.py test`) | **NO ejecutada** — opcional ampliar baseline |
| Migraciones / modelos / permisos / frontend | **Sin cambios** en esta tarea |
| Deuda Jest (`App.test.tsx` / `react-big-calendar` ESM) | **Ticket separado** — no corregido |

**Estado de la tarea infra tests:** **CERRADA** (dependencias declaradas, SQLite OK, smoke PostgreSQL focal OK en local).

---

## Resultado de cierre (filtro `estudio_id` — iteración anterior)

| Ítem | Estado |
|------|--------|
| Filtro `?estudio_id=` post-permisos | **Implementado** |
| Valores inválidos / cero / negativos / vacíos | **HTTP 400** (fail-closed) |
| Tests backend filtro | **12 tests, 96 subtests — OK** (SQLite in-memory) |
| `pytest laboratorio/tests/` | **328 passed** (SQLite in-memory) |
| `pytest usuarios/tests/` | **44 passed** (SQLite in-memory) |
| `pytest auditoria/tests/` | **14 passed** (SQLite in-memory) |
| Tests frontend alcance (`limsMicroApi` + detalle) | **15 passed** |
| `npm test -- --watchAll=false` (suite completa) | **FALLÓ** — `App.test.tsx` / `react-big-calendar` ESM (preexistente) |
| `npm run build` | **OK** |
| PostgreSQL nativo — smoke focal filtro micro (`synesis_user`) | **OK** (20 jun 2026, post-`CREATEDB`) — ver sección PostgreSQL abajo |
| Suite PostgreSQL completa | **NO ejecutada** |
| Migraciones / permisos / auditoría mutante | **Sin cambios** |

**Estado de la tarea filtro `estudio_id`:** **CERRADA** en código y tests de alcance.  
**Suite frontend global:** **NO CERRADA** por fallo preexistente ajeno al cambio.

---

## Implementación verificada

### Backend (`laboratorio/views_microbiologia.py`)

- `_apply_estudio_id_query_filter()` aplica filtro **después** del queryset autorizado por rol.
- Sin parámetro `estudio_id`: comportamiento previo.
- Con parámetro presente: entero positivo obligatorio; si no → `ValidationError` → **HTTP 400**.
- ID inexistente o no visible: lista vacía **200** (sin enumeración).

### Endpoints (8 recursos, ambos prefijos comparten ViewSet)

| Recurso | Lookup |
|---------|--------|
| `estudios/` | `pk` |
| `siembras/`, `lecturas/`, `aislados/`, `informes/` | `estudio_id` |
| `identificaciones/`, `antibiogramas/` | `aislado__estudio_id` |
| `resultados-antibiotico/` | `antibiograma__aislado__estudio_id` |

Prefijos: `/api/lab/microbiologia/*` y `/api/laboratorio/microbiologia/*`.

### Frontend (`frontend/` — monorepo)

- **Nota (jun 2026):** `frontend/` es carpeta normal del repo padre `emr`. Ya no es gitlink ni repo anidado con `.git` propio. SHA histórico del repo separado `emr-frontend`: `417e9a2`.
- **`frontend/package-lock.json` (estado actual):** versionado como archivo normal del monorepo desde la conversión jun 2026 (contenido importado del SHA histórico `417e9a2`; no regenerado en esa conversión).
- `limsMicroApi.ts`: 7 funciones `list*` aceptan `{ estudio_id?: number }`.
- `MicrobiologiaEstudioDetalle.tsx`: envía `estudio_id` server-side.

### Microbiología — migraciones (corrección documental)

- B3.1: `0005_lims_b3_1_microbiologia_base`
- B3.2: `0006_lims_b3_2_microbiologia_aislados`
- B3.3: `0007_lims_b3_3_microbiologia_antibiograma`
- **B3.4 informes: `0008_lims_b3_4_microbiologia_informes`**

---

## Resultados de tests ejecutados (20 jun 2026)

### Backend — infraestructura (esta tarea)

| Comando | Resultado | Notas |
|---------|-----------|-------|
| `python manage.py check` | **OK** | 0 issues |
| `DB_ENGINE=…sqlite3 DB_NAME=:memory: pytest laboratorio/tests/test_microbiologia_estudio_id_filter.py -q` | **OK** | 12 passed, 96 subtests; ~7 s |
| `DB_ENGINE=…sqlite3 DB_NAME=:memory: pytest laboratorio/tests/ -q` | **OK** | 328 passed, 96 subtests; ~102 s |
| `DB_ENGINE=…sqlite3 DB_NAME=:memory: pytest usuarios/tests/ -q` | **OK** | 44 passed; 1 warning paginación |
| `DB_ENGINE=…sqlite3 DB_NAME=:memory: pytest auditoria/tests/ -q` | **OK** | 14 passed; ~6 s |
| `python manage.py test laboratorio.tests.test_microbiologia_estudio_id_filter -v 2` (PostgreSQL) | **OK** | 12 tests; `test_synesis_db` creada/destruida; ~1.4 s |

**Dependencias de test:** `pytest` y `pytest-django` añadidos a `requirements.txt` (sección desarrollo/test). Versiones en venv local al verificar: pytest 9.1.1, pytest-django 4.12.0.

### Backend — filtro `estudio_id` (iteración anterior)

| Comando | Resultado | Notas |
|---------|-----------|-------|
| `python manage.py check` | **OK** | 0 issues |
| `pytest laboratorio/tests/test_microbiologia_estudio_id_filter.py -q` | **OK** | 12 passed, 96 subtests; SQLite `:memory:` |
| `pytest laboratorio/tests/ -q` | **OK** | 328 passed, 96 subtests; SQLite |
| `pytest usuarios/tests/ -q` | **OK** | 44 passed; SQLite |
| `pytest auditoria/tests/ -q` | **OK** | 14 passed; SQLite |
| `python manage.py test laboratorio.tests.test_microbiologia_estudio_id_filter -v 2` (PostgreSQL) | **OK** | 12 tests; ver validación PostgreSQL |

**Infra PostgreSQL — smoke focal validado (20 jun 2026, entorno local):**

- ENGINE: `django.db.backends.postgresql`
- BD productiva: `synesis_db` (`localhost:5432`)
- Usuario: `synesis_user` (`rolcreatedb=true`, `rolsuper=false`, `rolcreaterole=false`)
- Comando: `python manage.py test laboratorio.tests.test_microbiologia_estudio_id_filter -v 2`
- Salida relevante: `Creating test database for alias 'default' ('test_synesis_db')...` → migraciones → **12 tests OK** → `Destroying test database ... OK`
- `python manage.py check`: **OK**

**Histórico (misma iteración, antes de `CREATEDB` en local):** fallaba con `permission denied to create database`. En otros entornos, DBA: `ALTER USER synesis_user CREATEDB;`

**Pendiente opcional:** ampliar baseline PostgreSQL con `python manage.py test usuarios.tests auditoria.tests -v 2` y/o suite completa `laboratorio/tests/` (no ejecutada en esta verificación).

**Workaround SQLite (sigue siendo smoke rápido útil):**

```bash
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: pytest laboratorio/tests/test_microbiologia_estudio_id_filter.py -q
```

**Dependencias de test:** declaradas en `requirements.txt` — sección *Desarrollo / tests* (`pytest`, `pytest-django`).

### Frontend

| Comando | Resultado | Notas |
|---------|-----------|-------|
| `npm test -- --watchAll=false limsMicroApi.test.ts MicrobiologiaEstudioDetalle.test.tsx` | **OK** | 15 passed |
| `npm test -- --watchAll=false` | **FALLÓ** | 16/17 suites OK; `App.test.tsx` falla import ESM `react-big-calendar` vía `Turnos.tsx` — **preexistente**, no causado por filtro `estudio_id` |
| `npm run build` | **OK** | Warnings ESLint preexistentes en `api.ts` / `apiService.ts` |

---

## Documentación actualizada en esta tarea

| Archivo | Modificado |
|---------|------------|
| `requirements.txt` | **Sí** — sección desarrollo/test: `pytest`, `pytest-django` |
| `DOC_TESTS.md` | **Sí** — infra SQLite/PostgreSQL, CREATEDB, comandos reales |
| `DOC_ESTADO_ACTUAL_VERIFICADO.md` | **Sí** — este archivo |

### Iteración anterior (filtro `estudio_id`)

| Archivo | Modificado |
|---------|------------|
| `DOC_API_ENDPOINTS.md` | **Sí** — `?estudio_id=` IMPLEMENTADO; validación HTTP 400 |
| `DOC_FRONTEND.md` | **Sí** — secciones legacy OBSOLETO; nota histórica de estructura frontend (antes repo anidado/gitlink) |

---

## Seguridad

- Permisos LIMS: sin modificaciones
- Estados / auditoría mutante: sin modificaciones
- PHI en logs del filtro: **No**
- Enumeración por `estudio_id`: **Mitigado** — queryset por rol primero; estudio ajeno → vacío

---

## Limpieza de repo (iteración histórica — filtro `estudio_id`, jun 2026)

- Revertido `frontend/package-lock.json` en esa iteración anterior (cambio masivo no necesario para el filtro). **Estado actual (post-monorepo):** el lockfile vuelve a estar trackeado legítimamente como archivo normal; no fue regenerado en la conversión monorepo.
- Restaurados modos ejecutables de scripts shell revertidos (`backup_documentacion/*`, `deploy/*`, `entrypoint.sh`, `scripts/checkpoint.sh`)
- Eliminados archivos `._*` del árbol de trabajo
- Sin commit de archivos `.DS_Store`, `._*`, ni scripts de management no relacionados

---

## Riesgos pendientes

1. ~~PostgreSQL: `synesis_user` sin `CREATEDB`~~ — **resuelto en local (20 jun 2026):** smoke focal `manage.py test laboratorio.tests.test_microbiologia_estudio_id_filter` OK. Suite PostgreSQL completa sigue **opcional**.
2. ~~`pytest` no listado en `requirements.txt`~~ — **resuelto** (sección desarrollo/test).
3. `npm test` suite completa falla por `App.test.tsx` / `react-big-calendar` (ticket frontend separado).
4. ~~`frontend/` como repo anidado sin `.gitmodules`~~ — **resuelto (jun 2026):** `frontend/` integrado como carpeta normal del monorepo; repo `emr-frontend` queda como respaldo histórico (`417e9a2`).

---

## Próxima tarea recomendada

1. Ampliar baseline PostgreSQL: `python manage.py test usuarios.tests auditoria.tests -v 2` y/o `laboratorio/tests/` completo (opcional).
2. Frontend: corregir Jest + `react-big-calendar` ESM en `App.test.tsx` (ticket separado).
3. CI: pipeline que instale `requirements.txt` y ejecute smoke SQLite + smoke PostgreSQL focal documentados.
