# DOC_FLUJOS_LIMS — Flujos laboratoriales

**Fecha de generación:** 30 de abril de 2026  
**Actualización (hardening mínimo LIMS, resultados pendientes):** 2 de mayo de 2026  
**Actualización (Fase A — máquina de estados `SolicitudExamen`):** 3 de mayo de 2026  
**Actualización (Fase B2 — `ResultadoExamen.muestra`):** 5 de mayo de 2026  
**Actualización (Fase B2.1 — TOCTOU `validar` + transición auto `RECIBIDA→EN_PROCESO`):** 13 de mayo de 2026  
**Actualización (Fase B3.1 — Microbiología base: estudio, siembra, lectura):** 13 de mayo de 2026  
**Actualización (Fase B3.2 — Microorganismos, aislados, identificación):** 13 de mayo de 2026  
**Actualización (Fase B3.3 — Antibiograma microbiológico):** 13 de mayo de 2026  
**Actualización (Fase B3.4 — Informes microbiológicos):** 14 de mayo de 2026  
**Actualización (Frontend UI-2 — consola microbiología):** 17 de mayo de 2026  
**Actualización (B3-frontend-validación-A [VALIDADO] + UX parcial):** junio de 2026 — Alta estudio micro: picker solicitud/muestra LIMS (`RECIBIDA`/`CONSERVADA`/`EN_PROCESO`). Detalle micro: listados globales + filtro cliente [GAP filtros API].  

**Alcance:** Flujo LIMS **nativo** (`laboratorio` app) y vínculos con `solicitudes` / `integracion_lims`.

**Fuentes revisadas:** `laboratorio/models.py`, `laboratorio/models_catalog.py`, `laboratorio/serializers.py`, `laboratorio/views.py`, `laboratorio/solicitud_estado.py`, `laboratorio/resultado_muestra_validacion.py`, `solicitudes/models.py`, `integracion_lims/lims_service.py`.

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
- **Fase B1:** entidad transaccional **`Muestra`** (`EventoMuestra`, catálogos `AreaLaboratorio` / `SeccionLaboratorio` / `TipoContenedor`). Estados y acciones REST documentadas en `DOC_API_ENDPOINTS.md` y tests `test_muestras_*`.
- **Toma de muestra (Fase A — orden):** `POST .../tomar-muestra/` cambia la orden `PENDIENTE` → `TOMA_MUESTRA` (marcador de flujo); es independiente de la toma física por **`Muestra`** (`aplicar_tomar` en `muestra_estado.py`).
- **Etiqueta ZPL:** acción `GET .../etiqueta/` devuelve JSON con fragmento ZPL simulado.
- **Fase B2 [IMPLEMENTADO]:** `cargar-resultados` acepta **`muestra_id`** opcional por ítem (misma solicitud/paciente; estados **`RECIBIDA`**, **`CONSERVADA`**, **`EN_PROCESO`**). Sin muestra = legacy. Al primer vínculo desde RECIBIDA/CONSERVADA → **`EN_PROCESO`** vía `aplicar_iniciar_proceso` + `EventoMuestra.PROCESAMIENTO` + audit `muestra_procesamiento` (idempotente si ya `EN_PROCESO`). Asociación de muestra audita `resultado_muestra_asociar` sin `codigo_barra` ni valor clínico en metadata (`valor_presente` solo). No rechazar muestra con resultados; no cambiar muestra en resultado validado.
- **Fase B2-B [IMPLEMENTADO]:** `TipoExamen.requiere_muestra` (default `False`; admin/DB). Tipos configurados exigen muestra en carga. **B2-B-A:** si se asocia muestra, siempre se valida `tipo_muestra_requerida` (también con `requiere_muestra=False`). Fallos sin persistir ni auditar éxito. SPA LIMS debe adaptarse para enviar `muestra_id` en tipos obligatorios.
- **Fase B2-C [IMPLEMENTADO — frontend]:** `OrdenLimsDetalle` / `CargaResultadosLims` cargan muestras de la orden, permiten elegir `muestra_id` por resultado y envían payload extendido; validación UX alineada con backend; tipos sin muestra obligatoria siguen en modo legacy.

---

## Flujo de determinaciones

- Cada **`TipoExamen`** define un análisis; **`PanelExamen`** agrupa muchos tipos vía M2M.
- Al crear la orden, se generan filas **`ResultadoExamen`** por cada tipo (directo o expandido desde paneles), con **`valor_obtenido` vacío** (`''`) inicialmente — el campo en modelo admite blanco (`blank=True`, `default=''`) **solo** para representar “pendiente de carga”. La acción **`validar`** sigue **rechazando** la orden si queda algún resultado con valor vacío (no se valida con incompletos).

---

## Flujo de carga de resultados

- **Endpoint:** `POST /api/lab/solicitudes/{id}/cargar-resultados/` (y alias bajo `/api/laboratorio/solicitudes/{id}/cargar-resultados/`).
- **B4.1:** cada ítem puede incluir además `valor_numerico`, `unidad`, `es_critico`; se fijan snapshots de rango/unidad del `TipoExamen` al momento de la carga; cálculo básico de `es_patologico`/`es_critico` si hay rangos estructurados. Payload histórico (`valor` + `es_patologico`) sigue válido.
- **Payload (retrocompatible):** `{ "resultados": [ { "id": <ResultadoExamen.id>, "valor": "...", "es_patologico": bool, "observaciones": "...", "muestra_id": <opcional int|null> } ] }`. Si **`muestra_id`** no viene en el ítem, no se modifica la asociación previa. Si viene **`null`**, se limpia la muestra del resultado (misma política de bloqueo que la carga: orden no `VALIDADO`/`ENTREGADO`/`CANCELADO`).
- **Reglas (Fase A + B2):** rechaza si orden está en `CANCELADO`, `VALIDADO` o `ENTREGADO`. Transacción + bloqueo de fila (`select_for_update`) sobre la solicitud y cada resultado (`of=("self",)` en PostgreSQL para FK muestra nullable). Tras aplicar cambios a resultados: si el estado era `PENDIENTE` o `TOMA_MUESTRA`, transición a `EN_PROCESO` (compatibilidad: se puede cargar sin pasar obligatoriamente por toma). Si ya estaba en `EN_PROCESO`, solo se actualizan resultados (sin cambio de estado).
- **Auditoría (B2 / B2-A / B3-audit):** `log_update` por resultado con metadata: `resultado_id`, `solicitud_id`, `numero_solicitud`, `muestra_id`, `valor_presente`, `muestra_anterior_id` / `muestra_nueva_id` si cambió la asociación; **sin `codigo_barra`** ni valores clínicos en metadata. Microbiología (B3-audit): metadata con IDs técnicos (`estudio_id`, `muestra_id`, `siembra_id`, etc.) y flags `*_presente`; **sin** resultados micro crudos ni `codigo_barra`. `before_state` / `after_state` redactan vía `safe_model_snapshot`. El `codigo_barra` de la muestra sigue disponible en API operativa, no en `AuditEvent` genérico.

---

## Flujo de validación técnica / profesional

- Un único paso **`validar`** (`POST .../validar/`) que:
  - Solo acepta orden en estado **`EN_PROCESO`** (rechaza `PENDIENTE`, `TOMA_MUESTRA`, `VALIDADO`, `CANCELADO`, `ENTREGADO`).
  - Exige que no haya resultados con `valor_obtenido` vacío.
  - Si un resultado tiene **`muestra`** vinculada, la muestra **no** debe estar en `RECHAZADA`, `DESCARTADA`, `CANCELADA`, `PENDIENTE_TOMA` ni `TOMADA` (resultados **sin** muestra siguen validándose si los valores están completos — compatibilidad histórica). **Fase B2.1:** antes de leer el estado de cada muestra referenciada, la acción aplica `Muestra.objects.select_for_update().filter(pk__in=…)` **dentro de la transacción** de validación, mitigando la ventana TOCTOU que existía en B2 (otro proceso ya no puede mutar la fila entre lectura y commit).
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
- **Muestra (B1):** `log_create` al crear muestra; `log_update` tras cada acción de estado (`tomar`, `recibir`, `rechazar`, `conservar`, `descartar`, `cancelar`) y tras PATCH administrativo; siempre fila `EventoMuestra` por acción.
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
- ~~Sin entidad transaccional muestra/tubo~~ — **Fase B1:** modelo `Muestra` + `EventoMuestra` y acciones REST; sigue sin vinculación obligatoria `ResultadoExamen`→`Muestra` (fase posterior). La acción de orden `tomar-muestra` (Fase A) coexiste con la toma física por muestra; al **tomar** una muestra en `PENDIENTE_TOMA`, si la solicitud está `PENDIENTE`, el servicio intenta `PENDIENTE`→`TOMA_MUESTRA` de forma segura (idempotente si ya avanzó).

---

## Pendiente de confirmar

- Endpoints `ingesta/` y webhook en despliegue real.
- Evolución post–Fase A: cancelación desde `VALIDADO`, informes PDF, tubos con trazabilidad.

---

## Microbiología base — Fase B3.1

Cadena operativa (sin microorganismos / aislados / antibiograma / informes en esta fase):

```
SolicitudExamen → Muestra (RECIBIDA | CONSERVADA | EN_PROCESO)
                       └── EstudioMicrobiologia (B3.1)
                               └── SiembraMicrobiologia (B3.1)
                                       └── LecturaCultivo (B3.1)
```

**Reglas clave:**

- Microbiología **nunca** se serializa en `ResultadoExamen.valor_obtenido`.
- Sólo se inicia un estudio sobre una muestra **`RECIBIDA`**, **`CONSERVADA`** o **`EN_PROCESO`**. Estados de muestra `PENDIENTE_TOMA`, `TOMADA`, `RECHAZADA`, `DESCARTADA`, `CANCELADA` bloquean alta de estudio (modelo `clean` + servicio). **B3.1-gap:** `CONSERVADA` alineada con B2 (carga de resultados).
- La solicitud no puede estar `CANCELADO`, `VALIDADO` ni `ENTREGADO` al crear estudio.
- Una solicitud puede tener varios estudios microbiológicos (uno por muestra; varios estudios por muestra están permitidos si se justifica).
- Una siembra pertenece a un estudio y reutiliza la misma muestra del estudio (validación `clean`).
- Una lectura pertenece a una siembra; `siembra.estudio_id` debe coincidir con `estudio_id`.
- `fecha_lectura >= fecha_siembra` (validación de modelo).
- B3.1 **no** crea aislados, microorganismos, antibiogramas ni informes.
- B3.1 **no** cierra ni valida microbiología (queda para B3.4).

### Máquina de estados del estudio (sólo estados cableados con acciones)

| Desde | Disparador | Hacia |
|-------|------------|-------|
| `PENDIENTE` | `POST .../estudios/{id}/iniciar/` | `RECIBIDO` (idempotente; setea `fecha_inicio` y `responsable` si está vacío) |
| `PENDIENTE` o `RECIBIDO` | Creación de primera siembra válida | `SEMBRADO` (transición automática + auditoría `accion=auto_sembrado`) |
| `SEMBRADO` | Creación de lectura con `es_preliminar=True` | `LECTURA_PRELIMINAR` (auto + auditoría `accion=auto_lectura_preliminar`) |
| `PENDIENTE`, `RECIBIDO`, `SEMBRADO`, `LECTURA_PRELIMINAR` | `POST .../estudios/{id}/cancelar/` con `motivo` | `CANCELADO` (terminal; bloquea siembras y lecturas posteriores) |

**Estado decorativo no cableado en B3.1** (sigue sin transición operativa): `INCUBANDO`. Los demás choices extendidos (`IDENTIFICACION`, `ANTIBIOGRAMA`, `LISTO_PARA_VALIDAR`, `VALIDADO`, `INFORMADO`) se cablean en **B3.2 / B3.3 / B3.4** (ver secciones siguientes).

### Restricciones operativas adicionales (B3.1)

- `estado` de `EstudioMicrobiologia`, `SiembraMicrobiologia` y `LecturaCultivo` es **read-only** en serializers: PATCH/PUT no lo modifican.
- Cancelar exige `motivo` no vacío.
- No se permite sembrar ni leer sobre estudio cancelado; no se permite leer sobre siembra cancelada.
- `MedioCultivo` se desactiva (`activo=False`); no se borra. No se puede sembrar con medio inactivo.

### Aliases de URL

Todas las rutas microbiológicas viven bajo `/api/lab/microbiologia/...` con alias `/api/laboratorio/microbiologia/...` (mismas clases ViewSet).

---

## Microbiología — Fase B3.2 (microorganismos / aislados / identificación)

Extensión de la cadena B3.1:

```
… → LecturaCultivo
        └── AisladoMicrobiologico (B3.2)
                └── IdentificacionMicroorganismo (B3.2)
```

**Reglas clave (delta sobre B3.1):**

- Microbiología sigue **fuera** de `ResultadoExamen.valor_obtenido`. Aislados e identificaciones se serializan exclusivamente en sus modelos dedicados.
- Un aislado se crea **desde una `LecturaCultivo` válida** del mismo estudio. No se permite crear aislados desde lecturas de otro estudio ni desde lecturas cuya siembra está `CANCELADA`. Tampoco se permite si el estudio está `CANCELADO`.
- `AisladoMicrobiologico.microorganismo` es opcional al crear (`SOSPECHADO`); cuando se asigna directamente debe estar `activo=True`. Un aislado en estado `IDENTIFICADO` siempre tiene microorganismo (validación de modelo).
- `requiere_antibiograma` queda registrado pero **no dispara** creación de antibiograma en B3.2 (se procesará en B3.3).
- `IdentificacionMicroorganismo` es **append-only** (sin PATCH/DELETE): para corregir, se crea otra identificación o se descarta el aislado.

### Máquina de estados del aislado (B3.2)

| Desde | Disparador | Hacia |
|-------|------------|-------|
| `SOSPECHADO` | Creación de la primera `IdentificacionMicroorganismo` válida | `IDENTIFICADO` (auto + auditoría `accion=auto_identificado`) |
| `SOSPECHADO` o `IDENTIFICADO` | `POST .../aislados/{id}/descartar/` con `motivo` no vacío | `DESCARTADO` (terminal del aislado; bloquea identificaciones posteriores) |

### Transición del estudio cableada en B3.2

| Desde | Disparador | Hacia |
|-------|------------|-------|
| `SEMBRADO` o `LECTURA_PRELIMINAR` | Creación de identificación válida | `IDENTIFICACION` (auto + auditoría `accion=auto_identificacion`) |

`IDENTIFICACION` es estado nuevo de `EstudioMicrobiologia.ESTADO_CHOICES` añadido en B3.2 (cableado). Sigue **fuera** de B3.2 cualquier transición a `ANTIBIOGRAMA`, `LISTO_PARA_VALIDAR`, `VALIDADO` o `INFORMADO`.

### Restricciones operativas adicionales (B3.2)

- `Microorganismo` se desactiva con `activo=False`; no se borra. Catálogo administrativo (escritura solo admin).
- PATCH sobre aislado **no toca** `estado` ni `microorganismo` (read-only del serializer).
- Descarte de aislado exige `motivo` no vacío (igual patrón que cancelar estudio).
- B3.2 **no** crea antibiogramas, ni informes, ni cierre/validación profesional.

## Microbiología — Fase B3.3 (antibiograma)

Extensión de la cadena B3.2:

```
… → AisladoMicrobiologico (IDENTIFICADO)
        └── IdentificacionMicroorganismo
        └── Antibiograma (B3.3)
                └── ResultadoAntibiotico (B3.3)
```

**Reglas clave (delta sobre B3.2):**

- Microbiología sigue **fuera** de `ResultadoExamen.valor_obtenido`. Antibiogramas y resultados se serializan exclusivamente en sus modelos dedicados.
- Un `Antibiograma` se crea **solo sobre un aislado `IDENTIFICADO`** con microorganismo asignado y estudio no cancelado. No se admite sobre aislados `SOSPECHADO` ni `DESCARTADO`.
- `Antibiotico` es catálogo administrativo (escritura solo admin); se desactiva con `activo=False`, no se borra.
- `ResultadoAntibiotico` requiere antibiótico activo y un antibiograma editable (`PENDIENTE`/`EN_PROCESO`). El par `(antibiograma, antibiotico)` es **único** (UniqueConstraint).
- `requiere_antibiograma` del aislado (B3.2) **no** dispara antibiograma automático; sigue siendo una marca informativa.

### Máquina de estados del antibiograma (B3.3)

| Desde | Disparador | Hacia |
|-------|------------|-------|
| `PENDIENTE` | Creación del primer `ResultadoAntibiotico` válido | `EN_PROCESO` (auto + auditoría `accion=auto_en_proceso`) |
| `PENDIENTE` o `EN_PROCESO` | `POST .../antibiogramas/{id}/completar/` con resultados existentes | `COMPLETO` (setea `fecha_resultado`; bloquea cargas/PATCH) |
| `PENDIENTE` o `EN_PROCESO` | `POST .../antibiogramas/{id}/cancelar/` con `motivo` no vacío | `CANCELADO` (terminal; bloquea cargas/PATCH) |

### Transición del estudio cableada en B3.3

| Desde | Disparador | Hacia |
|-------|------------|-------|
| `IDENTIFICACION` (típico), `LECTURA_PRELIMINAR` o `SEMBRADO` | Creación de antibiograma o primer resultado | `ANTIBIOGRAMA` (auto + auditoría `accion=auto_antibiograma`) |

`ANTIBIOGRAMA` es estado nuevo de `EstudioMicrobiologia.ESTADO_CHOICES` añadido en B3.3 (cableado). Las transiciones a `LISTO_PARA_VALIDAR`, `VALIDADO` e `INFORMADO` se cablean en **B3.4** (informe final + validación + `marcar-informado`).

### Restricciones operativas adicionales (B3.3)

- PATCH sobre antibiograma **solo** edita `metodo` y `observaciones`; estado/fechas/motivo **solo** vía servicio.
- PATCH sobre `ResultadoAntibiotico` solo cambia `halo_mm`, `mic`, `interpretacion`, `observaciones`. No cambia `antibiograma` ni `antibiotico`. Bloqueado si antibiograma `COMPLETO`/`CANCELADO`.
- `completar` falla con 400 si el antibiograma no tiene resultados.
- `cancelar` exige `motivo` no vacío.
- B3.3 **no** emite informe preliminar/final, **no** valida profesionalmente, **no** cierra el estudio. Eso queda para B3.4.

## Microbiología — Fase B3.4 (informes, validación, informado)

Extensión de la cadena B3.3:

```
… → Antibiograma / ResultadoAntibiotico (cuando aplica)
        └── InformeMicrobiologia (PRELIMINAR opcional, FINAL obligatorio para cierre)
```

**Reglas clave:**

- Varios informes **PRELIMINAR** en cualquier estado (`BORRADOR` / `EMITIDO` / `ANULADO`). La emisión preliminar **no** cambia el estado del estudio.
- Un solo informe **FINAL** vigente por estudio (`UniqueConstraint` con `tipo=FINAL` y `estado≠ANULADO`).
- **Emitir** informe (cualquier tipo) exige texto no vacío. **Emitir FINAL** además exige completitud microbiológica (`verificar_completitud_para_informe_final`) y pasa el estudio a `LISTO_PARA_VALIDAR` (si no estaba ya en terminal avanzada).
- **Validar** solo el informe **FINAL** en `EMITIDO`, con estudio en `LISTO_PARA_VALIDAR`, y solo rol **admin** (+ superuser). Pasa informe y estudio a `VALIDADO` y setea `fecha_cierre` del estudio si estaba vacía.
- **Anular** con motivo obligatorio solo en `BORRADOR` o `EMITIDO` (no se anula un informe `VALIDADO` en B3.4).
- **Marcar informado** (`POST …/estudios/{id}/marcar-informado/`): estudio `VALIDADO` + existencia de informe final `VALIDADO` → estudio `INFORMADO`.

### Restricciones adicionales (B3.4)

- PATCH de informe solo en `BORRADOR`. No hay edición silenciosa de informe validado.
- Sin DELETE físico de informes.
- PDF queda fuera de alcance backend; el **frontend UI-2** cubre operación sin PDF (ver sección siguiente).

---

## Frontend UI-2 — Consola de microbiología (`frontend/`)

**Commit frontend:** `d46d276`. Flujo operativo en pantalla (paralelo al backend B3.1–B3.4):

```
Orden LIMS (SolicitudExamen) → Muestra → EstudioMicrobiologia
  → Siembra → Lectura → Aislado → Identificación → Antibiograma (+ ResultadoAntibiotico)
  → Informe PRELIMINAR (opcional) / FINAL → emitir → validar (admin) → marcar informado
```

**Rutas:** `/laboratorio/microbiologia`, `/laboratorio/microbiologia/estudios`, `/laboratorio/microbiologia/estudios/:id`, `/laboratorio/microbiologia/catalogos`.

**Detalle del estudio (`:id`):** tabs Resumen | Siembras y lecturas | Aislados e identificación | Antibiograma | Informes.

**API cliente:** solo `/lab/microbiologia/...` (`limsMicroApi.ts`). No usa alias `/laboratorio/microbiologia/` en cliente ni rutas EMR `/solicitudes`.

**Permisos UI:** ver `DOC_FRONTEND.md` (sección UI-2). Identificaciones: solo alta (append-only). **B3-frontend-validación-A:** estados cerrados `CANCELADO`/`VALIDADO`/`INFORMADO` bloquean formularios operativos; datos históricos visibles; «Marcar informado» solo desde `VALIDADO`. Backend es fuente de verdad.

**Limitaciones conocidas (MVP):** alta de estudio con IDs numéricos de solicitud/muestra; listas relacionadas cargadas globalmente y filtradas por `estudio` en cliente; motivos de cancelación/descarte/anulación vía `prompt()`.
