# Diseño — Estudios y procedimientos (con cirugía)

**Estado:** base aceptada para tickets por etapas (oct 2026).  
**Implementación:** **A0 cerrado**; **A1** empaquetado; **A2/A2b** implementado + cierre `CIERRE_ETAPA_A2.md` (depende A0+A1); **A3** ticket en revisión `tickets/TICKET_A3_SESION_ACTIVIDAD.md` — **no implementado**.  
**Restricción prevalente:** LIMS intocable (directa e indirectamente).  
**Checklist A0:** `docs_synesis/checklists/etapa-a0-regresion-lims-agenda.md`.

---

## 1. Precisiones finales (normativas)

### 1.1 LIMS intocable

- No modificar código, modelos, tablas, API, permisos, flujos, UI ni documentos de LIMS (`laboratorio/**`, pedidos/muestras/resultados/micro/IQC/validación/informes/impresiones lab y docs de reglas LIMS).
- Un PR con diff vacío en `laboratorio/` **no basta**: hay que preservar el comportamiento de **dependencias compartidas** (`turnos`, `medicos.agenda`, `Atencion`/`AtencionService`, pacientes, roles, auditoría, HC) en los caminos que LIMS/EMR ya usan.
- Si una solución exige alterar LIMS → descartarla. Si no hay alternativa compatible → informar impedimento, no implementar ese cambio.

**Dependencias compartidas a vigilar (regresión):**

| Compartido | Riesgo | Verificación |
|------------|--------|--------------|
| `turnos.Turno` / `Recurso` / `turno_estado` | Cambiar validaciones globales de agenda | Consultorio: reservar/reprogramar/cancelar igual que hoy |
| `medicos.agenda.validar_reserva` | Romper duración de slot ambulatorio | Turno médico 20/30 min sigue exigiendo duración de slot |
| `AtencionService` / factory hijo | Cambiar mapeo recurso→registro | Iniciar atención desde consultorio/guardia/sala sin cambio de semántica |
| Roles / pacientes / HC | Ampliar o restringir lab | Login laboratorio, listados lab, pedidos desde HC |

### 1.2 Catálogo `SIN_ASIGNAR`

- Se admite **solo** para conservar históricos / ítems aún no revisados.
- **Nuevas** solicitudes `PROCEDIMIENTO` / `CIRUGIA` exigen clasificación explícita (`NO_QUIRURGICO` o `QUIRURGICO`) en el catálogo elegido al crear.

### 1.3 Clasificación histórica

- Al **crear** la solicitud se guarda snapshot de clasificación (y `tipo_actividad`).
- Correcciones posteriores: acción **explícita**, autorizada (admin / rol definido) y **auditada**.
- Cambios administrativos del catálogo **no** reclasifican solicitudes ni actos existentes.

### 1.4 Atención con registro incompatible

- Si ya existe `Atencion` vinculable con registro hijo **incompatible** con `tipo_actividad`: **bloquear** la vinculación y exigir **resolución manual**.
- **No** crear otra atención automáticamente.
- **No** reemplazar ni eliminar el registro incompatible.

### 1.5 Multisesión

- La modalidad multisesión la define el flag/configuración de la indicación o del tipo (`permite_multi_sesion`), **no** el conteo actual de filas sesión.
- Una indicación multisesión **sigue siendo** multisesión aunque solo tenga una sesión cargada.

### 1.6 `EstudioComplementario.turno` (espejo) y endpoints legacy

**Significado exacto del espejo:**

| Situación | Valor de `estudio.turno` |
|-----------|---------------------------|
| Mono-sesión (`permite_multi_sesion=false`) — **A3 vigente** | FK **histórica** a `sesión#1.turno` (se conserva aunque el turno esté REALIZADO o CANCELADO). `null` solo si la sesión #1 no tiene turno. **No** limpiar por “dejar de estar vigente”. |
| Multisesión | **Diferido a A4** — no habilitado en API/admin en A3 |

Referencia futura A4 (no implementada):

| Situación (A4) | Valor de `estudio.turno` |
|----------------|---------------------------|
| Multisesión con **como máximo una** sesión con turno vigente (RESERVADO/CONFIRMADO) | Ese turno (conveniencia de lectura legacy) |
| Multisesión con **cero** turnos vigentes | `null` |
| Multisesión con **más de un** turno vigente | `null` (ambiguo; no elegir en silencio) |

- Canónico de reserva: `SesionActividad.turno` (por sesión).
- “Programado” (bandejas/UI) se deriva del **estado de la reserva**, separado del vínculo histórico `estudio.turno`.
- Escritura del espejo: **solo** en la misma TX que muta la sesión vía servicios del módulo.
- **Endpoints legacy** (`asignar-turno`, `agendar-turno`, y cualquier mutación que hoy asuma “el” turno del estudio):
  - Multisesión: **off** en A3 (A4: exigir `sesion_id` o 4xx; no inferir).
  - Mono-sesión: operan sobre la sesión #1 sin `sesion_id` (compat).
- **Lecturas:** no “reparar” divergencias espejo/sesión. Detección/reparación = comando/admin explícito, no en GET.

### 1.7 `RegistroQuirurgico` — acto vs cierre documental

Campos hoy obligatorios en modelo (`turnos/models.py`): `anestesista`, `diagnostico_preoperatorio`, `protocolo_quirurgico` (el resto es opcional/blank).

- Separar en diseño de etapas C/D: **datos mínimos del acto** (identidad del registro + vínculo atención + lo indispensable para crear la fila sin mentir) vs **requisitos de cierre documental** (protocolo completo, consentimiento, recuento, etc.).
- **No** placeholders (`"Pendiente de completar"`, anestesista dummy).
- **No** flexibilizar modelos compartidos (`RegistroQuirurgico` / `Atencion`) sin análisis de dependencias y **sin** impactar LIMS; si hace falta nullable, es decisión explícita de etapa posterior con migración aditiva y compatibilidad de flujos EMR existentes.

### 1.8 Reversión

- Debe existir una **versión de código desplegable** que lea/escriba de forma segura los datos nuevos (sesiones, snapshots, tipo_actividad) — p. ej. mantener la app en un tag que conoce el esquema aditivo.
- **No** depender de middleware/flags que el binario antiguo no tenga.
- **No** aplanar N sesiones en un turno.
- Rollback de feature = desplegar versión compatible + desactivar UI de features no listas; datos aditivos se conservan.

---

## 2. Alcance (recordatorio)

| Capa | Contenido |
|------|-----------|
| Final | Estudios, procedimientos, cirugías; programación quirúrgica básica; sesiones; bandejas; sin quirófano integral |
| Etapa A | Fundaciones de modelo + UI etiquetas/filtros/bandejas; sin reprogramar/cancelar avanzado ni realizar proc/cirugía |
| Posterior | Checklist OR, multi-recurso, etc. |

Nombre UI de sección: **Estudios y procedimientos**. Rutas/API legacy de estudios se conservan.

---

## 3. Modelo conceptual (Etapa A en adelante)

```
ProcedimientoCatalogo (+ clasificacion: SIN_ASIGNAR | NO_QUIRURGICO | QUIRURGICO)
TipoEstudioComplementario (estudios/prácticas)

EstudioComplementario  (indicación)
  tipo_actividad, snapshots, permite_multi_sesion
  tipo_estudio XOR procedimiento_catalogo (según tipo)
  turno = espejo (§1.6)
  └─ SesionActividad (1..N; canónico de reserva/realización por sesión)
        └─ Turno?  Atencion?  Informes por sesión (FK en etapas siguientes)
```

Registro clínico al realizar (etapas C/D, no A): por `tipo_actividad`, no por recurso.

---

## 4. Etapas (mapa)

| Etapa | Resumen |
|-------|---------|
| **A** | Clasificación catálogo; campos indicación + snapshot; `SesionActividad` + backfill; espejo turno; UI nombre/filtros/bandejas; reglas legacy endpoints |
| **B** | Reprogramar; cancelar sesión vs actividad; sync agenda; duración variable aislada; locks |
| **C** | Realizar estudio (como hoy) + procedimiento → Atencion+RegistroProcedimiento |
| **D** | Cirugía básica + RegistroQuirurgico sin placeholders; requisitos configurables |
| **E** | UI multisesión |
| **F** | Quirófano integral |

---

## 5. Tickets — Etapa A

### A0 — Guardrails LIMS y regresión compartida

| | |
|--|--|
| **Objetivo** | Checklist y pruebas de no-regresión antes/después de A1–A5 |
| **Alcance** | Documentar en el PR la matriz de smoke; ejecutar smoke EMR agenda + LIMS básico en local |
| **Archivos** | Checklist `docs_synesis/checklists/etapa-a0-regresion-lims-agenda.md`; referencia `DOC_DISENO_ESTUDIOS_PROCEDIMIENTOS.md`, `pre-commit-emr-lims.md` si aplica |
| **Fuera** | Cualquier cambio en `laboratorio/` |
| **Migraciones** | No |
| **Aceptación** | Diff `laboratorio/` vacío **en el paquete A0+A1**; verificación comparativa base vs A0+A1 sin regresiones nuevas en suites de referencia; fallos HEAD documentados sin “arreglar” LIMS/turnos |
| **Pruebas** | Suites de referencia en worktrees aislados + checklist; ver cierre `CIERRE_ETAPA_A0_A1.md` |
| **Cierre** | «Verificación comparativa completada, sin nuevas regresiones detectadas en las suites ejecutadas; cuatro fallos preexistentes documentados» |

---

### A1 — Clasificación en `ProcedimientoCatalogo`

| | |
|--|--|
| **Objetivo** | Campo de clasificación quirúrgica en catálogo de procedimientos |
| **Alcance** | Modelo + serializer/API catálogo + UI catálogo admin |
| **Archivos reales** | `catalogos/models.py` (`ProcedimientoCatalogo`); serializers/views de catálogos que expongan procedimientos; `frontend/src/pages/catalogos/Procedimientos.tsx`; tipos FE `frontend/src/types` (ProcedimientoCatalogo); servicios API de catálogo usados por esa página |
| **Migración** | Aditiva: `clasificacion_quirurgica` CharField nullable o default `SIN_ASIGNAR`; choices `SIN_ASIGNAR`, `NO_QUIRURGICO`, `QUIRURGICO`; backfill = `SIN_ASIGNAR` para filas existentes |
| **Compatibilidad** | Lectura antigua ignora el campo; escritura admin nueva lo muestra |
| **Aceptación** | Históricos quedan `SIN_ASIGNAR`; UI permite editar clasificación; no reclasifica solicitudes (aún no existen snapshots en A1 solo) |
| **Pruebas** | Test modelo/API catálogo: create/update clasificación; listado incluye campo |

---

### A2 — Campos de indicación: `tipo_actividad`, FKs, snapshots, multisesión

**Ticket normativo (prevalece):** `docs_synesis/tickets/TICKET_A2_A2b_ESTUDIOS_PROCEDIMIENTOS.md` (correspondencia exacta tipo↔snapshot, altas proc/cirugía deshabilitadas hasta circuitos, A2b restringido, `PROTECT`, backfill idempotente).

| | |
|--|--|
| **Objetivo** | Preparar estructura en `EstudioComplementario` sin romper estudios actuales ni habilitar aún proc/cirugía |
| **Alcance** | Modelo, migraciones EMR, validaciones, serializers/services, FE tipado; **sin** altas UI/API de `PROCEDIMIENTO`/`CIRUGIA` |
| **Archivos reales** | `estudios/models.py`; `estudios/serializers.py`; `estudios/services.py`; `estudios/views.py`; `frontend/src/types/estudios.ts`; `frontend/src/services/estudiosComplementariosApi.ts`; alta legacy en `EstudiosComplementarios.tsx` (solo estudio) |
| **Correspondencia** | `PROCEDIMIENTO`↔`NO_QUIRURGICO`; `CIRUGIA`↔`QUIRURGICO`; `ESTUDIO` sin FK ni snapshot quirúrgico |
| **Campos (aditivos)** | `tipo_actividad` (default `ESTUDIO`); `procedimiento_catalogo` FK **`PROTECT`** null; snapshot null/blank; `permite_multi_sesion=False` (no activable hasta A3/A4) |
| **Migración** | Aditiva + backfill idempotente a `ESTUDIO`; conservar relaciones/conteos; nullabilidad legacy verificada (solo EMR) |
| **Compatibilidad** | POST legacy → `ESTUDIO`; acciones realización/informes solo `ESTUDIO` |
| **A2b** | Admin; snapshot compatible con tipo; bloqueo post-realización y correcciones contradictorias; TX+audit atómicos; PATCH no toca FK/snapshot/`tipo_actividad` |

---

### A3 — Modelo `SesionActividad` + backfill + espejo `turno`

**Ticket normativo (prevalece):** `docs_synesis/tickets/TICKET_A3_SESION_ACTIVIDAD.md`.  
**Cierre:** `docs_synesis/CIERRE_ETAPA_A3.md` (implementado en código; sin merge/prod).

| | |
|--|--|
| **Objetivo** | Canónico por sesión; backfill 1:1; espejo TX según §1.6 (mono histórico) |
| **SoT reserva** | `SesionActividad.turno`; `EstudioComplementario.turno` = espejo histórico de `#1` |
| **Alcance** | Modelo; migración `0007`+backfill idempotente; `sesion_sync`; create/asignar/agendar/`marcar_realizado`/anular en misma TX |
| **Compat** | Endpoints actuales sin `sesion_id` (mono-sesión); A4 endurece multi |
| **Aceptación / pruebas** | Ver ticket A3 + suite `test_a3_sesion.py` |

---

### A4 — Endpoints legacy: sesión explícita o rechazo

**Ticket normativo:** `docs_synesis/tickets/TICKET_A4_ENDPOINTS_SESION.md`.  
**Cierre:** `docs_synesis/CIERRE_ETAPA_A4.md` (implementado; sin merge/prod).

| | |
| --- | --- |
| **Objetivo** | Cumplir §1.6 multisesión en mutaciones de assign; compat mono A3 |
| **Alcance** | `asignar-turno`, `agendar-turno` (+ `sesion_id`); rechazo legacy realizar/anular/informes en multi |
| **Espejo D5** | 0 / 1 / \>1 vigentes → null / ese / null; mono = histórico A3 |
| **Habilitación** | Multisesión **sigue off** en API/admin hasta realización/informes por sesión |
| **Aceptación / pruebas** | `test_a4_sesion_endpoints.py` + ticket |
| **Fuera** | A5+; LIMS; merge/prod |

---

### A5 — UI: nombre, bandejas por situación

**Ticket normativo:** `docs_synesis/tickets/TICKET_A5_UI_BANDEJAS.md`.  
**Cierre:** `docs_synesis/CIERRE_ETAPA_A5.md` (implementado; sin merge/prod).

| | |
| --- | --- |
| **Objetivo** | Nombre “Estudios y procedimientos”; bandejas con matriz de estados reales |
| **“Programado”** | Reserva vigente (RESERVADO/CONFIRMADO); realización/anulación prevalecen |
| **API** | `bandeja=` (filtra antes de paginar) + `bandejas-resumen/` (conteos alineados) |
| **Conservar** | Ruta, búsqueda, acciones, documentos, archivos, permisos; sin CTAs proc/cirugía/multi |
| **Aceptación / pruebas** | `test_a5_bandejas.py` + `bandejas.test.ts` |

---

### A6 — Documentación de diseño / API (no LIMS)

**Cierre:** `docs_synesis/CIERRE_ETAPA_A6.md` (documental; sin código de producto).  
**Ticket B (siguiente, solo revisión):** `docs_synesis/tickets/TICKET_B_REPROGRAMAR_CANCELAR.md`.

| | |
| --- | --- |
| **Objetivo** | Consolidar A0–A5; API, bandejas, permisos y features off |
| **Archivos** | `CIERRE_ETAPA_A6.md`; este doc; `DOC_FLUJOS_EMR.md`; `DOC_API_ENDPOINTS.md` (estudios) — **sin** `DOC_FLUJOS_LIMS.md` ni `reglas/` lab |
| **Aceptación** | Espejo §1.6 / D5, bandejas A5, deshabilitados documentados; cierre A5 con EXIT/buckets |

---

## 6. Orden sugerido de merge Etapa A

`A0` (checklist) → `A1` → `A2` (+A2b) → `A3` → `A4` → `A5` → `A6`

Dependencias: A3 requiere A2 (FK estudio); A4 requiere A3; A5 puede paralelizarse en parte tras A2 (filtro tipo) y completar bandejas tras A3.

---

## 7. Decisiones pendientes (fuera de A o para B–D)

1. Lista de requisitos pre-quirúrgicos (aviso vs bloqueo) — clínica.  
2. Política UI de resolución manual cuando hay Atencion incompatible (Etapa C/D).  
3. ¿Migración futura que haga nullable `protocolo_quirurgico` / separe cierre documental? Solo con análisis de dependencias EMR; **no** en A.  
4. Quién autoriza `corregir-clasificacion-snapshot` además de admin.

---

## 8. Criterios de aceptación globales Etapa A

- [x] Sin cambios en `laboratorio/` ni docs/reglas LIMS (A0–A6).  
- [ ] Smoke LIMS + agenda consultorio OK tras merge (merge aún no).  
- [x] Backfill: 1 sesión por indicación; espejo coherente en mono-sesión (A3).  
- [x] Nuevas proc/cirugía rechazan catálogo / altas (A1/A2).  
- [x] Snapshot / A2b; catálogo no reclasifica lo existente.  
- [x] Multisesión = flag off en altas; fixtures + `sesion_id` (A4).  
- [x] Legacy mutaciones: mono OK; multi sin `sesion_id` / acciones no soportadas → 400.  
- [x] Lecturas no reparan datos.  
- [x] UI renombrada + bandejas (A5).  
- [x] Docs consolidados (A6).  
- [ ] Reversión / merge producción: pendiente de decisión explícita.

---

## 9. Fuera de alcance explícito de Etapa A

Reprogramar; cancelar sesión vs actividad (lógica completa); realizar procedimiento/cirugía; `RegistroQuirurgico`/`RegistroProcedimiento` nuevos; quirófano; multisesión UI; cambios a `AtencionService` factory; cualquier tocado LIMS.
