# Jerarquía de reglas SYNESIS

## Propósito

Puerta de entrada a las reglas del sistema. **No sustituye** los documentos fuente: no copia reglas, no es consolidado para GPT y no es código.

Arquitectura: **fuentes canónicas especializadas → este índice → consolidados automáticos `SYNESIS_*.md`**.

## Cómo usarlo

1. Abrí este índice.
2. Abrí **solo** los documentos del dominio que vas a tocar.
3. Si el código contradice un doc, gana el código; reportá el conflicto. No reescribas la regla de memoria.

## Jerarquía documental

| Consultar | Documento |
|-----------|-----------|
| Mapa / estado actual | `DOC_MAPA_SISTEMA.md`, `DOC_ESTADO_ACTUAL_VERIFICADO.md` |
| Reglas generales de negocio | `DOC_REGLAS_NEGOCIO.md` |
| Modelo conceptual y entidades | `DOC_MODELO_FUNDAMENTAL_EMR_LIMS.md`, `DOC_ENTIDADES_PRINCIPALES.md` |
| Invariantes | `DOC_INVARIANTES.md` |
| Estados y transiciones | `DOC_ESTADOS_TRANSICIONES.md` |
| Reglas por dominio | `reglas/` (lista abajo) |
| Flujos EMR | `DOC_FLUJOS_EMR.md` |
| Flujos LIMS | `DOC_FLUJOS_LIMS.md` |
| Catálogo micro LabWin | `DOC_LABWIN_MICRO_CATALOGOS.md`, `reportes/labwin_micro_catalog_revision.md` |
| Modelos DB | `DOC_MODELOS_DB.md` |
| API | `DOC_API_ENDPOINTS.md` |
| Permisos y auditoría | `DOC_PERMISOS_AUDITORIA.md` |
| Frontend | `DOC_FRONTEND.md` |
| Tests | `DOC_TESTS.md` |
| Riesgos / deuda | `DOC_RIESGOS_DEUDA_TECNICA.md` |
| Protocolo de trabajo | `DOC_PROTOCOLO_TRABAJO_ASISTENTE.md`, `DOC_TRABAJO_SYNESIS_CURSOR_CODEX.md` |

Operación de producción (`PROD_*.md`), backup (`DOC_BACKUP_RESTAURACION.md`) y checklists no son reglas de dominio.

## Reglas por dominio

Archivos existentes en `docs_synesis/reglas/` (no inventar dominios):

- `reglas/auditoria.md`
- `reglas/control-calidad.md`
- `reglas/documentos-e-imagenes.md`
- `reglas/entorno-local.md`
- `reglas/ia.md`
- `reglas/instrumentos-analizadores.md`
- `reglas/inventario-reactivos.md`
- `reglas/pacientes.md`
- `reglas/produccion-servidor.md`
- `reglas/usuarios-y-permisos.md`

## Precedencia

1. **Código real** cuando se verifica implementación o comportamiento.
2. **Reglas e invariantes específicas** (`reglas/`, `DOC_INVARIANTES.md`).
3. **Estados y transiciones** (`DOC_ESTADOS_TRANSICIONES.md`).
4. **Contratos DB/API** (`DOC_MODELOS_DB.md`, `DOC_API_ENDPOINTS.md`).
5. **Flujos** (`DOC_FLUJOS_EMR.md`, `DOC_FLUJOS_LIMS.md`).
6. **Reglas generales y documentación descriptiva** (`DOC_REGLAS_NEGOCIO.md`, mapa, entidades, frontend, tests).
7. **Riesgos / deuda** (`DOC_RIESGOS_DEUDA_TECNICA.md`): alerta, no regla.

Ante conflicto código ↔ doc: **no decidir en silencio**; reportar.  
PHI, mezclar bases locales o tocar la otra app del servidor: `reglas/entorno-local.md` y `reglas/produccion-servidor.md`.

## Política anti-duplicación

- Las reglas detalladas viven **solo** en sus documentos especializados.
- Este índice **solo referencia**.
- Los `SYNESIS_*.md` (paquete `docs_synesis_gpt_knowledge/`) son **derivados** de `scripts/build_synesis_gpt_knowledge.py`. No editarlos a mano para meter una regla.
- Cualquier cambio de regla se hace **primero** en la fuente canónica de `docs_synesis/`; después se regenera el paquete.
- No definir reglas en `.cursor/rules`. Cursor solo tiene un puntero: `.cursor/rules/synesis-reglas.mdc`.

## Disparadores del asistente

Procedimiento en `DOC_PROTOCOLO_TRABAJO_ASISTENTE.md` (no repetir aquí):

- «checkpoint» / «volver» / «último checkpoint» → §5.7

Arranque local (cómo, no la política): `docs/dev-start.md`.
