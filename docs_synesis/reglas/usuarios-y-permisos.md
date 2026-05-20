# Reglas — Usuarios y permisos (Fase C0)

**Versión:** C5.9.1 — 20 de mayo de 2026  
**SoT operativo:** `DOC_PERMISOS_AUDITORIA.md`, `api/permissions.py`, `usuarios/models.py`.

---

## Propósito

Separar **identidad de acceso** (quién entra al sistema) de **autoridad clínica/analítica** (qué puede hacer sobre PHI y estados).

---

## Roles existentes **[IMPLEMENTADO]**

`usuarios.User.rol`:

| Rol | Alcance principal |
|-----|-------------------|
| `admin` | Administración, validación LIMS (`validar`), superusuario operativo |
| `medico` | EMR clínico, órdenes propias, lectura LIMS acotada |
| `secretaria` | Agenda, pacientes, gestión turnos |
| `enfermeria` | EMR clínico acotado (permisos compartidos con médico en varias vistas) |
| `laboratorio` | LIMS nativo: carga, toma, cancelar, entregar; **no** `validar` |
| `paciente` | Portal propio |

Además: **superuser**, **staff**, grupos Django (`Secretarias`, `Médicos`, `Pacientes`).

**[DEUDA]** El rol inexistente `tecnico` fue eliminado de filtros EMR (mayo 2026).

---

## Mínimo privilegio **[RECTOR]**

- Lectura, operación y **validación** son capacidades distintas (ej. `laboratorio` opera pero no valida).
- Anónimos bloqueados en LIMS tras hardening.
- Por defecto DRF: `IsAuthenticated`.

---

## Separación de capacidades

| Capacidad | Roles típicos |
|-----------|----------------|
| Leer catálogo LIMS | admin, laboratorio, medico, secretaria, enfermeria |
| Crear/cargar resultados | admin, laboratorio |
| Validar orden LIMS | admin (+ superuser) |
| Gestionar turnos (crear/modificar) | secretaria, admin/staff; médico y paciente solo propios; enfermería solo lectura (C5.8.1) |
| Cerrar atención | medico, enfermeria, admin |

Detalle: `LimsSolicitudExamenPermission`, `DOC_FLUJOS_LIMS.md`.

---

## Agenda global de turnos **[IMPLEMENTADO]** (C5.7.1)

| Rol / condición | `GET /api/turnos/` |
|-----------------|-------------------|
| superuser, staff, `admin`, `secretaria`, `enfermeria` | Todos los turnos (agenda institucional) |
| `medico` con ficha `Medico` vinculada | Solo turnos donde `medico` = su ficha |
| `medico` sin ficha `Medico` | Lista vacía |
| `paciente` vinculado | Solo sus turnos |
| `laboratorio` y otros roles no contemplados | Lista vacía |

- El query param `?all=true` **no** amplía el alcance de un médico (defensa alineada con `/api/pacientes/`).
- El frontend no envía `all=true` en la carga global de turnos (`DataContext.loadTurnos`).
- **[OBJETIVO]** Permiso explícito (p. ej. coordinación médica / `turnos.ver_agenda_global`) para excepciones auditables sin reabrir bypass por query param.

Implementación: `turnos.views.TurnoViewSet.get_queryset`, tests en `turnos/tests/test_api.py`.

---

## Mutaciones de turnos **[IMPLEMENTADO]** (C5.8.1)

`POST` / `PATCH` / `PUT` en `/api/turnos/` — `TurnoViewSet.perform_create` / `perform_update` (no usa `CanManageTurnos` del router activo).

| Rol | Leer turnos | Crear turnos | Modificar turnos |
|-----|-------------|--------------|------------------|
| superuser / staff | Global | Global | Global |
| `admin` | Global | Global | Global |
| `secretaria` | Global | Global | Global |
| `enfermeria` | Global | No (403) | No (403) |
| `medico` (con ficha) | Propios | Propios (`medico` forzado) | Propios; no reasignar `medico_id` |
| `medico` sin ficha | Vacío | No (403) | No (403) |
| `paciente` vinculado | Propios | Propios (`paciente` forzado) | Propios; no reasignar `paciente_id` |
| `laboratorio` | No | No (403) | No (403) |
| Rol no reconocido | Vacío | No (403) | No (403) |

- `DELETE` físico sigue **405** (cancelar vía `estado`, no borrado).
- Cambio de `estado` por PATCH directo: permitido dentro del turno editable por rol; **[DEUDA]** mover a acciones de negocio (`cancelar`, `confirmar`, etc.).
- Tests: `turnos/tests/test_permissions_mutations.py`, regresión en `turnos/tests/test_api.py`.
- **[DEUDA]** Aplicar `CanManageTurnos` o permiso DRF unificado; código duplicado en `api/views.TurnoViewSet` (no registrado en router).

---

## UI de turnos (frontend) **[IMPLEMENTADO]** (C5.8.2)

Helpers: `frontend/src/utils/turnoPermissions.ts` (`canCreateTurno`, `canEditTurno`, `canDeleteTurno` → siempre `false`).

| Rol | Pantalla `/turnos` | Crear (botón / slot) | Editar formulario |
|-----|-------------------|----------------------|-------------------|
| admin / staff / superuser / secretaria | Agenda global | Sí | Sí (todos) |
| enfermería | Agenda global, banner solo lectura | No | No (modal ver turno) |
| médico | Propios | Sí (médico fijo en modal) | Solo propios |
| paciente | Propios | Sí (paciente fijo) | Solo propios |
| laboratorio | Mensaje sin acceso | No | No |

- **DELETE** no se ofrece en UI (API 405).
- Cambio de **estado** por PATCH en formulario: **[DEUDA]** acciones de negocio (`cancelar`, `confirmar`, etc.).
- Backend sigue siendo fuente de verdad; la UI evita acciones que devolverían 403.

---

## Acciones de estado de turno **[IMPLEMENTADO]** (C5.9.1)

Endpoints activos en `turnos.views.TurnoViewSet`:

| Acción | Ruta | Transición | Roles |
|--------|------|------------|-------|
| Confirmar | `POST /api/turnos/{id}/confirmar/` | `RESERVADO` → `CONFIRMADO` (idempotente si ya confirmado) | admin/staff, secretaría, médico propio |
| Cancelar | `POST /api/turnos/{id}/cancelar/` | `DISPONIBLE`/`RESERVADO`/`CONFIRMADO` → `CANCELADO` (motivo **obligatorio**; idempotente si ya cancelado) | admin/staff, secretaría, médico propio, paciente propio |

- **PATCH/PUT `estado`:** bloqueado para **médico** y **paciente** (400); admin/secretaría pueden PATCH temporalmente **[DEUDA]** unificar solo acciones.
- Auditoría: `log_update` con metadata `accion`, `estado_anterior`, `estado_nuevo`, `turno_id`, `motivo` (cancelar), `view`.
- Servicio: `turnos/turno_estado.py`. Tests: `turnos/tests/test_estado_turnos.py`.
- `REALIZADO` no se cancela; no hay acción `marcar_realizado` en C5.9.1 (sigue vía atención/consulta).

---

## Acceso a PHI por contexto **[RECTOR]**

- Paciente: solo su registro.
- Médico: pacientes atendidos / turnos / consultas (filtros en views).
- Laboratorio: órdenes y muestras de laboratorio, no expediente HC completo por defecto.
- Admin/staff: amplio; uso solo operativo autorizado.

**[DEUDA]** Reglas duplicadas en `get_queryset` vs clases `api/permissions.py`.

---

## Cambios de permisos auditables **[OBJETIVO]**

- Cambio de `rol`, `is_staff`, grupos → `AuditEvent` con actor administrador.
- Revocación de sesión / rotación JWT en incidentes.

---

## Invariantes

Ver `DOC_INVARIANTES.md` (U1–U5).

---

## Pendientes de validación

- [ ] Matriz rol × endpoint crítica actualizada en `DOC_API_ENDPOINTS.md` tras cada fase LIMS.
- [x] Tests de permiso negativo create/patch turnos (C5.8.1).
- [ ] Matriz completa en `DOC_API_ENDPOINTS.md`.
