# Reglas — Pacientes (Fase C0 / C2 / C3 / C4 / C5 / C5.2 / C5.3 / C5.4)

**Versión:** C5.4 — 18 de mayo de 2026  
**Estado:** C5 trazabilidad en CRUD + paciente liviano en atenciones e internaciones legacy API.

**SoT operativo:** `DOC_REGLAS_NEGOCIO.md` (sección pacientes), `DOC_MODELOS_DB.md`, `pacientes/views.py`.

---

## Propósito

Garantizar **identidad única y trazable** del sujeto de atención en EMR y LIMS, con acceso proporcional por rol y sin pérdida de historia clínica.

---

## Invariantes (resumen)

Ver `DOC_INVARIANTES.md` (P1–P5). **[RECTOR]**

---

## Reglas

| Regla | Etiqueta |
|-------|----------|
| DNI único en base de datos. | **[IMPLEMENTADO]** |
| **Creación API** exige `dni`, `nombre`, `apellido`, `fecha_nacimiento` (`PacienteSerializer.validate`). | **[IMPLEMENTADO]** C2 |
| BD aún permite `NULL` en nombre/apellido/fecha (pacientes legacy). | **[DEUDA]** migración NOT NULL / limpieza futura |
| PATCH parcial no exige completar identidad legacy vacía. | **[IMPLEMENTADO]** C2 |
| Búsqueda: numérico → DNI; texto → nombre/apellido con prioridad. | **[IMPLEMENTADO]** `buscar` |
| Admin/secretaría/enfermería: listado amplio; médico: acotado; `?all=true` no escala médico. | **[IMPLEMENTADO]** `pacientes.views` |
| Paciente solo ve su ficha vía queryset activo. | **[IMPLEMENTADO]** |
| Alta vinculada a `User` cuando aplica (`ensure_paciente_linked_to_user`). | **[IMPLEMENTADO]** |
| DELETE físico API bloqueado (405). | **[IMPLEMENTADO]** |
| DELETE físico Django Admin bloqueado (`has_delete_permission=False`, sin `delete_selected`). | **[IMPLEMENTADO]** C3 |
| Auditoría CREATE/UPDATE en POST/PATCH/PUT (`log_create` / `log_update`). | **[IMPLEMENTADO]** — tests en `pacientes/tests/test_audit.py` |
| Auditoría fail-closed (fallo de log revierte operación). | **[OBJETIVO]** — no C4 |
| `creado_por` / `modificado_por` en modelo (API activa los setea; read-only en serializer). | **[IMPLEMENTADO]** C5 |
| `Paciente.user` = cuenta portal del paciente; `creado_por` / `modificado_por` = operadores staff. | **[IMPLEMENTADO]** C5 |
| Legacy / admin / shell / commands pueden dejar `creado_por` y `modificado_por` en NULL. | **[IMPLEMENTADO]** C5 |
| Fechas de trazabilidad: `fecha_registro` (creación) y `ultima_actualizacion` (última modificación). | **[IMPLEMENTADO]** — no duplicar campos de fecha |
| Serializers anidados no exponen ficha completa de paciente. | **[IMPLEMENTADO]** C5.2 |
| `/api/atenciones/` embebe paciente con `PacienteLightSerializer` (sin antecedentes ni `user` / provenance). | **[IMPLEMENTADO]** C5.2 |
| `/api/atenciones/` — `turno.paciente` vía `TurnoAtencionNestedSerializer` + `PacienteLightSerializer`. | **[IMPLEMENTADO]** C5.3 |
| `/api/internaciones/` embebe paciente con `PacienteLightSerializer`. | **[IMPLEMENTADO]** C5.4 |
| `/api/turnos/` global (puede seguir usando serializer completo de pacientes). | **[DEUDA]** |
| `api.serializers.PacienteSerializer` con `fields='__all__'` en otros legacy (p. ej. `api.TurnoSerializer`). | **[DEUDA]** |
| Deprecar / eliminar serializer duplicado en `api/serializers.py`. | **[DEUDA]** |
| Backfill opcional de `creado_por` / `modificado_por` en datos históricos. | **[DEUDA]** |
| Auditoría fail-closed (fallo de log revierte operación). | **[OBJETIVO]** — no C4 |
| Soft delete / desactivación (`activo=False`) / fusión de duplicados. | **[OBJETIVO]** |
| Estado activo/inactivo formal. | **[OBJETIVO]** |

---

## Criterios de aceptación (para cambios futuros)

1. Ningún endpoint expone listado global de PHI a rol no autorizado.
2. Crear paciente con DNI existente → error claro (409/400), no segundo registro.
3. PATCH demográfico genera `AuditEvent` con actor y diff sanitizado.
4. Import CSV (si se usa) exige modo dry-run por defecto y no commitear datos reales.

---

## Riesgos

| Riesgo | Etiqueta |
|--------|----------|
| Duplicados por carga manual o CSV sin validación. | **[DEUDA]** |
| `get_queryset` manual diverge de clase de permiso documentada. | **[DEUDA]** |
| Borrado vía shell/ORM directo (fuera API/Admin). | **[DEUDA]** solo política operativa |

---

## Auditoría esperada

| Evento | Estado |
|--------|--------|
| CREATE paciente | **[IMPLEMENTADO]** `perform_create` → `log_create` (best-effort) |
| UPDATE demográficos | **[IMPLEMENTADO]** `perform_update` → `log_update` (best-effort) |
| Vinculación User ↔ Paciente | **[DEUDA]** sin evento dedicado |

---

## Pendientes de validación contra código

- [x] Identidad mínima en POST (C2).
- [x] Sin delete físico en Admin (C3).
- [x] Tests de auditoría CREATE/UPDATE en API (C4).
- [x] Trazabilidad estructural `creado_por` / `modificado_por` (C5) — `pacientes/tests/test_provenance.py`.
- [x] Paciente liviano en `/api/atenciones/` directo y `turno.paciente` (C5.2 / C5.3) — `turnos/tests/test_atenciones_paciente_nested.py`.
- [x] Paciente liviano en `/api/internaciones/` (C5.4) — `historias_clinicas/tests/test_internaciones_paciente_nested.py`.
- [ ] Auditoría fail-closed (fase posterior).
- [ ] Revisar comandos `pacientes/management/` (no versionados) antes de cualquier commit.
- [ ] Alinear mensajes de error de DNI duplicado con frontend.

---

## Próximo paso recomendado

**C6+:** alinear `/api/turnos/` global; deprecar `api.PacienteSerializer` (`__all__`); soft-delete / fusión; fail-closed; NOT NULL tras limpieza legacy.
