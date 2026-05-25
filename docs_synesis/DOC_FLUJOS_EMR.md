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
2. **Turno:** estados `DISPONIBLE`, `RESERVADO`, `CONFIRMADO`, `CANCELADO`, `REALIZADO`. Acciones POST C5.9.2: confirmar, cancelar, reprogramar, marcar-realizado, marcar-no-asistio. **C5.10.1:** `iniciar-atencion` — flujo clínico real (crea/obtiene `Atencion`, pasa turno a `REALIZADO`, registro hijo). `marcar-realizado` = operación administrativa/excepción (no crea atención).
3. **Validación modelo:** `clean`/`save` en `Turno` — fin > inicio.
4. **API:** `TurnoViewSet` (`turnos.views`) — lectura por rol (C5.7.1); creación/modificación por matriz (C5.8.1); PATCH/PUT `estado` bloqueado para todos; filtros `start`/`end`; DELETE 405.
5. **Disponibilidad/excepción:** `DisponibilidadMedico`, `ExcepcionMedico` expuestos vía `api/views.py` registrados en router.

---

## Flujo de atenciones

1. **Flujo clínico activo (C5.10.1):** `POST /api/turnos/{id}/iniciar-atencion/` — `AtencionService.iniciar_atencion_clinica_desde_turno`; auditoría en `TurnoViewSet.iniciar_atencion`. Frontend médico (`TurnoModal`) usa esta acción.
2. **Compat/deprecated (C5.10.2):** `POST /api/atenciones/` — preservado; headers `Deprecation`, `X-Synesis-Deprecated-Endpoint`, `X-Synesis-Replacement-Endpoint`, `Warning` (299); **no** mueve turno ni crea hijo; JSON sin cambios. **[DEUDA]** retiro cuando no queden clientes legacy.
3. **Modo servicio completo legacy** (`api_post_compat=False` en `iniciar_atencion_desde_turno`): no idempotente; usado en tests; no enrutado en router principal.
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

## Flujo de documentos clínicos (C6.2 [IMPLEMENTADO])

1. **`emr.Documento`:** adjunto por `Atencion`; upload POST; lectura/descarga autenticada (`download`); sin eliminación física (405). Secretaría/enfermería/laboratorio sin acceso.
2. **`archivos_medicos.ArchivoMedico`:** adjunto por `Paciente` (+ opcional `Consulta` HC); médico ve pacientes vinculados por consulta HC, **atención** o **turno**; paciente solo propios; descarga auditada; DELETE → 405.

Ver `reglas/documentos-e-imagenes.md`.

## Flujo estudios complementarios (C6.4.1 [IMPLEMENTADO — solo backend])

1. Crear `EstudioComplementario` (SOLICITADO) vinculado a paciente (+ opcional atención/consulta/solicitud EMR).
2. `marcar-realizado` → REALIZADO; asociar archivos (`ArchivoMedico` del mismo paciente).
3. Informe: tras `marcar-realizado`, crear borrador → `emitir` → INFORMADO → `validar` (admin) → VALIDADO → `entregar` → ENTREGADO (visible paciente). No crear/emitir/validar en SOLICITADO (C6.4.1-A).
4. `anular` desde SOLICITADO/REALIZADO/INFORMADO con motivo.
5. Rectificación (estudio VALIDADO/ENTREGADO): nuevo borrador no vigente → emitir (INFORMADO; desde ENTREGADO usa reapertura controlada C6.4.1-B) → validar (único vigente) → `entregar` si vuelve a ENTREGADO.
6. **PATCH:** no cambia `paciente_id` ni `estado`.
7. **PDF informe (C6.4.3):** tras validar y entregar, paciente (o clínico autorizado) descarga PDF vía `GET …/informes/{id}/download-pdf/` — nombre seguro, auditoría `estudio_informe_pdf_download`; constraint DB garantiza un solo informe vigente.

No LIMS. No PACS/visor. **Frontend C6.4.2 [IMPLEMENTADO]:** listado, detalle, acciones e informes en `/estudios-complementarios` (descarga PDF informe: endpoint backend listo; UI puede adoptar `download_pdf_url` en fase posterior).

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
