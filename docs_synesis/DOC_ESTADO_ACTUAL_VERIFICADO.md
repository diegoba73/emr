# DOC_ESTADO_ACTUAL_VERIFICADO — Baseline operativo SYNESIS EMR + LIMS

**Fecha de verificación inicial:** 20 de junio de 2026  
**Cierre técnico filtro `?estudio_id=` (fail-closed HTTP 400):** 20 de junio de 2026  
**Infraestructura tests backend (pytest, SQLite, PostgreSQL):** 20 de junio de 2026  
**Método:** Inspección directa del código + ejecución de tests (prevalece sobre documentación histórica).

---

## Resultado de cierre — infraestructura tests backend (20 jun 2026)

| Ítem | Estado |
|------|--------|
| `pytest` / `pytest-django` declarados | **Sí** — sección *Desarrollo / tests* en `requirements.txt` |
| `python manage.py check` | **OK** |
| Tests SQLite in-memory (`laboratorio/`, `usuarios/`, `auditoria/`) | **OK** (ver tabla abajo) |
| PostgreSQL nativo (`manage.py test`) | **NO VALIDADO** — `synesis_user` sin `CREATEDB` |
| Migraciones / modelos / permisos / frontend | **Sin cambios** en esta tarea |
| Deuda Jest (`App.test.tsx` / `react-big-calendar` ESM) | **Ticket separado** — no corregido |

**Estado de la tarea infra tests:** **CERRADA** (dependencias declaradas, comandos documentados, bloqueo PostgreSQL registrado).

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
| PostgreSQL nativo (`synesis_user`) | **NO VALIDADO** — `permission denied to create database` |
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

### Frontend (repositorio anidado `frontend/`)

- **Nota:** `frontend/` es un **repositorio Git anidado** (directorio con `.git` propio). En el monorepo padre aparece como **gitlink** (`m frontend` en `git status`); **no hay `.gitmodules`** — no está registrado como submódulo Git configurado.
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
| `python manage.py test laboratorio.tests.test_microbiologia_estudio_id_filter -v 2` | **FALLÓ** | Ver bloqueo PostgreSQL |

**Dependencias de test:** `pytest` y `pytest-django` añadidos a `requirements.txt` (sección desarrollo/test). Versiones en venv local al verificar: pytest 9.1.1, pytest-django 4.12.0.

### Backend — filtro `estudio_id` (iteración anterior)

| Comando | Resultado | Notas |
|---------|-----------|-------|
| `python manage.py check` | **OK** | 0 issues |
| `pytest laboratorio/tests/test_microbiologia_estudio_id_filter.py -q` | **OK** | 12 passed, 96 subtests; SQLite `:memory:` |
| `pytest laboratorio/tests/ -q` | **OK** | 328 passed, 96 subtests; SQLite |
| `pytest usuarios/tests/ -q` | **OK** | 44 passed; SQLite |
| `pytest auditoria/tests/ -q` | **OK** | 14 passed; SQLite |
| `python manage.py test …` (PostgreSQL default) | **FALLÓ** | `permission denied to create database` |

**Infra PostgreSQL (sin aprobar como test OK):**

- Usuario: `synesis_user` (desde `.env`, sin exponer credenciales)
- Comando: `python manage.py test laboratorio.tests.test_microbiologia_estudio_id_filter -v 2`
- Salida relevante: `Creating test database for alias 'default' ('test_synesis_db')...`
- Error exacto: `Got an error creating the test database: permission denied to create database`
- Solución DBA: `ALTER USER synesis_user CREATEDB;`

**Workaround validado (env vars ya soportadas por `synesis/settings.py`, sin tocar settings productivos):**

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
| `DOC_FRONTEND.md` | **Sí** — secciones legacy OBSOLETO; aclaración repo anidado |

---

## Seguridad

- Permisos LIMS: sin modificaciones
- Estados / auditoría mutante: sin modificaciones
- PHI en logs del filtro: **No**
- Enumeración por `estudio_id`: **Mitigado** — queryset por rol primero; estudio ajeno → vacío

---

## Limpieza de repo (esta iteración)

- Revertido `frontend/package-lock.json` (cambio masivo no necesario)
- Restaurados modos ejecutables de scripts shell revertidos (`backup_documentacion/*`, `deploy/*`, `entrypoint.sh`, `scripts/checkpoint.sh`)
- Eliminados archivos `._*` del árbol de trabajo
- Sin commit de archivos `.DS_Store`, `._*`, ni scripts de management no relacionados

---

## Riesgos pendientes

1. PostgreSQL: `synesis_user` sin `CREATEDB` — `manage.py test` / pytest sin vars SQLite no validados en este entorno.
2. ~~`pytest` no listado en `requirements.txt`~~ — **resuelto** (sección desarrollo/test).
3. `npm test` suite completa falla por `App.test.tsx` / `react-big-calendar` (ticket frontend separado).
4. `frontend/` como repo anidado sin `.gitmodules` — riesgo de desincronización vs monorepo padre.

---

## Próxima tarea recomendada

1. DBA: `ALTER USER synesis_user CREATEDB;` y re-ejecutar `python manage.py test laboratorio.tests.test_microbiologia_estudio_id_filter -v 2`.
2. Frontend: corregir Jest + `react-big-calendar` ESM en `App.test.tsx` (ticket separado).
3. CI: pipeline que instale `requirements.txt` y ejecute smoke SQLite (`manage.py check` + suites documentadas).
