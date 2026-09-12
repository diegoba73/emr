# DOC_ESTADOS_TRANSICIONES — Máquinas de estado conceptuales (Fase C0)

**Versión:** C0 — 18 de mayo de 2026 · **actualización orden LIMS:** 12 de septiembre de 2026  
**Jerarquía:** `REGLAS_INDICE.md`. Leyenda: **[IMPLEMENTADO]** valor en código hoy | **[OBJETIVO]** futuro | **[CONCEPTUAL]** etiqueta de negocio no 1:1 con campo

**Detalle operativo LIMS:** `DOC_REGLAS_NEGOCIO.md`, `DOC_FLUJOS_LIMS.md`, `laboratorio/solicitud_estado.py`, `laboratorio/muestra_estado.py`, `laboratorio/microbiologia_estado.py`, `reglas/control-calidad.md`.

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

Transiciones C5.9.2 **[IMPLEMENTADO]** (`turnos/turno_estado.py`):

| Acción API | Desde | Hacia / efecto |
|------------|-------|----------------|
| `confirmar` | `RESERVADO` | `CONFIRMADO` |
| `cancelar` | `DISPONIBLE`, `RESERVADO`, `CONFIRMADO` | `CANCELADO` |
| `reprogramar` | `DISPONIBLE`, `RESERVADO`, `CONFIRMADO` | conserva estado; cambia fechas/médico/recurso |
| `marcar-realizado` | `CONFIRMADO` (médico); `RESERVADO`/`CONFIRMADO` (admin/secretaría) | `REALIZADO` |
| `marcar-no-asistio` | `RESERVADO`, `CONFIRMADO` | `CANCELADO` (metadata `marcar_no_asistio`) |
| `iniciar-atencion` **(C5.10.1)** | `RESERVADO`, `CONFIRMADO` (+ idempotencia si ya hay atención / `REALIZADO`) | `REALIZADO` + crea/obtiene `Atencion` y registro hijo si alta nueva |

- `REALIZADO` clínico: **`iniciar-atencion`** (agenda → atención) o `registrar-consulta`; `marcar-realizado` es operación administrativa (no crea atención).
- Idempotencia: confirmar/cancelar/marcar-realizado ya en estado destino → 200 `applied=false` sin auditoría duplicada.
- PATCH/PUT `estado`: bloqueado para todos (400).
- **[DEUDA]:** estado `NO_ASISTIO`; campos `cancelado_por`/`motivo_cancelacion`.

---

## Orden LIMS (`SolicitudExamen.estado`)

| Conceptual | **[IMPLEMENTADO]** | Acción / transición |
|------------|---------------------|---------------------|
| Pendiente | `PENDIENTE` | Creación |
| En proceso | `EN_PROCESO` | **No** es regla universal que `POST .../tomar-muestra/` pase inmediatamente `PENDIENTE` → `EN_PROCESO`. Con tubos reales la orden puede seguir `PENDIENTE` hasta que el tubo correspondiente se registre/escanee como `TOMADA`. El flujo legacy **sin** tubos puede avanzar durante `tomar-muestra`. |
| Informe parcial | `INFORMADO_PARCIAL` | Carga incompleta |
| Listo para validar | `LISTO_PARA_VALIDAR` | Carga completa; exige IQC del día. Reapertura: vaciar un resultado completo → `EN_PROCESO`. |
| Finalizado | `FINALIZADO` | `POST .../validar/` (alias `.../finalizar/`); admin / bioquímico / superuser |

Ya **no** existen en este modelo: `TOMA_MUESTRA`, `VALIDADO`, `ENTREGADO`, `CANCELADO` (pueden figurar en docs Fase A).

IQC bloquea **carga** y **validar**, no la toma. Agregar/quitar ensayos permitido hasta `FINALIZADO` (con reglas de tubos y resultados vacíos). Ver `DOC_REGLAS_NEGOCIO.md`.

Separación técnica vs profesional: **roles** (`laboratorio` opera, `bioquimico` libera), no estados extra.

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
| Informado | Orden `FINALIZADO` / informe micro | No estado en fila resultado |
| Corregido | **[OBJETIVO]** | Sin flujo de corrección versionada |
| Anulado | **[OBJETIVO]** | — |

---

## Informe — química/hematología general

| Conceptual | Código | Notas |
|------------|--------|--------|
| PDF básico | `GET …/informe-pdf` | **[IMPLEMENTADO]** PDF-1; no cambia estado |
| Liberado | Orden `FINALIZADO` | Marcador operativo de cierre |

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
PENDIENTE ──tomar-muestra──► EN_PROCESO ──carga incompleta──► INFORMADO_PARCIAL
                                  │                              │
                                  └──carga completa──────────────┴──► LISTO_PARA_VALIDAR ──validar──► FINALIZADO
                                                                        │
                                                                        └──(vaciar valor)──► EN_PROCESO
```

IQC (día local) en carga y en validar. Muestra física corre en paralelo (`PENDIENTE_TOMA` → `TOMADA` → `RECIBIDA` → `EN_PROCESO` → terminales).
