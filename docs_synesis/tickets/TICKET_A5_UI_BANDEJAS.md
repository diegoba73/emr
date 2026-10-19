# Ticket A5 — UI “Estudios y procedimientos”: nombre, bandejas y filtros

**Estado:** implementado en código (ver `CIERRE_ETAPA_A5.md`) — **sin merge ni producción**  
**Depende de:** A0+A1 + A2–A4  
**SoT diseño:** `docs_synesis/DOC_DISENO_ESTUDIOS_PROCEDIMIENTOS.md` §A5 — **este ticket prevalece**  
**Restricción:** LIMS intocable. Sin A6+, merge ni producción.

---

## 0. Decisiones cerradas

| # | Decisión |
| --- | --- |
| D1 | Nombre visible: **“Estudios y procedimientos”**. Ruta `/estudios-complementarios` conservada. |
| D2 | Matriz de bandejas §1 (estados reales de estudio + reserva + informe). |
| D3 | **Realización y anulación prevalecen** sobre la reserva. Un estudio REALIZADO+ no vuelve a “Pendiente de programar” aunque el turno esté cancelado o desactualizado. |
| D4 | “Programado” = reserva **vigente** (turno RESERVADO/CONFIRMADO), no la sola FK histórica. |
| D5 | GET **no** repara espejo/sesión ni muta estados para acomodar la UI. |
| D6 | Filtrar **antes** de paginar (servidor). Contadores con los **mismos** criterios, permisos y búsqueda del listado. |
| D7 | Extensiones API **read-only** mínimas del módulo estudios (`bandeja`, resumen de conteos). |
| D8 | Conservar rutas, búsqueda, acciones, documentos, archivos y permisos. Sin controles de proc/cirugía/multisesión deshabilitados. |
| D9 | Ningún registro inaccesible: bandeja **Todos** + cobertura completa de estados en la matriz. |

---

## 1. Matriz definitiva de bandejas

Estados de estudio: `SOLICITADO`, `CONFIRMADO`, `REALIZADO`, `INFORMADO`, `VALIDADO`, `ENTREGADO`, `ANULADO`.  
Reserva vigente: existe turno ligado (espejo o sesión) con estado `RESERVADO` o `CONFIRMADO`.

| Bandeja (`bandeja=`) | Criterio exacto |
| --- | --- |
| `pendiente_programar` | `estado ∈ {SOLICITADO, CONFIRMADO}` **y** sin reserva vigente |
| `programados` | `estado ∈ {SOLICITADO, CONFIRMADO}` **y** con reserva vigente |
| `documentacion_pendiente` | `estado ∈ {REALIZADO, INFORMADO}` — informe aún requiere elaboración, emisión o validación (reglas actuales: hasta quedar VALIDADO el estudio) |
| `pendiente_entrega` | `estado = VALIDADO` — documentación lista, aún no entregada |
| `finalizados` | `estado = ENTREGADO` |
| `anulados` | `estado = ANULADO` |
| `todos` / vacío | Sin filtro de bandeja (acceso a cualquier registro permitido por permisos) |

### Precedencia (D3)

1. `ANULADO` → `anulados` (aunque haya turno vigente histórico).  
2. `ENTREGADO` → `finalizados`.  
3. `VALIDADO` → `pendiente_entrega`.  
4. `REALIZADO` / `INFORMADO` → `documentacion_pendiente` (la reserva **no** los mueve a programar/pendiente programar).  
5. `SOLICITADO` / `CONFIRMADO` → según reserva vigente.

### INFORMADO / VALIDADO / ENTREGADO e informes

| Situación | Bandeja |
| --- | --- |
| Informe borrador / emitido; estudio `REALIZADO` o `INFORMADO` | `documentacion_pendiente` |
| Informe validado vigente; estudio `VALIDADO` | `pendiente_entrega` |
| Estudio `ENTREGADO` | `finalizados` |
| Informe rectificado (estudio vuelve a circuito de emisión/validación → suele `INFORMADO`) | `documentacion_pendiente` |
| Informe anulado sin estudio entregado | Según `estado` del estudio (no se “pierde”: `todos` o bandeja del estado) |
| Estudio `ANULADO` | `anulados` |

---

## 2. API read-only (mínima)

| Extensión | Uso |
| --- | --- |
| Query `bandeja=` en `GET /estudios-complementarios/` | Filtra queryset **antes** de paginar; respeta `search`, `practica`, `estado` (si se combina), permisos de `get_queryset` |
| `GET /estudios-complementarios/bandejas-resumen/` | Conteos por bandeja con los **mismos** filtros de búsqueda/práctica/paciente y permisos |

Sin writes; sin cambios LIMS.

---

## 3. UI

- Labels: “Estudios y procedimientos” (sidebar, página, header/`navLabels`, card Dashboard si aplica; paciente puede conservar “Mis …” + nombre nuevo).  
- Chips/tabs de bandeja + contadores del resumen.  
- Conservar filtros de búsqueda paciente y práctica; el filtro por `estado` crudo puede coexistir o subordinarse a bandeja (preferir bandeja como primario).  
- Sin UI de alta/filtro proc/cirugía/multi.

---

## 4. Pruebas

- Matriz: cada estado+reserva cae en la bandeja esperada; realizado+turno cancelado ≠ pendiente programar.  
- Paginación: filtro bandeja en servidor; conteos = mismos criterios.  
- Permisos: laboratorio sin acceso; roles actuales intactos.  
- Flujo: crear → programar → realizar → informe → validar → entregar.  
- Frontend checks disponibles + regresión A4/A3/A2 + A0 (fallos preexistentes documentados).

---

## 5. Entregables

Diff exclusivo A5 (sobre A4), evidencias, `CIERRE_ETAPA_A5.md`. Sin merge/prod.
