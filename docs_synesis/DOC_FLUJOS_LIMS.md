# DOC_FLUJOS_LIMS — Flujos laboratoriales

**Fecha de generación:** 30 de abril de 2026  
**Actualización (hardening mínimo LIMS, resultados pendientes):** 2 de mayo de 2026  
**Actualización (Fase A — máquina de estados `SolicitudExamen`):** 3 de mayo de 2026  

**Alcance:** Flujo LIMS **nativo** (`laboratorio` app) y vínculos con `solicitudes` / `integracion_lims`.

**Fuentes revisadas:** `laboratorio/models.py`, `laboratorio/serializers.py`, `laboratorio/views.py`, `laboratorio/solicitud_estado.py`, `solicitudes/models.py`, `integracion_lims/lims_service.py`.

---

## Flujo de órdenes (`SolicitudExamen`)

1. **Creación:** `POST` al ViewSet registrado como `lab/solicitudes` y duplicado `laboratorio/solicitudes` (mismo ViewSet).
2. **Serializer lectura:** `SolicitudExamenSerializer` expone `medico_display` (propiedad del modelo) como `CharField(read_only=True)` **sin** `source` redundante (compatible con DRF reciente).
3. **Serializer escritura:** `SolicitudExamenCreateSerializer` recibe `paciente_id`, `medico_id` opcional, `medico_externo_nombre`, `origen_solicitud`, `examenes_ids`, `paneles_ids`, fechas/observaciones.
4. **Número de protocolo:** generado en `save()` si vacío: `LAB-YYYY-XXXXX` secuencial.
5. **Origen:** `EMR`, `GUARDIA`, `EXTERNO_PAPEL`.
6. **Médico híbrido:** `medico_interno` (FK) o texto `medico_externo_nombre`.

---

## Flujo de muestras

- **Catálogo:** `TipoMuestra` (código, nombre, color tubo).
- **No hay entidad transaccional “Muestra” / tubo** con trazabilidad por alícuota en BD — el flujo es por **orden y resultados**.
- **Toma de muestra (Fase A):** la acción `POST .../tomar-muestra/` solo cambia el estado de la orden a `TOMA_MUESTRA`; **no** crea filas de muestra ni recepción física.
- **Etiqueta ZPL:** acción `GET .../etiqueta/` devuelve JSON con fragmento ZPL simulado.

**Aún no implementado:** recepción de muestra transaccional, rechazo de muestra, tubos con ID de trazabilidad.

---

## Flujo de determinaciones

- Cada **`TipoExamen`** define un análisis; **`PanelExamen`** agrupa muchos tipos vía M2M.
- Al crear la orden, se generan filas **`ResultadoExamen`** por cada tipo (directo o expandido desde paneles), con **`valor_obtenido` vacío** (`''`) inicialmente — el campo en modelo admite blanco (`blank=True`, `default=''`) **solo** para representar “pendiente de carga”. La acción **`validar`** sigue **rechazando** la orden si queda algún resultado con valor vacío (no se valida con incompletos).

---

## Flujo de carga de resultados

- **Endpoint:** `POST /api/lab/solicitudes/{id}/cargar-resultados/` (y alias bajo `/api/laboratorio/solicitudes/{id}/cargar-resultados/`).
- **Payload:** `{ "resultados": [ { "id": <ResultadoExamen.id>, "valor": "...", "es_patologico": bool, "observaciones": "..." } ] }`.
- **Reglas (Fase A):** rechaza si orden está en `CANCELADO`, `VALIDADO` o `ENTREGADO`. Transacción + bloqueo de fila (`select_for_update`) sobre la solicitud. Tras aplicar cambios a resultados: si el estado era `PENDIENTE` o `TOMA_MUESTRA`, transición a `EN_PROCESO` (compatibilidad: se puede cargar sin pasar obligatoriamente por toma). Si ya estaba en `EN_PROCESO`, solo se actualizan resultados (sin cambio de estado).
- **Auditoría:** `log_update` por resultado; en transición de estado, evento de solicitud con metadata (`accion`, `estado_anterior`, `estado_nuevo`, `solicitud_id`, `numero_solicitud`) vía `laboratorio/solicitud_estado.py`.

---

## Flujo de validación técnica / profesional

- Un único paso **`validar`** (`POST .../validar/`) que:
  - Solo acepta orden en estado **`EN_PROCESO`** (rechaza `PENDIENTE`, `TOMA_MUESTRA`, `VALIDADO`, `CANCELADO`, `ENTREGADO`).
  - Exige que no haya resultados con `valor_obtenido` vacío.
  - Transiciona `EN_PROCESO` → `VALIDADO` mediante la misma capa de transiciones auditadas que el resto de acciones.
  - Asigna `validado_por` y `fecha_validacion` a **todos** los `ResultadoExamen` vía `queryset.update` (mismo usuario/fecha para todos).
- **Permiso:** solo **`admin`** o **superuser** puede invocar `validar`. El rol **`laboratorio`** puede cargar resultados, tomar muestra, cancelar y marcar entregado, pero **no** validar.
- **No hay** distinción explícita entre validación técnica y profesional como estados separados — sigue siendo deuda funcional; un solo estado `VALIDADO`.

---

## Flujo de emisión de informes

- **No hay** generador PDF ni informe final automático en LIMS nativo; la acción `marcar-entregado` solo pone `ENTREGADO` en la orden (sin PDF).
- Datos en JSON del serializer y acción `etiqueta` (ZPL simulado).

---

## Estados (`SolicitudExamen`) — Fase A

Transiciones **permitidas** (solo vía acciones explícitas del ViewSet; `estado` **no** se modifica por `PATCH`/`PUT` estándar — campo `read_only` en `SolicitudExamenSerializer`):

| Desde | Disparador | Hacia |
|-------|------------|--------|
| `PENDIENTE` | `POST .../tomar-muestra/` | `TOMA_MUESTRA` |
| `PENDIENTE` | `POST .../cargar-resultados/` | `EN_PROCESO` (compatibilidad sin toma previa) |
| `TOMA_MUESTRA` | `POST .../cargar-resultados/` | `EN_PROCESO` |
| `EN_PROCESO` | `POST .../cargar-resultados/` | `EN_PROCESO` (sin cambio de estado) |
| `EN_PROCESO` | `POST .../validar/` | `VALIDADO` |
| `VALIDADO` | `POST .../marcar-entregado/` | `ENTREGADO` |
| `PENDIENTE`, `TOMA_MUESTRA`, `EN_PROCESO` | `POST .../cancelar/` | `CANCELADO` |

**Terminales (sin salida en Fase A):** `CANCELADO`, `ENTREGADO`. No se permite cancelar desde `VALIDADO` ni `ENTREGADO` en esta fase.

**Cancelación:** no elimina ni vacía filas `ResultadoExamen`; la integridad “no cargar en cancelada” sigue en `ResultadoExamen.clean()`.

---

## Roles involucrados (estado actual tras hardening + Fase A)

Implementación en `api/permissions.py` (`LimsCatalogReadPermission`, `LimsSolicitudExamenPermission`) y `get_queryset` en `SolicitudExamenViewSet`:

| Rol | Catálogos (`lab/muestras`, `examenes`, `paneles`) | Solicitudes list/detail/create/update | `tomar-muestra` | `cargar-resultados` | `cancelar` | `marcar-entregado` | `validar` | `etiqueta` |
|-----|---------------------------------------------------|----------------------------------------|-----------------|---------------------|------------|-------------------|-----------|------------|
| **Anónimo** | No | No | No | No | No | No | No | No |
| **paciente** | No | No | No | No | No | No | No | No |
| **secretaria** | Sí (solo lectura GET) | No | No | No | No | No | No | No |
| **enfermeria** | Sí (solo lectura GET) | No | No | No | No | No | No | No |
| **medico** | Sí (solo lectura GET) | Crear y ver **solo** órdenes con `medico_interno.user` = request.user; sin listado global | No | No | No | No | No | No |
| **laboratorio** | Sí | Listar/ver/crear/editar órdenes (destroy solo admin) | Sí | Sí | Sí | Sí | **No** | Sí |
| **admin** | Sí | Sí (incluye destroy según permiso) | Sí | Sí | Sí | Sí | **Sí** | Sí |
| **superuser** | Sí | Sí | Sí | Sí | Sí | Sí | Sí | Sí |

**Aliases:** `/api/laboratorio/tipos-examen/` y `/api/laboratorio/solicitudes/` — mismos ViewSets y **misma** matriz de permisos que `/api/lab/...`.

---

## Eventos auditables

- `log_create` / `log_update` en crear/actualizar orden (campos permitidos por serializer, sin `estado` por PATCH), `cargar_resultados`, `validar`, `tomar_muestra`, `cancelar`, `marcar_entregado`.
- Transiciones de estado de solicitud: metadata con `accion`, `estado_anterior`, `estado_nuevo`, `solicitud_id`, `numero_solicitud` (además de `before_state`/`after_state` del snapshot).
- En `validar`, por resultado se captura snapshot **antes** del `update()` masivo para `before_state`.
- `log_event` (`DELETE`) en borrado de orden (`perform_destroy`, solo rol admin): incluye `before_state` de la solicitud eliminada.

---

## Controles de calidad

- **No detectados** modelos específicos (QC, lotes, Levey-Jennings) en `laboratorio/models.py`.

---

## Restricciones

- `unique_together` en `ResultadoExamen`: una fila por `(solicitud, tipo_examen)`.
- No crear ni mutar resultados si orden cancelada (`ResultadoExamen.clean()` y rechazo en `cargar_resultados`). La orden **sí** puede cancelarse aunque existan `ResultadoExamen` vacíos autogenerados al crear la orden.

---

## Integración EMR ↔ LIMS externo

1. **`solicitudes.Solicitud`:** puede disparar `lims_service.enviar_solicitud_a_lims` si `LIMS_AUTO_SEND=true` y tipo `EXAMEN_LABORATORIO`.
2. **`lims_service`:** POST a `http://localhost:8001/api/laboratorio/solicitudes/ingesta/` — **URL fija**; falla silenciosamente en excepción.
3. **`integracion_lims` modelos** `SolicitudExamenLims` / `ResultadoExamenLims` para espejo de datos externos.
4. **URLs** `integracion_lims/urls.py` (webhook, análisis por paciente) **no incluidas** en `synesis/urls.py` — endpoints **no expuestos** por el proyecto raíz tal como está.

---

## Riesgos de trazabilidad o integridad

- ~~Permisos abiertos (`AllowAny`) en LIMS nativo~~ — **cerrado** en hardening mínimo (autenticación obligatoria + roles).
- ~~Validación masiva sin `before_state` por resultado~~ — mitigado: snapshots previos al `update()` y relevo desde BD antes de `log_update` por fila.
- Dos vías de “solicitud” (`solicitudes` vs `laboratorio.SolicitudExamen`) pueden confundir operación si no están gobernadas por proceso.

---

## Riesgos o inconsistencias

- Validación técnica / profesional no separada en estados distintos (deuda).
- Sin entidad transaccional muestra/tubo ni recepción/rechazo de muestra en BD (solo catálogo + `tomar-muestra` como marca de estado + etiqueta ZPL).

---

## Pendiente de confirmar

- Endpoints `ingesta/` y webhook en despliegue real.
- Evolución post–Fase A: cancelación desde `VALIDADO`, informes PDF, tubos con trazabilidad.
