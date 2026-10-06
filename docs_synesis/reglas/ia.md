# Reglas — Inteligencia artificial

**Versión:** C1 — octubre 2026  
**Estado del producto:** **[IMPLEMENTADO]** (capa de sugerencia) — cliente MedGemma/Ollama opcional + fallback a reglas. Campos preparatorios en HC siguen inertes.

---

## Propósito

La IA actúa como **asistente documental y de sugerencia**, nunca como autoridad clínica ni analítica.

---

## Entornos

| Entorno | MedGemma / Ollama | Comportamiento |
|---------|-------------------|----------------|
| Local (dev) | Opcional: `MEDGEMMA_ENABLED=true` + Ollama + `medgemma:4b` | Sugerencias con `fuente=medgemma` si responde; si no, reglas |
| Producción (`emr.sytes.net`) | **No soportado** — no instalar Ollama | `MEDGEMMA_ENABLED=false`; siempre motor de reglas |

How-to local: `docs/medgemma-ollama.md`.

---

## Reglas **[RECTOR]** (obligatorias)

| # | Regla |
|---|--------|
| 1 | **IA no valida** resultados de laboratorio ni estados `VALIDADO` / informes finales. |
| 2 | **IA no emite** informes finales ni firma digital clínica. |
| 3 | **IA no reemplaza** criterio profesional (médico, bioquímico, microbiólogo). |
| 4 | Toda salida de IA debe estar **marcada como sugerencia** (UI + respuesta API). |
| 5 | Toda **aceptación o rechazo** de sugerencia registra **usuario humano**, timestamp y contexto (cuando exista flujo de accept). |
| 6 | IA solo opera sobre **datos ya trazables** en el EMR/LIMS (misma cadena que humanos). |
| 7 | **No usar IA** para eludir permisos ni roles (`laboratorio`, `paciente`, etc.). |
| 8 | **No enviar PHI** a servicios externos. Payload mínimo (códigos, valores, rangos); Ollama solo en red local. |

---

## Alcance cableado **[IMPLEMENTADO]**

- Conclusión de hemograma (`POST …/sugerir-conclusion-hemograma/`).
- Reseñas de pedidos / impresión.
- Borrador de informe de estudios complementarios.
- Interpretación de orden (`POST …/sugerir-interpretacion/`) — no persiste en HC.
- Resumen opcional de **agregados** de analítica poblacional (nunca filas de paciente).

Fallback: plantillas/heurísticas con `fuente=reglas` si MedGemma está off o no responde.

---

## Alcance prohibido

- Diagnóstico definitivo automático publicado en HC.
- Auto-validación de `ResultadoExamen` o `InformeMicrobiologico`.
- Decisiones de transición de estado sin actor humano autorizado.
- Entrenamiento con datos de producción sin anonimización y gobernanza.
- Ollama / MedGemma en el host de producción EMR.

---

## Auditoría

| Evento | Estado |
|--------|--------|
| `IA_SUGGESTION_CREATED` (entidad, modelo/fuente, sin texto PHI en logs) | **[IMPLEMENTADO]** en flujos de sugerencia |
| `IA_SUGGESTION_ACCEPTED` / `REJECTED` | **[OBJETIVO]** cuando exista accept/reject en HC |

Sin almacenar prompts con PHI en logs de aplicación.

---

## Relación con modelos HC

Campos en `Consulta`, `Diagnostico`, `Tratamiento`, etc. documentados como “para IA” — **[OBJETIVO]** permanecen inertes hasta pipeline de aceptación.

---

## Invariantes

Ver `DOC_INVARIANTES.md` (IA1–IA4).
