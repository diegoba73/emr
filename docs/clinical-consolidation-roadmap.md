# Roadmap gradual de consolidación del dominio clínico

Documento de **planificación únicamente**. **No implementa cambios**, no modifica código productivo, **no crea migraciones**, no asume eliminación de `historias_clinicas` ni consolidación destructiva automática.

**Inputs:** [`clinical-domain-audit.md`](./clinical-domain-audit.md), [`clinical-ownership-map.md`](./clinical-ownership-map.md).

---

## 0. Principio rector (coexistencia deliberada)

El EMR puede y, en muchos despliegues, **debe** mantener dos capas con responsabilidades distintas:

| Capa | Rol | Pivote conceptual recomendado en evolución |
|------|-----|---------------------------------------------|
| **Operacional (encuentro del día)** | Lo que ocurre en agenda / turno / acto asistencial inmediato | **`Atencion` = canonical clinical encounter** para flujo operativo, auditoría operativa, adjuntos del encuentro (`emr.Documento`), registros hijos 1:1. |
| **Longitudinal (historia por paciente)** | Expediente continuo, línea de tiempo HC, problemas, órdenes retrospectivas, vistas “chart” | **`HistoriaClinica` + `Consulta` (HC)** + hijos (`Diagnostico`, `Prescripcion`, `Tratamiento`) como **capa de expediente**, **no** como reemplazo obligatorio del spine operativo. |

**Consolidación objetivo del roadmap:** reforzar **`Atencion` como encuentro clínico canónico en la capa operacional**, alineando procesos, APIs, permisos y —cuando aplique— **sincronización controlada** hacia/desde la capa longitudinal **sin** fundir modelos por fuerza.

---

## 1. Visión de arquitectura objetivo (orientativa, no código)

```
                    [ Scheduling ]
                    Turno · Recurso
                          │
                          ▼
              [ Encounter operacional CANÓNICO ]
                      Atencion
         ┌──────────────┼──────────────┐
         │              │              │
  ConsultaAmb.   RegistroProc.   RegistroQuir.
  · Documento    · adjuntos      · documentos M2M
  · SignosVit.   · informe
         │
         │  sync opcional / proyectada
         ▼
   [ Capa longitudinal CONTINUA ]
   HistoriaClinica → Consulta (HC) → Diagnostico / Prescripcion / Tratamiento
```

---

## 2. Prioridades globales

1. **Reducir divergencia accidental** (dos narrativas escritas sin vínculo conocido) antes que “una sola tabla”.
2. **Definir ownership explícito por capa** y documentar quién escribe qué.
3. **Evitar breaking changes** en APIs públicas hasta fases maduras.
4. **Mantener trazabilidad legal** (integridad de expediente, no borrar historia).

---

## 3. Fase 1 — Consolidación conceptual

### Objetivo

Fijar en la organización y en la documentación técnica **qué es “encuentro canónico operacional”** (`Atencion`), **qué es “registro de expediente longitudinal”** (`HistoriaClinica` / `Consulta` HC), y **cómo deben convivir** (incl. reglas de sincronización **eventual** o **manual**, no obligatorias en esta fase).

### Entidades / artefactos afectados

- **Conceptuales:** `Atencion`, `ConsultaAmbulatoria`, `historias_clinicas.Consulta`, `HistoriaClinica`, `Diagnostico`, `Prescripcion`, `Tratamiento`.
- **Integración:** `solicitudes.Solicitud` vs `laboratorio.SolicitudExamen` (solo alineación de **rol** en documentación).
- **Internación:** dos modelos `Internacion` (solo **mapa de uso** y “sistema de verdad” por proceso).
- **Código legacy:** duplicado `api.views` vs `turnos.views` (inventario de qué rama es “oficial” según `api/urls.py`).

### Riesgos

- Bajo **técnico**; riesgo **organizativo** si médicos/operación no participan y las reglas quedan solo en ingeniería.

### Impacto clínico

- **Bajo directo**; mejora **coherencia de uso** si se traduce a formación y guías de captura.

### Impacto técnico

- **Nulo** en runtime; posible actualización de documentación interna y diagramas.

### Estrategia rollback

- No aplica (solo documentación); revertir es **despublicar** guías.

### Dependencias

- Lectura de audit + ownership map; posible entrevista con stakeholders clínicos.

### Dificultad estimada

- **Baja** (días a 1–2 semanas con validación clínica).

---

## 4. Fase 2 — Deprecation controlada

### Objetivo

Marcar **superficies y patrones** como “**deprecated para nuevos desarrollos**” sin eliminar modelos ni romper contratos: rutas duplicadas, ViewSets no usados en router, campos duplicados **como antipatrón** si se documenta alternativa canónica operacional.

### Entidades / superficies candidatas a “deprecated” (conceptual, no borrado)

| Superficie | Tipo de deprecación |
|------------|---------------------|
| Lógica duplicada **`api.views.AtencionViewSet`** (si sigue existiendo paralela) | **Código legacy** — nuevas features solo en `turnos.views`. |
| **`models.py` raíz duplicado `emr`** | **Definición fuente** — marcar una ruta como fuente de verdad para reviews. |
| Uso **sin criterio** de `/consultas/` vs `/atenciones/.../registrar-consulta/` | **Proceso** — guía: “texto de acto en consultorio → …; CIE y prescripción estructurada → …”. |
| Segundo sistema de internación (el no usado por negocio) | **API / proceso** — “deprecado para nuevas integraciones” hacia el sistema acordado. |

**No se depreca `historias_clinicas`** como módulo; se deprecan **solo** **confusiones de uso**, no el dominio longitudinal.

### Riesgos

- Equipos pueden ignorar marcadores si no hay lint/revisión.

### Impacto clínico

- Bajo si es **solo política**; medio si se **reforma flujo de captación** sin formación.

### Impacto técnico

- Bajo: comentarios, ADR, changelog interno; **opcionalmente** `@deprecated` en docstrings donde la cultura lo permita (sin cambiar comportamiento).

### Rollback

- Retirar avisos de deprecación en documentación.

### Dependencias

- Fase 1 cerrada con acuerdo de boundaries.

### Dificultad estimada

- **Baja–media**.

---

## 5. Fase 3 — Migración gradual de source of truth (operacional → coherencia)

### Objetivo

Mover gradualmente —**solo mediante cambios posteriores acordados fuera de este documento**— los **significados operativos** hacia **`Atencion`** como pivote único para “lo ocurrido en esta visita con este turno”, y definir **dónde vive cada tipo de evidencia**.

**Dos caminos válidos para la longitudinal (no destructivos):**

1. **`Consulta` (HC)** sigue siendo donde vive **Dx CIE, prescripción estructurada, tratamiento** hasta que exista proyecto específico.
2. **Sincronización controlada:** eventos o jobs que **crean o actualizan** filas HC **desde** cierre de `Atencion` / `ConsultaAmbulatoria` (o al revés según política), con **tabla de mapeo o log** (diseño futuro), sin asumir merge en campo único ya.

### Entidades típicamente afectadas por evolución de SoT (futuras iteraciones)

- **Narrativa duplicada:** `Consulta` HC ↔ `ConsultaAmbulatoria` (estrategia: una **fuente operativa autoritativa**, otra derivada o enriquecida).
- **Órdenes:** posible vínculo **opcional** `atencion_id` en modelo de orden (solo como **idea** de diseño futuro — **no aquí**).
- **Archivos:** alinear permisos y contexto (**`ArchivoMedico`** vs **`Documento`**) mediante reglas claras por tipo de archivo.
- **`SignosVitales`:** exponer API estable si debe ser evidencia encuentro-canónico.

### Riesgos

- Altos si se apresura **dual write** sin idempotencia o sin auditoría.
- Riesgo de **inconsistencia temporal** entre capas durante transición.

### Impacto clínico

- **Alto** si se mueve cómo/registran los médicos sin formación.

### Impacto técnico

- **Alto** cuando se implemente (fuera del alcance de este papel): migraciones, servicios, pruebas de regresión.

### Rollback (estratégico)

- Feature flags, **sincronización desactivable**, restauración de política “solo HC” o “solo operativo” documentada.

### Dependencias

- Fases 1–2; métricas de uso de APIs; acuerdo legal sobre expediente.

### Dificultad estimada

- **Alta** en implementación real; **media** en diseño detallado previo.

---

## 6. Fase 4 — Cleanup legacy (no destructivo prematuro)

### Objetivo

Reducir **deuda** cuando el riesgo sea aceptable: eliminar **código muerto** (ViewSets no ensambrados), consolidar **un solo archivo de modelos `emr`**, tests y documentación. **Eliminación de tablas o modelos Django** solo si hay **proyecto aparte** con backup y ventana de mantenimiento — **no** parte del presente roadmap automático.

### Entidades / artefactos

- Código **no referenciado** en `api/urls.py`.
- Duplicación **`models.py` raíz / `emr/models.py`** (cleanup de **fuente**, no de BD en este documento).
- Documentación obsoleta que contradiga `Atencion` canónico operacional.

### Riesgos

- Borrar código aún usado por **cliente no versionado** o script.

### Impacto clínico

- Nulo si solo código muerto; **alto** si se confunde con migración de datos.

### Impacto técnico

- Medio (CI, revisiones exhaustivas).

### Rollback

- Revert git; restauración de rutas si se encapsula en ramas cortas.

### Dependencias

- Cobertura de tests; inventario de consumidores API.

### Dificultad estimada

- **Media**.

---

## 7. Validaciones obligatorias (determinaciones)

### 7.1 ¿Qué entidades pueden quedar deprecadas?

**Deprecation de producto/API/proceso (no necesariamente eliminación de modelo):**

- **Patterns** de escritura duplicada sin vínculo (guías que desaconsejan nuevos desarrollos que ignoren `Atencion`).
- **`api.views`** duplicados de flujos ya cubiertos por `turnos.views` (**deprecación de código**).
- Una de las **internaciones duales** para **nuevas integraciones** externas — la que negocio no elija como primaria (**deprecación de entrada**, no DDL).
- **`solicitudes.Solicitud` como orden lab** donde ya exista **flujo maduro `SolicitudExamen`** (**deprecación de uso paralelo**) — decisión caso por caso.

**Qué **no** se depreca en este roadmap como principio:**

- **`HistoriaClinica`**, **`Consulta` HC**, **`Diagnostico`**, **`Prescripcion`**, **`Tratamiento`** como capa longitudinal (permanecen válidos como dominio de expediente).

### 7.2 ¿Qué migraciones serían peligrosas?

- **Migraciones destructivas**: `DROP`/merge de tablas HC, pérdida de historial clinico.
- **Merge forzado** de `Consulta` HC y `ConsultaAmbulatoria` en una fila **sin** reglas de negocio y reconciliación.
- **Cambiar FKs** de `Diagnostico`/`Prescripcion` sin periodo de doble escritura auditada.
- **Unificar dos `Internacion`** sin mapeo de camas centros/catalogs.
- Cualquier **backfill masivo** que sobrescriba texto clínico sin versión anterior.

### 7.3 ¿Qué APIs podrían romperse?

Cualquier futura consolidación mal gestionada que:

- Quite o renombre **`/api/consultas/`**, **`/api/diagnosticos/`**, **`/api/prescripciones/`**, **`/api/historias-clinicas/`** sin compatibilidad.
- Cambie contratos de **`/api/atenciones/`**, **`registrar-consulta`**, **`consultas-ambulatorias`**, **`documentos`**.
- Altere **filtros usados por reporting** (`historia_clinica_id`, `paciente`, `turno`).

**Mitigación en estrategia:** versionado `/v2/` o campos paralelos antes de retire.

### 7.4 ¿Qué frontend depende de modelos legacy?

Estado del repositorio auditado **en esta sesión:** el **`frontend`** versionado muestra muy pocos archivos fuente (`AuditEventsPage`); **no permite inventario completo** de dependencias SPA histórica.

**Recomendación:** en Fase 1, inventariar **`grep`/OpenAPI** contra:

- `GET/POST …/consultas`, `historias-clinicas`, `atenciones`, `consultas-ambulatorias`, `documentos`, `archivos-medicos`, `solicitudes`, `lab/`, `laboratorio/`.
- Clientes externos, apps móviles, notebooks, BI.

Sin ese inventario, el riesgo de romper cliente es **incierto** (clasificado como **alto proceso**).

### 7.5 ¿Qué reporting podría verse afectado?

- Reportes basados en **conteos de `Consulta` HC** vs **consultas efectivas en agenda** (`Atencion`/`Turno` REALIZADO).
- **Lab:** métricas duplicadas si existen KPIs tanto sobre **`Solicitud`** como **`SolicitudExamen`**.
- **Dx CIE:** hoy correlacionados con **`Diagnostico`→ HC**; si el SoT operativo enfatiza **`ConsultaAmbulatoria`**, los informes CIE pueden **subrepresentar** actividad del día si no hay sync.
- **Internación:** dos fuentes imposibilitan totales sin **regla de exclusión**.

### 7.6 ¿Qué riesgos legales existen?

- **Integridad y conservación** del expediente (no alterar ni perder datos clínicos históricos; trazabilidad de quién escribió qué y cuándo).
- **Consentimiento y acceso** si se cambian reglas de visibilidad (p. ej. archivos médicos ligados solo a HC vs atención).
- **Estándares sectoriales locales** sobre historia clínica única versus acto administrativo — la **doble capa** debe ser **explicable** ante auditorías (documentar ownership y sync).
- Cualquier **decisión automatizada** de copiar Dx/prescripción entre capas sin revisión médica donde la ley exija juicio profesional.

---

## 8. Roadmap recomendado — orden y ritmo

| Orden | Fase | Artefacto de salida sugerido |
|-------|------|-------------------------------|
| 1 | **Fase 1** | Documento boundaries operacional/longitudinal + matriz RACI escritura/consulta. |
| 2 | **Fase 2** | ADRs de deprecación; lista de rutas código “solo mantenimiento”. |
| 3 | **Fase 3** | Diseños de sync (posteriormente implementados por proyecto); flags; pilotos por servicio médico. |
| 4 | **Fase 4** | Limpieza código fuente bajo QA; sin tocar BD salvo proyecto explícito. |

**Cadencia recomendada:** **trimestral** revisión del comité clínico+ingeniería hasta estabilizar reglas.

---

## 9. Recomendaciones arquitectónicas (no implementación)

1. **`Atencion` id estable** como correlación futura opcional desde HC (`consulta.externo_atencion_id` **como idea futura** — sólo después de ACID acordados).
2. **Eventos de dominio internos** (log de auditoría ya existente) para trazar “escritura operativa” antes de proyectar longitudinal.
3. **No fusionar modelo** hasta que política legal y clínica aprueben **fuente autoritativa por tipo de dato** (Dx estructurado vs texto).
4. **Versionar APIs** antes de cualquier retire de campos públicos.

---

## 10. Métricas de éxito (post-implementaciones futuras, orientativas)

- % de encuentros donde existe **`Atencion`** y víncelo explícito a HC cuando reglas lo exigen.
- Reducción de **consultas médicas huérfanas** operativamente (definición en negocio).
- Cero regressions severas en **reportes** comparando snapshots pre/post sprint.

---

*Fin del roadmap de planificación.*
