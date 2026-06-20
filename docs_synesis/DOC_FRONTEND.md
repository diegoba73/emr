# DOC_FRONTEND — Frontend real del repositorio

**Fecha de generación:** 30 de abril de 2026  
**Última actualización:** junio 2026 (cierre filtro `estudio_id` micro + corrección secciones legacy)

> **Nota de actualización:** Las secciones marcadas **[OBSOLETO — escaneo C0]** describían un estado previo **sin** SPA en el árbol principal. El frontend real vive en **`frontend/`**, carpeta normal del monorepo `emr` (desde jun 2026; antes era gitlink/repo anidado sin `.gitmodules`). Último SHA del repo histórico `emr-frontend`: `417e9a2`. Stack: React + TypeScript + MUI. Pantallas LIMS/micro confirmadas en código (`App.tsx`, `pages/laboratorio/*`, `services/limsMicroApi.ts`).

**Alcance:** Descripción del frontend en `frontend/` (monorepo) y contratos API consumidos.

**Fuentes revisadas:** `frontend/package.json`, `frontend/src`, `synesis/settings.py` (CORS/CSRF).

---

## Stack frontend (`frontend/` — monorepo)

**Estado actual:** aplicación SPA en `frontend/` versionada directamente en el repo padre `emr` (un solo commit/push/PR). El remoto histórico `https://github.com/diegoba73/emr-frontend.git` queda como respaldo; ya no es dependencia operativa.

El backend está preparado para `http://localhost:3000` (CORS, cookies de sesión). El cliente de producción es `frontend/`.

---

## Estructura de carpetas (histórico + actual)

- **`frontend/` (monorepo):** aplicación React (`src/pages`, `src/modules`, `src/services`).
- **`backup_documentacion/`:** scripts Node de prueba API — no son la SPA de producción.

---

## Rutas / páginas / componentes (resumen)

Ver secciones **Frontend EMR+LIMS (`frontend/`)** y **Estudios complementarios (C6.4.2)** más abajo.

---

## [OBSOLETO — escaneo C0] Secciones históricas (no usar como fuente de verdad)

> **Advertencia:** El bloque siguiente refleja un escaneo de abril 2026 cuando no se indexaba `frontend/`. **No refleja el estado actual.** Ver secciones posteriores «Frontend EMR+LIMS» y «UI-2 Microbiología».

## Layout, módulos EMR/LIMS, formularios, tablas, modales, hooks

**[OBSOLETO]** ~~No detectado.~~ — **Confirmado jun 2026:** módulos en `frontend/src/pages`, `components`, `services`.

## Servicios API y estado

**[OBSOLETO]** Los únicos consumos referenciados en el repo (fuera de tests Django) aparecen en scripts bajo `backup_documentacion/`, por ejemplo:

- `POST /api/auth/login/` (sesión/cookies)
- `GET /api/auth/current-user/`
- `PUT /api/turnos/{id}/`

**[OBSOLETO]** ~~Pendiente de confirmar: si el frontend real vive en otro repositorio o rama.~~ — **Confirmado:** `frontend/` en monorepo con SPA React; consumo real vía `limsApi.ts`, `limsMicroApi.ts`, `estudiosComplementariosApi.ts`, etc.

## Validaciones frontend, errores, permisos/guards

**[OBSOLETO]** ~~No hay código de aplicación que auditar.~~ — **Confirmado:** guards en `utils/limsAccess.ts`, `DataContext`, rutas protegidas en `App.tsx`.

## Pantallas críticas y flujos de usuario

**[OBSOLETO]** ~~Inferidos solo desde documentación de backup…~~ — **Confirmado en código:** órdenes LIMS, detalle micro por tabs, estudios complementarios.

## Endpoints consumidos (inferido desde scripts de backup)

| Uso aproximado | Endpoint |
|----------------|----------|
| Auth | `/api/auth/login/`, `/api/auth/current-user/` |
| Turnos | `/api/turnos/` |

Lista completa de API en `DOC_API_ENDPOINTS.md`.

---

## Inconsistencias con backend

**[OBSOLETO parcial]**
- ~~No se puede afirmar qué endpoints usa una SPA inexistente en el repo.~~ — La SPA existe; ver servicios en `frontend/src/services/`.
- El backend documenta compatibilidad con prefijos `catalogos/` y `archivos-medicos/`; el frontend consume alias `lab/` (equivalente a `laboratorio/`).

## Deuda técnica visual o funcional

- **[OBSOLETO]** ~~Ausencia total de UI versionada~~ — UI versionada en `frontend/` (monorepo).
- Riesgo de **drift** entre frontend y alias `lab/` vs `laboratorio/` (mitigado: backend usa mismas clases ViewSet).
- **`window.prompt` en acciones con motivo** — **resuelto (jun 2026):** reemplazado por `MotivoDialog` MUI (`frontend/src/components/common/MotivoDialog.tsx`) en microbiología (`MicrobiologiaEstudioDetalle`, `AntibiogramaPanel`, `AisladosIdentificacionPanel`, `InformesMicrobiologiaPanel`) y en agenda EMR (`TurnoModal.tsx`: cancelar, no asistió, reprogramar).

---

## Riesgos o inconsistencias

- CORS en `DEBUG=True` permite todos los orígenes (`CORS_ALLOW_ALL_ORIGINS`) — impacto solo backend, pero el cliente “típico” asumido en settings no está acá.

---

## Pendiente de confirmar

- Ubicación y stack del cliente EMR+LIMS real (React, otro).
- Si Storybook o assets estáticos existen fuera del repo.

---

## Frontend EMR+LIMS (`frontend/`) — actualización UI-2

> Las secciones anteriores de este documento reflejan un escaneo previo sin SPA. La aplicación React vive en **`frontend/`** (carpeta normal del monorepo; antes gitlink `417e9a2` en repo histórico `emr-frontend`).

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

- **`frontend/src/services/limsMicroApi.ts`:** prefijo canónico `/lab/microbiologia/...` (medios, estudios, siembras, lecturas, microorganismos, aislados, identificaciones, antibióticos, antibiogramas, resultados, informes + acciones `iniciar`, `cancelar`, `marcar_informado`, `descartar`, `completar`, `emitir`, `validar`, `anular`). Listados relacionados con estudio aceptan **`?estudio_id=<entero positivo>`** server-side; valores inválidos → **HTTP 400** (jun 2026).
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
- **[IMPLEMENTADO — jun 2026]** Detalle micro (`MicrobiologiaEstudioDetalle.tsx`) envía `?estudio_id=` en listados filtrados vía `limsMicroApi.ts` (backend: `_apply_estudio_id_query_filter` en `views_microbiologia.py`).
- **[GAP]** E2E browser micro: sin Playwright/Cypress en repo (E2E-1/E2E-1-A jun 2026 validan flujo crítico y cierre micro en backend: `test_lims_flujo_critico.py`).
- Tests Jest: `limsAccess.test.ts`, `limsMicroUx.test.ts` (además de `limsCargaMuestra.test.ts` B2-C).
- **PDF-1-FE (jun 2026) [IMPLEMENTADO]:** botón «Descargar informe PDF» en `OrdenLimsDetalle.tsx`; servicio `downloadInformeLimsPdf` / `getInformeLimsPdfBlob` en `limsApi.ts` (`GET /lab/solicitudes/{id}/informe-pdf/`, `responseType: blob`); helpers `limsDownload.ts` (filename seguro, errores 403/404/500); permiso UI `canDownloadInformeLimsPdf` (admin/laboratorio/médico). Sin `/media/`, sin logs sensibles, URL temporal revocada vía `triggerBlobDownload`. Tests: `limsAccess.test.ts`, `limsDownload.test.ts`.
- Portal paciente / QC / CLSI-EUCAST / PDF profesional: fuera de alcance.

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
