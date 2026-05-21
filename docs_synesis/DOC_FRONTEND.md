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

---

## Frontend EMR+LIMS (submódulo `frontend/`) — actualización UI-2

> Las secciones anteriores de este documento reflejan un escaneo previo sin SPA. La aplicación React vive en el **submódulo Git** `frontend/` (commit UI-2: `d46d276`). Repo padre referencia ese commit en `4de661d`.

**Stack:** React + TypeScript + MUI + React Router; cliente HTTP con sesión/cookies; tests CRA/Jest.

### Rutas LIMS — UI-2 Microbiología

| Ruta | Componente |
|------|----------------|
| `/laboratorio/microbiologia` | `MicrobiologiaHub` (redirige a estudios) |
| `/laboratorio/microbiologia/estudios` | `MicrobiologiaEstudios` |
| `/laboratorio/microbiologia/estudios/:id` | `MicrobiologiaEstudioDetalle` (tabs) |
| `/laboratorio/microbiologia/catalogos` | `MicrobiologiaCatalogos` |

**UI-1 (sin cambios):** `/laboratorio/ordenes`, `/laboratorio/ordenes/:id`. No se modifica `/solicitudes` EMR.

### Componentes principales (UI-2)

- **Páginas:** `MicrobiologiaEstudios`, `MicrobiologiaEstudioDetalle`, `MicrobiologiaCatalogos`, `MicrobiologiaHub`.
- **Panels (tabs detalle):** `EstudioMicroResumenTab`, `SiembrasLecturasPanel`, `AisladosIdentificacionPanel`, `AntibiogramaPanel`, `InformesMicrobiologiaPanel`.
- **Badges:** `MicroBadges.tsx` (`EstudioMicrobiologiaEstadoBadge`, `AisladoEstadoBadge`, `AntibiogramaEstadoBadge`, `InformeMicrobiologiaEstadoBadge`, `InterpretacionAntibioticoBadge`).

### Servicios API (cliente)

- **`frontend/src/services/limsMicroApi.ts`:** prefijo canónico `/lab/microbiologia/...` (medios, estudios, siembras, lecturas, microorganismos, aislados, identificaciones, antibióticos, antibiogramas, resultados, informes + acciones `iniciar`, `cancelar`, `marcar_informado`, `descartar`, `completar`, `emitir`, `validar`, `anular`).
- Re-export desde `limsApi.ts`; errores DRF vía `formatDrfError` (403 → toast, sin logout).

### Permisos visuales (`frontend/src/utils/limsAccess.ts`)

| Función | Quién |
|---------|--------|
| `canAccessMicrobiologia` | ADMIN, LABORATORIO, MEDICO (lectura) |
| `canOperateMicrobiologia` | ADMIN, LABORATORIO |
| `canValidarInformeMicro` | ADMIN |
| `canEditMicroCatalogos` | ADMIN |

Médico: sin acciones operativas. Backend sigue siendo fuente de verdad en 403.

### Validaciones ejecutadas (UI-2, mayo 2026)

```bash
cd frontend && npx tsc --noEmit && npm run build
CI=true npm test -- --watchAll=false --runInBand
```

Resultado: TypeScript OK, build OK, **11 suites / 25 tests** OK.

### Fuera de alcance UI-2

PDF, firma digital, QC/equipamiento, portal paciente, endpoints legacy `/solicitudes-examen/` y `/resultados-examen/`.

---

### Turnos — permisos UI (C5.8.2, mayo 2026)

Alineado con matriz backend C5.8.1 (`turnos.views.TurnoViewSet`).

| Archivo | Rol |
|---------|-----|
| `frontend/src/utils/turnoPermissions.ts` | Helpers `canCreateTurno`, `canEditTurno`, `canDeleteTurno` (siempre false) |
| `frontend/src/pages/Turnos.tsx` | Oculta “Nuevo Turno”, slots y franjas si no puede crear; laboratorio: mensaje; enfermería: banner solo lectura |
| `frontend/src/components/TurnoModal.tsx` | `forceReadOnly`; médico bloqueado para rol `MEDICO`; paciente bloqueado para `PACIENTE` |

- No hay botón eliminar (DELETE → 405 en API).
- **Estado del turno:** chip de solo lectura en `TurnoModal`; cambios vía acciones POST (`confirmar`, `cancelar`, `reprogramar`, `marcar-realizado`, `marcar-no-asistio`). **C5.10.1:** inicio clínico vía `apiService.iniciarAtencionTurno` → `POST .../iniciar-atencion/` (no `createAtencion` en flujo médico principal). No PATCH `estado`.

### Turnos — acciones de estado (C5.9.2)

| UI | API |
|----|-----|
| Botones en `TurnoModal`: Confirmar, Cancelar, Marcar realizado, No asistió | `POST .../confirmar/`, `cancelar/`, `marcar-realizado/`, `marcar-no-asistio/` |
| Crear / abrir consulta (médico) | `POST .../iniciar-atencion/` vía `iniciarAtencionTurno` (C5.10.1) |
| Chip de estado (solo lectura) para todos los roles | PATCH/PUT `estado` bloqueado (400) |
| Guardar con cambio de fecha/médico/recurso | `POST .../reprogramar/` (motivo por `prompt`) **[DEUDA]** modal dedicado |
| `cancelarTurno(id, motivo)` en `api.ts` | Motivo obligatorio (prompt mínimo) |

- Validación: `cd frontend && npm run build && npm exec -- tsc --noEmit`.
