# Cierre exclusivo — Etapa A0 + A1

**Base HEAD:** `1ecd0df` (`fix(mobile): QR del login como data URI inline`)  
**Fecha de cierre documental:** 2026-10-16  
**Alcance de este cierre:** solo A0+A1. **No** incluye WIP LIMS, docs ajenos, merge ni producción.  
**A2:** no implementado; ticket en `docs_synesis/tickets/TICKET_A2_A2b_ESTUDIOS_PROCEDIMIENTOS.md`.

---

## 1. Cierre A0 (verificación)

> **Verificación comparativa completada, sin nuevas regresiones detectadas en las suites ejecutadas; cuatro fallos preexistentes documentados.**

### Método

Worktrees aislados (sin alterar el working tree principal):

| Entorno | Contenido |
|---------|-----------|
| `emr-wt-base` | HEAD limpio |
| `emr-wt-a01` | HEAD + únicamente A0+A1 |
| `emr-wt-wip` | HEAD + únicamente WIP `laboratorio/` |

DBs de prueba dedicadas (`test_a0_*`, `test_a0_mig_clasif`). **No** producción ni DB operativa.

Detalle: `/home/diego/proyectos/emr-a0-compare-artifacts/COMPARATIVA_A0.md`.

### Suites ejecutadas (idénticas en base / A0+A1 / WIP)

| Suite | Resultado |
|-------|-----------|
| `laboratorio.tests.test_api.TestLimsAuthorization` | OK — 12 |
| `laboratorio.tests.test_lims_flujo_critico` | FAIL — 2 |
| `turnos.tests.test_api.TestTurnoAPI.test_solapamiento_turnos` | OK |
| `turnos.tests.test_estado_turnos` | 75 OK / 2 FAIL |

### Cuatro fallos preexistentes (no corregidos)

| # | Caso | Esperado | Obtenido | Causa (sin PHI) | Atribución |
|---|------|----------|----------|-----------------|------------|
| 1–2 | `test_lims_flujo_critico` (×2) | 201 create solicitud | 400 | Body: `fecha_programada_toma` requerido; fixture E2E no lo envía | **HEAD** (no A0+A1, no WIP) |
| 3 | `test_laboratorio_no_puede_cancelar` | 404 | 403 | `detail`: sin permiso para cancelar | **HEAD** |
| 4 | `test_laboratorio_no_puede` (iniciar-atención) | 404 | 403 | Forbidden (deny explícito vs ocultamiento) | **HEAD** |

**Política:** no se modificó LIMS, sus pruebas ni permisos/expectativas de turnos para obtener verde.

### Límites de la verificación A0

- No se ejecutó la suite completa del repo ni CI remoto.
- Smoke manual (health / login lab UI) no fue requisito de este cierre documental.
- Contenedores efímeros con `--entrypoint python` y settings overlay de comparación; no sustituyen el runtime `emr_backend` montado al working tree sucio.
- La aceptación “diff `laboratorio/` vacío en el PR” aplica al **paquete A0+A1**, no al working tree local (que conserva WIP LIMS aparte).

---

## 2. Cierre A1 (código empaquetado)

### Entregable

Campo aditivo `ProcedimientoCatalogo.clasificacion_quirurgica`  
(`SIN_ASIGNAR` \| `NO_QUIRURGICO` \| `QUIRURGICO`), default `SIN_ASIGNAR`; sin reclasificación automática por nombre; consumidores legacy no endurecidos.

Migración `catalogos.0010_procedimientocatalogo_clasificacion_quirurgica` verificada en DB de prueba: filas seed preservadas; todas `SIN_ASIGNAR`.

Pruebas A1 (fuera de `laboratorio/`): `pytest catalogos/tests/test_models.py` + `test_procedimiento_clasificacion_api.py` → **10 passed** (corrida previa en entorno local).

### Paquete exclusivo

Directorio: `/home/diego/proyectos/emr-a0-compare-artifacts/a01_package/`

| Artefacto | Uso |
|-----------|-----|
| `a01_exclusive_complete.patch` | Diff binario/aplicable **incluyendo archivos nuevos** |
| `a01_exclusive_complete.stat` | `--stat` |
| `a01_patch_paths.txt` | Lista de paths en el patch |
| `files/` | Copia de archivos del paquete |
| `MANIFEST.txt` | Inventario |

**Incluye:** migración, tests catálogo, FE catálogo, serializer, checklist A0, diseño, este cierre, ticket A2/A2b.  
**Excluye:** `laboratorio/**`, `DOC_PROTOCOLO_TRABAJO_ASISTENTE.md`, `reglas/control-calidad.md`, `reglas/produccion-servidor.md`, y cualquier otro WIP.

### Working tree principal

Conservado íntegramente (A0+A1 + WIP LIMS + docs ajenas). Este cierre **no** hace commit, merge ni deploy.

---

## 3. Estado respecto a A2

A2/A2b **no iniciado**. Ticket detallado listo para implementación posterior. LIMS permanece intocable.
