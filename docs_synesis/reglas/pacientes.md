# Reglas — Pacientes (Fase C0 / C2 / C3 / C4)

**Versión:** C4 — 18 de mayo de 2026  
**Estado:** C2 identidad mínima + C3 sin delete Admin + C4 auditoría verificada en tests.

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
| `creado_por` / `modificado_por` en modelo. | **[DEUDA]** |
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
- [ ] Auditoría fail-closed (fase posterior).
- [ ] Revisar comandos `pacientes/management/` (no versionados) antes de cualquier commit.
- [ ] Alinear mensajes de error de DNI duplicado con frontend.

---

## Próximo paso recomendado

**C5:** soft-delete (`activo`) o fusión de duplicados; fail-closed de auditoría solo si negocio lo exige; migración NOT NULL tras limpieza legacy.
