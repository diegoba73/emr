# Cierre — Etapa A6 (documentación consolidada A0–A5)

**Fecha:** 2026-10-16  
**Estado:** documental cerrado; **sin código de producto nuevo, sin merge ni producción**  
**Alcance:** solo docs EMR del módulo estudios/procedimientos. **LIMS intocable** (no se editó `DOC_FLUJOS_LIMS.md`, `reglas/` de lab, ni `laboratorio/`).  
**SoT diseño:** `docs_synesis/DOC_DISENO_ESTUDIOS_PROCEDIMIENTOS.md`  
**API:** `docs_synesis/DOC_API_ENDPOINTS.md` (sección estudios)  
**Flujos EMR:** `docs_synesis/DOC_FLUJOS_EMR.md` (sección estudios)  
**Siguiente:** `docs_synesis/tickets/TICKET_B_REPROGRAMAR_CANCELAR.md` (revisión; no implementar)

---

## 1. Dependencias y orden Etapa A

| Etapa | Entregable | Paquete / artefacto | Depende de |
| --- | --- | --- | --- |
| A0 | Checklist no-regresión LIMS/agenda; 4 fallos HEAD documentados | `checklists/etapa-a0-regresion-lims-agenda.md`, `CIERRE_ETAPA_A0_A1.md` | — |
| A1 | `clasificacion_quirurgica` en catálogo + migración `catalogos.0010` | `a01_package` | A0 |
| A2/A2b | `tipo_actividad`, FK proc PROTECT, snapshot, multi off; corrección admin snapshot | `a2_package`, `estudios.0006` | A0+A1 |
| A3 | `SesionActividad`, backfill, espejo mono histórico, sync TX | `a3_package`, `estudios.0007` | A2 |
| A4 | `sesion_id`, espejo multi D5 (fixtures), rechazo legacy multi | `a4_package` | A3 |
| A5 | UI “Estudios y procedimientos”, bandejas + resumen | `a5_package` | A4 |
| A6 | Este consolidado + API/flujos EMR | docs only | A5 |

Orden de apply: **A0 → A1 → A2 → A3 → A4 → A5** (código). A6 no aporta migraciones.

---

## 2. Modelo y espejo (código vigente)

### Indicación `EstudioComplementario`

- `tipo_actividad`: `ESTUDIO` | `PROCEDIMIENTO` | `CIRUGIA` (altas operativas solo **ESTUDIO**).
- `procedimiento_catalogo` FK **PROTECT**; `clasificacion_quirurgica_snapshot`; `permite_multi_sesion` (altas **False**).
- Estados: `SOLICITADO` → `CONFIRMADO` → `REALIZADO` → `INFORMADO` → `VALIDADO` → `ENTREGADO`; `ANULADO` terminal.

### `SesionActividad` (A3)

- SoT de reserva por sesión: `SesionActividad.turno`.
- Constraints: único `(estudio, numero_sesion)`; único `turno` donde not null.
- Mono operativo: espejo histórico `estudio.turno = sesión#1.turno` (no limpiar por REALIZADO/CANCELADO del turno).

### Espejo multi (A4 D5; flag off en API)

| Turnos vigentes (RESERVADO/CONFIRMADO) | `estudio.turno` |
| --- | --- |
| 0 | `null` |
| 1 | ese turno |
| \>1 | `null` |

Vínculos históricos en `SesionActividad.turno` **nunca** se borran por vigencia. GET no repara.

---

## 3. API estudios (resumen A6)

Base: `/api/estudios-complementarios/`. Detalle actualizado en `DOC_API_ENDPOINTS.md`.

| Método | Ruta | Notas |
| --- | --- | --- |
| GET | `/` | Filtros: `paciente`/`paciente_id`, `estado`, `practica`, `search`, **`bandeja`** (A5; filtra antes de paginar) |
| GET | `/bandejas-resumen/` | Conteos A5; mismos permisos/search/práctica; **sin** filtro `bandeja` |
| POST | `/` | Alta ESTUDIO; rechaza proc/cirugía/multi |
| GET/PATCH | `/{id}/` | PATCH no cambia `estado` ni campos A2 protegidos |
| POST | `/agendar-turno/` | Crea mono o asigna a `estudio_id` existente; `sesion_id` opcional |
| POST | `/{id}/asignar-turno/` | `sesion_id` opcional (mono = PK de `#1`); multi fixture lo exige |
| POST | `/{id}/marcar-realizado/` | Solo mono; multi → 400 sin escrituras |
| POST | `/{id}/anular/` | Solo mono; multi → 400 sin escrituras |
| POST | `/{id}/entregar/` | Requiere informe validado; estudio `VALIDADO` |
| POST | `/{id}/corregir-clasificacion-snapshot/` | A2b admin |
| Informes / archivos | como C6.4 | Sin cambio LIMS |

### Bandejas (`bandeja=`)

| Valor | Criterio |
| --- | --- |
| `pendiente_programar` | `SOLICITADO`/`CONFIRMADO` sin reserva vigente |
| `programados` | `SOLICITADO`/`CONFIRMADO` con reserva vigente |
| `documentacion_pendiente` | `REALIZADO`/`INFORMADO` |
| `pendiente_entrega` | `VALIDADO` |
| `finalizados` | `ENTREGADO` |
| `anulados` | `ANULADO` |
| `todos` / vacío | sin filtro |

Precedencia: anulación y realización **sobre** la reserva. “Programado” = estado de turno vigente, no FK histórica sola.

---

## 4. Permisos (módulo estudios)

| Acción | Roles (resumen) |
| --- | --- |
| Ver listado / detalle clínico | admin, médico (pacientes vinculados), secretaría, enfermería, roles estudio; paciente solo `ENTREGADO` propios |
| Crear / escribir contenido / informes | admin, médico, roles estudio |
| Asignar / agendar turno | admin, secretaría |
| Entregar | según `usuario_puede_entregar_estudio` |
| Corregir snapshot (A2b) | admin |
| Laboratorio | **sin acceso** al módulo (LIMS separado) |

Sin cambios a matriz LIMS ni a `turno_estado` global en Etapa A.

---

## 5. Funciones todavía deshabilitadas

| Feature | Estado | Hasta |
| --- | --- | --- |
| Altas `PROCEDIMIENTO` / `CIRUGIA` | Rechazadas en API/admin | Etapas C/D |
| `permite_multi_sesion=True` en altas | Rechazado | Flujos realización/informes por sesión |
| Realización / anulación / informes en multi | 400 sin escrituras (A4) | B/C+ |
| Reprogramar / cancelar reserva de estudio (avanzado) | No existe endpoint dedicado de estudio | **Etapa B** |
| UI multisesión / quirófano | No | E/F |
| Cualquier cambio LIMS | Prohibido en A–B de este diseño | — |

---

## 6. Fallos preexistentes (referencia transversal)

Mantener **siempre separados**:

1. **Bucket A0 (4):** dos LIMS `fecha_programada_toma` 400; dos turnos lab 403 vs 404. Artefactos `results_a*.txt`.  
2. **Bucket estudios (1):** `test_asignar_turno_estudio_rechaza_sala_ocupada` — `sala_ocupada_head_vs_a3.txt`. No “arreglar” vía agenda global en tickets A/B sin decisión explícita.

---

## 7. Criterios A6

- [x] Consolidado A0–A5 y dependencias.  
- [x] API, bandejas, permisos y features off documentados (EMR; no LIMS).  
- [x] Cierre A5 con EXIT efectivos y buckets separados.  
- [x] Ticket B preparado para revisión.  
- [x] Sin merge/prod; LIMS intocable.
