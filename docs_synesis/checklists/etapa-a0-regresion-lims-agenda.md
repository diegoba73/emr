# Checklist A0 — Regresión LIMS + agenda (Etapa A)

**SoT diseño:** `DOC_DISENO_ESTUDIOS_PROCEDIMIENTOS.md`  
**Cierre:** `docs_synesis/CIERRE_ETAPA_A0_A1.md`  
**Estado A0:** *Verificación comparativa completada, sin nuevas regresiones detectadas en las suites ejecutadas; cuatro fallos preexistentes documentados.*  
**Regla:** no modificar `laboratorio/` ni alterar comportamiento LIMS vía dependencias compartidas. No cambiar permisos/expectativas de turnos para conseguir verde.

Usar **antes y después** de merges de Etapa A (A1+). Marcar resultados en la descripción del PR / informe de implementación.

---

## 1. Diff LIMS

- [x] **A0+A1 no tocó `laboratorio/`** (ningún archivo LIMS en el diff de este ticket).
- [ ] Working tree local **sí** tiene WIP previo bajo `laboratorio/` (listado/IQC) **ajeno** a A0+A1 — no mezclar en el PR de Etapa A.
- [x] Sin cambios en `DOC_FLUJOS_LIMS.md` por A0+A1.

## 2. Pruebas existentes — LIMS (referencia)

Ejecutar en Docker/local (ej. `docker exec emr_backend`):

```bash
python manage.py test laboratorio.tests.test_lims_flujo_critico -v1 --keepdb
```

Opcional acotado (autorización básica):

```bash
python manage.py test laboratorio.tests.test_api.TestLimsAuthorization -v1 --keepdb
```

**Comparativa aislada 2026-10-16** (worktrees `emr-wt-base` / `emr-wt-a01` / `emr-wt-wip`; detalle en `/home/diego/proyectos/emr-a0-compare-artifacts/COMPARATIVA_A0.md`):

| Suite | base HEAD | A0+A1 only | WIP LIMS only |
|-------|-----------|------------|---------------|
| `TestLimsAuthorization` | OK 12 | OK 12 | OK 12 |
| `test_lims_flujo_critico` | FAIL 2 | FAIL 2 | FAIL 2 |
| Causa 400 | Fixture sin `fecha_programada_toma` (campo requerido en HEAD) | igual | igual |

**Atribución:** fallos **preexistentes en HEAD**, no introducidos por A0+A1 ni por WIP LIMS. **No corregidos** (no tocar LIMS).

## 3. Pruebas existentes — agenda / turnos (dependencia compartida)

```bash
python manage.py test turnos.tests.test_api.TestTurnoAPI.test_solapamiento_turnos turnos.tests.test_estado_turnos -v1 --keepdb
```

**Comparativa 2026-10-16:**

| Suite | base / a01 / wip |
|-------|------------------|
| `test_solapamiento_turnos` | OK |
| `test_estado_turnos` | 75 OK / 2 FAIL en los tres |
| Fallos | `test_laboratorio_no_puede*` — **obtenido 403**, esperado **404**; body cancelar: permiso denegado explícito |

**Atribución:** preexistente en HEAD (no A0+A1, no WIP). **No corregido.**

## 4. Smoke manual mínimo (opcional si tests pasan)

- [ ] `GET /api/health/` → ok
- [ ] Login rol laboratorio; listado solicitudes lab responde
- [ ] Agenda: crear/cancelar turno consultorio sin error nuevo

## 5. Qué no hacer en A0

- No refactorizar ni “arreglar” fallos preexistentes de LIMS en este ticket.
- No añadir tests **dentro** de `laboratorio/` por A0/A1; cualquier harness extra va en `docs_synesis/checklists/` o apps no-LIMS (`catalogos/tests`, etc.).
