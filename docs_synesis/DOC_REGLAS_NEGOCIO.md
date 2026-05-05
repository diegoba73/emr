# DOC_REGLAS_NEGOCIO — Reglas funcionales reales

**Fecha de generación:** 30 de abril de 2026  
**Actualización (hardening mínimo LIMS):** 2 de mayo de 2026  
**Actualización (Fase A — máquina de estados `SolicitudExamen`):** 3 de mayo de 2026  

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
- `PacienteViewSet`: admin/secretaría/enfermería ven todos; médico ve pacientes con turno o consulta con él, o todos con `?all=true`; paciente solo su ficha.
- `buscar`: numérico → DNI icontains; texto → nombre/apellido; orden por prioridad de coincidencia.
- Actualización demográfica: permiso `CanUpdatePacienteDemographics` (médico puede PATCH cualquier paciente según clase).

---

## Reglas de turnos

- Estados: DISPONIBLE, RESERVADO, CONFIRMADO, CANCELADO, REALIZADO.
- Validación: `fecha_hora_fin` > inicio si ambas presentes.
- Paciente al crear/actualizar: debe tener ficha vinculada (`ensure_paciente_linked_to_user`) y no puede cambiar paciente ajeno.
- Médico ve solo sus turnos salvo `?all=true` o ausencia de objeto médico.
- Filtros de calendario: query params `start`, `end`.

---

## Reglas de atenciones

- `AtencionViewSet.create`: requiere ID de turno; usa `AtencionService` modo compat (no altera estado del turno ni crea hijo) vs servicio interno documentado en `AtencionService` que sí cambia turno a REALIZADO y crea registro hijo.
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
- **Fase B2 — muestra opcional:** FK nullable `ResultadoExamen.muestra`; si está definida: misma `SolicitudExamen`, mismo paciente que la orden; no `RECHAZADA`, `DESCARTADA`, ni `CANCELADA` (`clean`). Para **carga** vía API: muestra en **`RECIBIDA`** o **`EN_PROCESO`** únicamente (no `PENDIENTE_TOMA` ni `TOMADA`). Resultados **sin** muestra siguen siendo válidos (compatibilidad histórica hasta política futura).
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

---

## Reglas de auditoría

- `AuditEvent` inmutable; requiere `request_id`, `action`, `entity_type`.
- Middleware provee `request_id` por petición.

---

## Restricciones funcionales

- Secretaría: **sin** acceso a listados de archivos médicos (`queryset.none()`).
- Paciente: turnos y datos acotados a su vínculo.
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
