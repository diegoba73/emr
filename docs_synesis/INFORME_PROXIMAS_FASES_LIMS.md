# Informe — Próximas fases LIMS (jun 2026)

## 1. Estado B3-frontend-validación-A

**[VALIDADO]** — Bloqueo operación técnica en `CANCELADO` / `VALIDADO` / `INFORMADO`. Excepción: `VALIDADO` → `INFORMADO`. Commits base `35d1edc` / `75d56b2`. Paquete auditoría: `B3_VALIDACION_A_CODEX_AUDIT.md`.

## 2. B3-frontend-UX (esta corrida)

| Ítem | Estado |
|------|--------|
| Filtros server-side por `estudio_id` en API micro | **[GAP]** — backend sin `DjangoFilterBackend`; UI detalle sigue listado global + filtro cliente |
| Picker solicitud/muestra al crear estudio | **[IMPLEMENTADO]** — APIs `listSolicitudesExamen`, `listMuestrasPorSolicitud` |
| Tests helpers | **[IMPLEMENTADO]** — `limsMicroUx.test.ts`, ampliación `limsAccess.test.ts` |
| E2E LIMS micro | **[GAP]** — sin Playwright/Cypress |

## 3. Recomendación de siguiente fase

**A. B3-frontend-UX restante (backend acotado):** añadir query `estudio_id` en ViewSets micro (siembras, lecturas, aislados, antibiogramas, resultados, informes) — requiere cambio backend mínimo + tests API; evaluar con arquitecto antes de migrar.

Alternativas posteriores: **B** E2E crítico; **C** informes PDF; **D** recepción masiva/etiquetas; **E** auditoría legal ACL; **F** hardening producción.

## 4. Riesgos priorizados

| Prioridad | Riesgo |
|-----------|--------|
| Medio | Detalle micro con volumen alto (N+1 listados globales) |
| Medio | Modelo `clean()` solo bloquea `CANCELADO`; cierre `VALIDADO`/`INFORMADO` depende del servicio |
| Bajo | Picker solicitud muestra nombres de paciente en etiqueta (mismo patrón que órdenes LIMS) |

## 5. Restricciones respetadas

Sin modelos, migraciones, permisos backend, estados globales, EMR funcional, Estudios Complementarios, PACS, management commands, PDF, CLSI/EUCAST, C5 ni IA.
