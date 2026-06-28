# DOC_TESTS — Pruebas existentes

**Fecha de generación:** 30 de abril de 2026  
**Actualización (PROD-6 readiness smoke):** junio 2026
**Actualización (PROD-8 pre-piloto checklist):** junio 2026
**Actualización (PROD-9 observabilidad mínima):** junio 2026
**Actualización (PROD-10 piloto técnico):** junio 2026
**Actualización (PROD-13 hardening operativo sostenido):** junio 2026
**Actualización (PROD-3 CERRADO):** 7 de junio de 2026
**Actualización (PROD-3 Nginx reverse proxy):** 7 de junio de 2026
**Actualización (PROD-2-B CERRADO):** 7 de junio de 2026
**Actualización (PROD-2-B healthcheck ALLOWED_HOSTS/SSL):** 7 de junio de 2026
**Actualización (PROD-2-B runtime ejecutable):** 7 de junio de 2026
**Actualización (PROD-2-A runtime Gunicorn):** 7 de junio de 2026  
**Actualización (PROD-1-A SECRET_KEY productiva):** 7 de junio de 2026  
**Actualización (PROD-1 settings seguridad):** 7 de junio de 2026  
**Actualización (PDF-1-FE frontend descarga LIMS):** 7 de junio de 2026  
**Actualización (PDF-1 LIMS informe básico):** 6 de junio de 2026  
**Actualización (E2E-1-A LIMS cierre micro API-level):** 6 de junio de 2026  
**Actualización (E2E-1 LIMS flujo crítico API-level):** 4 de junio de 2026  
**Actualización (rol laboratorio, tests LIMS API):** 2 de mayo de 2026  
**Actualización (Fase A LIMS — máquina de estados):** 3 de mayo de 2026  
**Actualización (Fase B3.4 LIMS — Informes microbiológicos):** 14 de mayo de 2026  
**Actualización (Frontend UI-2 — microbiología LIMS):** 17 de mayo de 2026  
**Actualización (infra tests backend — pytest, SQLite, PostgreSQL):** 20 de junio de 2026  
**Actualización (PostgreSQL smoke focal microbiología — CREATEDB validado):** 20 de junio de 2026
**Actualización (Jest global frontend — mock `react-big-calendar`, commit `30e75d3`):** 21 de junio de 2026
**Actualización (CI/smoke mínimo — GitHub Actions + script local):** 21 de junio de 2026
**Actualización (CI smoke — build con CI=false por warnings CRA):** 21 de junio de 2026
**Actualización (AUD-01 — redacción PHI snapshots auditoría genérica):** 22 de junio de 2026

**Alcance:** Tests automatizados bajo el repositorio; excluye deliberadamente la carpeta `backup_documentacion/` salvo mención como no-canónica.

**Fuentes revisadas:** `conftest.py`, `pytest.ini`, `requirements.txt`, `synesis/settings.py`, `glob **/test*.py`, exclusiones por convención.

---

## Infraestructura de tests

### Runner y dependencias

| Componente | Ubicación / valor |
|------------|-------------------|
| Runner principal | **pytest** (suite backend usa `pytest.mark.django_db`, subtests, etc.) |
| Runner alternativo | `python manage.py test` (Django TestRunner; crea BD `test_*` en PostgreSQL por defecto) |
| Config pytest | `pytest.ini` — `DJANGO_SETTINGS_MODULE=synesis.settings`, `--import-mode=importlib` |
| Bootstrap Django | `conftest.py` (raíz) — `django.setup()` antes de importar modelos |
| Dependencias test | `requirements.txt` — sección **Desarrollo / tests**: `pytest`, `pytest-django` |
| Datos sintéticos | **Faker** en `requirements.txt` (producción); no hay `factory_boy` declarado |

**Instalación (desarrollo/CI):**

```bash
pip install -r requirements.txt
```

No existe `requirements-dev.txt` ni `pyproject.toml` / `setup.cfg` / `tox.ini` en el repositorio.

### Base de datos de test (`synesis/settings.py`)

`DATABASES['default']` lee variables de entorno (sin modificar settings productivos):

| Variable | Default productivo | Uso en tests |
|----------|-------------------|--------------|
| `DB_ENGINE` | `django.db.backends.postgresql` | `django.db.backends.sqlite3` para validación rápida |
| `DB_NAME` | `synesis_db` | `:memory:` para SQLite in-memory |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | postgres / localhost / 5432 | Ignorados por SQLite |

### Validación rápida — SQLite in-memory

Recomendado para desarrollo local y smoke sin PostgreSQL. **No sustituye** validación con PostgreSQL (constraints, tipos, `select_for_update`, etc.).

Desde la raíz del repo (con venv activo o `emr_env/bin/`):

```bash
python manage.py check

DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: pytest laboratorio/tests/test_microbiologia_estudio_id_filter.py -q
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: pytest laboratorio/tests/ -q
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: pytest usuarios/tests/ -q
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: pytest auditoria/tests/ -q
```

**Resultado documentado (20 jun 2026):**

| Comando | Resultado |
|---------|-----------|
| `python manage.py check` | OK — 0 issues |
| `pytest laboratorio/tests/test_microbiologia_estudio_id_filter.py -q` | **12 passed**, 96 subtests (~7 s) |
| `pytest laboratorio/tests/ -q` | **328 passed**, 96 subtests (~102 s) |
| `pytest usuarios/tests/ -q` | **44 passed** (~13 s) |
| `pytest auditoria/tests/ -q` | **14 passed** (~6 s) |

### Validación CI / real — PostgreSQL

Con `.env` apuntando a PostgreSQL (`DB_USER=synesis_user`, `DB_NAME=synesis_db`, `localhost:5432`), el smoke focal con Django TestRunner crea y destruye `test_synesis_db`:

```bash
python manage.py check
python manage.py test laboratorio.tests.test_microbiologia_estudio_id_filter -v 2
```

Equivalente con pytest (misma BD por defecto, sin vars SQLite):

```bash
pytest laboratorio/tests/test_microbiologia_estudio_id_filter.py -q
```

**Resultado documentado — entorno local actual (20 jun 2026):**

| Campo | Valor |
|-------|-------|
| Comando | `python manage.py test laboratorio.tests.test_microbiologia_estudio_id_filter -v 2` |
| ENGINE | `django.db.backends.postgresql` |
| BD productiva | `synesis_db` |
| Usuario DB | `synesis_user` |
| Host / puerto | `localhost` / `5432` |
| `rolcreatedb` | **true** (`rolsuper=false`, `rolcreaterole=false`) |
| Resultado | **OK** — 12 tests; `test_synesis_db` creada y destruida correctamente (~1.4 s) |

**Histórico (20 jun 2026, antes de habilitar `CREATEDB` en local):** el mismo comando fallaba con `Got an error creating the test database: permission denied to create database`.

**En otros entornos:** si reaparece `permission denied to create database`, el DBA debe ejecutar (solo sobre `synesis_user`, sin ampliar a `SUPERUSER`):

```sql
ALTER USER synesis_user CREATEDB;
```

Alternativa operativa: usuario con `CREATEDB` solo en entorno de test/CI, o pre-crear `test_synesis_db` y `pytest --reuse-db` / `manage.py test --keepdb` (requiere permisos sobre esa BD).

**Advertencia:** no declarar validada la **suite PostgreSQL completa** hasta ejecutarla en el entorno objetivo. El smoke focal microbiología sí está validado en local; ampliar baseline con `usuarios.tests`, `auditoria.tests` y/o `laboratorio/tests/` completo sigue **opcional**.

### Frontend Jest global — deuda `react-big-calendar` **CERRADA** (commit `30e75d3`)

**Causa raíz (histórica):** `App.test.tsx` importaba `App.tsx` → `Turnos.tsx` → `react-big-calendar`, provocando fallo ESM/CJS (`dom-helpers/position`) en Jest/jsdom.

**Corrección (commit `30e75d3` — `test(frontend): mock react-big-calendar for jest`):**

| Archivo | Rol |
|---------|-----|
| `frontend/src/setupTests.ts` | Registra `jest.mock('react-big-calendar')` solo en entorno Jest |
| `frontend/src/__mocks__/react-big-calendar.tsx` | Mock manual con `Calendar`, `dateFnsLocalizer` y `Views` usados por el código |

El mock es **exclusivo de Jest**; no entra en el bundle productivo ni altera runtime/build.

**Auditoría Codex:** veredicto **ACEPTAR CON OBSERVACIONES** (sin bloqueantes).

**Evidencia documentada (21 jun 2026):**

| Comando | Resultado |
|---------|-----------|
| `cd frontend && npm test -- --watchAll=false src/App.test.tsx` | **PASS** — 1 suite / 1 test |
| `cd frontend && npm test -- --watchAll=false limsMicroApi.test.ts MicrobiologiaEstudioDetalle.test.tsx` | **PASS** — 2 suites / 15 tests |
| `cd frontend && npm test -- --watchAll=false` | **PASS** — **19 suites / 82 tests** |
| `cd frontend && npm run build` | **PASS** — main **419.07 kB** gzip; warnings ESLint `react-hooks/exhaustive-deps` preexistentes (no bloqueantes) |

**Observación futura:** tests específicos de agenda/`Turnos` no deben asumir que la librería `react-big-calendar` real se ejercita bajo la suite Jest global; el mock sustituye el componente calendario en jsdom.

### CI / smoke mínimo reproducible

**Implementación (jun 2026):**

| Artefacto | Rol |
|-----------|-----|
| `.github/workflows/smoke.yml` | GitHub Actions — jobs `backend-checks` y `frontend-checks` en push/PR a `master`/`main` y `workflow_dispatch` |
| `scripts/smoke_local.sh` | Mismo smoke en local (`set -euo pipefail`); usa `emr_env/bin/python` si existe |

**Backend (SQLite in-memory — sin PostgreSQL en CI mínimo):**

```bash
export DB_ENGINE=django.db.backends.sqlite3
export DB_NAME=:memory:
python manage.py check
pytest usuarios/tests/ auditoria/tests/ -q
pytest laboratorio/tests/test_microbiologia_estudio_id_filter.py -q
```

**Frontend:**

```bash
cd frontend
npm ci --legacy-peer-deps
CI=true npm test -- --watchAll=false
CI=false npm run build   # CRA: con CI=true los warnings ESLint fallan el build
```

**Primer run GitHub Actions (workflow Smoke #1, commit `820ac5c`):** `backend-checks` **PASS**; `frontend-checks` **FAIL** en *Production build* — GitHub Actions exporta `CI=true` y Create React App trata warnings `react-hooks/exhaustive-deps` preexistentes como error (exit code 1). Jest ya pasaba con `CI=true`.

**Corrección:** Jest sigue con `CI=true`; build de smoke usa `CI=false` para validar compilación sin bloquear por deuda ESLint hooks (no resuelta en este ticket).

**Local (todo en uno):**

```bash
bash scripts/smoke_local.sh
```

**PostgreSQL:** no bloquea el CI mínimo (sin secrets). Smoke focal PostgreSQL (`manage.py test laboratorio.tests.test_microbiologia_estudio_id_filter`) sigue **manual/opcional** en entornos con `CREATEDB`; ver sección *Validación CI / real — PostgreSQL* arriba.

**Stack CI:** Python 3.12, Node 18, `pip install -r requirements.txt`, `npm ci --legacy-peer-deps` en `frontend/`.

---

## Infraestructura de tests (detalle histórico)

- **`conftest.py` (raíz):** configura `DJANGO_SETTINGS_MODULE=synesis.settings` y `django.setup()` para pytest.
- **Fixtures/factories:** uso de **Faker** listado en `requirements.txt`; no hay factory_boy explícito en requirements (pendiente de confirmar si se usa en algún test).

---

## Tests backend (por app / área)

| Ubicación | Contenido inferido |
|-----------|-------------------|
| `pacientes/tests/` | `test_models.py`, `test_api.py` |
| `medicos/tests/` | `test_models.py` |
| `turnos/tests/` | `test_api.py`, `test_models.py`, `test_services.py`, `test_consulta_ambulatoria.py`, `test_atencion_viewset.py` |
| `historias_clinicas/tests/` | `test_api.py`, `test_models.py` |
| `laboratorio/tests/` | `test_models.py`, `test_api.py` |
| `archivos_medicos/tests/` | `test_models.py`, `tests.py` |
| `auditoria/tests/` | `test_audit_event_model.py`, `test_audit_integration.py`, `test_auditoria_hardening.py`, **`test_snapshot_phi_redaction.py`** (AUD-01: Paciente/Consulta/Atencion/ConsultaAmbulatoria/Solicitud sin PHI en snapshots/`entity_repr`) |
| `integracion_lims/tests.py` | app-level |
| `solicitudes/tests/` | `test_models.py`, **`test_permissions_api.py`** (PERM-01/DOC-01: permisos por rol; regresión sin envío LIMS aunque `LIMS_AUTO_SEND=true`), `conftest.py`, `tests.py` |
| `internacion/tests/` | `test_infraestructura.py`, `test_admision.py`, `tests.py` |
| `usuarios/tests/` | `test_models.py`, `test_health.py`, **`test_laboratorio_rol.py`** (rol `laboratorio`, login/current-user/JWT) |
| `api/tests.py` | app api |
| `catalogos/tests.py` | app catalogos |
| `backend/tests/test_registro_paciente.py` | registro paciente |
| `pacientes/tests.py`, `medicos/tests.py`, `solicitudes/tests.py`, `archivos_medicos/tests.py`, `internacion/tests.py`, `historias_clinicas/tests.py` | ficheros legacy `tests.py` |

**`backup_documentacion/`:** numerosos scripts `test_*.py` / `test_*.js` — **no son suite pytest estándar** del proyecto; tratar como experimentos.

---

## Tests frontend

La suite vive en el directorio **`frontend/`** del monorepo (Create React App + Jest + Testing Library). **No hay** Playwright ni Cypress configurados en el repo (búsqueda `playwright.config.*` / `cypress.config.*` vacía).

**Suite Jest global (24 jun 2026, FE-PERM-01):** `npm test -- --watchAll=false` → **21 suites / 97 tests PASS**. Smoke `App.test.tsx` valida pantalla de login en `/login`. Nuevos: `permissions.test.ts`, `apiError.test.ts` (matriz de roles y mensajes 403/404 seguros).

**E2E-1 / E2E-1-A LIMS (jun 2026) — Opción B (sin framework browser):**

- Test crítico API base: `laboratorio/tests/test_lims_flujo_critico.py` → `test_flujo_critico_lims_muestra_resultado_microbiologia` (solicitud → muestra tomada/recibida → `cargar-resultados` con `muestra_id` → estudio micro → `iniciar` → siembra → lectura preliminar → informe `PRELIMINAR` en `BORRADOR`; intento médico siembra → `403` sin crear siembra ni auditoría `crear_siembra`; usuario `laboratorio`; sin logs PHI).
- Test crítico cierre micro: `test_flujo_critico_lims_microbiologia_final_validado_informado` (mismo arranque LIMS → aislado → identificación → antibiograma → resultado → completar → informe `FINAL` emitido → `LISTO_PARA_VALIDAR` → admin valida → `VALIDADO` → `marcar-informado` → `INFORMADO`; operación técnica post-cierre → `400`).
- Helpers frontend reforzados previamente: `limsAccess.test.ts`, `limsMicroUx.test.ts`, `limsCargaMuestra.test.ts`.
- **FE-PERM-01 (jun 2026):** `permissions.test.ts` (pacientes, solicitudes, archivos, LIMS, auditoría por rol); `apiError.test.ts` (403/404 sin PHI).
- **QA-ROLE-01 (jun 2026):** `api/tests/test_atencion_permissions_api.py` (roles en `/api/atenciones/`, incl. staff/superuser); `permissions.test.ts` (`canAccessAtenciones`, `canOperateAtenciones`); `Sidebar.test.tsx` (menú Consultas); `AtencionDetailDrawer.test.tsx` (enfermería/paciente solo lectura, médico/admin edición); `no-console-guard.test.ts` (sin `console.*` en `modules/atenciones`); `turnos/tests/test_atencion_viewset.py` (contrato 400 payload inválido vs 403 no autorizado en POST compat).
- **PHI laboratorio EMR (jun 2026):** `pacientes/tests/test_api.py` — `laboratorio` con `is_staff=True` no lista/busca/retrieve pacientes EMR; `api/tests/test_atencion_permissions_api.py` — `test_laboratorio_is_staff_bloqueado` (403 list/detail/patch/cerrar). LIMS sin regresión: `usuarios/tests/test_laboratorio_rol.py`, `laboratorio/tests/test_lims_flujo_critico.py`.
- **Staff bypass EMR audit (jun 2026):** `emr_staff_or_admin_global` en `api/permissions.py`; tests `turnos/tests/test_api.py` (`test_laboratorio_is_staff_no_ve_turnos`), `turnos/tests/test_permissions_mutations.py` (`test_laboratorio_is_staff_no_puede_crear_turno`), `historias_clinicas/tests/test_api.py` (HC list/resumen bloqueados para lab+staff).
- **QA-FE-LOGS-02 (jun 2026):** `no-console-clinical-views-guard.test.ts` — sin `console.*` en `PatientIntegratedView.tsx` y `Turnos.tsx`.
- **QA-FE-LOGS-03 (jun 2026):** `no-console-focused-modules-guard.test.ts` — sin `console.*` en `apiService.ts`, `internacion/*`, `TurnoModal.tsx`, `Solicitudes.tsx`, `Pacientes.tsx`, `csrf.ts`.
- **QA-FE-ERR-01 (jun 2026):** `no-raw-clinical-errors-guard.test.ts` — sin `alert(error…)`, `response?.data?.error/detail/message` ni `error.message` crudo en mensajes visibles del alcance focal (`TurnoModal`, `internacion/*`, `Solicitudes`, `Pacientes`, `apiService`, `csrf`); `apiError.test.ts` extendido (`getSafeClinicalActionMessage`). Comandos: `cd frontend && npm test -- --watchAll=false`, `npm run build`; backend focal sin cambios.
- **QA-FE-ERR-02 (jun 2026):** `no-phi-clinical-ui-alerts-guard.test.ts` — `Solicitudes.tsx` sin PHI/PII en `alert`/toast visibles; callers de `MotivoDialog` (TurnoModal, LIMS micro) sin `formatDrfError`/`error.message` propagados al diálogo. `apiError.test.ts` extendido (`limsCancelarEstudioMicro`). Comandos ejecutados: `npm test -- --watchAll=false`, `npm run build`; backend focal sin cambios.
- **QA-FE-ERR-03 (jun 2026):** `no-raw-lims-ui-errors-guard.test.ts` — `components/lims/*` y `pages/laboratorio/*` sin `toast.error(formatDrfError(...))` ni `response.data` en feedback visible; toasts LIMS usan `getSafeClinicalActionMessage`. `apiError.test.ts` extendido (acciones LIMS adicionales).
- **QA-FE-ERR-03A (jun 2026):** `formatLimsPdfDownloadError` saneado (sin `detail`/`ax.message`); guardrail reforzado (`snackbar`/`formatLimsHttpError`/`response.data.*`); `limsDownload.test.ts` extendido. Deuda cerrada: descarga PDF LIMS.
- **GAP pendiente:** E2E browser LIMS/micro (requiere instalar y cablear Playwright o Cypress en CI). No se implementó PDF ni CLSI/EUCAST.

**Comandos validados (UI-2, commit `d46d276`, mayo 2026):**

```bash
export PATH="$HOME/.nvm/versions/node/v18.20.8/bin:$PATH"  # si aplica
cd frontend
npx tsc --noEmit
npm run build
CI=true npm test -- --watchAll=false --runInBand
```

**Resultado documentado:** TypeScript OK, build OK, **11 test suites / 25 tests** passed (incluye regresión UI-1; **sin** tests unitarios dedicados a pantallas `Microbiologia*`).

**Pendiente:** tests frontend específicos de microbiología (panels, permisos por rol, manejo 400/403).

---

## Cobertura funcional inferida

- **Modelos:** varias apps con `test_models.py`.
- **API:** `turnos`, `pacientes`, `historias_clinicas`, `laboratorio`, `test_atencion_viewset`.
- **Servicios:** `turnos/tests/test_services.py` (AtencionService / negocio).
- **Auditoría:** modelo append-only + integración + hardening.

**Huecos probables (sin exhaustividad de grep):** flujo completo `Solicitud`+LIMS externo, webhooks `integracion_lims` no cableados, duplicación `Internacion`. ~~Permisos LIMS `AllowAny`~~ cubiertos por hardening + `laboratorio/tests/test_api.py`. Transiciones de estado `SolicitudExamen` (Fase A) cubiertas en **`TestSolicitudExamenEstadoAPI`**, **`TestSolicitudExamenEstadoAuditoria`** y ajustes en **`TestLimsAuthorization`** dentro de `laboratorio/tests/test_api.py`; cancelación con resultados vacíos en `laboratorio/tests/test_models.py`.

---

## Módulos con tests

`pacientes`, `medicos`, `turnos`, `historias_clinicas`, `laboratorio`, `archivos_medicos`, `auditoria`, `solicitudes`, `internacion`, `usuarios`, `api`, `catalogos`, `integracion_lims`, `backend/tests`.

---

## Módulos sin tests (o solo stubs)

- **`core`:** sin tests dedicados vistos.
- **`emr` (app):** no se listó `emr/tests` en el glob (pendiente: verificar si existe).
- **`integracion_lims`:** solo `tests.py` genérico — cobertura probablemente superficial vs `lims_service`.

---

## Comandos para correr tests

Desde la raíz del repo (con entorno virtual y dependencias de `requirements.txt` instaladas).

**Validación rápida (SQLite in-memory — recomendado en local sin PostgreSQL):**

```bash
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: pytest
```

Por app:

```bash
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: pytest turnos/tests/ laboratorio/tests/ auditoria/tests/
```

**Con PostgreSQL** (requiere `CREATEDB` o BD de test preexistente; ver sección Infraestructura):

```bash
pytest laboratorio/tests/ -q --reuse-db
```

**Comandos validados post-hardening LIMS / rol laboratorio:**

```bash
python manage.py check
python -m pytest usuarios/tests/test_laboratorio_rol.py usuarios/tests/test_models.py -q
python manage.py test laboratorio.tests.test_api
```

**Comando validado post–Fase A (máquina de estados + rol laboratorio):**

```bash
emr_env/bin/python manage.py check
emr_env/bin/pytest laboratorio/tests/test_api.py laboratorio/tests/test_models.py usuarios/tests/test_laboratorio_rol.py -q --reuse-db
```

**Resultado documentado (3 may 2026):** `45 passed` (sin fallos en ese subconjunto).

- **`laboratorio.tests.test_api`:** incluye `TestSolicitudExamenAPI` (flujo crear/cargar/validar/etiqueta), **`TestLimsAuthorization`**, **`TestLimsAuditTrail`**, **`TestSolicitudExamenEstadoAPI`** (transiciones, PATCH de `estado`, permisos médico), **`TestSolicitudExamenEstadoAuditoria`** (metadata `cancelar`), y alias `/api/laboratorio/...`.
- **`laboratorio.tests.test_models`:** principalmente modelos; suele ejecutarse con **`pytest`** si usas marcadores `pytest.mark.django_db` (`manage.py test` puede no recoger todos los métodos pytest-style según versión).

**Pendiente de confirmar:** umbral de cobertura. **CI mínimo:** `.github/workflows/smoke.yml` (backend SQLite + frontend Jest/build); ver sección *CI / smoke mínimo reproducible*.

---

## Riesgos por falta de pruebas

- Regresiones en **filtros por rol** (`get_queryset` en múltiples ViewSets).
- Regresiones en **transiciones de estado** LIMS más allá de la Fase A (p. ej. futura cancelación desde `VALIDADO`).
- **Doble modelo de internación** sin tests de consistencia cruzada.

---

## Tests recomendados para EMR

1. Creación idempotente `POST /api/atenciones/` con mismo `turno`.
2. Paciente sin ficha: error en `TurnoViewSet.perform_create` para rol paciente.
3. `HistoriaClinicaViewSet` / `ConsultaViewSet` límites por médico/paciente.
4. Subida y descarga `ArchivoMedico` por rol (secretaría bloqueada).

---

## Tests recomendados para LIMS

1. `SolicitudExamenCreateSerializer`: creación de `ResultadoExamen` por paneles con solapamiento (**cubierto en parte** por `test_api`).
2. `cargar_resultados` con solicitud `VALIDADO` / `CANCELADO` / `ENTREGADO` (**cubierto** en `TestSolicitudExamenEstadoAPI`).
3. `validar`: solo `EN_PROCESO`, resultados vacíos rechazados; `bulk update` en resultados + auditoría (**cubierto** en `test_api` + estado).
4. ~~Permisos finales (sustituir `AllowAny` y testear roles)~~ — **cubierto** por `TestLimsAuthorization` + usuario `rol=laboratorio` en setup de `test_api`.
5. Acciones `tomar-muestra`, `cancelar`, `marcar-entregado`, `PATCH` sin mutar `estado`, auditoría de transición (**cubierto** en `TestSolicitudExamenEstadoAPI` / `TestSolicitudExamenEstadoAuditoria`).

**Fase B0/B1:** `laboratorio/tests/test_muestras_models.py` (catálogos, `crear_muestra`, transiciones y coordinación solicitud); `laboratorio/tests/test_muestras_api.py` (permisos catálogo, CRUD muestra, acciones, PATCH `estado` ignorado, auditoría con `captureOnCommitCallbacks`).

**Fase B2 [IMPLEMENTADO]:** `test_resultados_muestras_models.py` (FK, integridad, `PROTECT`, no rechazar con resultados); `test_resultados_muestras_api.py` (carga con/sin `muestra_id`, CONSERVADA→EN_PROCESO, `PROCESAMIENTO`, rechazo con resultados, resultado validado sin cambio de muestra, permisos).
**Fase B2-B [IMPLEMENTADO]:** `laboratorio/tests/test_tipo_examen_muestra_requerida.py` (legacy sin muestra, obligatoriedad por tipo, tipo de muestra incorrecto/correcto, estados no procesables, auditoría en fallo/éxito); `test_resultados_muestras_models.py` (`requiere_muestra` configurable). Migración `0012_tipo_examen_requiere_muestra`.
**Fase B2-B-A [IMPLEMENTADO]:** mismos tests con `TipoMuestra.codigo` ≤10 (PostgreSQL); `test_tipo_no_requiere_muestra_pero_si_se_envia_muestra_debe_coincidir_tipo`; validación tipo muestra con `requiere_muestra=False` si hay `muestra_id`.
**Fase B2-C [frontend]:** `frontend/src/utils/limsCargaMuestra.test.ts` (validación requiere_muestra, payload con/sin `muestra_id`, filtro procesables); verificación manual `npm exec tsc --noEmit` y `npm run build` en `frontend/`.
**Fase B2-A [IMPLEMENTADO]:** `auditoria/tests/test_audit_integration.py` (`test_resultado_examen_snapshot_redacta_valor_clinico`); `test_resultados_muestras_api.py` (`test_cargar_resultados_con_muestra_no_audita_codigo_barra_ni_valor_clinico` — metadata y snapshots sin PHI/codigo_barra).

**Fase B3-audit [IMPLEMENTADO]:** `laboratorio/tests/test_microbiologia_auditoria.py` — metadata micro sin `codigo_barra`/CIM/diámetro/interpretación/texto de informe; snapshots redactados; conservación de IDs técnicos.

**Fase B3-frontend-validación [IMPLEMENTADO — jun 2026]:** relevamiento SPA microbiología (UI-2); contrato `limsMicroApi.ts` verificado; `tsc` + `build` + Jest focal `limsCargaMuestra.test.ts` OK; backend micro **161/161** OK. Corrección bug crecimiento `AUSENTE`→`SIN_DESARROLLO`/`MIXTO`. Sin suite Jest micro dedicada (gap documentado en `DOC_FRONTEND.md`).

**Fase B3-frontend-validación-A [VALIDADO — jun 2026]:** bloqueo operación técnica micro en estados cerrados `CANCELADO`/`VALIDADO`/`INFORMADO`. Backend: `TestEstudioMicroCerradoOperacionAPI` (4 tests); suite `test_microbiologia_*` 165 passed; regresión LIMS 315 passed (PostgreSQL). Frontend: `limsAccess.test.ts`. Auditoría Codex: `B3_VALIDACION_A_CODEX_AUDIT.md`.

**B3-frontend-UX [PARCIAL — jun 2026]:** `limsMicroUx.test.ts` (muestras procesables, labels, validación crear estudio); ampliación matriz roles en `limsAccess.test.ts`. **[GAP]** E2E browser LIMS micro sin framework (E2E-1/E2E-1-A cubren flujo crítico vía pytest API).

**E2E-1 [IMPLEMENTADO — jun 2026]:** `laboratorio/tests/test_lims_flujo_critico.py` — validación reproducible del flujo operativo crítico LIMS+micro sin dependencias E2E nuevas.

**E2E-1-A [IMPLEMENTADO — jun 2026]:** extiende `test_lims_flujo_critico.py` al cierre microbiológico (`FINAL` → `VALIDADO` → `INFORMADO`) y refuerza side effects del `403` médico (sin crear entidad ni auditoría de éxito). Sin Playwright/Cypress, PDF ni CLSI/EUCAST.

```bash
emr_env/bin/pytest laboratorio/tests/test_lims_flujo_critico.py -q --reuse-db
```

**PDF-1 [IMPLEMENTADO — jun 2026]:** `laboratorio/tests/test_lims_pdf_informe.py` — descarga PDF (`%PDF`, `Content-Type`, nombre seguro), permisos (lab/admin/médico propio; secretaría/enfermería/paciente bloqueados; médico ajeno → 404), sin `codigo_barra` en bytes, auditoría `lims_informe_pdf_download` sin PHI, descarga idempotente sin cambio de estado, intento bloqueado sin audit de éxito.

```bash
emr_env/bin/pytest laboratorio/tests/test_lims_pdf_informe.py -q --reuse-db
```

**PROD-1 [IMPLEMENTADO — jun 2026]:** `api/tests/test_prod_settings_security.py` — SECRET_KEY/ALLOWED_HOSTS/CORS en producción, Browsable API solo DEBUG, `/media/` condicionado, helpers `env_config`.

**PROD-1-A [IMPLEMENTADO — jun 2026]:** refuerzo `validate_production_secret_key` — rechaza placeholders documentados, `django-insecure-*`, cadenas repetitivas y baja diversidad; acepta clave sintética fuerte y `get_random_secret_key()`.

**PROD-2-A [IMPLEMENTADO — jun 2026]:** `api/tests/test_prod_runtime_config.py` — lectura estática: entrypoint runserver/gunicorn, compose dev/prod, env examples, gunicorn en requirements.

**PROD-2-B [CERRADO — jun 2026]:** extiende `api/tests/test_prod_runtime_config.py` (**24 tests** en suite runtime/healthcheck):

| Clase / área | Tests | Qué valida |
|--------------|-------|------------|
| `TestEntrypointRuntime` | 3 | Lectura estática entrypoint (runserver, gunicorn, runtime inválido) |
| `TestEntrypointExecutable` | 6 | Ejecución real con stubs: runtime inválido, runserver, gunicorn, `BIND_ADDR`, `RUN_MIGRATIONS`, sin secretos |
| `TestDockerComposeDev` | 1 | Dev usa `runserver` |
| `TestDockerComposeProdExample` | 3 | Prod usa `gunicorn`; sin secretos reales; healthcheck presente |
| `TestDockerComposeProdHealthcheck` | 6 | `/api/health/`, `DJANGO_HEALTHCHECK_HOST`, `Host`, `X-Forwarded-Proto`, urllib sin curl/wget, sin secretos hardcodeados |
| `TestEnvExamples` | 3 | Env dev/prod runtime; `DJANGO_HEALTHCHECK_HOST` en prod example |
| `TestRequirements` | 1 | `gunicorn` en requirements |
| `test_doc_runtime_existe` | 1 | `PROD_RUNTIME.md` existe |

Técnica entrypoint: stubs temporales de `nc`, `python`, `gunicorn` y `sleep` en `PATH`; no levanta servidores ni Postgres reales. Healthcheck: validación estática del compose prod (sin contenedores).

**Evidencia de cierre (jun 2026):** 24 passed runtime PROD-2-B; regresión mínima documentada. Sin impacto EMR/LIMS.

**PROD-3 [CERRADO — jun 2026]:** tests estáticos Nginx/compose en `api/tests/test_prod_runtime_config.py` (**39 tests** suite runtime total, incluye PROD-2-B + PROD-3):

| Clase / área | Qué valida |
|--------------|------------|
| `TestNginxProdExample` | Plantilla Nginx; proxy `backend:8000`; headers; map `$proxy_x_forwarded_proto`; `/media/` y dotfiles bloqueados |
| `TestDockerComposeProdExample` | Servicio `nginx`; backend interno; `nginx` → `backend` healthy; healthcheck PROD-2-B |

Validación operativa: `nginx -t` con Docker documentado en `PROD_RUNTIME.md`.

**Evidencia de cierre (jun 2026):** 39 passed runtime; 63 passed regresión mínima. Sin impacto EMR/LIMS.

**PROD-4 [CERRADO — jun 2026]:** storage privado media clínica — **11 archivos** en commit (ver `PROD_RUNTIME.md`; incluye `deploy/nginx/nginx.prod.example.conf` untracked hasta `git add` explícito).

| Clase / área | Qué valida |
|--------------|------------|
| `TestNginxProdExample` (ampliado) | Sin `alias` público a media; sin `autoindex` |
| `TestDockerComposeProdExample` (ampliado) | Nginx sin volumen `media` |
| `TestProdPrivateMediaStorage` | Compose/env/docs declaran media privada; sin credenciales cloud en `.env.production.example` |

Tests funcionales permisos archivos (`archivos_medicos/tests/` — **33 passed**, incluye C6.2 + modelos):

| Test | Qué valida |
|------|------------|
| `test_anonimo_no_lista_archivos` | Listado sin auth → 401/403 |
| `test_anonimo_no_descarga` | Download sin auth → 401/403 |
| (C6.2 existentes) | Sin `/media/` en API; paciente ajeno bloqueado; auditoría sin paths |

**Evidencia de cierre (jun 2026):** **49 passed** runtime; **73 passed** regresión mínima; **33 passed** `archivos_medicos/tests/`. Sin impacto EMR/LIMS.

**PROD-4-A adjuntos turnos [CERRADO — jun 2026]:** `api/tests/test_registro_adjuntos_download_prod4a.py` — **15 passed** (PostgreSQL).

**PROD-4-B auditoría download adjuntos turnos [CERRADO — jun 2026]:** `api/tests/test_registro_adjuntos_download_audit_prod4b.py` — **6 passed**; descarga exitosa crea `AuditEvent`; actor/entidad/metadata correctos; sin path/`/media/`/filename; no autorizado/sin archivo no audita. Regresión mínima (+ PROD-4-A): **121 passed**.

**PROD-5 backups/restore [CERRADO — jun 2026]:** `test_prod_backup_config.py` — **31 passed**.

**PROD-5-A restore drill [IMPLEMENTADO — jun 2026]:** `test_prod_restore_drill_config.py` — documento staging, verify script, sin restore real en pytest.

**PROD-6 readiness smoke [IMPLEMENTADO — jun 2026]:** `api/tests/test_prod_readiness_smoke.py` — documentación `PROD_READINESS_SMOKE.md`, script `deploy/smoke/prod_readiness_smoke.example.sh`, rutas críticas URLConf, media bloqueada, descargas+auditoría referenciadas; sin producción real ni servicios externos.

**PROD-8 pre-piloto checklist [IMPLEMENTADO — jun 2026]:** `api/tests/test_prod_prepilot_checklist.py` — documentación `PROD_PREPILOT_CHECKLIST.md`; verifica precondiciones GO/NO-GO (`DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS`, CSRF/CORS, TLS/`X-Forwarded-Proto`, `/media/`, backups, restore drill, monitoreo, rollback, usuarios/roles, datos sintéticos, frontend separado, producción clínica abierta fuera de alcance, evidencia sanitizada, sin PHI/secretos); sin producción real.

```bash
emr_env/bin/pytest api/tests/test_prod_prepilot_checklist.py -q --reuse-db
```

Regresión mínima productiva (PROD-8):

```bash
emr_env/bin/pytest api/tests/test_prod_runtime_config.py api/tests/test_prod_readiness_smoke.py api/tests/test_prod_backup_config.py api/tests/test_prod_restore_drill_config.py api/tests/test_prod_prepilot_checklist.py -q --reuse-db
```

**PROD-9 observabilidad mínima [IMPLEMENTADO — jun 2026]:** `api/tests/test_prod_observability_min.py` — documentación `PROD_OBSERVABILITY_MIN.md`, script `deploy/observability/check_observability.example.sh`; verifica logs, 4xx/5xx, healthcheck, contenedores, DB, disco, backups, incidentes, GO/NO-GO, evidencia sanitizada, sin PHI/secretos; sin producción real.

```bash
emr_env/bin/pytest api/tests/test_prod_observability_min.py -q --reuse-db
bash -n deploy/observability/check_observability.example.sh
```

Regresión mínima productiva (PROD-9):

```bash
emr_env/bin/pytest api/tests/test_prod_runtime_config.py api/tests/test_prod_readiness_smoke.py api/tests/test_prod_backup_config.py api/tests/test_prod_restore_drill_config.py api/tests/test_prod_prepilot_checklist.py api/tests/test_prod_observability_min.py -q --reuse-db
```

**PROD-10 piloto técnico [IMPLEMENTADO — jun 2026]:** `api/tests/test_prod_technical_pilot.py` — runbook `PROD_TECHNICAL_PILOT_RUNBOOK.md`, plantilla evidencia, script `deploy/smoke/prod_technical_pilot.example.sh`; verifica PROD-8/9, ventana piloto, smoke, GO/NO-GO, evidencia fuera del repo; sin producción real.

```bash
emr_env/bin/pytest api/tests/test_prod_technical_pilot.py -q --reuse-db
bash -n deploy/smoke/prod_technical_pilot.example.sh
```

Regresión mínima productiva (PROD-10):

```bash
emr_env/bin/pytest api/tests/test_prod_runtime_config.py api/tests/test_prod_readiness_smoke.py api/tests/test_prod_backup_config.py api/tests/test_prod_restore_drill_config.py api/tests/test_prod_prepilot_checklist.py api/tests/test_prod_observability_min.py api/tests/test_prod_technical_pilot.py -q --reuse-db
```

**PROD-11 revisión post-piloto [IMPLEMENTADO — jun 2026]:** `api/tests/test_prod_post_pilot_review.py` — `PROD_POST_PILOT_REVIEW.md`, `PROD_POST_PILOT_ACTIONS_TEMPLATE.md`; revisión evidencia externa, GO/NO-GO post-piloto, acciones correctivas; sin producción real.

```bash
emr_env/bin/pytest api/tests/test_prod_post_pilot_review.py -q --reuse-db
```

Regresión mínima productiva (PROD-11):

```bash
emr_env/bin/pytest api/tests/test_prod_runtime_config.py api/tests/test_prod_readiness_smoke.py api/tests/test_prod_backup_config.py api/tests/test_prod_restore_drill_config.py api/tests/test_prod_prepilot_checklist.py api/tests/test_prod_observability_min.py api/tests/test_prod_technical_pilot.py api/tests/test_prod_post_pilot_review.py -q --reuse-db
```

**PROD-12 autorización institucional piloto datos reales mínimos [IMPLEMENTADO — jun 2026]:** `api/tests/test_prod_min_real_data_auth.py` — `PROD_MIN_REAL_DATA_AUTH.md`, `PROD_MIN_REAL_DATA_SCOPE_TEMPLATE.md`; GO post-piloto PROD-11, autorización externa, alcance limitado, datos mínimos; sin producción real.

```bash
emr_env/bin/pytest api/tests/test_prod_min_real_data_auth.py -q --reuse-db
```

Regresión mínima productiva (PROD-12):

```bash
emr_env/bin/pytest api/tests/test_prod_runtime_config.py api/tests/test_prod_readiness_smoke.py api/tests/test_prod_backup_config.py api/tests/test_prod_restore_drill_config.py api/tests/test_prod_prepilot_checklist.py api/tests/test_prod_observability_min.py api/tests/test_prod_technical_pilot.py api/tests/test_prod_post_pilot_review.py api/tests/test_prod_min_real_data_auth.py -q --reuse-db
```

**PROD-13 hardening operativo sostenido [IMPLEMENTADO — jun 2026]:** `api/tests/test_prod_operational_hardening.py` — `PROD_OPERATIONAL_HARDENING.md`, `PROD_MONITORING_ALERTS_TEMPLATE.md`, `PROD_SECRET_ROTATION_RUNBOOK.md`; monitoreo/APM, alertas, secretos, TLS, WAF; sin producción real.

```bash
emr_env/bin/pytest api/tests/test_prod_operational_hardening.py -q --reuse-db
```

Regresión mínima productiva (PROD-13):

```bash
emr_env/bin/pytest api/tests/test_prod_runtime_config.py api/tests/test_prod_readiness_smoke.py api/tests/test_prod_backup_config.py api/tests/test_prod_restore_drill_config.py api/tests/test_prod_prepilot_checklist.py api/tests/test_prod_observability_min.py api/tests/test_prod_technical_pilot.py api/tests/test_prod_post_pilot_review.py api/tests/test_prod_min_real_data_auth.py api/tests/test_prod_operational_hardening.py -q --reuse-db
```

Regresión mínima PROD-6 (incluye readiness si existe):

```bash
emr_env/bin/pytest api/tests/test_prod_settings_security.py api/tests/test_prod_runtime_config.py laboratorio/tests/test_lims_flujo_critico.py archivos_medicos/tests/ api/tests/test_registro_adjuntos_download_prod4a.py api/tests/test_registro_adjuntos_download_audit_prod4b.py api/tests/test_prod_readiness_smoke.py -q --reuse-db
```

```bash
emr_env/bin/pytest api/tests/test_prod_settings_security.py api/tests/test_prod_runtime_config.py laboratorio/tests/test_lims_flujo_critico.py -q --reuse-db
```

```bash
emr_env/bin/pytest api/tests/test_prod_settings_security.py -q --reuse-db
```

**PDF-1-FE [IMPLEMENTADO — jun 2026]:** Jest `limsAccess.test.ts` (`canDownloadInformeLimsPdf` por rol), `limsDownload.test.ts` (filename seguro, validación id, errores HTTP, `revokeObjectURL`).

```bash
cd frontend && CI=true npm test -- --watchAll=false --runInBand src/utils/limsAccess.test.ts src/utils/limsDownload.test.ts
```

**Fase B4.1:** `laboratorio/tests/test_resultados_clinicos_models.py` (TipoExamen rangos/críticos/sección; ResultadoExamen numérico, snapshots, patológico/crítico, pendiente); `laboratorio/tests/test_resultados_clinicos_api.py` (payload viejo, `valor_numerico`, unidad default, cálculo patológico/crítico, validar, permisos laboratorio/médico).

**Fase B3.1 (Microbiología base):**

- `laboratorio/tests/test_microbiologia_models.py`: alta de `MedioCultivo` (incluido `codigo` único), creación de `EstudioMicrobiologia` con muestras `RECIBIDA`/`CONSERVADA`/`EN_PROCESO`, rechazo con muestras `PENDIENTE_TOMA`/`TOMADA`/`RECHAZADA`/`DESCARTADA`/`CANCELADA`, consistencia solicitud/paciente, validaciones de `SiembraMicrobiologia` (medio activo, misma muestra que el estudio) y `LecturaCultivo` (siembra y estudio coincidentes, no cancelados, fecha coherente).
- `laboratorio/tests/test_microbiologia_api.py`: permisos del catálogo medios (admin escribe, laboratorio no), permisos sobre estudios/siembras/lecturas por rol (laboratorio opera, médico solo ve sus estudios, paciente/anónimo bloqueados), creación de estudio con auditoría `CREATE`, fallas con muestras inválidas, idempotencia de `iniciar`, cancelación con/sin motivo, PATCH sin cambio de `estado`, transiciones automáticas `SEMBRADO` / `LECTURA_PRELIMINAR`, bloqueos por estudio/siembra cancelados, aliases `/api/laboratorio/microbiologia/...`. Las aserciones de auditoría usan `captureOnCommitCallbacks(execute=True)` para materializar los eventos `on_commit`.

**Fase B3.1-gap [IMPLEMENTADO]:** tests `test_estudio_microbiologia_permite_muestra_conservada`, `test_siembra_microbiologia_permite_muestra_conservada` (modelos); `test_api_crear_estudio_microbiologia_con_muestra_conservada`, `test_api_crear_siembra_con_muestra_conservada` (API).

**Fase B3.2 (Microorganismos / aislados / identificación):**

- `laboratorio/tests/test_microbiologia_models.py` (clases nuevas `TestMicroorganismoModel`, `TestAisladoModel`, `TestIdentificacionModel`): alta de `Microorganismo` (con `codigo` único), creación de aislado desde lectura válida, validaciones (lectura del estudio incorrecto, estudio cancelado, microorganismo inactivo, `IDENTIFICADO` exige microorganismo), `requiere_antibiograma` se registra sin disparar antibiograma, creación de identificación, bloqueos por microorganismo inactivo y aislado descartado, y verificación end-to-end con el servicio `crear_identificacion` para confirmar que actualiza el aislado a `IDENTIFICADO` y el estudio a `IDENTIFICACION`.
- `laboratorio/tests/test_microbiologia_api.py` (clases nuevas `TestMicroorganismoAPI`, `TestAisladoAPI`, `TestIdentificacionAPI`): catálogo de microorganismos (admin escribe, laboratorio no, paciente/anónimo bloqueados, alias), aislados (laboratorio crea, médico/paciente no, lectura de otro estudio rechazada, estudio cancelado bloquea, microorganismo inactivo bloquea, `descartar` con/sin motivo, PATCH no toca `estado`, alias), identificaciones (crea + actualiza aislado y estudio con auditoría `auto_identificacion`, microorganismo inactivo bloquea, aislado descartado y estudio cancelado bloquean, médico no crea, append-only via 405 en PATCH, alias). Continúa usando `captureOnCommitCallbacks(execute=True)` para auditoría.

**Fase B3.3 (Antibiograma microbiológico):**

- `laboratorio/tests/test_microbiologia_models.py` (clases nuevas `TestAntibioticoModel`, `TestAntibiogramaModel`, `TestResultadoAntibioticoModel`, `TestServiciosAntibiograma`): alta de `Antibiotico` con `codigo` único; creación de `Antibiograma` para aislado `IDENTIFICADO` y rechazo para aislados `SOSPECHADO`/`DESCARTADO` y para estudios `CANCELADO`; creación de `ResultadoAntibiotico` con interpretaciones válidas; bloqueo por antibiótico inactivo, interpretación inválida, antibiograma `COMPLETO`/`CANCELADO` y duplicado de antibiótico (UniqueConstraint); servicio `aplicar_completar_antibiograma` falla sin resultados, completa setea `fecha_resultado`; servicio `crear_antibiograma` mueve el estudio a `ANTIBIOGRAMA` y el primer resultado lleva el antibiograma a `EN_PROCESO`.
- `laboratorio/tests/test_microbiologia_api.py` (clases nuevas `TestAntibioticoAPI`, `TestAntibiogramaAPI`, `TestResultadoAntibioticoAPI`): catálogo de antibióticos (admin escribe y desactiva con auditoría `actualizar_antibiotico`, laboratorio lista pero no crea, paciente/anónimo bloqueados, sin DELETE, alias `/api/laboratorio/microbiologia/antibioticos/`); antibiogramas (laboratorio crea con auditoría `crear_antibiograma` + `auto_antibiograma`, médico/paciente/anónimo bloqueados para crear, fallas 400 con aislado descartado/no identificado/estudio cancelado, completar sin resultados falla, cancelar con/sin motivo, PATCH bloqueado si `COMPLETO`, médico vinculado lee solo su antibiograma —ajeno 404—, alias); resultados (laboratorio carga con auditoría y avanza a `EN_PROCESO`, duplicar antibiótico 400, antibiótico inactivo 400, no se carga si antibiograma `COMPLETO`/`CANCELADO`, completar con resultados funciona, PATCH bloqueado si antibiograma `COMPLETO`, alias). Auditoría sigue verificada con `captureOnCommitCallbacks(execute=True)`.

**Fase B3.4 (Informes microbiológicos):**

- `laboratorio/tests/test_microbiologia_models.py` (`TestInformeMicrobiologiaModel`): informes preliminares múltiples; unicidad de `FINAL` vigente; emisión con texto obligatorio; completitud (lecturas, aislados, antibiograma `COMPLETO` cuando `requiere_antibiograma`); transiciones de estudio `LISTO_PARA_VALIDAR` / `VALIDADO` / `INFORMADO`; anulación con motivo; bloqueos PATCH tras `VALIDADO`; etc.
- `laboratorio/tests/test_microbiologia_api.py` (`TestInformeMicrobiologiaAPI`): permisos lab/admin/médico/paciente; `validar` solo admin; `marcar-informado`; anulación con motivo; alias de rutas; auditoría con `captureOnCommitCallbacks(execute=True)`.

**Fase B2.1:** ampliación de `laboratorio/tests/test_resultados_muestras_api.py`:
- `test_carga_muestra_descartada_400`, `test_carga_muestra_cancelada_400` (matriz API completa de estados inválidos).
- `test_carga_primer_resultado_transiciona_muestra_a_en_proceso` (transición automática `RECIBIDA→EN_PROCESO` + `EventoMuestra` + `AuditEvent`, usando `captureOnCommitCallbacks`).
- `test_carga_segundo_resultado_misma_muestra_idempotente` (no duplica evento si muestra ya `EN_PROCESO`).
- `test_validar_muestra_descartada_falla`, `test_validar_muestra_cancelada_falla`, `test_validar_releyendo_muestras_con_select_for_update` (TOCTOU defensivo: mutación de muestra entre carga y validar bloquea la validación).

---

## Pruebas mínimas antes de cambios importantes

- `pytest turnos/tests/test_services.py turnos/tests/test_atencion_viewset.py`
- `pytest auditoria/tests/`
- `pytest laboratorio/tests/`
- Smoke `pytest pacientes/tests/test_api.py`

---

## Riesgos o inconsistencias

- Duplicación de lógica entre `api/views.py` y viewsets de apps puede hacer que los tests ejerciten **rutas equivocadas** si no importan el mismo módulo que el router.

---

## Pendiente de confirmar

- Configuración CI/CD y umbral de cobertura.
- Base de datos de test (SQLite vs PostgreSQL) en entornos locales.
