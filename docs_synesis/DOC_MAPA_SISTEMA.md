# DOC_MAPA_SISTEMA — Resumen ejecutivo SYNESIS

**Fecha de generación:** 30 de abril de 2026  
**Actualización (PROD-1 configuración producción):** 7 de junio de 2026  
**Actualización (LIMS hardening, rol `laboratorio`):** 2 de mayo de 2026  

**Alcance:** Visión de conjunto del repositorio `emr` (proyecto Django `synesis`): EMR + LIMS embebido en backend, sin asumir despliegue productivo ni frontend en este repo.

**Fuentes revisadas:** `synesis/settings.py`, `synesis/urls.py`, `api/urls.py`, apps listadas en `INSTALLED_APPS`, estructura de carpetas, ausencia de `package.json` / `frontend/`.

---

## Qué hace el sistema

Backend **Django 5.x** con **Django REST Framework** que modela:

- **EMR:** pacientes, usuarios con roles, médicos y especialidades, turnos y recursos, atenciones clínicas (consulta ambulatoria, procedimiento, quirúrgico), historia clínica y consultas, diagnósticos CIE-10, prescripciones, internación (dos modelados: catálogo `historias_clinicas.Internacion` vs app `internacion`), documentos clínicos y archivos médicos.
- **LIMS (en el mismo proyecto):** catálogo de tipos de muestra, tipos de examen, paneles; órdenes (`SolicitudExamen`) con estados; resultados por examen; acciones de carga masiva y validación vía API.
- **Integración:** app `solicitudes` (órdenes genéricas EMR→LIMS externo vía `integracion_lims.lims_service`) y modelos espejo `integracion_lims` para sincronización; **servicio HTTP apunta a URL fija** (posiblemente otro proceso).

---

## Módulos principales (apps Django)

| App | Rol aproximado |
|-----|----------------|
| `core` | Health check; sin modelos de negocio |
| `usuarios` | `User` extendido (`rol`), perfiles, secretarias |
| `pacientes` | Ficha paciente |
| `medicos` | Médicos, especialidades, disponibilidad/excepciones |
| `emr` | Signos vitales, documentos por atención |
| `turnos` | Recursos, turnos, atención y registros hijos |
| `historias_clinicas` | HC, consultas, diagnósticos, tratamientos, prescripciones, `Internacion` (cama catálogo) |
| `catalogos` | CIE-10, medicamentos, procedimientos, centros físicos, tipos atención, áreas/camas internación, estudios/procedimientos catálogo |
| `api` | Routers agregados, vistas legacy duplicadas (`api/views.py`) |
| `archivos_medicos` | Archivos adjuntos clínicos |
| `integracion_lims` | Modelos LIMS externos + `lims_service`; **URLs de webhook no montadas en `synesis.urls`** |
| `solicitudes` | Solicitudes transversales y sync opcional |
| `internacion` | Sectores, camas, internaciones simplificadas |
| `laboratorio` | LIMS nativo (órdenes, resultados) |
| `auditoria` | `AuditEvent` append-only, middleware de contexto |

---

## Arquitectura general

```
Cliente (React esperado en :3000 según CORS; no presente en repo)
    → HTTP /api/... (session + JWT + token legacy)
    → Django + DRF + django-filter
    → PostgreSQL (config por env)
```

---

## Backend

- **Proyecto:** `synesis` (`synesis/settings.py`, `synesis/env_config.py`, `synesis/urls.py`).
- **PROD-1:** configuración por env; validación producción; checklist `PROD_CHECKLIST.md`.
- **API principal:** prefijo `/api/` (`api.urls`).
- **Usuarios/JWT:** `/api/usuarios/` (`usuarios.urls`).
- **Patrón:** `DefaultRouter` con muchos `ViewSet`; permisos por rol en `get_queryset` y clases en `api/permissions.py`.

---

## Frontend

**No hay aplicación frontend en el repositorio** (sin `package.json`, sin `frontend/src`). Solo scripts de prueba en `backup_documentacion/*.js` que consumen la API. Ver `DOC_FRONTEND.md`.

---

## Base de datos

- Motor por defecto: **PostgreSQL** (`django.db.backends.postgresql`).
- Modelos repartidos por apps; **duplicidad conceptual:** dos modelos `Internacion` y dos flujos de camas/internación.

---

## Flujos principales

1. **Agenda:** `Turno` (estados) → filtrado por rol; creación con reglas para paciente.
2. **Atención:** POST `/api/atenciones/` con `turno` → `AtencionService` (modo compat no mueve estado del turno igual que modo servicio interno).
3. **Historia:** `HistoriaClinica` + `Consulta` + diagnósticos/prescripciones.
4. **Laboratorio:** POST orden lab → `SolicitudExamen` + filas `ResultadoExamen` vacías → `cargar-resultados` → `validar`.
5. **Solicitudes EMR:** `solicitudes.Solicitud` con envío opcional a LIMS externo si `LIMS_AUTO_SEND=true`.

---

## Puntos críticos

- LIMS nativo: permisos por rol (`LimsCatalogReadPermission`, `LimsSolicitudExamenPermission`); rol **`laboratorio`** en `User`; sin `AllowAny` en ViewSets LIMS sensibles.
- ~~Deuda `tecnico` en EMR~~ — retirado de `IsEMRClinician` y `api/views.py`; operador lab formal **`laboratorio`** solo en flujos LIMS.
- Comparación de roles en `solicitudes` con `.upper()` vs valores en minúsculas en el modelo.
- `api/views.py` contiene ViewSets extensos que **pueden solaparse** con los importados desde apps; el router usa explícitamente los de `pacientes.views`, `turnos.views`, etc.
- Webhooks `integracion_lims/urls.py` **no incluidos** en URLconf raíz.

---

## Dependencias (runtime)

Ver `requirements.txt`: Django ≥5, DRF, cors-headers, django-filter, psycopg2-binary, python-dotenv, djangorestframework-simplejwt, Faker, requests.

---

## Documentos generados (SYNESIS)

En `docs_synesis/`:

1. `DOC_MAPA_SISTEMA.md` (este archivo)
2. `DOC_REGLAS_NEGOCIO.md`
3. `DOC_MODELOS_DB.md`
4. `DOC_API_ENDPOINTS.md`
5. `DOC_BACKEND.md`
6. `DOC_FRONTEND.md`
7. `DOC_FLUJOS_EMR.md`
8. `DOC_FLUJOS_LIMS.md`
9. `DOC_PERMISOS_AUDITORIA.md`
10. `DOC_TESTS.md`
11. `DOC_RIESGOS_DEUDA_TECNICA.md`

---

## Cómo debe usar SYNESIS esta documentación

- Tratar estos archivos como **fuente de verdad del código presente**, no del producto desplegado.
- Antes de diseñar cambios: `DOC_MAPA_SISTEMA` → `DOC_REGLAS_NEGOCIO` → módulo específico (`DOC_FLUJOS_*`, `DOC_MODELOS_DB`, `DOC_API_ENDPOINTS`).
- Para seguridad y trazabilidad: `DOC_PERMISOS_AUDITORIA.md`.
- Para riesgos y deuda: `DOC_RIESGOS_DEUDA_TECNICA.md`.
- Para coordinar SYNESIS, Cursor y Codex: `DOC_TRABAJO_SYNESIS_CURSOR_CODEX.md`.

---

## Orden recomendado de lectura

1. `DOC_MAPA_SISTEMA.md`
2. `DOC_REGLAS_NEGOCIO.md`
3. `DOC_MODELOS_DB.md`
4. `DOC_API_ENDPOINTS.md`
5. `DOC_BACKEND.md`
6. `DOC_FLUJOS_EMR.md` y `DOC_FLUJOS_LIMS.md`
7. `DOC_PERMISOS_AUDITORIA.md`
8. `DOC_FRONTEND.md`
9. `DOC_TESTS.md`
10. `DOC_RIESGOS_DEUDA_TECNICA.md`
11. `DOC_TRABAJO_SYNESIS_CURSOR_CODEX.md` (proceso IA: SYNESIS → Cursor → Codex → validación → commit)

---

## Riesgos o inconsistencias

Resumidas aquí; detalle en `DOC_RIESGOS_DEUDA_TECNICA.md` y secciones homónimas en cada documento.

---

## Pendiente de confirmar

- Si en producción existe un frontend separado no versionado aquí.
- Si `integracion_lims` webhook debe montarse bajo algún prefijo.
- Configuración real de BD, `DEBUG`, `SECRET_KEY`, y orígenes CORS en producción.
