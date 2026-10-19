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

## Flujo estudios y procedimientos (C6.4 + Etapa A [IMPLEMENTADO])

> SoT diseño: `DOC_DISENO_ESTUDIOS_PROCEDIMIENTOS.md`. Cierres A0–A6. **LIMS intocable.** UI: «Estudios y procedimientos» (`/estudios-complementarios`).

1. Crear `EstudioComplementario` (SOLICITADO, `tipo_actividad=ESTUDIO`); se crea `SesionActividad` `#1`. Altas proc/cirugía/multi **rechazadas**.
2. Programar: `asignar-turno` / `agendar-turno` → turno en sala; sesión `#1` + espejo histórico `estudio.turno`; estado → CONFIRMADO. `sesion_id` opcional (mono = PK real de `#1`).
3. `marcar-realizado` → REALIZADO (dual-write a sesión `#1`); asociar archivos (`ArchivoMedico` mismo paciente).
4. Informe: borrador → `emitir` → INFORMADO → `validar` → VALIDADO → `entregar` → ENTREGADO (visible paciente).
5. `anular` con motivo (mono); conserva vínculo histórico de turno en sesión/espejo.
6. Bandejas listado (A5): pendiente programar / programados / documentación pendiente / pendiente entrega / finalizados / anulados / todos — filtro servidor `bandeja=` + `bandejas-resumen/`.
7. **PATCH:** no cambia `paciente_id` ni `estado` ni campos A2 protegidos.
8. **PDF informe:** `GET …/informes/{id}/download-pdf/`.

**Aún no:** reprogramar/cancelar reserva de estudio (Etapa B); proc/cirugía operativos; multisesión UI/realización por sesión.

No LIMS. No PACS/visor.

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

## Datos demo QA (`seed_data`, jun 2026)

Comando: `python manage.py seed_data` (idempotente; solo desarrollo). Ver `docs/dev-start.md`.

| Artefacto | Clave | Roles útiles |
|-----------|-------|--------------|
| Paciente Demo Uno | `paciente1` | paciente / turno / LIMS |
| Paciente Demo Ajeno | DNI `QA-DEMO-AJENO-01` | aislamiento médico/paciente |
| Turno demo | motivo `QA DEMO TURNO MEDICO1-PACIENTE1` | medico1, admin, secretaria, paciente1 |
| Atención demo | vinculada al turno QA | medico1, admin, enfermeria (lectura) |

Si el paciente demo ya tiene otra atención ambulatoria o de guardia abierta/en
revisión, o una internación activa, el seed conserva esa situación y omite crear
una atención adicional. Informa la omisión y continúa con los datos LIMS. Una
atención ya vinculada al turno QA se reutiliza sin modificarla, incluso finalizada.
No cierra encuentros ni los reasigna al turno demo para forzar la carga.

Sin PHI real. No ejecutar en producción con datos clínicos.

---

## Pendiente de confirmar

- Uso real del `DashboardViewSet` y métricas expuestas.
- Si el frontend unifica `Consulta` HC con `ConsultaAmbulatoria`.
