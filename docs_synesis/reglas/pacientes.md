# Reglas — Pacientes (Fase C0 / C2)

**Versión:** C2 — 18 de mayo de 2026  
**Estado:** Constitución + auditoría C1 + identidad mínima en creación API.

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
| Auditoría create/update best-effort (`log_create` / `log_update`). | **[IMPLEMENTADO]** — **[DEUDA]** fail-closed |
| `creado_por` / `modificado_por` en modelo. | **[DEUDA]** |
| Soft delete / fusión de duplicados. | **[OBJETIVO]** |
| Estado activo/inactivo formal. | **[OBJETIVO]** |
| Borrado en Django Admin. | **[DEUDA]** |

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
| Borrado accidental en admin Django. | **[RECTOR]** mitigar con política operativa |

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
- [ ] Tests de auditoría en CI.
- [ ] Revisar comandos `pacientes/management/` (no versionados) antes de cualquier commit.
- [ ] Alinear mensajes de error de DNI duplicado con frontend.

---

## Próximo paso recomendado

**C3:** tests de auditoría fail-closed o bloquear DELETE en Django Admin; sin migración hasta limpieza de legacy.
