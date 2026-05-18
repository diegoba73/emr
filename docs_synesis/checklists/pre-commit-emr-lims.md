# Checklist — Pre-commit EMR/LIMS (Fase C0)

**Versión:** C0 — 18 de mayo de 2026  
Usar antes de **cada commit** que toque backend, frontend, migraciones o documentación operativa.

Marcar mentalmente o en descripción de PR; no sustituye CI.

---

## 1. Propósito

- [ ] El commit tiene **un objetivo claro** (fix, fase LIMS, docs, tooling).
- [ ] No mezcla refactors masivos con features no relacionadas.

---

## 2. Regla de negocio

- [ ] Identifiqué la **entidad y transición de estado** afectadas.
- [ ] Consulté `DOC_REGLAS_NEGOCIO.md` y, si aplica, `reglas/*.md` / `DOC_INVARIANTES.md`.
- [ ] No contradigo LIMS ya implementado (Fases A, B1–B4, B3 micro).

---

## 3. PHI

- [ ] No hay DNI, nombres reales, credenciales ni dumps en el diff.
- [ ] Logs y metadata de auditoría sin texto clínico libre innecesario.

---

## 4. Permisos

- [ ] Rol correcto para la acción (ej. solo **admin** en `validar`).
- [ ] `get_queryset` / permission_classes coherentes con `DOC_PERMISOS_AUDITORIA.md`.

---

## 5. Auditoría

- [ ] Mutaciones relevantes llaman `log_create` / `log_update` o capa de estado auditada.
- [ ] Dentro de `atomic()`, eventos vía `on_commit` cuando corresponde.

---

## 6. Estados

- [ ] Transiciones solo por acciones/servicios permitidos (no PATCH estado read-only).
- [ ] Terminales (`CANCELADO`, `VALIDADO`, `INFORMADO`, …) respetados.

---

## 7. Trazabilidad

- [ ] Resultado ligado a orden; muestra coherente si `muestra_id` presente.
- [ ] Muestra rechazada no habilita validación indebida.

---

## 8. Tests

- [ ] Tests nuevos o actualizados para la regla tocada.
- [ ] `pytest` / `manage.py test` en módulo afectado (mínimo).

---

## 9. Regresión

- [ ] Sin romper idempotencia `POST /api/atenciones/`.
- [ ] Sin reabrir `AllowAny` en LIMS.

---

## 10. Riesgo

- [ ] Deuda nueva documentada en `DOC_RIESGOS_DEUDA_TECNICA.md` si es significativa.
- [ ] Migraciones revisadas (solo si el commit las incluye — muchos commits deben **no** llevarlas).

---

## Exclusiones habituales (verificar que no entraron por error)

- `git add .` sin revisión
- `poblar_db`, CSV con PHI, scripts con rutas `/Users/...`
- Cambios en `docs_synesis/` sin alinear SoT
