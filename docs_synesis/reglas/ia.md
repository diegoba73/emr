# Reglas — Inteligencia artificial (Fase C0)

**Versión:** C0 — 18 de mayo de 2026  
**Estado del producto:** **[OBJETIVO]** — No hay motor IA productivo cableado en el repo. Existen **campos preparatorios** en `historias_clinicas` (comentarios “para IA”).

---

## Propósito

Cuando se incorpore IA, debe actuar como **asistente documental y de sugerencia**, nunca como autoridad clínica ni analítica.

---

## Reglas **[RECTOR]** (obligatorias en cualquier implementación futura)

| # | Regla |
|---|--------|
| 1 | **IA no valida** resultados de laboratorio ni estados `VALIDADO` / informes finales. |
| 2 | **IA no emite** informes finales ni firma digital clínica. |
| 3 | **IA no reemplaza** criterio profesional (médico, bioquímico, microbiólogo). |
| 4 | Toda salida de IA debe estar **marcada como sugerencia** (UI + persistencia). |
| 5 | Toda **aceptación o rechazo** de sugerencia registra **usuario humano**, timestamp y contexto. |
| 6 | IA solo opera sobre **datos ya trazables** en el EMR/LIMS (misma cadena que humanos). |
| 7 | **No usar IA** para eludir permisos ni roles (`laboratorio`, `paciente`, etc.). |
| 8 | **No enviar PHI** a servicios externos sin política explícita (DPIA, contrato, minimización, región). |

---

## Alcance permitido **[OBJETIVO]**

- Borradores de texto clínico (anamnesis, resumen) bajo supervisión.
- Extracción de entidades con revisión humana.
- Alertas no bloqueantes (ej. posible interacción medicamentosa) como **hint**, no orden.

---

## Alcance prohibido

- Diagnóstico definitivo automático publicado en HC.
- Auto-validación de `ResultadoExamen` o `InformeMicrobiologico`.
- Decisiones de transición de estado sin actor humano autorizado.
- Entrenamiento con datos de producción sin anonimización y gobernanza.

---

## Auditoría esperada **[OBJETIVO]**

| Evento |
|--------|
| `IA_SUGGESTION_CREATED` (entidad, modelo, versión prompt) |
| `IA_SUGGESTION_ACCEPTED` / `REJECTED` (usuario, diff aplicado o motivo rechazo) |

Sin almacenar prompts con PHI en logs de aplicación.

---

## Relación con modelos HC

Campos en `Consulta`, `Diagnostico`, `Tratamiento`, etc. documentados como “para IA” — **[OBJETIVO]** permanecen inertes hasta pipeline definido.

---

## Invariantes

Ver `DOC_INVARIANTES.md` (IA1–IA4).

---

## Pendientes antes de cualquier feature IA

1. Política de datos y proveedor (documento legal, no solo técnico).
2. Feature flag por entorno.
3. Tests: IA no puede llamar `validar` ni transiciones de estado terminales.
