# DOC_FLUJOS_EMR — Flujos clínicos

**Fecha de generación:** 30 de abril de 2026  

**Alcance:** Flujos implementados en backend para práctica clínica ambulatoria e internación según modelos y vistas.

**Fuentes revisadas:** `turnos/models.py`, `turnos/services.py`, `turnos/views.py`, `historias_clinicas/*`, `emr/models.py`, `archivos_medicos/*`, `pacientes/views.py`.

---

## Flujo de pacientes

1. **Registro de ficha:** modelo `pacientes.Paciente` (DNI único); usuario opcional `OneToOne` a `User`.
2. **API:** `PacienteViewSet` — listado filtrado por rol (admin/secretaría/enfermería todo; médico acotado por relación; `?all=true` no escala; paciente solo su id).
3. **Búsqueda:** `GET /api/pacientes/buscar/?q=` — numérico → DNI; texto → nombre/apellido.
4. **Vinculación usuario–paciente:** `ensure_paciente_linked_to_user` usado en turnos para rol paciente.

---

## Flujo de turnos

1. **Recurso:** `Recurso` (ubicación CEHTA/ICPL, tipo consultorio/sala/quirófano).
2. **Turno:** estados `DISPONIBLE`, `RESERVADO`, `CONFIRMADO`, `CANCELADO`, `REALIZADO`. Acciones POST C5.9.2: confirmar, cancelar, reprogramar, marcar-realizado, marcar-no-asistio (`turnos/turno_estado.py`). `REALIZADO` ideal vía atención/consulta.
3. **Validación modelo:** `clean`/`save` en `Turno` — fin > inicio.
4. **API:** `TurnoViewSet` (`turnos.views`) — lectura por rol (C5.7.1); creación/modificación por matriz (C5.8.1); PATCH/PUT `estado` bloqueado para todos; filtros `start`/`end`; DELETE 405.
5. **Disponibilidad/excepción:** `DisponibilidadMedico`, `ExcepcionMedico` expuestos vía `api/views.py` registrados en router.

---

## Flujo de atenciones

1. **Creación desde API:** `POST /api/atenciones/` con `turno` (ID) — delega en `AtencionService.iniciar_atencion_desde_turno(..., api_post_compat=True)`.
2. **Comportamiento modo API (compat):** si ya existe `Atencion` para el turno, **devuelve la existente** (idempotente); **no** cambia estado del turno ni crea registro hijo en este modo (según docstring del servicio).
3. **Modo servicio completo** (`api_post_compat=False`): exige turno `RESERVADO`/`CONFIRMADO`, pasa a `REALIZADO`, crea `Atencion` y registro hijo según tipo de recurso (`ConsultaAmbulatoria`, `RegistroProcedimiento`, `RegistroQuirurgico`).
4. **Cierre:** acción `cerrar` en `AtencionViewSet` (detalle en código; no expandido aquí).
5. **Permisos:** `IsMedicoOrEnfermeriaOrAdmin`; queryset limita por médico principal o paciente.

**Riesgo de trazabilidad:** dos modos de iniciar atención con efectos distintos en turno — fácil confundir si el cliente llama solo al ViewSet.

---

## Flujo de evolución clínica

- **`Consulta` (historias_clinicas):** vinculada a `HistoriaClinica` y opcionalmente a `Turno` (`OneToOne`).
- **`ConsultaAmbulatoria` (turnos):** ligada 1:1 a `Atencion` — paralelo al modelo “consulta de HC”; **coexisten dos conceptos de “consulta”**.

---

## Flujo de diagnósticos / procedimientos

- **Por consulta HC:** `Diagnostico` con CIE-10 opcional, `Tratamiento`, `Prescripcion` (catálogo `Medicamento`).
- **Por atención (turnos):** `RegistroProcedimiento`, `RegistroQuirurgico` con catálogos `EstudioDiagnostico`, `ProcedimientoCatalogo`.
- **API agregada:** `DiagnosticoViewSet`, `PrescripcionViewSet`, `ConsultaAmbulatoriaViewSet`, etc. bajo prefijo `/api/` desde `api/views.py`.

---

## Flujo de documentos clínicos

1. **`emr.Documento`:** archivo por `Atencion`, tipos INFORME, ESTUDIO, etc. — `DocumentoViewSet` en `api/views.py`.
2. **`archivos_medicos.ArchivoMedico`:** archivo por paciente y opcionalmente `Consulta`; reglas de visibilidad estrictas por rol (secretaría: sin acceso).

---

## Estados (EMR ambulatorio)

| Entidad | Estados relevantes |
|---------|-------------------|
| Turno | DISPONIBLE → … → REALIZADO / CANCELADO |
| Atencion | ABIERTA, FINALIZADA, EN_REVISION |
| Internación (historias_clinicas) | ACTIVA, ALTA_*, etc. |
| Internación (internacion app) | activo + estado de cama |

---

## Acciones permitidas (resumen)

- Depende de **rol** y **queryset** en cada ViewSet; no hay matriz única centralizada en código.

---

## Roles involucrados

Paciente, médico, secretaría, enfermería, admin (+ staff/superuser en varios caminos).

---

## Eventos auditables

- Turnos: create/update/delete con `log_*`.
- Laboratorio y solicitudes: ver `DOC_FLUJOS_LIMS` y `solicitudes`.
- `AuditEvent` genérico para muchas mutaciones.

---

## Validaciones

- Modelo `Turno`, `Solicitud` (fechas), `Internacion` (historias) con `numero_internacion` autogenerado.
- Paciente debe tener HC al crear `Consulta` (`get_or_create` en `ConsultaViewSet.perform_create`).

---

## Riesgos de seguridad o trazabilidad

- Dos flujos de consulta/atención pueden generar **duplicación semántica** en historial.
- **Dos modelos de internación** — riesgo de reportes inconsistentes.
- Archivos médicos: reglas en queryset; comprobar **descarga** alinear con listado.

---

## Riesgos o inconsistencias

- `AtencionService` modo API vs modo interno: documentar en runbooks operativos.
- `HistoriaClinicaViewSet` es read-only; escritura va por `Consulta`.

---

## Pendiente de confirmar

- Uso real del `DashboardViewSet` y métricas expuestas.
- Si el frontend unifica `Consulta` HC con `ConsultaAmbulatoria`.
