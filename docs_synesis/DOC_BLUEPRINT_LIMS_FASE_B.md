# DOC_BLUEPRINT_LIMS_FASE_B — Blueprint funcional-técnico

**Versión:** 1.0 (solo diseño; sin implementación)  
**Fecha:** 3 de mayo de 2026  
**Alcance:** LIMS nativo (`laboratorio`) — núcleo común, muestras transaccionales, clínica general, microbiología completa, informes micro (preliminar opcional / final obligatorio), permisos, auditoría, API, tests, plan incremental.  
**Fuera de alcance de esta fase:** anatomía patológica, biología molecular avanzada, toxicología, equipamiento avanzado, QC Westgard, integración automática con equipos, informes con rectificaciones avanzadas (solo **extensión** y deuda explícita).

**Restricciones de diseño:** no romper `SolicitudExamen`, `ResultadoExamen`, endpoints Fase A ni aliases `/api/lab/...` y `/api/laboratorio/...`; no mezclar `solicitudes.Solicitud` (EMR) con `laboratorio.SolicitudExamen` (LIMS nativo); no usar string legacy `tecnico`; no eliminar datos ni migraciones destructivas; auditoría obligatoria; PHI mínima en logs.

**Estado de fases B implementadas:** B0/B1 (catálogos + `Muestra` transaccional), **B2** (vínculo `ResultadoExamen.muestra`, `cargar-resultados` con `muestra_id`, `PROCESAMIENTO`) y **B2-A** (docs + `safe_model_snapshot` sin PHI en snapshots/metadata genéricos de resultado) cerradas. **B2.1:** `validar` con `select_for_update`; transición RECIBIDA/CONSERVADA→EN_PROCESO al cargar primer resultado. **B2-B:** `TipoExamen.requiere_muestra` (default `False`); validación en `assert_tipo_examen_muestra_carga`. **B2-B-A:** tipo de muestra se valida siempre que hay muestra asociada; fixtures/tests PostgreSQL (`TipoMuestra.codigo` ≤10); `requiere_muestra` read-only en API catálogo. **B2-C [IMPLEMENTADO]:** el frontend LIMS permite seleccionar `muestra_id` por determinación al cargar resultados, valida `requiere_muestra` y `tipo_muestra_requerida`, y conserva compatibilidad legacy para tipos no obligatorios; el backend sigue siendo fuente de verdad. Quedan pendientes: UX avanzada, creación/recepción de muestras desde el mismo flujo, etiquetas/escaneo y E2E. No incluye microbiología, informes PDF ni recepción masiva.

**B3.1 (13 may 2026)** cerrada — **Microbiología base**: modelos `MedioCultivo`, `EstudioMicrobiologia`, `SiembraMicrobiologia`, `LecturaCultivo` (`laboratorio/models_microbiologia.py`); servicio de transiciones `laboratorio/microbiologia_estado.py` (`crear_estudio`, `aplicar_iniciar_estudio`, `aplicar_cancelar_estudio`, `crear_siembra`, `crear_lectura` con transiciones automáticas `auto_sembrado` y `auto_lectura_preliminar`); serializers/ViewSets dedicados; permisos `LimsMicrobiologiaCatalogPermission` y `LimsMicrobiologiaPermission`; endpoints `/api/lab/microbiologia/medios|estudios|siembras|lecturas/` con aliases `/api/laboratorio/...`; migración aditiva `0005_lims_b3_1_microbiologia_base`. **Estados cableados** del estudio: `PENDIENTE`, `RECIBIDO`, `SEMBRADO`, `LECTURA_PRELIMINAR`, `CANCELADO`. Estados de blueprint **no incluidos** en B3.1 para evitar choices sin acción: `INCUBANDO`, `IDENTIFICACION`, `ANTIBIOGRAMA`, `LISTO_PARA_VALIDAR`, `VALIDADO`, `INFORMADO` (postergados a B3.2/B3.3/B3.4). Microbiología nunca se serializa en `ResultadoExamen.valor_obtenido`. **B3.1-gap [IMPLEMENTADO]:** `MUESTRA_ESTADOS_VALIDOS_INICIAR_MICRO` incluye `CONSERVADA` (alineado con B2). **B3-audit [IMPLEMENTADO]:** metadata microbiológica sin `codigo_barra` ni valores microbiológicos crudos; snapshots genéricos redactan observaciones, textos, CIM, halo, interpretación y motivos sensibles. Se conservan IDs técnicos para trazabilidad. Queda pendiente una auditoría legal/especializada old/new con ACL estricto si se requiere. **B3-frontend-validación [IMPLEMENTADO — jun 2026]:** SPA microbiología UI-2 relevada y validada (`tsc`, `build`, contrato API); bug crecimiento lectura corregido; gaps UX (filtros server-side, picker muestra, E2E) documentados en `DOC_FRONTEND.md`.

**B3.2 (13 may 2026)** cerrada — **Microbiología: microorganismos, aislados, identificación**: modelos `Microorganismo` (catálogo admin), `AisladoMicrobiologico` (estados cableados `SOSPECHADO` / `IDENTIFICADO` / `DESCARTADO`), `IdentificacionMicroorganismo` (append-only); servicios `crear_aislado`, `aplicar_descartar_aislado`, `crear_identificacion` con transiciones automáticas (`auto_identificado` del aislado y `auto_identificacion` del estudio); permisos reutilizados (`LimsMicrobiologiaCatalogPermission` para microorganismos; `LimsMicrobiologiaPermission` extendido con `descartar`); endpoints `/api/lab/microbiologia/{microorganismos,aislados,identificaciones}/` con aliases `/api/laboratorio/...`; migración `0006_lims_b3_2_microbiologia_aislados` (aditiva: 3 modelos + `AlterField` no destructivo agregando `IDENTIFICACION` a `EstudioMicrobiologia.estado`). Identificaciones sin PATCH/DELETE (correcciones por nueva identificación o descarte). `requiere_antibiograma` queda registrado pero **no dispara** antibiograma en B3.2.

**B3.3 (13 may 2026)** cerrada — **Microbiología: antibiograma**: modelos `Antibiotico` (catálogo admin, sin destroy, `activo=False` para desactivar), `Antibiograma` (FK `AisladoMicrobiologico`, estados `PENDIENTE` / `EN_PROCESO` / `COMPLETO` / `CANCELADO`) y `ResultadoAntibiotico` (FK `Antibiograma`+`Antibiotico` con `UniqueConstraint`, interpretaciones `S`/`I`/`R`/`SDD`/`NO_APLICA`, halo/MIC opcionales). Servicios `crear_antibiograma`, `crear_resultado_antibiotico`, `actualizar_resultado_antibiotico`, `aplicar_completar_antibiograma`, `aplicar_cancelar_antibiograma` con transiciones automáticas (`auto_en_proceso` del antibiograma al primer resultado y `auto_antibiograma` del estudio). Permisos: `LimsMicrobiologiaCatalogPermission` para `Antibiotico`; `LimsMicrobiologiaPermission` extendido con acción `completar`; resolución de `solicitud` en objetos `antibiograma → aislado → estudio` y `resultado → antibiograma → aislado → estudio` para visibilidad médica. Endpoints `/api/lab/microbiologia/{antibioticos,antibiogramas,resultados-antibiotico}/` con aliases `/api/laboratorio/...` y acciones `POST .../{id}/completar/` y `POST .../{id}/cancelar/` (motivo obligatorio). Migración `0007_lims_b3_3_microbiologia_antibiograma` (aditiva: 3 modelos + `AlterField` no destructivo agregando `ANTIBIOGRAMA` a `EstudioMicrobiologia.estado` + `UniqueConstraint(antibiograma, antibiotico)`). Reglas: antibiograma **solo** sobre aislado `IDENTIFICADO` con microorganismo y estudio no cancelado; no se cargan/editan resultados si antibiograma `COMPLETO` o `CANCELADO`; antibiótico inactivo bloquea carga; no se puede completar sin resultados; cancelación exige motivo. **No** se implementa informe ni validación profesional; el cierre llega en B3.4.

**B3.4 (14 may 2026)** cerrada — **Microbiología: informes, validación y cierre**: modelo `InformeMicrobiologia` (`tipo` `PRELIMINAR`/`FINAL`, `estado` `BORRADOR`/`EMITIDO`/`VALIDADO`/`ANULADO`); `UniqueConstraint` condicional un informe **final** vigente por estudio (`tipo=FINAL` y `estado≠ANULADO`). Servicios `crear_informe_borrador`, `actualizar_informe_borrador`, `aplicar_emitir_informe`, `aplicar_validar_informe_final`, `aplicar_anular_informe`, `aplicar_marcar_estudio_informado`, `verificar_completitud_para_informe_final` (lectura obligatoria; aislados `DESCARTADO` no bloquean; `CONTAMINANTE`/`FLORA_HABITUAL` en `SOSPECHADO` permitidos sin identificar; otros `SOSPECHADO` bloquean; `requiere_antibiograma` exige `Antibiograma` `COMPLETO`). Transiciones estudio: emisión informe final → `LISTO_PARA_VALIDAR`; validación informe final (solo **admin**) → `VALIDADO` + `fecha_cierre`; `POST estudios/{id}/marcar-informado/` → `INFORMADO`. Permiso dedicado `LimsMicrobiologiaInformePermission` (lab crea/emite/anula; admin valida; médico solo lectura filtrada; paciente/secretaría/enfermería/anónimo sin acceso). Endpoints `/api/lab/microbiologia/informes/` + acciones `emitir`, `validar`, `anular` (motivo obligatorio) y aliases `/api/laboratorio/...`. Migración `0008_lims_b3_4_microbiologia_informes`. **No** PDF, **no** frontend, **no** rectificación avanzada.

**B3-frontend-validación-A (jun 2026) [VALIDADO]** — Bloqueo operación técnica en `CANCELADO`/`VALIDADO`/`INFORMADO`. Commits `35d1edc`/`75d56b2`. Revalidación pytest 165 + regresión 315. Paquete: `B3_VALIDACION_A_CODEX_AUDIT.md`.

**B3-frontend-UX (jun 2026) [PARCIAL]** — Picker solicitud/muestra al alta de estudio (API LIMS existente). **[GAP]** filtros server-side por `estudio_id` en endpoints micro; **[GAP]** E2E browser.

**E2E-1 (jun 2026) [IMPLEMENTADO — API-level]** — Sin instalar Playwright/Cypress: `laboratorio/tests/test_lims_flujo_critico.py` valida solicitud → muestra → resultado con `muestra_id` → micro (iniciar/siembra/lectura/informe preliminar). Ver `DOC_TESTS.md` y `DOC_FLUJOS_LIMS.md`.

**Pendiente (post-B3.4):** PDF, frontend dedicado de informes, rectificación/addendum avanzado, integración externa, QC/equipamiento.

---

## 1. Estado actual confirmado

### 1.1 Modelos LIMS (`laboratorio/models.py`)

| Modelo | Rol |
|--------|-----|
| `TipoMuestra` | Catálogo (no es muestra física). |
| `TipoExamen` | Determinación; FK a `TipoMuestra` requerida. |
| `PanelExamen` | Agrupa tipos de examen (M2M). |
| `SolicitudExamen` | Orden/protocolo; estados Fase A; M2M tipos/paneles; FK `Paciente`, médico híbrido. |
| `ResultadoExamen` | Una fila por `(solicitud, tipo_examen)`; `valor_obtenido` texto; `es_patologico`; validación usuario/fecha. |

**No existe:** entidad muestra física, recepción, contenedor transaccional, microbiología, informes estructurados, áreas/secciones.

### 1.2 Máquina de estados orden (Fase A) — `laboratorio/solicitud_estado.py` + vistas

Transiciones auditadas vía `apply_solicitud_estado_transition` + `log_update` con metadata (`accion`, `estado_anterior`, `estado_nuevo`, `solicitud_id`, `numero_solicitud`). Llamadas bajo `transaction.atomic()` + `select_for_update()` en `SolicitudExamenViewSet`.

Endpoints vigentes: listado en `DOC_API_ENDPOINTS.md` y `DOC_FLUJOS_LIMS.md` (incl. `tomar-muestra`, `cancelar`, `marcar-entregado`, etc.).

### 1.3 Permisos (`api/permissions.py`)

`LimsSolicitudExamenPermission` y `LimsCatalogReadPermission`; `validar` solo **admin**/superuser; **laboratorio** opera carga/toma/cancelar/marcar entregado según matriz documentada.

### 1.4 Auditoría (`auditoria/audit_service.py`, `snapshot.py`)

`log_create`, `log_update`, `log_event`; snapshots conservadores; eventos post-commit en transacciones.

### 1.5 EMR vs LIMS nativo

- **`solicitudes.Solicitud`:** flujo EMR (`/api/solicitudes/`, frontend `/solicitudes`); puede intentar `lims_service.enviar_solicitud_a_lims` hacia URL fija **no garantizada** en este proyecto (`integracion_lims/lims_service.py`).
- **`laboratorio.SolicitudExamen`:** orden LIMS nativa (`/api/lab/solicitudes/`, alias `laboratorio/solicitudes`). **Sin FK obligatoria** entre ambos en modelo actual — riesgo operativo conocido; Fase B **no** debe fusionarlos; opcional futuro: `SolicitudExamen.origen_emr_solicitud_id` nullable (solo diseño futuro, no parte mínima B).

### 1.6 Frontend (`frontend/src/`)

- **`/laboratorio/examenes-test`:** prueba de catálogo `TipoExamen` (no consola LIMS).
- **`/solicitudes`:** EMR, no órdenes `SolicitudExamen`.
- **No hay** módulo SPA completo para órdenes LIMS, muestras ni microbiología.

### 1.7 Migraciones app `laboratorio`

A la fecha de redacción: `0001_initial`, `0002_alter_resultadoexamen_valor_obtenido` aplicadas (ver `showmigrations laboratorio`).

---

## 2. Brechas respecto al LIMS objetivo (Fase B)

| Brecha | Impacto |
|--------|---------|
| Sin `Muestra` transaccional | No hay trazabilidad física ni recepción/rechazo real. |
| `tomar-muestra` solo marca orden | No registra quién/cuándo/dónde tomó material ni vínculo a tubo. |
| `ResultadoExamen` único por tipo sin muestra | Órdenes multi-muestra o multi-contenedor no modeladas. |
| Microbiología ausente | Cultivos, siembras, lecturas, aislados, antibiograma, informes no existen. |
| Informes | Sin preliminar/final estructurado para micro; clínica general sigue en JSON/valor texto. |
| Catálogo sin área/sección | Escalabilidad operativa y permisos por sección limitados. |
| Concurrencia | Recepción masiva y doble escaneo de código de barras requieren diseño explícito. |

---

## 3. Diseño propuesto — visión general

1. **Núcleo común:** catálogos `AreaLaboratorio`, `SeccionLaboratorio` (opcional B.1 si se prioriza velocidad: empezar con `SeccionLaboratorio` ligada a `TipoExamen`/`TipoMuestra` por FK nullable).
2. **Muestra física:** `Muestra` + `EventoMuestra` (trazabilidad append-only o semántica equivalente) + catálogo `TipoContenedor` + relación contenedor-instancia en `Muestra` (campos directos o `ContenedorMuestra` 1:1 si se requiere historial de cambio de frasco).
3. **Clínica general:** extensión **no rompente** de `ResultadoExamen` (campos opcionales + FK nullable `muestra`); reglas de negocio que exijan muestra **recibida** antes de cargar cuando aplique.
4. **Microbiología:** grafo propio (`EstudioMicrobiologia` → siembras → lecturas → aislados → identificación → antibiograma → resultados antibiótico → informes); **nunca** serializar antibiograma ni identificación en `valor_obtenido`.
5. **Enlace orden–micro:** `EstudioMicrobiologia` FK a `SolicitudExamen` y FK a `Muestra`; `TipoExamen` con categoría o flag `modalidad` = `QUIMICA_CLINICA` | `MICROBIOLOGIA` | `OTRO` para saber qué filas generan estudio vs solo `ResultadoExamen`.
6. **Informes micro:** `InformeMicrobiologia` con unicidad lógica del final vigente por estudio (constraint parcial o validación en servicio + índice único condicional `WHERE tipo=FINAL AND estado!=ANULADO` si la BD lo soporta; si no, **servicio de dominio** + lock).

---

## 4. Modelos propuestos

### 4.1 Catálogos núcleo (nuevos)

**`AreaLaboratorio`**  
- `codigo` (unique), `nombre`, `activo`, orden opcional.  
- Uso: reporting, permisos futuros por área, routing.

**`SeccionLaboratorio`**  
- FK `area` (nullable si área única al inicio), `codigo`, `nombre`, `activo`.  
- Uso: filtrar estudios y muestras en UI operativa.

**`TipoContenedor`** (catálogo liviano)  
- `codigo`, `nombre`, `material` (plástico/vidrio/…), `activo`.  
- No sustituye a `TipoMuestra` (matriz vs envase).

**`MedioCultivo`**, **`Microorganismo`**, **`Antibiotico`**  
- Campos según especificación usuario; `activo`; índices por `codigo`.

**`TipoExamen` — extensión sugerida (migración additive)**  
- `modalidad` (choices: `QUIMICA_CLINICA`, `MICROBIOLOGIA`, `OTRO`) default `QUIMICA_CLINICA`.  
- `seccion` FK nullable a `SeccionLaboratorio`.  
- **Micro:** si `MICROBIOLOGIA`, al crear orden se crea `EstudioMicrobiologia` (y no se rellena microbiología en `valor_obtenido`).

### 4.2 Transaccional — muestra

**`Muestra`** (campos alineados al requerimiento; tipos Django afinados en implementación)

| Campo | Notas |
|-------|--------|
| `id` | PK |
| `codigo_barra` | Unique global o unique por `solicitud` (decisión: **unique global** recomendado para escaneo en recepción; alternativa `unique_together(solicitud, codigo_interno)` + código global opcional). |
| `solicitud` | FK `SolicitudExamen`, CASCADE o PROTECT según política de archivo (recomendación: **PROTECT** si se impide borrar orden con muestras; hoy destroy admin existe — **documentar** que destroy orden debe bloquearse si hay muestras no archivadas). |
| `paciente` | FK redundante controlada por `clean` (= solicitud.paciente) para consultas rápidas e índices; **no** sustituye integridad principal. |
| `tipo_muestra` | FK `TipoMuestra`. |
| `tipo_contenedor` | FK `TipoContenedor` nullable. |
| `etiqueta_fabricante` | Char nullable (código impreso en tubo). |
| `estado` | Ver §5.1 máquina muestra. |
| `fecha_toma`, `tomada_por` | User nullable hasta toma real. |
| `fecha_recepcion`, `recibida_por` | |
| `fecha_rechazo`, `rechazada_por`, `motivo_rechazo` | Motivo **obligatorio** si `RECHAZADA`. |
| `observaciones` | Text |
| `ubicacion_actual` | Char o FK futuro a ubicación física; Fase B: Char acotado. |
| `fecha_conservacion`, `fecha_descarte`, `descartada_por` | |
| `created_at`, `updated_at` | |

**Índices:** `(estado)`, `(solicitud)`, `(paciente)`, `(fecha_toma)`, `(codigo_barra)`.

**`EventoMuestra`** (trazabilidad granular)  
- FK `muestra`, `tipo_evento` (enum: `CREADA`, `TOMA`, `RECEPCION`, `RECHAZO`, `CAMBIO_UBICACION`, `CONSERVACION`, `DESCARTE`, `VINCULACION_RESULTADO`, …), `actor`, `timestamp`, `metadata` JSON (sin PHI innecesaria), `estado_anterior`, `estado_nuevo` opcionales.  
- Complementa `AuditEvent` a nivel negocio (consultas operativas sin join masivo a auditoría global).

**`ContenedorMuestra` (opcional B.1)**  
- Solo si se requiere **historial** de cambio de frasco (1 muestra lógica, varios contenedores físicos). Si no: campos en `Muestra` bastan para Fase B mínima.

### 4.3 Clínica general — `ResultadoExamen` (extensión)

| Campo nuevo | Tipo | Notas |
|---------------|------|--------|
| `muestra` | FK nullable `Muestra` | Obligatorio cuando la determinación exige muestra recibida y hay >1 línea muestra. |
| `unidad` | Char nullable | p.ej. mg/dL |
| `valor_numerico` | Decimal nullable | Opcional para reporting; **no** reemplazar `valor_obtenido` en B para no romper clientes. |
| `es_critico` | Boolean default false | Auditoría reforzada al marcar. |
| `rango_referencia_snapshot` | Char nullable | Copia al validar orden (inmutable tras validación salvo flujo rectificación futura). |

**Regla:** `modalidad=MICROBIOLOGIA` → no usar `valor_obtenido` para payload micro; como mucho valores agregados tipo `VER_INFORME_FINAL` **después** de cierre de estudio (definición en servicio; preferible **sin** poblar y mostrar UI desde `InformeMicrobiologia`).

### 4.4 Microbiología (nuevos; nombres alineados al requerimiento)

- **`EstudioMicrobiologia`:** `solicitud`, `muestra`, `estado` (§5.2), `tipo_estudio` (FK cat simple o choices: `CULTIVO_RUTINA`, `UROCULTIVO`, etc.), `observaciones`, fechas inicio/cierre, `responsable`, `validado_por`, `fecha_validacion`.  
- **`SiembraMicrobiologia`:** `estudio`, `muestra` (o solo estudio si muestra implícita), `medio`, `fecha_siembra`, `sembrado_por`, `condicion_incubacion`, `observaciones`, `estado`.  
- **`LecturaCultivo`:** `siembra`, `fecha_lectura`, `leido_por`, `horas_incubacion`, `crecimiento` (choices: NEGATIVO / ESCASO / MODERADO / ABUNDANTE / etc.), `descripcion_colonias`, `tincion_gram`, `observaciones`, `es_preliminar`, `genera_informe_preliminar` (bool).  
- **`AisladoMicrobiologico`:** `estudio`, `lectura_origen` FK, `microorganismo` FK, `estado`, `descripcion`, `cantidad`, `significancia`, `requiere_antibiograma`, `observaciones`.  
- **`IdentificacionMicroorganismo`:** `aislado`, `metodo`, `resultado`, `confianza`, `fecha`, `realizado_por`.  
- **`Antibiograma`:** `aislado`, `metodo`, `estado`, `fecha_inicio`, `fecha_resultado`, `realizado_por`, `validado_por`, `observaciones`.  
- **`ResultadoAntibiotico`:** `antibiograma`, `antibiotico`, `halo_mm`, `mic`, `interpretacion` (S/I/R/SDD/NO_APLICA), `observaciones`. **Unique:** `(antibiograma, antibiotico)`.  
- **`InformeMicrobiologia`:** `estudio`, `tipo` (PRELIMINAR/FINAL), `estado` (BORRADOR/EMITIDO/VALIDADO/ANULADO), `texto`, `version`, `emitido_por`, `fecha_emision`, `validado_por`, `fecha_validacion`, `reemplaza_a` FK self nullable, `observaciones`.

**Catálogo `TipoEstudioMicrobiologico`** (opcional): desacopla choices fijos.

### 4.5 Informes clínica general (Fase B.2 opcional)

**`InformeLaboratorio`** genérico (PDF path + metadata) **no** obligatorio para cerrar clínica general en B; priorizar vista API + export B.2. Evita duplicar con micro.

---

## 5. Relaciones (diagrama lógico)

```
SolicitudExamen ──┬── Muestra (N)
                  ├── ResultadoExamen (N) ──► TipoExamen
                  │         └── opcional FK Muestra
                  └── EstudioMicrobiologia (0..N por muestra/tipo)
                            ├── SiembraMicrobiologia
                            │       └── LecturaCultivo
                            │               └── (origen) AisladoMicrobiologico
                            │                       ├── IdentificacionMicroorganismo
                            │                       └── Antibiograma ── ResultadoAntibiotico
                            └── InformeMicrobiologia (0..N prelim, 0..1 final vigente)
TipoMuestra ◄── Muestra
TipoContenedor ◄── Muestra
Paciente ◄── SolicitudExamen (y redundante en Muestra para índices)
```

**`PanelExamen`:** sin cambio estructural; la expansión a `ResultadoExamen` / estudios sigue reglas actuales de creación + nuevas reglas por `modalidad`.

---

## 6. Estados y transiciones

### 6.1 Máquina `Muestra`

**Estados propuestos:**  
`PENDIENTE_TOMA`, `TOMADA`, `EN_TRANSITO` (opcional B.1 courier), `RECIBIDA`, `RECHAZADA`, `EN_PROCESO`, `CONSERVADA`, `DESCARTADA`, `CANCELADA`.

| Desde | Evento / acción | Hacia | Notas |
|-------|-------------------|-------|--------|
| `PENDIENTE_TOMA` | Toma registrada | `TOMADA` | Usuario + fecha. |
| `TOMADA` | Recepción en lab | `RECIBIDA` | No si solicitud `CANCELADO`. |
| `TOMADA` | Rechazo en recepción | `RECHAZADA` | Motivo obligatorio. |
| `RECIBIDA` | Inicio técnico (siembra o asignación a técnica) | `EN_PROCESO` | |
| `RECIBIDA` | Conservación | `CONSERVADA` | Reglas de autorización §7. |
| `EN_PROCESO` | Fin uso técnico | `CONSERVADA` o `DESCARTADA` | |
| `*` | Orden cancelada antes de uso | `CANCELADA` | Solo si política lo permite; no borrar fila. |

**Invariantes:** no recepcionar si `SolicitudExamen` cancelada; no procesar si `RECHAZADA`/`DESCARTADA`/`CANCELADA`; rechazo exige motivo; recepción exige usuario y fecha.

### 6.2 Máquina `EstudioMicrobiologia`

**Estados propuestos (ajustables):**  
`PENDIENTE`, `RECIBIDO`, `SEMBRADO`, `INCUBANDO`, `LECTURA_PENDIENTE`, `LECTURA_PRELIMINAR`, `EN_IDENTIFICACION`, `EN_ANTIBIOGRAMA`, `LISTO_PARA_INFORMAR`, `LISTO_PARA_VALIDAR`, `VALIDADO`, `INFORMADO`, `CANCELADO`.

**Justificación del ajuste respecto a lista literal del PRD:** separar `INCUBANDO` de lectura evita ambigüedad con lecturas seriadas; `LECTURA_PRELIMINAR` puede ser estado **o** flag en `LecturaCultivo` (recomendación: **estado del estudio** deriva de agregación de siembras/lecturas vía **servicio** para no desincronizar).

Transiciones típicas:

- `PENDIENTE` → `RECIBIDO` cuando muestra asociada `RECIBIDA`.  
- `RECIBIDO` → `SEMBRADO` al crear primera `SiembraMicrobiologia` válida.  
- `SEMBRADO` → `INCUBANDO` (automático o al registrar incubadora/tiempo).  
- Tras lecturas: → `LECTURA_PENDIENTE` / `LECTURA_PRELIMINAR` según negocio.  
- Con aislados: → `EN_IDENTIFICACION` → `EN_ANTIBIOGRAMA` si algún aislado `requiere_antibiograma`.  
- `LISTO_PARA_INFORMAR` cuando reglas de completitud lo permiten (preliminar **no** exigido).  
- Tras informe **FINAL** `VALIDADO` → `INFORMADO` (o unificar `VALIDADO` micro con usuario validador en estudio — **decisión:** duplicar criterio Fase A orden vs validación micro; recomendación: **validación micro en estudio** + orden `VALIDADO` solo vía flujo orden existente cuando todo lo requerido por la orden esté cerrado).

**Cierre estudio:** obligatorio **exactamente un** `InformeMicrobiologia` FINAL en estado `VALIDADO` (vigente); preliminares 0..N; **no** cerrar si aislados **reportables** incompletos (definir catálogo `significancia` reportable); permitir cultivo sin desarrollo con informe final negativo (regla explícita “sin crecimiento”); flora/contaminante vía `significancia` + texto en informe.

### 6.3 Coordinación `SolicitudExamen` (Fase A + B)

| Pregunta | Propuesta |
|----------|-----------|
| ¿Cuándo `TOMA_MUESTRA` → `EN_PROCESO`? | Mantener compatibilidad Fase A: `cargar_resultados` sigue pudiendo mover orden sin muestra (legacy). **Paralelamente:** cuando **todas** las `Muestra` requeridas por la orden estén `RECIBIDA` **o** exista política “orden sin muestra física” (excepción documentada por `TipoExamen`), servicio puede proponer transición a `EN_PROCESO` sin depender solo de carga de resultado. |
| ¿Todas muestras rechazadas? | **Opción A (recomendada B):** estado orden `CANCELADO` automático con motivo agregado y auditoría. **Opción B:** nuevo estado `NO_FACTIBLE` — **fuera B mínima**; dejar en deuda. |
| `tomar-muestra` | Evolucionar a: crear `Muestra` en `PENDIENTE_TOMA` o `TOMADA` + evento + opcionalmente mantener transición orden a `TOMA_MUESTRA` si aún no hay muestras. **Plan:** Fase B.1 sin romper: `tomar-muestra` sigue igual; B.2 añade creación de filas `Muestra` desde payload o plantilla por `TipoExamen.tipo_muestra_requerida`. |

---

## 7. Validaciones funcionales (resumen)

- **Muestra:** reglas §6.1 + no descartar en proceso sin rol/perfil autorizado (admin o política `CONSERVACION_APROBADA` en metadata evento).  
- **SolicitudExamen:** conservar Fase A; sin `PATCH` de `estado`; coordinación vía servicios.  
- **Resultado simple:** valor requerido para “completo”; unidad/rango según `TipoExamen`; crítico auditado; no validar orden con pendientes; no editar tras validación sin **CorreccionResultado** (futuro, fuera B mínima).  
- **Micro:** no siembra sin muestra `RECIBIDA`; siembra requiere medio; lectura requiere siembra; aislado requiere lectura compatible; reportable requiere identificación; antibiograma completo si `requiere_antibiograma`; preliminar opcional; final único vigente; sin edición silenciosa de final validado (solo nueva versión o anulación + re-emisión auditada).

---

## 8. Endpoints REST propuestos

**Prefijos:** mantener `/api/lab/...` y alias `/api/laboratorio/...`. Los nuevos pueden registrarse como `lab/muestras-transaccionales` vs anidar bajo solicitud — **recomendación:** anidar bajo solicitud para claridad de tenencia, más listados globales con filtros para recepción.

### 8.1 Mantener (sin cambiar contrato) — Fase A

Lista completa en `DOC_API_ENDPOINTS.md` (GET/POST solicitudes, PATCH sin estado, acciones `tomar-muestra`, `cargar-resultados`, `validar`, `marcar-entregado`, `cancelar`, `etiqueta`).

### 8.2 Núcleo — catálogos (Fase B obligatorios donde se indique)

| Método | Ruta (conceptual) | Entidad | Acción | Payload (resumen) | Respuesta | Permisos | Auditoría | Obligatoriedad |
|--------|-------------------|---------|--------|---------------------|-----------|----------|-----------|----------------|
| GET/POST | `/api/lab/areas/` | `AreaLaboratorio` | CRUD | Campos área | Lista/objeto | admin (escritura); lab lectura opcional | log_create/update | **B.1** |
| GET/POST | `/api/lab/secciones/` | `SeccionLaboratorio` | CRUD | + area_id | idem | idem | idem | **B.1** |
| GET/POST | `/api/lab/tipos-contenedor/` | `TipoContenedor` | CRUD | catálogo | idem | admin catálogo; lab read | idem | **B.1** |

**Nota:** catálogos pueden reutilizar patrón `ReadOnly` + admin write vía admin Django en B.0 ultra-mínimo; REST completo en B.1.

### 8.3 Muestras y eventos

| Método | Ruta | Acción | Payload | Respuesta | Permisos | Auditoría | Oblig. |
|--------|------|--------|---------|-----------|----------|-----------|--------|
| GET | `/api/lab/solicitudes/{sid}/muestras/` | Listar | — | Lista `Muestra` | lab, admin; médico solo órdenes propias read | opcional list | **B** |
| POST | `/api/lab/solicitudes/{sid}/muestras/` | Crear muestra(s) | `{ plantilla_id?, tipo_muestra_id, n, contenedor? }` | Creadas | lab, admin | log_create + evento | **B** |
| GET | `/api/lab/muestras/{mid}/` | Detalle | — | Objeto + últimos eventos | idem | — | **B** |
| POST | `/api/lab/muestras/{mid}/registrar-toma/` | Toma | `{ ubicacion?, observaciones? }` | Muestra `TOMADA` | lab, admin; enfermería **si** política | log_update + EventoMuestra | **B** |
| POST | `/api/lab/muestras/{mid}/recibir/` | Recepción | `{ observaciones? }` | `RECIBIDA` | lab, admin | obligatoria | **B** |
| POST | `/api/lab/muestras/{mid}/rechazar/` | Rechazo | `{ motivo }` | `RECHAZADA` | lab, admin | obligatoria + motivo | **B** |
| POST | `/api/lab/muestras/{mid}/conservar/` | Conservación | `{ motivo? }` | `CONSERVADA` | lab, admin | sí | **B.1** |
| POST | `/api/lab/muestras/{mid}/descartar/` | Descarte | `{ motivo, autorizacion_id? }` | `DESCARTADA` | admin o lab según política | sí | **B.1** |
| GET | `/api/lab/muestras/{mid}/eventos/` | Trazabilidad | query limit | Lista `EventoMuestra` | lab, admin | read audit trail | **B** |

**Recepción masiva (opcional B.2):** `POST /api/lab/recepcion/escaneo/` con array de códigos.

### 8.4 Resultados simples (extensión)

| Método | Ruta | Acción | Permisos | Auditoría | Oblig. |
|--------|------|--------|----------|-----------|--------|
| POST | `/api/lab/solicitudes/{sid}/cargar-resultados/` | **Misma**; cuerpo puede incluir `muestra_id` por resultado | lab (sin validar) | log_update resultado + posible transición orden | **B** compatible |
| PATCH | `/api/lab/resultados-examen/{rid}/` | Edición controlada pre-validación (nuevo endpoint para no romper semántica masiva) | lab | sí | **B.2** si se separa de acción masiva |

**Recomendación:** no cambiar contrato `cargar-resultados`; añadir campos opcionales en items del array.

### 8.5 Microbiología

| Método | Ruta | Entidad | Oblig. |
|--------|------|---------|--------|
| GET/POST | `/api/lab/solicitudes/{sid}/estudios-micro/` | `EstudioMicrobiologia` | **B** |
| GET/PATCH | `/api/lab/estudios-micro/{eid}/` | detalle / metadata | **B** |
| POST | `/api/lab/estudios-micro/{eid}/siembras/` | `SiembraMicrobiologia` | **B** |
| GET | `/api/lab/siembras/{sid}/` | detalle | **B** |
| POST | `/api/lab/siembras/{sid}/lecturas/` | `LecturaCultivo` | **B** |
| POST | `/api/lab/lecturas/{lid}/aislados/` | `AisladoMicrobiologico` | **B** |
| POST | `/api/lab/aislados/{aid}/identificaciones/` | `IdentificacionMicroorganismo` | **B** |
| POST | `/api/lab/aislados/{aid}/antibiogramas/` | `Antibiograma` | **B** |
| POST/PATCH | `/api/lab/antibiogramas/{abid}/resultados/` | bulk `ResultadoAntibiotico` | **B** |
| POST | `/api/lab/estudios-micro/{eid}/informes/` | crear PRELIMINAR o BORRADOR FINAL | **B** |
| POST | `/api/lab/informes-micro/{iid}/emitir/` | `EMITIDO` | **B** |
| POST | `/api/lab/informes-micro/{iid}/validar/` | `VALIDADO` (rol según matriz) | **B** |
| POST | `/api/lab/informes-micro/{iid}/anular/` | `ANULADO` + motivo | admin / perfil alto | **B.1** |

**Catálogos micro:** `GET/POST /api/lab/medios-cultivo/`, `microorganismos/`, `antibioticos/` (paralelo a `lab/examenes`).

### 8.6 Permisos por endpoint (matriz mínima)

| Acción | admin/superuser | laboratorio | medico | secretaria | enfermeria | paciente | anónimo |
|--------|-----------------|-------------|--------|------------|-------------|----------|---------|
| CRUD catálogos área/sección/contenedor/medio/micro/antibiótico | escr | lectura (configurable) | lectura catálogo LIMS existente | no | no | no | no |
| Crear/listar muestras orden propia / todas (lab) | sí | sí operativo | solo ver órdenes propias + muestras vinculadas | no | toma si política | no | no |
| Recepción / rechazo muestra | sí | sí | no | no | no | no | no |
| Siembra / lectura / aislado / identificación / AB | sí | sí | no | no | no | no | no |
| Emitir preliminar micro | sí | sí si política | no | no | no | no | no |
| Validar informe final micro | **sí** (Fase A alinea validación orden admin) | **no** en B salvo cambio de política explícita | no | no | no | no | no |
| Validar orden `SolicitudExamen` (existente) | sí | no | no | no | no | no | no |

**Granularidad futura** (`operador_toma`, `bioquimico_validador`): mapear con **grupos Django** o campo `perfil_lims` en `User` — **fuera B mínima**; documentar extensión.

---

## 9. Auditoría

- Reutilizar `log_create`, `log_update`, `log_event` con `safe_model_snapshot` y `metadata` enriquecido (IDs técnicos y acción): `accion`, `estado_anterior`, `estado_nuevo`, `solicitud_id`, `muestra_id`, `resultado_id`, `estudio_micro_id`, `numero_solicitud`.  
- **Regla SYNESIS (B1/B2/B3-audit):** `codigo_barra` es identificador operativo de `Muestra` para usuarios autorizados, pero **no** se registra en `AuditEvent.metadata` genérica ni se expone en snapshots genéricos (incluye microbiología B3-audit). La auditoría usa `muestra_id` / `solicitud_id` / IDs técnicos del dominio micro.
- **EventoMuestra:** duplicación semántica aceptable para consultas rápidas; auditoría canónica sigue en `AuditEvent`.  
- **Informe final validado:** cualquier corrección futura = nueva fila versión o `reemplaza_a` + anulación auditada (sin `UPDATE` silencioso de texto validado).

---

## 10. Frontend futuro (estrategia)

- **Nuevo módulo** bajo prefijo `/laboratorio` (no reutilizar `/solicitudes` EMR):  
  - `LaboratorioDashboard`, `LaboratorioOrdenes`, `LaboratorioOrdenDetalle`, `LaboratorioMuestras`, `LaboratorioRecepcion`, `LaboratorioResultados`, `LaboratorioMicroEstudios`, `LaboratorioMicroEstudioDetalle`, `LaboratorioInformes`, `LaboratorioCatalogos` (subrutas).  
- **Menú:** rol `laboratorio` y `admin`; médico solo lecturas acotadas.  
- **Acciones visibles** por estado (orden y muestra y estudio) — capa de **policy** en frontend alineada a respuestas API 403/400.  
- **Datos sensibles:** paginar listados; no loguear respuestas completas en consola.

---

## 11. Tests (plan; no implementados aquí)

### 11.1 Modelos

- Creación `Muestra`; unicidad `codigo_barra`; transiciones válidas; rechazo sin motivo → error; no procesar `RECHAZADA`; `EstudioMicrobiologia` con muestra no recibida → error en siembra; lectura sin siembra → error; aislado sin lectura → error; AB sin aislado → error; unique `ResultadoAntibiotico`; un solo FINAL vigente; múltiples preliminares; cierre bloqueado sin final validado; aislado reportable incompleto bloquea final.

### 11.2 API

- Permisos por rol en cada nuevo endpoint; recepción/rechazo; flujo micro completo feliz + bloqueos; preliminar 0 o N; final obligatorio; regresión Fase A (`pytest` existente + nuevos casos: PATCH estado, `cargar-resultados`, `validar`, `cancelar`, aliases).

### 11.3 Auditoría

- `captureOnCommitCallbacks` en transiciones muestra, rechazo, siembra, informe final (patrón ya usado en `laboratorio/tests/test_api.py`).

---

## 12. Migraciones (estrategia; no ejecutar en este blueprint)

1. **0003** — Catálogos `AreaLaboratorio`, `SeccionLaboratorio`, `TipoContenedor` + seeds datos mínimos.  
2. **0004** — `Muestra` + `EventoMuestra` (índices).  
3. **0005** — Nullable FKs en `ResultadoExamen` (`muestra`, `unidad`, `es_critico`, `valor_numerico`, `rango_referencia_snapshot`).  
4. **0006** — `TipoExamen.modalidad` + `seccion` nullable + backfill `QUIMICA_CLINICA`.  
5. **0007** — Catálogos micro (`MedioCultivo`, `Microorganismo`, `Antibiotico`).  
6. **0008** — `EstudioMicrobiologia` + cadena siembra → … → `InformeMicrobiologia`.  
7. **0009** — constraints únicos parciales (DB específica) o índices + validación servicio.

**Siempre:** `--dry-run` / revisión en staging; sin `RunPython` destructivo; datos existentes preservados.

---

## 13. Fases de implementación recomendadas (orden de riesgo creciente)

| Fase | Contenido | Riesgo regresión | Utilidad operativa |
|------|-------------|------------------|----------------------|
| **B0** | Catálogos área/sección/contenedor; permisos lectura; admin carga | Bajo | Medio |
| **B1** | `Muestra` + `EventoMuestra` + API recepción/rechazo/toma; integrar con `tomar-muestra` (payload opcional) | Medio | Alto |
| **B2** | FK `muestra` en `ResultadoExamen` + reglas carga; coordinación estados orden ↔ muestras; índices recepción | Medio | Alto |

**Implementación B2 (SYNESIS, mayo 2026):** migración `laboratorio.0004_lims_b2_resultado_muestra`; payload retrocompatible en `cargar-resultados`; validación de muestra en `validar`; sin pasar muestra automáticamente a `EN_PROCESO` al cargar resultado (dejado para refinamiento **B2.1**).
| **B3** | `EstudioMicrobiologia` + siembra + lectura + reglas incubación | Medio | Alto |
| **B4** | Aislados + identificación + significancia/reportable | Medio | Alto |
| **B5** | Antibiograma + `ResultadoAntibiotico` + validaciones completitud | Medio | Alto |
| **B6** | `InformeMicrobiologia` prelim/final + gates + validación + bloqueo edición | Alto (reglas) | Muy alto |
| **B7** | Frontend módulo Laboratorio (órdenes, muestras, micro, informes) | Bajo en backend | Muy alto |
| **B8** | Export PDF, recepción masiva, correcciones versionadas | — | B.2 / C |

**Prioridad explícita usuario:** seguridad clínica → trazabilidad → mínima regresión → compatibilidad Fase A → utilidad real → eficiencia desarrollo → el orden B0–B7 respeta eso (micro informes al final de backend micro).

---

## 14. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Doble verdad EMR `Solicitud` vs LIMS orden | No FK automática en B; documentar integración opcional; no usar `lims_service` URL fija como verdad. |
| Concurrencia recepción doble | `select_for_update` en `Muestra`; código barra unique. |
| Performance listados | Índices compuestos; paginación; `select_related`/`prefetch_related`. |
| Complejidad UI | Entregar por fases B7 con feature flags por rol. |
| Validación doble (orden vs estudio micro) | Documentar flujo: cierre micro no implica automáticamente `VALIDADO` orden hasta servicio de cierre global ordene `validar` cuando todos los componentes (simple + micro) cumplan. |

---

## 15. Recomendación final

1. **Congelar** contrato Fase A en suite de regresión antes del primer merge B1.  
2. Implementar **B0–B2** antes de modelar antibiograma: sin muestra real, la micro en producción es frágil.  
3. **Microbiología** siempre en tablas dedicadas; `ResultadoExamen` como puntero/estado agregado opcional, nunca como almacén de antibiograma.  
4. **Informe final** micro: reglas en **servicio de dominio** (`laboratorio/services/` o app `domain`) con tests unitarios fuertes antes de exponer API pública.  
5. **Frontend** después de B6 estable para no desalinear contratos.  
6. Revisión clínica (bioquímico/microbiólogo) de estados `significancia` y lista “reportable” antes de go-live.

---

## 16. Checklist blueprint (entregable)

- [x] Código funcional no modificado por este documento.  
- [x] Migraciones no creadas.  
- [x] Modelos/endpoints/permisos actuales referenciados.  
- [x] Núcleo + muestra + recepción/rechazo + clínica + micro + informes diseñados.  
- [x] Estados/transiciones/endpoints/permisos/auditoría/tests/fases/riesgos.  
- [x] Fuera de alcance explícito (AP, molecular, toxicología, QC avanzado, equipos, rectificaciones avanzadas).  
- [x] Separación EMR `/solicitudes` vs LIMS nativo reiterada.

---

## 17. Archivos revisados para este blueprint

`docs_synesis/DOC_REGLAS_NEGOCIO.md`, `DOC_MODELOS_DB.md` (si existe contenido laboratorio), `DOC_FRONTEND.md`, `DOC_API_ENDPOINTS.md`, `DOC_BACKEND.md`, `DOC_PERMISOS_AUDITORIA.md`, `DOC_TESTS.md`, `DOC_FLUJOS_LIMS.md`, `DOC_RIESGOS_DEUDA_TECNICA.md`, `laboratorio/models.py`, `laboratorio/serializers.py`, `laboratorio/views.py`, `laboratorio/solicitud_estado.py`, `laboratorio/tests/test_api.py`, `laboratorio/tests/test_models.py`, `api/permissions.py`, `api/urls.py`, `auditoria/audit_service.py`, `auditoria/snapshot.py`, `usuarios/models.py`, `solicitudes/models.py`, `integracion_lims/lims_service.py`, `frontend/src/App.tsx`, `frontend/src/pages/laboratorio/ListaExamenesTest.tsx`, `frontend/src/pages/Solicitudes.tsx` (contexto rutas).

---

## 18. Comandos de verificación ejecutados (análisis; sin alterar código)

```text
emr_env/bin/python manage.py check          → OK (0 issues)
emr_env/bin/python manage.py showmigrations laboratorio → 0001, 0002 aplicadas
```

**Tests:** no re-ejecutados en la sesión de creación de este archivo; último resultado documentado en `DOC_TESTS.md`: **45 passed** con el comando `pytest laboratorio/tests/test_api.py laboratorio/tests/test_models.py usuarios/tests/test_laboratorio_rol.py -q --reuse-db`.
