# DOC_ESTADO_ACTUAL_VERIFICADO — Baseline operativo SYNESIS EMR + LIMS

**Fecha de verificación inicial:** 20 de junio de 2026  
**Cierre técnico filtro `?estudio_id=` (fail-closed HTTP 400):** 20 de junio de 2026  
**Infraestructura tests backend (pytest, SQLite, PostgreSQL):** 20 de junio de 2026  
**PostgreSQL smoke focal microbiología (CREATEDB validado en local):** 20 de junio de 2026  
**Cierre deuda Jest global frontend (`react-big-calendar`, commit `30e75d3`):** 21 de junio de 2026  
**CI/smoke mínimo (`.github/workflows/smoke.yml` + `scripts/smoke_local.sh`):** 21 de junio de 2026
**Corrección smoke remoto frontend build (CRA + CI=true):** 21 de junio de 2026
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
| Deuda Jest (`App.test.tsx` / `react-big-calendar` ESM) | **CERRADA** — commit `30e75d3`; mock Jest en `setupTests.ts` + `__mocks__/react-big-calendar.tsx`; Codex **ACEPTAR CON OBSERVACIONES** (sin bloqueantes) |

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
| `npm test -- --watchAll=false` (suite completa) | **OK** (21 jun 2026, post-`30e75d3`) — 19 suites / 82 tests |
| `npm run build` | **OK** |
| PostgreSQL nativo — smoke focal filtro micro (`synesis_user`) | **OK** (20 jun 2026, post-`CREATEDB`) — ver sección PostgreSQL abajo |
| Suite PostgreSQL completa | **NO ejecutada** |
| Migraciones / permisos / auditoría mutante | **Sin cambios** |

**Estado de la tarea filtro `estudio_id`:** **CERRADA** en código y tests de alcance.  
**Suite frontend global:** **CERRADA** (commit `30e75d3`; ver sección *Cierre deuda Jest global frontend*).

---

## Resultado de cierre — deuda Jest global frontend (21 jun 2026)

| Ítem | Estado |
|------|--------|
| Commit | **`30e75d3`** — `test(frontend): mock react-big-calendar for jest` |
| Archivos tocados | `frontend/src/setupTests.ts`, `frontend/src/__mocks__/react-big-calendar.tsx` |
| Causa raíz | `App.test.tsx` → `App.tsx` → `Turnos.tsx` → `react-big-calendar` (fallo ESM/CJS `dom-helpers/position` en Jest/jsdom) |
| Solución | Mock manual localizado solo para Jest; build productivo **sin** el mock |
| Backend / migraciones / permisos / guards / rutas / API / LIMS / turnos | **Sin cambios** |
| Auditoría Codex | **ACEPTAR CON OBSERVACIONES** — sin bloqueantes |
| `npm test -- --watchAll=false src/App.test.tsx` | **OK** — 1 suite / 1 test |
| `npm test -- --watchAll=false limsMicroApi.test.ts MicrobiologiaEstudioDetalle.test.tsx` | **OK** — 2 suites / 15 tests |
| `npm test -- --watchAll=false` | **OK** — 19 suites / 82 tests |
| `npm run build` | **OK** — main 419.07 kB gzip |

**Warnings no bloqueantes (persisten):** React Router v7 future flags; deprecación `punycode` (Node); MUI `TouchRipple` / `act(...)` en algunos tests; ESLint `react-hooks/exhaustive-deps` en archivos fuera del commit.

**Fuera de alcance (no declarado):** producción clínica abierta; E2E browser Playwright/Cypress; suite PostgreSQL completa (no ejecutada).

**Estado de la tarea Jest frontend:** **CERRADA**.

---

## CI / smoke mínimo (21 jun 2026)

| Ítem | Estado |
|------|--------|
| GitHub Actions | **`.github/workflows/smoke.yml`** — jobs `backend-checks`, `frontend-checks` |
| Script local | **`scripts/smoke_local.sh`** — mismos checks; SQLite in-memory |
| PostgreSQL en CI mínimo | **No requerido** — smoke focal PG sigue manual/opcional |
| Backend | `manage.py check` + pytest `usuarios/`, `auditoria/`, `test_microbiologia_estudio_id_filter` |
| Frontend | Jest con `CI=true`; build smoke con `CI=false` (warnings `react-hooks/exhaustive-deps` no bloquean) |
| Producción clínica / E2E browser | **Fuera de alcance** — no declarado |

**Primer run remoto (GitHub Actions Smoke #1, `820ac5c`):** `backend-checks` **PASS**; `frontend-checks` **FAIL** en build — `CI=true` en runner + warnings ESLint preexistentes → CRA exit 1.

**Corrección:** build smoke con `CI=false`; Jest mantiene `CI=true`. Warnings hooks siguen como **deuda no bloqueante** (sin tocar componentes en este ticket).

**Estado CI smoke mínimo:** **IMPLEMENTADO**; corrección build pendiente de segundo run tras push del fix.

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
| `npm test -- --watchAll=false src/App.test.tsx` | **OK** | 1 suite / 1 test (post-`30e75d3`) |
| `npm test -- --watchAll=false limsMicroApi.test.ts MicrobiologiaEstudioDetalle.test.tsx` | **OK** | 2 suites / 15 tests |
| `npm test -- --watchAll=false` | **OK** | **19 suites / 82 tests** (post-`30e75d3`; mock Jest `react-big-calendar`) |
| `npm run build` | **OK** | main 419.07 kB gzip; warnings ESLint preexistentes (`react-hooks/exhaustive-deps`, `api.ts` / `apiService.ts`) |

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
3. ~~`npm test` suite completa falla por `App.test.tsx` / `react-big-calendar`~~ — **resuelto (21 jun 2026, commit `30e75d3`):** mock Jest localizado; suite global 19/82 PASS. Tests de agenda no deben asumir calendario real bajo Jest global.
4. ~~`frontend/` como repo anidado sin `.gitmodules`~~ — **resuelto (jun 2026):** `frontend/` integrado como carpeta normal del monorepo; repo `emr-frontend` queda como respaldo histórico (`417e9a2`).

---

## Próxima tarea recomendada

1. Ampliar baseline PostgreSQL: `python manage.py test usuarios.tests auditoria.tests -v 2` y/o `laboratorio/tests/` completo (opcional).
2. ~~CI: pipeline smoke SQLite + frontend~~ — **implementado (21 jun 2026):** `.github/workflows/smoke.yml` + `scripts/smoke_local.sh`.
3. (Opcional) Tests frontend específicos de agenda/`Turnos` que ejerciten comportamiento calendario fuera del mock Jest global.
4. (Opcional) Job PostgreSQL focal en CI cuando haya servicio/secrets documentados (no bloqueante).
