# DOC_FRONTEND — Frontend real del repositorio

**Fecha de generación:** 30 de abril de 2026  
**Última actualización:** mayo 2026 (C6.4.2 / C6.4.2-A)

> **Nota de actualización:** Las secciones históricas más abajo describían un escaneo previo del repo **sin** SPA en el árbol principal. Hoy el frontend vive en el **submódulo Git `frontend/`** (React + TypeScript + MUI). Las pantallas implementadas hasta **C6.4.2** (estudios complementarios, LIMS microbiología, turnos C5, archivos C6.2, etc.) se documentan en las secciones posteriores de este archivo — no inferir ausencia de UI por el texto legacy.

**Alcance:** Descripción del frontend en submódulo `frontend/` y contratos API consumidos.

**Fuentes revisadas:** `frontend/package.json`, `frontend/src`, `synesis/settings.py` (CORS/CSRF).

---

## Stack frontend (submódulo `frontend/`)

**Estado actual:** aplicación SPA en submódulo `frontend/` (no en la raíz del monorepo padre).

El backend está preparado para `http://localhost:3000` (CORS, cookies de sesión). El cliente de producción es el submódulo `frontend/`.

---

## Estructura de carpetas (histórico + actual)

- **`frontend/` (submódulo):** aplicación React (`src/pages`, `src/modules`, `src/services`).
- **`backup_documentacion/`:** scripts Node de prueba API — no son la SPA de producción.

---

## Rutas / páginas / componentes (resumen)

Ver secciones **Frontend EMR+LIMS (submódulo `frontend/`)** y **Estudios complementarios (C6.4.2)** más abajo.

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

### LIMS B2-C — Carga de resultados con muestra

- **Pantalla:** `OrdenLimsDetalle` → tab **Resultados** → `CargaResultadosLims`.
- **API:** `GET /lab/muestras-transaccionales/?solicitud=<id>`; `POST …/cargar-resultados/` con `muestra_id` opcional por ítem.
- **UX:** selector de muestra por determinación; badge **Requiere muestra** y **Tipo requerido** según catálogo `TipoExamen` (`requiere_muestra`, `tipo_muestra_requerida`); solo muestras **RECIBIDA / CONSERVADA / EN_PROCESO**; opciones filtradas al tipo requerido.
- **Validación frontend (B2-C):** bloquea submit si `requiere_muestra` sin muestra o si la muestra no coincide con `tipo_muestra_requerida`; el backend sigue siendo fuente de verdad.
- **Payload:** `muestra_id` solo si hay selección (no se envía `null` ni string vacío).
- **Errores:** `formatLimsHttpError` — 403/404/500 con mensajes genéricos; 400 muestra mensaje DRF (`error`/`detail`) sin loguear respuesta completa.
- **Privacidad:** etiquetas de muestra por id + tipo + estado (no `console.log` de payload/orden/muestra).
- **Roles:** carga editable solo con `canOperateLims` (admin/laboratorio), igual que UI-1.
- **Tests:** `frontend/src/utils/limsCargaMuestra.test.ts` (validación y payload).

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

### LIMS B3-frontend-validación [IMPLEMENTADO — jun 2026]

Relevamiento y validación del SPA microbiología existente (UI-2) contra backend B3.x.

**Rutas confirmadas:** `/laboratorio/microbiologia`, `/laboratorio/microbiologia/estudios`, `/laboratorio/microbiologia/estudios/:id` (5 tabs), `/laboratorio/microbiologia/catalogos`.

**Pantallas cubiertas (confirmado por código):**

| Dominio | UI |
|---------|-----|
| Estudios | listado + detalle + acciones `iniciar` / `cancelar` / `marcar-informado` |
| Siembras / lecturas | tab «Siembras y lecturas» |
| Aislados / identificaciones | tab «Aislados» |
| Antibiogramas / resultados | tab «Antibiograma» |
| Informes | tab «Informes» (`emitir`, `validar` admin, `anular`) |
| Catálogos | medios, microorganismos, antibióticos (escritura admin) |

**Contrato API:** `limsMicroApi.ts` alinea prefijo `/lab/microbiologia/...` con todos los endpoints backend B3.1–B3.4. Re-export vía `limsApi.ts`.

**Correcciones aplicadas (bugs mínimos):**

1. **Crecimiento lectura:** el selector usaba `AUSENTE` (inválido en backend); corregido a `SIN_DESARROLLO` + `MIXTO` (`SiembrasLecturasPanel.tsx`, `types/lims.ts`).
2. **Estudio cancelado:** tabs operativas ocultaban formularios solo si `estado === CANCELADO` (corregido en B3-frontend-validación-A).

**B3-frontend-validación-A [IMPLEMENTADO — jun 2026]:** `CANCELADO`, `VALIDADO` e `INFORMADO` bloquean operación técnica en UI. Helpers: `limsAccess.ts` (`isMicroEstudioCerrado`, `canOperateMicroEstudioTecnico`, `canMarcarMicroEstudioInformado`); constante en `types/lims.ts`. Alert en detalle; datos históricos visibles; «Marcar informado» solo desde `VALIDADO`. Backend (`ESTADOS_BLOQUEAN_OPERACION_MICRO` + `assert_estudio_micro_operable`) es fuente de verdad. Test Jest: `limsAccess.test.ts`.

**B3-frontend-validación-A [VALIDADO — jun 2026]:** revalidado con PostgreSQL: `TestEstudioMicroCerradoOperacionAPI` 4/4; `test_microbiologia_*` 165/165; regresión LIMS 315/315. Paquete Codex: `docs_synesis/B3_VALIDACION_A_CODEX_AUDIT.md`.

**B3-frontend-UX [PARCIAL — jun 2026]:**

- **[IMPLEMENTADO]** Picker solicitud/muestra al crear estudio (`MicrobiologiaEstudios.tsx`): `listSolicitudesExamen`, `listMuestrasPorSolicitud`, muestras `RECIBIDA`/`CONSERVADA`/`EN_PROCESO` vía `limsMicroUx.ts`; ingreso manual en acordeón avanzado.
- **[GAP]** Detalle sigue cargando listados micro globales y filtra en cliente — backend micro no expone filtro `estudio_id` (solo `SearchFilter`/`OrderingFilter`).
- **[GAP]** E2E browser micro: sin Playwright/Cypress en repo.
- Tests Jest: `limsAccess.test.ts`, `limsMicroUx.test.ts` (además de `limsCargaMuestra.test.ts` B2-C).
- PDF / portal paciente / QC / CLSI-EUCAST: fuera de alcance.

**Seguridad frontend:** sin `console.log`/`console.error` sensibles en componentes LIMS/micro (confirmado por grep). Errores vía `formatDrfError` + toast.

**Validaciones ejecutadas (jun 2026):**

```bash
cd frontend && npm exec -- tsc --noEmit          # OK
cd frontend && npm run build                     # OK
CI=true npm test -- --watchAll=false --runInBand src/utils/limsCargaMuestra.test.ts  # 6/6 OK
./emr_env/bin/python manage.py check             # OK
./emr_env/bin/python manage.py makemigrations --check --dry-run  # sin cambios
./emr_env/bin/pytest laboratorio/tests/test_microbiologia_*.py -q --reuse-db  # 161/161 OK
```

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
- **Estado del turno:** chip de solo lectura en `TurnoModal`; cambios vía acciones POST (`confirmar`, `cancelar`, `reprogramar`, `marcar-realizado`, `marcar-no-asistio`). **C5.10.1:** inicio clínico vía `iniciarAtencionTurno`. **C5.10.2:** `createAtencion` marcado `@deprecated` (compat); agenda no debe usarlo. No PATCH `estado`.

### Turnos — acciones de estado (C5.9.2)

| UI | API |
|----|-----|
| Botones en `TurnoModal`: Confirmar, Cancelar, Marcar realizado, No asistió | `POST .../confirmar/`, `cancelar/`, `marcar-realizado/`, `marcar-no-asistio/` |
| Crear / abrir consulta (médico) | `POST .../iniciar-atencion/` vía `iniciarAtencionTurno` (C5.10.1) |
| Cerrar atención | `POST .../cerrar/` vía `closeAtencion` (C5.10.1-A; antes `/cerrar_atencion/` legacy) |
| `TurnosMedico.tsx` | **No enrutado** en `App.tsx`; migrado a `iniciarAtencionTurno` por si se reactiva |
| Chip de estado (solo lectura) para todos los roles | PATCH/PUT `estado` bloqueado (400) |
| Guardar con cambio de fecha/médico/recurso | `POST .../reprogramar/` (motivo por `prompt`) **[DEUDA]** modal dedicado |
| `cancelarTurno(id, motivo)` en `api.ts` | Motivo obligatorio (prompt mínimo) |

- Validación: `cd frontend && npm run build && npm exec -- tsc --noEmit`.

### Archivos y documentos clínicos (C6.2)

| Archivo | Cambio |
|---------|--------|
| `Sidebar.tsx` | Menú **Archivos** solo `medico`, `admin`, `paciente` |
| `ArchivosMedicos.tsx` | Descarga vía `downloadArchivoMedico`; sin botón eliminar |
| `apiService.ts` | Errores genéricos; `getArchivosPorConsulta` filtra por `consulta` |
| `DocumentosAdjuntos.tsx` | Descarga vía `apiService.downloadDocumento`; sin URL media directa |
| `types/index.ts` | `download_url`, `archivo_nombre`, `archivo_size` |

### Estudios complementarios EMR (C6.4.2) [IMPLEMENTADO]

| Ruta | Componente |
|------|------------|
| `/estudios-complementarios` | `EstudiosComplementarios.tsx` |
| `/estudios-complementarios/:id` | `EstudioComplementarioDetalle.tsx` |

**Servicios:** `frontend/src/services/estudiosComplementariosApi.ts` (re-export opcional desde `apiService.ts`).

**Tipos:** `frontend/src/types/estudios.ts`.

**Permisos UI:** `frontend/src/modules/estudios/permissions.ts`.

| Rol | Módulo sidebar | Acciones visibles |
|-----|----------------|-----------------|
| admin / superuser | Sí | CRUD metadata, estados, informes, validar, rectificar, archivos |
| médico | Sí | Crear, marcar realizado, informar, rectificar; **sin validar** |
| paciente | Sí | Solo estudios **ENTREGADO**; descarga si backend permite |
| secretaría / enfermería / laboratorio | **No** | — |

**Reglas UI:** estado solo lectura (chip); acciones POST; sin `/media/`; descarga blob; rectificación desde ENTREGADO (emitir → INFORMADO).

**Deuda:** visor/PACS; subida directa de archivo desde estudio (solo asociar `ArchivoMedico` existente); tests E2E dedicados.

**Validación (mayo 2026):** `npm exec -- tsc --noEmit` OK; `npm run build` OK.

**C6.4.2-A:** `UpdateEstudioComplementarioPayload` tipado aparte de create (sin `paciente_id` ni `estado` en PATCH). Jest/E2E dedicados: deuda.
