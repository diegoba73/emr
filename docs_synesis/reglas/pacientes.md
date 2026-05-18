# Reglas — Pacientes (Fase C0)

**Versión:** C0 — 18 de mayo de 2026  
**Estado:** Constitución + checklist de auditoría. **No certifica** cumplimiento total sin revisión de código en cada release.

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
| Búsqueda: numérico → DNI; texto → nombre/apellido con prioridad. | **[IMPLEMENTADO]** `buscar` |
| Admin/secretaría/enfermería: listado amplio; médico: acotado salvo `?all=true`. | **[IMPLEMENTADO]** |
| Paciente solo ve/edita su ficha según `CanUpdatePacienteDemographics`. | **[IMPLEMENTADO]** |
| Alta de paciente vinculada a `User` cuando aplica (`ensure_paciente_linked_to_user` en turnos). | **[IMPLEMENTADO]** |
| Fusión de duplicados con auditoría. | **[OBJETIVO]** |
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
| Borrado accidental en admin Django. | **[RECTOR]** mitigar con política operativa |

---

## Auditoría esperada

| Evento | Estado |
|--------|--------|
| CREATE paciente | **[OBJETIVO]** instrumentar si no está en todas las rutas |
| UPDATE demográficos | **[DEUDA]** verificar cobertura en views |
| Vinculación User ↔ Paciente | **[DEUDA]** |

---

## Pendientes de validación contra código

- [ ] Confirmar `log_create`/`log_update` en todas las rutas de alta/edición de `PacienteViewSet`.
- [ ] Revisar comandos `pacientes/management/` (no versionados) antes de cualquier commit.
- [ ] Alinear mensajes de error de DNI duplicado con frontend.

---

## Próximo paso recomendado

**Auditoría C1 del módulo `pacientes/`** (views, serializers, tests) contra esta hoja de reglas.
