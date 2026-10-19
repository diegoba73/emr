# Ticket B — Reprogramar y cancelar actividad (estudios)

**Estado:** cerrado (implementado; sin merge ni producción)  

**Depende de:** Etapa A (A0–A6)  
**Restricción:** LIMS intocable. Multi/proc/cirugía off. Sin C+, merge ni producción.

---

## Decisiones cerradas

### 1. Cancelación
| Tema | Decisión |
| --- | --- |
| Semántica | Cancelar actividad previa a realización = **solicitud ANULADA** + reserva vigente **CANCELADA** |
| Camino | Extender `anular` / `anular_estudio` (sin endpoint duplicado) |
| Bloqueo | No anular si estado ∈ `REALIZADO` \| `INFORMADO` \| `VALIDADO` \| `ENTREGADO` \| `ANULADO` |
| Rectificación | `rectificar` / `informar` documental **intacta** (no usa anular) |
| Histórico | Docs, archivos, informes y vínculos **no se borran** |
| Motivo | Obligatorio |
| Fuera de B | “Dejar pendiente de nueva fecha” |

### 2. Historial
| Tema | Decisión |
| --- | --- |
| Ubicación | Tabla en **`estudios/`** — sin campos nuevos en `Turno` |
| Modelo | `HistorialTurnoSesionActividad`: sesión, turno_anterior, turno_nuevo, actor, fecha (`created_at`), motivo |
| FKs | **PROTECT** a sesión y turnos |
| TX | Turno nuevo + cancelar anterior + historial + sync espejo + auditoría **misma TX** |

### 3. Agenda general (P3)
| Tema | Decisión |
| --- | --- |
| Alcance | Turnos vinculados: espejo `estudio_complementario`, `SesionActividad.turno` **y** turnos en `HistorialTurnoSesionActividad` (anterior/nuevo) |
| Acción | Rechazar `cancelar` / `reprogramar` por camino genérico (API turnos + móvil + servicio) |
| Mensaje | Operar desde **Estudios y procedimientos** |
| Bypass | Flag **solo kwarg interno** `desde_modulo_estudios=True` en el servicio de estudios; **no** legible desde body/query API ni móvil |
| Histórico | Consulta de historial/turnos previos **permitida**; solo se bloquean mutaciones genéricas |
| Ajenos | Turnos no vinculados al módulo: comportamiento **sin cambio** |

### 4. Duración y disponibilidad
| Tema | Decisión |
| --- | --- |
| Helper | `estudios/disponibilidad.py` — asignar, agendar y reprogramar |
| Contrato | `inicio`/`fin` con fin > inicio; duración variable **solo** estudios |
| Conservar | Locks, ocupación profesional, excepciones de agenda, buffer sala actual |
| Global | `medicos.agenda.validar_reserva` **intacta** para consultorio / turnos no-estudio |

### 5. Concurrencia
| Tema | Decisión |
| --- | --- |
| Orden | Compatible con existentes: estudio → sesión → turno → médico → recurso (sin inversiones) |
| Reprogram | Excluir reserva propia al validar |
| Fallo | Rollback total; reserva anterior íntegra |
| Tests | Competencia entre **solicitudes distintas** por sala y por profesional |

### 6. Interfaz
| Tema | Decisión |
| --- | --- |
| Reprogramar | Desde detalle del estudio (permisos actuales de asignar turno) |
| Cancelar | Anular con motivo (permisos de escritura actuales) |
| Error | Disponibilidad fallida visible; reserva anterior conservada |
| Completitud | B no está operativo si solo hay endpoints sin UI |

### 7. Alcance y verificación
| Tema | Decisión |
| --- | --- |
| Off | Multisesión / procedimientos / cirugías |
| LIMS | Absolutamente intocable (directa e indirectamente) |
| WIP | Preservar; pruebas B + regresión estudios + FE + comparación A0 |
| No hacer | Corregir fallos preexistentes ajenos; C+; merge; producción |

---

## Pruebas (`estudios/tests/test_b_*.py`)
- Anular → ANULADO + reserva CANCELADA; docs/vínculos conservados
- Rechazo anular post-REALIZADO
- Reprogram OK: historial + turno nuevo + anterior CANCELADO + sync
- Reprogram fallida: reserva anterior intacta
- Conflictos sala / médico (solicitudes distintas)
- Guarda agenda: cancelar/reprogramar genérico rechazado; bypass estudios OK
- Flag `desde_modulo_estudios` no activable por payload/query API ni móvil
- Guarda cubre turnos históricos de `HistorialTurnoSesionActividad` (consulta intacta)
- `test_asignar_turno_estudio_rechaza_sala_ocupada` sobre B: **passed**
- A0: mismos 4 fallos documentados (sin “arreglar”)

Siguiente (solo revisión): `TICKET_C_PROCEDIMIENTOS_NO_QUIRURGICOS.md`.
