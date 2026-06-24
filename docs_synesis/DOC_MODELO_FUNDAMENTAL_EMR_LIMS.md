# DOC_MODELO_FUNDAMENTAL_EMR_LIMS — Constitución funcional-técnica (Fase C0)

**Versión:** C0 — 18 de mayo de 2026  
**Estado:** Documento rector complementario. **No reemplaza** los `DOC_*` operativos existentes; los integra y orienta evolución futura.

**Jerarquía documental:**

| Nivel | Documentos |
|-------|------------|
| **SoT operativo (código + hechos)** | `DOC_REGLAS_NEGOCIO.md`, `DOC_MODELOS_DB.md`, `DOC_API_ENDPOINTS.md`, `DOC_FLUJOS_EMR.md`, `DOC_FLUJOS_LIMS.md`, `DOC_PERMISOS_AUDITORIA.md` |
| **Constitución (este bloque C0)** | Este archivo + `DOC_ENTIDADES_PRINCIPALES.md`, `DOC_ESTADOS_TRANSICIONES.md`, `DOC_INVARIANTES.md`, `reglas/*` |
| **Arquitectura complementaria** | `docs/` (roadmaps, auditorías) |

---

## Principio central

**[RECTOR]** Este EMR + LIMS **no se construye alrededor de pantallas**. Se construye alrededor de **verdades clínicas y analíticas trazables**.

Cada módulo debe preservar, como mínimo conceptual:

- **identidad** (quién es el sujeto de atención / la orden);
- **estado** (en qué punto del ciclo de vida está cada hecho);
- **responsabilidad** (qué rol o actor puede actuar);
- **auditoría** (qué cambió, quién, cuándo y en qué contexto);
- **versión histórica** (especialmente informes y resultados validados).

Las pantallas (React) y los endpoints (DRF) son **proyecciones** de esas verdades, no su sustituto.

---

## Cadena principal de valor

**[RECTOR]** Cadena conceptual unificadora (no implica un solo modelo físico por paso):

```
Paciente
  → Atención / Episodio (encuentro asistencial)
    → Orden (pedido clínico o analítico)
      → Muestra (material biológico trazable, cuando aplica)
        → Determinación / Examen (qué se mide o cultiva)
          → Resultado (valor u observación analítica)
            → Validación (acto profesional o técnico autorizado)
              → Informe (síntesis comunicable; en micro: preliminar/final)
                → Auditoría (traza transversal de todo lo anterior)
```

**[IMPLEMENTADO]** En el repositorio actual existen **dos vías de “orden”** que conviven:

1. **LIMS nativo:** `SolicitudExamen` → `Muestra` → `ResultadoExamen` (+ rama microbiología B3.x).
2. **Solicitudes EMR genéricas:** `solicitudes.Solicitud` en `/api/solicitudes/` — envío a LIMS HTTP externo **solo** por acciones explícitas admin (`enviar_lims`, `sincronizar_lims`); sin auto-envío en `save()`. `LIMS_AUTO_SEND` legacy sin efecto.

**[DEUDA]** Unificar operativamente EMR ↔ LIMS nativo sin doble carga manual (`DOC_RIESGOS_DEUDA_TECNICA.md`).

---

## Reglas fundamentales

| # | Regla | Etiqueta |
|---|--------|----------|
| 1 | Ningún **resultado clínicamente usable** sin trazabilidad a paciente, orden y (cuando corresponda) muestra. | **[RECTOR]** — **[IMPLEMENTADO]** parcial (B2: `muestra_id` opcional en carga; histórico sin muestra aún admisible). |
| 2 | Ningún **informe validado** se modifica en silencio; correcciones futuras deben versionarse o anularse explícitamente. | **[RECTOR]** — **[IMPLEMENTADO]** micro B3.4 (`InformeMicrobiologico` con estados); **[OBJETIVO]** informe PDF general LIMS. |
| 3 | Todo cambio clínico/analítico **relevante** se audita (`auditoria.AuditEvent`). | **[RECTOR]** — **[IMPLEMENTADO]** en flujos instrumentados (ver `reglas/auditoria.md`). |
| 4 | Paciente **no se duplica** sin control (DNI único; fusión futura). | **[RECTOR]** — **[IMPLEMENTADO]** DNI unique; **[OBJETIVO]** fusión/merge. |
| 5 | Muestra **rechazada** no debe sustentar resultado **validado** en la misma orden. | **[RECTOR]** — **[IMPLEMENTADO]** en `validar` (bloqueo por estado de muestra vinculada). |
| 6 | **IA sugiere; el profesional valida** (nunca al revés). | **[RECTOR]** — **[OBJETIVO]** (campos “para IA” en HC; sin motor IA productivo cableado). |
| 7 | Acceso según **rol / contexto / permiso**; PHI mínima necesaria. | **[RECTOR]** — **[IMPLEMENTADO]** con deuda en `get_queryset` disperso. |
| 8 | El sistema debe poder explicar **quién hizo qué, cuándo y por qué** (auditoría + eventos de muestra/orden). | **[RECTOR]** — **[IMPLEMENTADO]** parcial (`EventoMuestra`, metadata en `AuditEvent`). |

---

## Relación con módulos existentes

| Módulo | Rol en la cadena |
|--------|------------------|
| `pacientes` | Identidad demográfica |
| `turnos` + `Atencion` | Episodio operativo del día |
| `historias_clinicas` | Expediente longitudinal |
| `laboratorio` | Orden analítica nativa, muestra, resultado, micro |
| `solicitudes` | Orden administrativa / integración externa |
| `auditoria` | Trazabilidad transversal |
| `usuarios` | Actor y rol |

---

## Qué no es este documento

- No enumera endpoints ni serializers (ver `DOC_API_ENDPOINTS.md`, `DOC_REGLAS_NEGOCIO.md`).
- No sustituye pruebas (`DOC_TESTS.md`).
- No autoriza cambios de código por sí solo.

---

## Próximos pasos documentales (C1+)

1. Auditar módulo **pacientes** contra `reglas/pacientes.md`.
2. Cerrar política de **informe general** LIMS (PDF) vs estado `ENTREGADO` de orden.
3. Definir roadmap IA solo tras política de datos (`reglas/ia.md`).
