# DOC_INVARIANTES — Invariantes del dominio (Fase C0)

**Versión:** C0 — 18 de mayo de 2026  
**Leyenda:** **[RECTOR]** | **[IMPLEMENTADO]** | **[OBJETIVO]** | **[DEUDA]** incumplimiento parcial conocido

Cada invariante debe poder verificarse por tests, reglas de modelo o política documentada.

---

## Pacientes

| ID | Invariante | Estado |
|----|------------|--------|
| P1 | DNI único en `Paciente`. | **[IMPLEMENTADO]** |
| P2 | Paciente con historia clínica u órdenes no se elimina físicamente sin proceso controlado. | **[RECTOR]** — delete no es flujo estándar |
| P3 | Usuario `rol=paciente` accede solo a su ficha (salvo staff). | **[IMPLEMENTADO]** con filtros en views |
| P4 | No existen dos pacientes “oficiales” para el mismo DNI. | **[IMPLEMENTADO]** DB; **[DEUDA]** duplicados por error de carga CSV |
| P5 | Fusión de pacientes preserva trazabilidad. | **[OBJETIVO]** |

---

## Usuarios y permisos

| ID | Invariante | Estado |
|----|------------|--------|
| U1 | Mínimo privilegio por rol. | **[RECTOR]** — **[DEUDA]** dispersión en `get_queryset` |
| U2 | Rol `laboratorio` no valida órdenes LIMS (`validar` solo admin). | **[IMPLEMENTADO]** |
| U3 | Rol `laboratorio` no sustituye clínico EMR en `IsEMRClinician`. | **[IMPLEMENTADO]** |
| U4 | Cambios de permisos/rol sensibles auditables. | **[OBJETIVO]** parcial |
| U5 | Ningún acceso a PHI fuera de permiso y contexto de objeto. | **[RECTOR]** — revisión continua |

---

## Atenciones

| ID | Invariante | Estado |
|----|------------|--------|
| A1 | Una `Atencion` por `Turno` (OneToOne). | **[IMPLEMENTADO]** |
| A2 | `POST /api/atenciones/` idempotente por turno (200 vs 201). | **[IMPLEMENTADO]** `api_post_compat` |
| A3 | Datos de paciente/médico en alta vienen del turno, no inventados por cliente. | **[IMPLEMENTADO]** servicio |
| A4 | Cierre explícito antes de tratar encuentro como finalizado. | **[IMPLEMENTADO]** `cerrar` |
| A5 | No dos “consultas” canónicas sin vínculo (HC vs ambulatoria). | **[DEUDA]** |

---

## Órdenes

| ID | Invariante | Estado |
|----|------------|--------|
| O1 | Estado de `SolicitudExamen` solo vía acciones dedicadas, no PATCH CRUD. | **[IMPLEMENTADO]** |
| O2 | Número de protocolo único. | **[IMPLEMENTADO]** |
| O3 | Al crear orden LIMS, existen filas `ResultadoExamen` por tipo solicitado. | **[IMPLEMENTADO]** |
| O4 | Cancelar orden no borra resultados; marca `CANCELADO`. | **[IMPLEMENTADO]** |
| O5 | Orden EMR (`solicitudes`) y orden LIMS nativa son trazables por separado. | **[DEUDA]** sin FK única |

---

## Muestras

| ID | Invariante | Estado |
|----|------------|--------|
| M1 | Muestra pertenece a la misma solicitud y paciente (validación `clean`). | **[IMPLEMENTADO]** |
| M2 | Muestra `RECHAZADA` / `DESCARTADA` / `CANCELADA` no permite validar orden con resultados que la referencian. | **[IMPLEMENTADO]** en `validar` |
| M3 | Transición de muestra genera `EventoMuestra` auditable. | **[IMPLEMENTADO]** |
| M4 | Toda muestra analizada tiene trazabilidad a orden. | **[IMPLEMENTADO]** |

---

## Resultados

| ID | Invariante | Estado |
|----|------------|--------|
| R1 | Un resultado por (orden, tipo_examen). | **[IMPLEMENTADO]** |
| R2 | No cargar resultados en orden `CANCELADO` / `VALIDADO` / `ENTREGADO`. | **[IMPLEMENTADO]** |
| R3 | No validar con valores vacíos. | **[IMPLEMENTADO]** |
| R4 | Resultado validado no se edita directamente sin política de corrección. | **[RECTOR]** — **[DEUDA]** no hay API “corregir” |
| R5 | `muestra_id` en carga debe ser de la misma orden y estados admitidos. | **[IMPLEMENTADO]** B2 |

---

## Informes

| ID | Invariante | Estado |
|----|------------|--------|
| I1 | Informe micro FINAL validado conserva historial; anulación explícita. | **[IMPLEMENTADO]** B3.4 |
| I2 | Informe emitido no se sobrescribe silenciosamente. | **[RECTOR]** — micro; **[OBJETIVO]** PDF general |
| I3 | Preliminar ≠ final en microbiología. | **[IMPLEMENTADO]** |

---

## Auditoría

| ID | Invariante | Estado |
|----|------------|--------|
| AUD1 | `AuditEvent` append-only en ORM. | **[IMPLEMENTADO]** |
| AUD2 | Eventos dentro de `atomic()` persisten en `on_commit`. | **[IMPLEMENTADO]** |
| AUD3 | Snapshots sin secretos ni binarios crudos. | **[IMPLEMENTADO]** sanitizer |
| AUD4 | Toda transición crítica de orden/muestra deja rastro. | **[IMPLEMENTADO]** parcial |

---

## IA

| ID | Invariante | Estado |
|----|------------|--------|
| IA1 | IA no valida resultados ni firma informes. | **[RECTOR]** — **[OBJETIVO]** enforcement |
| IA2 | Sugerencias marcadas como no definitivas. | **[OBJETIVO]** |
| IA3 | Aceptación/rechazo registra usuario humano. | **[OBJETIVO]** |
| IA4 | IA no eleva permisos ni accede PHI fuera de política. | **[RECTOR]** |
