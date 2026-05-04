# DOC_FRONTEND — Frontend real del repositorio

**Fecha de generación:** 30 de abril de 2026  

**Alcance:** Descripción del frontend **presente en el repositorio**; no se asume código React/Vue fuera del tree.

**Fuentes revisadas:** búsqueda global de `package.json`, `*.tsx`, `*.jsx`, `frontend/src`; `backup_documentacion/*.js`; `synesis/settings.py` (CORS, CSRF para `localhost:3000`).

---

## Stack frontend

**No detectado en el código actual:** no hay `package.json` en la raíz ni carpeta `frontend/` con aplicación SPA.

El backend está **preparado** para un cliente en `http://localhost:3000` (CORS, `CSRF_TRUSTED_ORIGINS`, comentarios en `REST_FRAMEWORK` sobre sesión/cookies). Eso indica intención de un frontend separado; **no está incluido en este repo**.

---

## Estructura de carpetas

- **`backup_documentacion/`:** scripts Node (`axios`, `fetch`) que prueban login, turnos, etc. contra `http://127.0.0.1:8000` u otros puertos — **no son la aplicación de producción**, son artefactos de depuración/documentación histórica.

---

## Rutas / páginas / componentes

**No aplicable:** sin árbol `src/` de aplicación.

---

## Layout, módulos EMR/LIMS, formularios, tablas, modales, hooks

**No detectado.**

---

## Servicios API y estado

Los únicos consumos referenciados en el repo (fuera de tests Django) aparecen en scripts bajo `backup_documentacion/`, por ejemplo:

- `POST /api/auth/login/` (sesión/cookies)
- `GET /api/auth/current-user/`
- `PUT /api/turnos/{id}/`

**Pendiente de confirmar:** si el frontend real vive en otro repositorio o rama.

---

## Validaciones frontend, errores, permisos/guards

**No hay código de aplicación** que auditar.

---

## Pantallas críticas y flujos de usuario

Inferidos solo desde documentación de backup y comentarios en backend; **no verificables en código frontend**.

---

## Endpoints consumidos (inferido desde scripts de backup)

| Uso aproximado | Endpoint |
|----------------|----------|
| Auth | `/api/auth/login/`, `/api/auth/current-user/` |
| Turnos | `/api/turnos/` |

Lista completa de API en `DOC_API_ENDPOINTS.md`.

---

## Inconsistencias con backend

- El backend documenta compatibilidad con prefijos `catalogos/` y `archivos-medicos/`; los scripts de backup no cubren todo el contrato.
- No se puede afirmar qué endpoints usa una SPA inexistente en el repo.

---

## Deuda técnica visual o funcional

- **Ausencia total de UI versionada** imposibilita revisión de UX, accesibilidad o coherencia con DRF.
- Riesgo de **drift** entre un futuro frontend y los múltiples alias de rutas en `api/urls.py` (p. ej. `lab/` vs `laboratorio/`).

---

## Riesgos o inconsistencias

- CORS en `DEBUG=True` permite todos los orígenes (`CORS_ALLOW_ALL_ORIGINS`) — impacto solo backend, pero el cliente “típico” asumido en settings no está acá.

---

## Pendiente de confirmar

- Ubicación y stack del cliente EMR+LIMS real (React, otro).
- Si Storybook o assets estáticos existen fuera del repo.
