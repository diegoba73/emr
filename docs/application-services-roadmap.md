# Roadmap — Application Services pragmáticos (sin implementación)

Este documento **diseña** una capa de **Application Services** (orquestación de casos de uso) alineada con [`workflow-audit.md`](./workflow-audit.md) y los documentos clínicos previos. **No mueve código**, **no crea archivos `services/` reales**.

**Principios:** consistencia operacional, menos efectos ocultos, **tests** dirigidos por casos de uso, sin Clean Architecture dogmática ni buses de eventos.

---

## 1. Alcance

- Extraer gradualmente **orquestación** de **views**, no del dominio catálogo puro.
- **No** absorbente de serialización de entrada/salida DRF donde no aporte (los serializers pueden seguir como capa IO).
- **Coexistencia** con capa longitudinal (**`historias_clinicas`**) intacta hasta decisiones posteriores; servicios enfocados primero en **spine Turno→Atencion→evidencias** y **lab/solicitudes** donde el acoplamiento es máximo.

---

## 2. Servicios propuestos (concepto)

Para cada uno: responsibility, inputs, outputs, transacciones, entidades tocadas, side effects, auditoría.

### 2.1 `TurnoBookingService` (nombre orientativo)

| Aspecto | Contenido |
|---------|-----------|
| **Responsabilidad** | Reservar/modificar turno aplicando **reglas de disponibilidad, solape y rol** cuando esas reglas deban ser únicas fuente de verdad. |
| **Inputs** | Usuario actor, datos de creación/edición (`medico`,`recurso`, ventanas, `estado`). |
| **Outputs** | `Turno` persistido o error de dominio estable. |
| **Transacciones** | Una transacción por operación atomizable; mismo patrón que hoy pero **centralizado**. |
| **Entidades** | `Turno`, opcionalmente lecturas `DisponibilidadMedico` / `ExcepcionMedico` / otros `Turno`. |
| **Side effects** | Auditoría; **no** crear `Atencion` aquí salvo política explícita (actualmente divergente entre legacy `api/views` y activo). |
| **Auditoría** | `log_create` / `log_update` encapsulados. |

**Motivación:** hoy parte de esa lógica está **solo** en `api/views.TurnoViewSet` (**no enrutada**); el activo `turnos.views` es más delgado — el servicio unifica **cuando se decida** qué política es la oficial.

---

### 2.2 `CrearAtencionDesdeTurnoService`

| Aspecto | Contenido |
|---------|-----------|
| **Responsabilidad** | Equivalente estable a **`AtencionViewSet.create`** + idempotencia: obtener o crear **una** `Atencion` por `turno` con tipos desde `Recurso`. |
| **Inputs** | `turno_id`, usuario, observaciones opcionales. |
| **Outputs** | `Atencion` (+ `created: bool`). |
| **Transacciones** | `atomic` recomendable alrededor de create + cargas relacionadas si se amplía. |
| **Entidades** | `Turno`, `Atencion`, `Paciente`, `Medico`, `Recurso`. |
| **Side effects** | Auditoría única estándar. |
| **Auditoría** | `log_create` en alta real. |

**Nota:** convive con **`AtencionService.iniciar_atencion_desde_turno`** (ya atómico, crea hijo si aplica): decidir si **fusión conceptual** futura (“un solo servicio con flags”) sin duplicar transacciones anidadas.

---

### 2.3 `FinalizarAtencionService`

| Aspecto | Contenido |
|---------|-----------|
| **Responsabilidad** | Cerrar atención (`FINALIZADA`, `fecha_cierre`) validando estado previo **ABIERTA** y reglas de negocio (p.ej. documentos pendientes opcionales en el futuro). |
| **Inputs** | `atencion_id`, usuario. |
| **Outputs** | `Atencion` actualizada. |
| **Transacciones** | `atomic`. |
| **Side effects** | Auditoría; **no** tocar turno aquí si la política es “solo en registrar_consulta” (evitar doble escritura accidental). |

---

### 2.4 `RegistrarConsultaAmbulatoriaService`

| Aspecto | Contenido |
|---------|-----------|
| **Responsabilidad** | Contenido hoy del action **`registrar-consulta`**: upsert **`ConsultaAmbulatoria`**, actualizar opcional **`estado_clinico`**, marcar **`Turno` REALIZADO** si contenido, auditoría ordenada. |
| **Inputs** | `atencion_id`, payload usuario, usuario autenticado. |
| **Outputs** | DTO/`ConsultaAmbulatoria` lista para responder (o errores HTTP mapeados en la view fina delgada). |
| **Transacciones** | **Obligatorio `atomic`** (ya existe en decorador — mover alcance exacto dentro del método de servicio al migrar). |
| **Entidades** | `Atencion`, `ConsultaAmbulatoria`, `Turno`. |
| **Side effects** | **Múltiples** `AuditEvent`; logs. |
| **Auditoría** | Centralizar orden: atención → turno si aplica. |

**Prioridad:** **Alta** (mayor masa de reglas en un único método de view).

---

### 2.5 `LaboratorioResultadosService`

Suboperaciones dentro del mismo módulo o clases internas livianas sin microservicios.

| Aspecto | `cargar_resultados` | `validar_solicitud` |
|---------|---------------------|---------------------|
| **Responsabilidad** | Iterar resultados con `select_for_update`, persistir valores, mover estado solicitud si aplica, auditoría consistente | Validar invariantes (“no vacíos”), `VALIDADO`, marcar validación usuario/fecha sin romper modelo |
| **Transacciones** | `atomic` | `atomic` |
| **Riesgos a aislar** | — | Considerar **`update()` masivo vs `save()`** por resultado para política de señales/auditoría uniforme |

---

### 2.6 `CompletarSolicitudAdministrativaService` (nombre orientativo)

| Aspecto | Contenido |
|---------|-----------|
| **Responsabilidad** | `marcar_como_completada`, `cancelar`, `reabrir` sin **doble `save`** innecesario; opcional **`envío LIMS`** en create separado como paso explícito. |
| **Inputs** | Solicitud ID, usuario, método (completar/cancelar/reabrir). |
| **Outputs** | `Solicitud` final. |
| **Transacciones** | Una transacción; **LIMS opcional fuera del commit clínico** o con política retry documentada (mismo comportamiento observable que hoy hasta decidir SLA). |

---

### 2.7 `EmitirAuditoriaCasoDeUso` (helper opcional)

| Aspecto | Contenido |
|---------|-----------|
| **Responsabilidad** | Encapsular llamadas `log_*` con **captura estándar** de actor y política **`on_commit`**. |
| **Inputs** | Tipo evento + entidades. |
| **Outputs** | Ninguno o referencia asíncrona. |

Reduce duplicación y olvidos cuando se muevan acciones desde views.

---

## 3. Prioridades recomendadas

| Prioridad | Servicio(s) | Justificación breve |
|-----------|---------------|---------------------|
| **P0** | `RegistrarConsultaAmbulatoriaService` + helpers auditoría | Máximo acoplamiento y efectos por request. |
| **P1** | `LaboratorioResultadosService` (`cargar`, `validar`) | Atomización + discrepancia bulk vs audit. |
| **P2** | `CompletarSolicitudAdministrativaService` (+ create con LIMS explícito) | Side channel LIMS + doble save. |
| **P3** | `CrearAtencionDesdeTurnoService` / alinear con **`AtencionService`** existente | Reducir duplicación conceptual create vs iniciar desde turno. |
| **P4** | `TurnoBookingService` | Tras política única disponibilidad (activar/refactor desde legacy codificado pero no routeado). |
| **P5** | `FinalizarAtencionService` | Ligero pero conviene después de registrar consulta para orden de llamadas estable. |

---

## 4. Orden sugerido de migración (gradual)

1. **Feature flag OFF por defecto** o “extract method” dentro de la **misma view** llamando función en `*_services.py` colocalizada (solo cuando se apruebe implementar — **aquí solo plan**).
2. **Un solo action migrate** (`registrar-consulta`) → servicio detrás mismo endpoint sin cambiar contrato.
3. **Laboratorio**: extraer método de view a función pura bien testeado.
4. **Solicitudes**: eliminar double-save en servicio antes de mover otras vistas.
5. **Turno disponibilidad:** portar sólo cuando se consolide **`api/views` vs `turnos.views`**.

---

## 5. Estrategia gradual — reglas operativas

- **Las views se quedan delgadas:** auth HTTP, despacho serializer, código HTTP status.
- **Los servicios** retornan **resultados o errores de dominio** (excepciones personalizadas o `Result`).
- **No** mover serializers completos dentro de services.
- **Transacciones** solo en borde aplicación (servicios), **no anidadas** sin causa.
- **LIMS**: fuera del commit DB o mismo patrón observable que producción hasta diseño SLA.

---

## 6. Riesgos si se implementara mañana (meta‑riesgo del cambio futuro)

| Riesgo | Mitigación de diseño |
|--------|----------------------|
| Regresiones en contratos REST | Migración interna; mismos serializers. |
| Duplicidad con `AtencionService` | Comparar antes fusionar; tabla de decisión. |
| Testing insuficiente | Introducir tests de servicio **antes** de quitar código de view. |

---

## 7. Impacto esperado

| Aspecto | Efecto buscado |
|---------|----------------|
| **Operacional** | Menos sorpresa en producción cuando se tocó “un solo lugar” por caso de uso. |
| **Mantenibilidad** | Queries de negocio legibles fuera de vistas de 400 líneas. |
| **Clínico/legal** | Misma política observable hasta que stakeholder decida SLA LIMS/expediente HC. |

---

## 8. Dependencias externas entre módulos (diseño, no grafos Django)

```
turnos  ←→ auditoria.context (request_id / actor)
turnos  ← catalogos resolve_tipo...
solicitudes ← integracion_lims.lims_service
laboratorio ← auditoria.snapshot + audit_service
historias_clinicas ← (futuros servicios síncronos solo si proyecto explícito)
```

---

*Documento de planificación cerrado. Para detalle factual de comportamiento HTTP actual véase [`workflow-audit.md`](./workflow-audit.md).*
