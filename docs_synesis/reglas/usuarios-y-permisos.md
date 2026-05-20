# Reglas — Usuarios y permisos (Fase C0)

**Versión:** C5.7.1 — 20 de mayo de 2026  
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
| Gestionar turnos | secretaria, admin, médico (propios) |
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
- [ ] Tests de permiso negativo por rol en rutas nuevas.
