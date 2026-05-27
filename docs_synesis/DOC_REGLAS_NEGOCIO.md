# DOC_REGLAS_NEGOCIO — Reglas funcionales reales

**Fecha de generación:** 30 de abril de 2026  
**Actualización (hardening mínimo LIMS):** 2 de mayo de 2026  
**Actualización (Fase A — máquina de estados `SolicitudExamen`):** 3 de mayo de 2026  
**Actualización (Fase B3.1 — Microbiología base):** 13 de mayo de 2026  
**Actualización (Fase B3.2 — Microorganismos / aislados / identificación):** 13 de mayo de 2026  
**Actualización (Fase B3.3 — Antibiograma microbiológico):** 13 de mayo de 2026  
**Actualización (Fase B3.4 — Informes microbiológicos):** 14 de mayo de 2026  

**Alcance:** Reglas inferidas de modelos, serializers, vistas y permisos **existentes**; sin extrapolar funcionalidades no implementadas.

**Fuentes revisadas:** `api/permissions.py`, `pacientes/views.py`, `turnos/views.py`, `turnos/services.py`, `turnos/models.py`, `historias_clinicas/*`, `laboratorio/*` (incl. `laboratorio/solicitud_estado.py`), `solicitudes/*`, `archivos_medicos/views.py`, `usuarios/models.py`.

---

## Resumen general del sistema

Backend clínico con agenda (turnos/recursos), encuentros asistenciales (`Atencion` + registros), historia clínica por paciente (`Consulta` y derivados), catálogos (CIE-10, fármacos, centros, etc.), archivos médicos, internación (dos enfoques en datos), y módulo de laboratorio con órdenes (`SolicitudExamen`), resultados y validación por API. Existe además capa de **solicitudes** genéricas con sincronización opcional a un LIMS HTTP externo.

---

## Módulos existentes

Ver `INSTALLED_APPS` en `synesis/settings.py` y `DOC_BACKEND.md`. Incluye: `core`, `usuarios`, `pacientes`, `medicos`, `emr`, `turnos`, `historias_clinicas`, `catalogos`, `api`, `archivos_medicos`, `integracion_lims`, `solicitudes`, `internacion`, `laboratorio`, `auditoria`.

---

## Roles de usuario detectados

En `usuarios.User.rol`: **paciente**, **medico**, **secretaria**, **enfermeria**, **laboratorio**, **admin**.

- **`laboratorio`:** operador del LIMS nativo (app `laboratorio`): órdenes, toma de muestra (marca de estado), carga de resultados, cancelación, marcar entregado, etiquetas; **no** puede validar órdenes (solo **admin** / superuser). **No** es rol “técnico” legacy ni sustituye enfermería clínica EMR.

Además: **superuser**, **staff** Django, y **grupos** nombrados en permisos (`Secretarias`, `Médicos`, `Pacientes`).

**EMR (mayo 2026):** el string **`tecnico`** (inexistente en `ROL_CHOICES`) fue eliminado de `IsEMRClinician` y de filtros en `api/views.py`. El rol operativo de laboratorio sigue siendo **`laboratorio`** (LIMS), sin formar parte del conjunto “clínico EMR general” de esa clase.

---

## Permisos

- Clases en `api/permissions.py` (secretaría, médico, paciente, gestión turnos, EMR clinician, **LIMS**: `LimsCatalogReadPermission`, `LimsSolicitudExamenPermission`, etc.).
- Muchas reglas están en **`get_queryset`** de ViewSets en lugar de permisos por objeto.
- **LIMS nativo (`laboratorio/views.py`):** ya **no** usa `AllowAny` en ViewSets sensibles; anónimos bloqueados; permisos por rol vía clases anteriores + `get_queryset` para médicos (solo solicitudes con `medico_interno.user` = usuario).

---

## Flujos principales

1. **Paciente** buscado/creado → **Turno** asignado a recurso/médico → **Atención** iniciada (POST con turno) → registros clínicos / documentos.
2. **Consulta** en historia clínica (posible vínculo a turno) → diagnósticos, tratamientos, prescripciones.
3. **Orden de laboratorio** creada en `PENDIENTE` → filas `ResultadoExamen` vacías → opcional `tomar-muestra` (`TOMA_MUESTRA`) → `cargar-resultados` (`EN_PROCESO`) → `validar` (`VALIDADO`, admin) → `marcar-entregado` (`ENTREGADO`) o `cancelar` (`CANCELADO`) desde estados no finales según `DOC_FLUJOS_LIMS.md`.
4. **Solicitud** (`solicitudes`) opcionalmente enviada a LIMS externo si `LIMS_AUTO_SEND=true`.

---

## Reglas de pacientes

- DNI **único** en modelo.
- `PacienteViewSet`: admin/secretaría/enfermería ven todos; médico acotado a relación turno/consulta (`?all=true` no escala); paciente solo su ficha.
- `buscar`: numérico → DNI icontains; texto → nombre/apellido; orden por prioridad de coincidencia.
- Actualización demográfica: permiso `CanUpdatePacienteDemographics` (médico puede PATCH cualquier paciente según clase).

---

## Reglas de turnos

- Estados: DISPONIBLE, RESERVADO, CONFIRMADO, CANCELADO, REALIZADO.
- Validación: `fecha_hora_fin` > inicio si ambas presentes.
- **Lectura** (`GET`): admin/staff/superuser/secretaría/enfermería agenda global; médico solo propios; paciente solo propios; laboratorio/otros vacío (**[IMPLEMENTADO]** C5.7.1).
- **Creación** (`POST`): admin/staff/secretaría global; médico solo con su `Medico` forzado; paciente solo con su ficha forzada; enfermería/laboratorio/rol desconocido → 403 (**[IMPLEMENTADO]** C5.8.1).
- **Modificación** (`PATCH`/`PUT`): misma matriz; médico/paciente no reasignan `medico_id`/`paciente_id` ajenos; enfermería/laboratorio → 403 (**[IMPLEMENTADO]** C5.8.1).
- Paciente: ficha vía `ensure_paciente_linked_to_user`; sin ficha → 403 en mutaciones.
- `?all=true` no escala lectura de médico (C5.7.1).
- DELETE físico: 405; transiciones por acciones `POST` dedicadas (**[IMPLEMENTADO]** C5.9.1 / C5.9.2 / **C5.10.1**): `confirmar`, `cancelar`, `reprogramar`, `marcar-realizado`, `marcar-no-asistio`, **`iniciar-atencion`** (flujo clínico).
- PATCH/PUT directo de `estado`: bloqueado para **todos** los roles (400). Creación: no permitir `REALIZADO` ni `CANCELADO` en POST genérico.
- No asistencia: `marcar-no-asistio` → `CANCELADO` con metadata `marcar_no_asistio` (sin estado `NO_ASISTIO`) **[DEUDA]** campos estructurales.
- Validación serializer: solapamiento, bloqueo de cambios en turno REALIZADO/consulta cargada.
- Filtros de calendario: query params `start`, `end`.

---

## Reglas de atenciones

- **C5.10.1 `iniciar-atencion`:** estados permitidos `RESERVADO`/`CONFIRMADO`; rechaza `CANCELADO`/`DISPONIBLE`; idempotente si ya existe `Atencion` (200, sin duplicar auditoría de alta); si atención existe y turno sigue `CONFIRMADO`, sincroniza a `REALIZADO` y audita turno. Permisos: médico propio; admin/staff/superuser; no secretaría/paciente/enfermería/laboratorio.
- **C5.10.2 `POST /api/atenciones/`:** compat/deprecated (headers HTTP); no altera `Turno.estado`; puede dejar turno `CONFIRMADO` con atención abierta — no usar como inicio clínico en UI. Integraciones externas pueden seguir consumiendo el JSON; migrar a `iniciar-atencion`.
- `marcar-realizado`: no sustituye `iniciar-atencion` (no crea atención).
- Permisos: `IsMedicoOrEnfermeriaOrAdmin`; queryset médico = `medico_principal`; paciente = su paciente.
- Acción **cerrar** para finalizar (detalle en implementación).

---

## Reglas de profesionales (médicos)

- Médico con matrícula única; especialidad opcional.
- Disponibilidad semanal y excepciones con unicidad compuesta.
- Varios filtros de visibilidad: turnos propios, consultas propias, archivos de pacientes atendidos.

---

## Reglas de especialidades

- Catálogo `Especialidad`; FK desde `Medico` y procedimientos `catalogos.Procedimiento`.

---

## Reglas de órdenes (laboratorio)

- `SolicitudExamen`: origen EMR/guardia/externo papel; médico interno o nombre externo; generación de número LAB-YYYY-…
- **`estado`:** no se modifica por `PATCH`/`PUT` del CRUD estándar (`SolicitudExamenSerializer`: `estado` read-only). Los cambios son solo por acciones `POST` dedicadas (`tomar-muestra`, `cargar-resultados`, `validar`, `cancelar`, `marcar-entregado`).
- No cargar resultados si estado `CANCELADO`, `VALIDADO` o `ENTREGADO` (vistas + integridad en modelo resultado).
- **Cancelar:** no borra ni altera filas `ResultadoExamen`; solo pasa la solicitud a `CANCELADO` (permitido aunque existan resultados vacíos autogenerados).
- Al crear: M2M a tipos y paneles; se generan `ResultadoExamen` por tipo (panel expande sin duplicar tipo).

---

## Reglas de muestras

- Catálogo `TipoMuestra`; cada `TipoExamen` exige un tipo de muestra.
- **Fase B1:** entidad **`Muestra`** vinculada a `SolicitudExamen` y `Paciente` (redundante validada en `Muestra.clean`); eventos y transiciones en `laboratorio/muestra_estado.py`.
- La acción de orden `tomar-muestra` (Fase A) sigue siendo **marcador** `PENDIENTE` → `TOMA_MUESTRA`; la toma física es la transaccional **Muestra** (`PENDIENTE_TOMA` → …).

---

## Reglas de determinaciones

- Una fila `ResultadoExamen` por par (solicitud, tipo_examen) — `unique_together`.

---

## Reglas de resultados

- Valor en texto (`valor_obtenido`); bandera `es_patologico`.
- **B4.1 — clínico general estructurado:** `valor_numerico` opcional; `unidad` (payload o `TipoExamen.unidad_default`); snapshots de rango/críticos al cargar; `es_critico` si valor numérico fuera de umbrales críticos del catálogo (`<= crit_min` o `>= crit_max`); `es_patologico` si fuera de `rango_min`/`rango_max` cuando hay rango estructurado. Sin rango suficiente no se recalcula patológico salvo payload explícito. Reglas **no** incluyen edad/sexo, Westgard ni conversión de unidades.
- **Fase B2 — muestra opcional:** FK nullable `ResultadoExamen.muestra` (`PROTECT`); misma solicitud/paciente; no terminales inválidas (`clean`). **Carga** con `muestra_id`: estados **`RECIBIDA`**, **`CONSERVADA`** o **`EN_PROCESO`**; primer vínculo desde RECIBIDA/CONSERVADA → **`EN_PROCESO`** + `EventoMuestra.PROCESAMIENTO`. No rechazar muestra con resultados asociados. No cambiar `muestra` en resultado **validado**. Legacy sin muestra sigue válido.
- **Fase B2-B — obligatoriedad progresiva:** `TipoExamen.requiere_muestra` (default `False`). Si `requiere_muestra=True`, `POST …/cargar-resultados/` exige `muestra_id` efectivo (payload o FK previa); sin muestra → **400** (`"Este tipo de examen requiere una muestra asociada."`). Si hay muestra y el catálogo define `tipo_muestra_requerida`, `muestra.tipo_muestra` debe coincidir; si no → **400** (`"La muestra no corresponde al tipo requerido para este examen."`). Tipos con `requiere_muestra=False` mantienen carga legacy sin `muestra_id`. Fallos no crean resultado/auditoría de éxito ni `EventoMuestra.PROCESAMIENTO`.
- **Fase B2-A — auditoría:** `AuditEvent` de resultados y muestras (B1/B2) **no** incluye `codigo_barra` en metadata; `safe_model_snapshot(ResultadoExamen)` redacta valores clínicos (`valor_obtenido`, `valor_numerico`, `unidad`, rangos snapshot, `observaciones`). La API de lectura autorizada sigue exponiendo valores clínicos.
- **Pendiente de carga:** `valor_obtenido` puede estar **vacío** en modelo (`blank=True`, `default=''`) al crear filas `ResultadoExamen`; eso **no** autoriza validar la orden incompleta: la acción `validar` sigue rechazando si queda algún resultado con valor vacío. Con muestra vinculada, `validar` además rechaza si la muestra quedó en estados incompatibles (listado en `DOC_FLUJOS_LIMS.md`).
- Carga masiva vía acción `cargar-resultados` con transacción y bloqueo de solicitud; no modificar si orden está en `VALIDADO`, `CANCELADO` o `ENTREGADO`.
- Validación de orden: solo desde **`EN_PROCESO`**; no permitir validar con valores vacíos; asigna usuario y fecha a resultados. Solo rol **admin** (y superuser) puede ejecutar `validar`; rol **laboratorio** puede tomar muestra, cargar, cancelar y marcar entregado, pero **no** validar.
- **Entrega:** `marcar-entregado` solo desde **`VALIDADO`**; no genera PDF.

---

## Reglas de validación técnica

- No separadas explícitamente del resto: el paso `validar` aglutina control de completitud y cierre de orden.

---

## Reglas de validación profesional / bioquímica

- **No detectado** como rol o estado distinto en el código analizado; un solo estado `VALIDADO` y usuario validador.

---

## Reglas de informes

- **No detectado** generador de informe PDF oficial; etiqueta ZPL como JSON y datos en API.

---

## Reglas de estados (laboratorio)

Valores de modelo: `PENDIENTE`, `TOMA_MUESTRA`, `EN_PROCESO`, `VALIDADO`, `ENTREGADO`, `CANCELADO`.

Transiciones implementadas (Fase A): ver tabla en **`DOC_FLUJOS_LIMS.md`** (incluye `PENDIENTE`/`TOMA_MUESTRA` → `EN_PROCESO` por carga, `VALIDADO` → `ENTREGADO`, cancelación desde no finales). Terminales: **`CANCELADO`**, **`ENTREGADO`**.

**No implementado (sigue pendiente):** validación técnica vs profesional como estados distintos; informe PDF final; vinculación **obligatoria** `ResultadoExamen`↔`Muestra` para órdenes nuevas; transición automática de muestra `RECIBIDA`→`EN_PROCESO` al cargar resultado; microbiología/QC avanzado.

**Implementado (Fase B1):** entidad **`Muestra`** (material físico) vinculada a `SolicitudExamen` y `TipoMuestra`; **`EventoMuestra`**; catálogos **`AreaLaboratorio`**, **`SeccionLaboratorio`**, **`TipoContenedor`**. Cambios de estado de muestra **solo** por acciones POST dedicadas; `PATCH` no altera `estado`. Recepción solo desde **`TOMADA`** (sin recepción directa desde `PENDIENTE_TOMA` en esta fase). Rechazo exige **motivo**. Auditoría y eventos por acción.

**Implementado (Fase B2):** FK opcional **`ResultadoExamen.muestra`** (`PROTECT`); reglas de carga y validación coordinadas con estados de muestra; migración **`0004_lims_b2_resultado_muestra`**.

**Implementado (Fase B3.1 — microbiología base):** modelos `MedioCultivo`, `EstudioMicrobiologia`, `SiembraMicrobiologia`, `LecturaCultivo`; flujo Solicitud → Muestra (`RECIBIDA`/`EN_PROCESO`) → Estudio → Siembra → Lectura; estados cableados del estudio (`PENDIENTE`/`RECIBIDO`/`SEMBRADO`/`LECTURA_PRELIMINAR`/`CANCELADO`); cambios de estado solo por acciones (`iniciar`, `cancelar`) o transiciones automáticas en creación de siembra/lectura; cancelación con motivo obligatorio; medios se desactivan (no se borran); microbiología **no** se serializa en `ResultadoExamen.valor_obtenido`; migración **`0005_lims_b3_1_microbiologia_base`**.

**Implementado (Fase B3.2 — microorganismos, aislados, identificación):** modelos `Microorganismo`, `AisladoMicrobiologico`, `IdentificacionMicroorganismo`; flujo `LecturaCultivo → AisladoMicrobiologico → IdentificacionMicroorganismo`. Aislado: estados cableados `SOSPECHADO` (default) / `IDENTIFICADO` (auto al crear primera identificación válida) / `DESCARTADO` (acción `descartar` con motivo). Estudio: nuevo choice cableado `IDENTIFICACION` (auto desde `SEMBRADO` o `LECTURA_PRELIMINAR` al crear identificación). Identificación es append-only (sin PATCH/DELETE). `requiere_antibiograma` queda registrado pero **no** crea antibiograma en B3.2. Microorganismos: catálogo administrativo (escritura solo admin); se desactiva con `activo=False`; no se permite identificar con microorganismo inactivo. Microbiología sigue fuera de `ResultadoExamen.valor_obtenido`. Migración **`0006_lims_b3_2_microbiologia_aislados`** (aditiva: 3 modelos nuevos + `AlterField` no destructivo sobre `EstudioMicrobiologia.estado`).

**Implementado (Fase B3.3 — antibiograma microbiológico):** modelos `Antibiotico`, `Antibiograma`, `ResultadoAntibiotico`; flujo `AisladoMicrobiologico (IDENTIFICADO) → Antibiograma → ResultadoAntibiotico`. Antibiograma: estados cableados `PENDIENTE` (default) / `EN_PROCESO` (auto al cargar primer resultado válido) / `COMPLETO` (acción `completar`, requiere ≥1 resultado, setea `fecha_resultado`) / `CANCELADO` (acción `cancelar` con motivo obligatorio). Reglas de creación: solo sobre aislado `IDENTIFICADO` con microorganismo asignado y estudio no `CANCELADO`; bloqueado para `SOSPECHADO`/`DESCARTADO`. Resultados: par `(antibiograma, antibiotico)` único por `UniqueConstraint`; antibiótico debe estar `activo`; carga/edición bloqueada si antibiograma `COMPLETO`/`CANCELADO`; interpretaciones permitidas `S`/`I`/`R`/`SDD`/`NO_APLICA`. Estudio: nuevo choice cableado `ANTIBIOGRAMA` (auto desde `IDENTIFICACION`, `LECTURA_PRELIMINAR` o `SEMBRADO` al crear antibiograma o primer resultado). Antibióticos: catálogo administrativo (escritura solo admin); se desactiva con `activo=False`; sin destroy. PATCH limitado: antibiograma solo `metodo`/`observaciones`; resultado solo `halo_mm`/`mic`/`interpretacion`/`observaciones` (sin cambiar `antibiograma`/`antibiotico`). Microbiología sigue fuera de `ResultadoExamen.valor_obtenido`. Migración **`0007_lims_b3_3_microbiologia_antibiograma`** (aditiva: 3 modelos nuevos + `AlterField` no destructivo sobre `EstudioMicrobiologia.estado` + `UniqueConstraint`).

**Implementado (Fase B3.4 — informes microbiológicos):** modelo `InformeMicrobiologia` (`PRELIMINAR`/`FINAL`; estados `BORRADOR`/`EMITIDO`/`VALIDADO`/`ANULADO`); a lo sumo un `FINAL` no `ANULADO` por estudio. Completitud para informe final (`verificar_completitud_para_informe_final`): ≥1 `LecturaCultivo`; aislados `DESCARTADO` ignorados; `SOSPECHADO` bloquea salvo significancia `CONTAMINANTE` o `FLORA_HABITUAL`; `IDENTIFICADO` con `requiere_antibiograma` exige antibiograma en `COMPLETO`. Servicios: `crear_informe_borrador`, `actualizar_informe_borrador`, `aplicar_emitir_informe` (texto no vacío al emitir; `FINAL` emitido → estudio `LISTO_PARA_VALIDAR`), `aplicar_validar_informe_final` (solo admin: `FINAL` `EMITIDO` + estudio `LISTO_PARA_VALIDAR` → informe y estudio `VALIDADO`; setea `fecha_cierre` del estudio si vacía), `aplicar_anular_informe` (motivo obligatorio; solo `BORRADOR`/`EMITIDO`, no `VALIDADO`), `aplicar_marcar_estudio_informado` (estudio `VALIDADO` + existe `FINAL` `VALIDADO` → `INFORMADO`). Anular un `FINAL` `EMITIDO` deja el estudio en `LISTO_PARA_VALIDAR` hasta un nuevo `FINAL` emitido. PATCH de informe solo en `BORRADOR`. Migración **`0008_lims_b3_4_microbiologia_informes`**. Sigue **fuera** de alcance: PDF, frontend dedicado, integración LIMS externa, QC/equipamiento avanzado.

---

## Reglas de auditoría

- `AuditEvent` inmutable; requiere `request_id`, `action`, `entity_type`.
- Middleware provee `request_id` por petición.

---

## Restricciones funcionales

- Secretaría / enfermería / laboratorio: **sin** archivos clínicos (`ArchivoMedico`, `Documento`) en C6.2.
- Secretaría: **sin** acceso a listados de archivos médicos (`queryset.none()`).
- Paciente: turnos y datos acotados a su vínculo; archivos propios; documentos de sus atenciones (lectura/descarga).
- **C6.2 [IMPLEMENTADO]:** APIs no exponen URL `/media/`; descarga vía `…/download/`; DELETE → 405; auditoría create/update/download. Detalle: `reglas/documentos-e-imagenes.md`.
- **C6.4.1 [IMPLEMENTADO]:** `estudios.EstudioComplementario` — estados por acciones POST; informes versionados; archivos vía `ArchivoEstudioComplementario` → `ArchivoMedico`; paciente solo ve **ENTREGADO**; sin LIMS.
- **C6.4.1-A:** `paciente_id` inmutable por PATCH; informes alineados a estados (crear/emitir desde REALIZADO+; validar solo INFORMADO); un informe vigente validado por estudio.
- **C6.4.1-B:** rectificación desde ENTREGADO puede emitirse (`ENTREGADO→INFORMADO` solo vía `permitir_reapertura_por_rectificacion` en servicio de emisión de rectificación).
- **C6.4.3:** máximo un informe `es_vigente=True` por estudio (constraint `uniq_informe_vigente_por_estudio`); PDF de informe solo por endpoint protegido; nombre de descarga generado; sin URL `/media/` ni `archivo_pdf.url` en API; paciente descarga PDF solo en ENTREGADO con informe validado vigente.
- Médico — archivos: pacientes vinculados por `Consulta` HC, `Atencion` o `Turno` (no solo HC legacy).
- Resultados: no editar orden validada vía acción de carga.

---

## Casos borde detectados

- Médico sin registro `Medico` asociado: queryset de turnos puede abrirse a todos o none según rama (`ObjectDoesNotExist`). En LIMS, médico sin vínculo `Medico` ve **ninguna** solicitud de examen (filtro vacío).
- Login devuelve `rol` en mayúsculas; otras rutas usan minúsculas en modelo — clientes deben normalizar.

---

## Comportamientos que no deben romperse

- **Idempotencia** `POST /api/atenciones/` con mismo turno ya atendido.
- **Unicidad** DNI paciente y matrícula médico.
- **Append-only** auditoría.
- **PROTECT** en catálogos referenciados por historia (medicamentos, tipos de examen con resultados).

---

## Inconsistencias o reglas implícitas encontradas

- Dos conceptos de consulta: `historias_clinicas.Consulta` vs `ConsultaAmbulatoria` ligada a `Atencion`.
- Dos internaciones y dos camas (ver `DOC_MODELOS_DB.md`).
- `solicitudes.Solicitud.get_queryset`: comparación `rol_upper == 'ADMIN'` mientras el modelo usa `'admin'` — riesgo de lógica incorrecta para usuarios que no pasan por `is_superuser`.
- ~~`IsEMRClinician` y string `tecnico`~~ — corregido; ver roles arriba.

---

## Riesgos o inconsistencias

Ver sección anterior y `DOC_RIESGOS_DEUDA_TECNICA.md`.

---

## Pendiente de confirmar

- Reglas exactas de `DashboardViewSet` y transiciones `TOMA_MUESTRA` / `ENTREGADO`.
- Si existe workflow de informe legal aparte de la API.
