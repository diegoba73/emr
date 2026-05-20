# DOC_ESTADOS_TRANSICIONES — Máquinas de estado conceptuales (Fase C0)

**Versión:** C0 — 18 de mayo de 2026  
**Leyenda:** **[IMPLEMENTADO]** valor en código hoy | **[OBJETIVO]** futuro | **[CONCEPTUAL]** etiqueta de negocio no 1:1 con campo

**Detalle operativo LIMS:** `DOC_FLUJOS_LIMS.md`, `laboratorio/solicitud_estado.py`, `laboratorio/muestra_estado.py`, `laboratorio/microbiologia_estado.py`.

---

## Paciente

| Estado conceptual | En código | Notas |
|-------------------|-----------|--------|
| Activo | **[CONCEPTUAL]** | Sin campo `estado` en `Paciente`. |
| Inactivo | **[OBJETIVO]** | Baja lógica sin borrar historia. |
| Fusionado | **[OBJETIVO]** | Merge de duplicados con traza. |

---

## Atención (`Atencion.estado_clinico`)

| Conceptual | **[IMPLEMENTADO]** | Transiciones principales |
|------------|---------------------|---------------------------|
| Pendiente / no iniciada | — | Cubierto por `Turno` antes de `POST /api/atenciones/`. |
| En curso | `ABIERTA` | Alta vía `AtencionService` (`api_post_compat` o completo). |
| Cerrada | `FINALIZADA` | Acción `cerrar`. |
| En revisión | `EN_REVISION` | **[IMPLEMENTADO]** en modelo; uso en UI/API según implementación. |
| Cancelada | **[OBJETIVO]** | No hay `CANCELADA` en `EstadoClinico` hoy. |

**Turno** (agenda): `DISPONIBLE`, `RESERVADO`, `CONFIRMADO`, `CANCELADO`, `REALIZADO` — **[IMPLEMENTADO]**.

Transiciones C5.9.1 (acciones dedicadas, `turnos/turno_estado.py`):

| Acción API | Desde | Hacia |
|------------|-------|-------|
| `confirmar` | `RESERVADO` | `CONFIRMADO` |
| `cancelar` | `DISPONIBLE`, `RESERVADO`, `CONFIRMADO` | `CANCELADO` |

- `REALIZADO`: vía `registrar-consulta` (consulta con contenido) o `AtencionService` completo; no por `cancelar`.
- Idempotencia: confirmar en `CONFIRMADO` / cancelar en `CANCELADO` → 200 sin duplicar auditoría de cambio.
- **[DEUDA]:** `NO_ASISTIO`, reprogramar, campos `cancelado_por`/`motivo_cancelacion`, bloquear PATCH estado para admin.

---

## Orden LIMS (`SolicitudExamen.estado`)

| Conceptual | **[IMPLEMENTADO]** | Acción / transición |
|------------|---------------------|---------------------|
| Pendiente | `PENDIENTE` | Creación |
| Toma muestra (marcador orden) | `TOMA_MUESTRA` | `POST .../tomar-muestra/` |
| En proceso | `EN_PROCESO` | `cargar-resultados` (desde PENDIENTE/TOMA_MUESTRA/EN_PROCESO) |
| Validado | `VALIDADO` | `validar` (solo **admin**) |
| Entregado | `ENTREGADO` | `marcar-entregado` |
| Cancelado | `CANCELADO` | `cancelar` |

**[DEUDA]** No hay estados separados “validación técnica” vs “profesional”.

---

## Muestra (`Muestra.estado`)

| **[IMPLEMENTADO]** | Significado |
|--------------------|-------------|
| `PENDIENTE_TOMA` | Pendiente de toma física |
| `TOMADA` | Tomada |
| `RECIBIDA` | Recibida en laboratorio |
| `EN_PROCESO` | En análisis |
| `RECHAZADA` | Rechazada (no sustenta validación de resultados vinculados) |
| `CONSERVADA` | En conservación |
| `DESCARTADA` | Descartada |
| `CANCELADA` | Cancelada |

Transiciones: `laboratorio/muestra_estado.py` + `EventoMuestra`.

---

## Resultado (`ResultadoExamen`)

No hay campo `estado` dedicado; el ciclo se infiere:

| Conceptual | **[IMPLEMENTADO]** hoy | Notas |
|------------|------------------------|--------|
| Pendiente | `valor_obtenido == ''` | Al crear orden |
| Cargado | Valor no vacío, sin `fecha_validacion` | Tras `cargar-resultados` |
| Validado | `validado_por` + `fecha_validacion` | Tras `validar` en orden |
| Informado | Indirecto vía orden `ENTREGADO` / informe micro | No estado en fila resultado |
| Corregido | **[OBJETIVO]** | Sin flujo de corrección versionada |
| Anulado | **[OBJETIVO]** | — |

---

## Informe — química/hematología general

| Conceptual | Código | Notas |
|------------|--------|--------|
| Borrador / emitido / validado PDF | **[OBJETIVO]** | Solo orden `ENTREGADO` como marcador operativo |
| — | `ENTREGADO` en orden | **[IMPLEMENTADO]** sin PDF |

---

## Informe microbiología (`InformeMicrobiologico`)

| **[IMPLEMENTADO]** | Uso |
|--------------------|-----|
| `BORRADOR` | Edición |
| `EMITIDO` | Emitido |
| `VALIDADO` | Validación profesional |
| `ANULADO` | Anulación |

Tipo: `PRELIMINAR` | `FINAL` — **[IMPLEMENTADO]** B3.4.

**Estudio micro** (`EstudioMicrobiologico.estado`): `PENDIENTE` → `RECIBIDO` → … → `LISTO_PARA_VALIDAR` → `VALIDADO` → `INFORMADO` | `CANCELADO` — **[IMPLEMENTADO]** B3.1–B3.4. **[OBJETIVO]** `INCUBANDO` documentado pero no cableado.

---

## Solicitud EMR (`solicitudes.Solicitud`)

Estados propios del módulo `solicitudes` (ver `DOC_REGLAS_NEGOCIO.md`) — **[IMPLEMENTADO]** paralelo a LIMS nativo; no confundir con `SolicitudExamen`.

---

## Diagrama resumen LIMS nativo (orden + muestra)

```
PENDIENTE ──tomar-muestra──► TOMA_MUESTRA
     │                            │
     └────cargar-resultados───────┴──► EN_PROCESO ──validar──► VALIDADO ──marcar-entregado──► ENTREGADO
              │                         │
              └─────────────────────────┴──► CANCELADO (desde estados no finales según reglas)
```

Muestra física corre en paralelo (`PENDIENTE_TOMA` → `TOMADA` → `RECIBIDA` → `EN_PROCESO` → terminales).
