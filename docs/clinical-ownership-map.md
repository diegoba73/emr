# Mapa de ownership clínico y source of truth

Documento derivado de [`clinical-domain-audit.md`](./clinical-domain-audit.md). **No modifica código**, **no propone migraciones** y **no prescribe** eliminar `historias_clinicas` ni el modelo `Consulta`. Su propósito es **formalizar responsabilidades**, **límites (boundaries)** y **estado de cada entidad** respecto a autoría y verdad de datos.

---

## 1. Leyenda

### Tipo (`Tipo`)

| Valor | Significado |
|--------|-------------|
| **Scheduling** | Agenda, cupo, recurso temporal; no es en sí el registro clínico narrativo. |
| **ClinicalEncounter** | Instancia de encuentro / episodio / contenedor bajo el cual tiene sentido hablar de “esta visita”. |
| **ClinicalEvidence** | Texto, diagnóstico estructurado, prescripción, archivo, medición, informe: contenido usable clínicamente. |
| **OrderManagement** | Pedido, solicitud, resultado de pedido; workflow de órdenes. |
| **Administrative** | Maestro, configuración, catálogo, identidad administrativa. |

### Estado (`Estado`)

| Valor | Significado |
|--------|-------------|
| **canonical** | En la práctica actual del diseño, esta entidad **es** la referencia esperada para ese rol (aunque existan duplicados narrativos en otra parte). |
| **duplicated** | Misma responsabilidad conceptual **repetida** en otra entidad sin unión referencial única. |
| **transitional** | Patrón coexistiendo con otro; vigencia o migración de uso **no está cerrada en el modelo**. |
| **legacy** | Código o superficie duplicada (p. ej. ViewSet alternativo) que compite con el camino principal sin estar “oficialmente” retirada. |
| **unclear** | Límite de ownership **no deducible** solo del esquema (depende de proceso / cliente / convención). |

---

## 2. Clasificación por entidad

### 2.1 Identidad y historia longitudinal

| Entidad | Responsabilidad | Source of Truth (rol) | Tipo | Estado |
|---------|-----------------|------------------------|------|--------|
| **Paciente** | Identidad demográfica del sujeto de atención | **Identidad de paciente**: datos de persona/ficha | Administrative | canonical |
| **HistoriaClinica** | Contenedor 1:1 del expediente longitudinal por paciente | **Agregación HC** “por paciente”; no es un encuentro en sí | ClinicalEncounter | canonical (como *container* de chart, no como visita operativa) |
| **historias_clinicas.Consulta** | Registrar una **visita/consulta en el eje HC**; texto clínico amplio; opcional enlace a **Turno** | **Encuentro longitudinal** + texto de consulta cuando el flujo usa `/consultas/` | ClinicalEncounter | duplicated (vs `Atencion`+`ConsultaAmbulatoria`), **transicional** (convive con flujo operativo) |

### 2.2 Agenda y encuentro operativo (turnos)

| Entidad | Responsabilidad | Source of Truth (rol) | Tipo | Estado |
|---------|-----------------|------------------------|------|--------|
| **Recurso** | Lugar/tipo de cupo planificable | Configuración de **dónde y qué** se agenda | Administrative | canonical |
| **Turno** | Reserva temporal: paciente, médico, recurso, estado, motivo corto | **Cupos y estado de agenda** (`RESERVADO`…`REALIZADO`) — *no* el contenido clínico de la visita | Scheduling | canonical |
| **Atencion** | Contenedor del **encuentro clínico operativo** vinculado al turno; estado de la visita desde la perspectiva EMR operativo | **Encuentro bajo `/api/atenciones/`** (propósito declarado en el modelo) | ClinicalEncounter | canonical (eje **operativo**) |
| **ConsultaAmbulatoria** | Registro **1:1** con `Atencion`: narrativa tipo consulta (anamnesis, examen, plan, dx texto, antecedentes…) | Evidencia de **consulta externa ligada al encuentro** cuando el recurso es consultorio — **truth operativa para ese texto** en ese FK | ClinicalEvidence | duplicated (Campos paralelos a `Consulta` HC); **canonical** dentro del lazo **Atencion** |

### 2.3 Registros clínicos por tipo de recurso / intervención

| Entidad | Responsabilidad | Source of Truth (rol) | Tipo | Estado |
|---------|-----------------|------------------------|------|--------|
| **RegistroProcedimiento** | Estudio/procedimiento para la atención: informe, hallazgos, catálogo, archivo adjunto | Evidencia de **procedimiento/diagnóstico por imagen** atada a una `Atencion` | ClinicalEvidence | canonical (en su familia de registro hijo 1:1) |
| **RegistroQuirurgico** | Acto quirúrgico/ protocolo / equipo / Dx pre y post operatorio | Evidencia de **cirugía/hemodinamia** ligada a `Atencion` | ClinicalEvidence | canonical (en su familia de registro hijo 1:1) |

### 2.4 Evidencia anclada a HC (`historias_clinicas`)

| Entidad | Responsabilidad | Source of Truth (rol) | Tipo | Estado |
|---------|-----------------|------------------------|------|--------|
| **Diagnostico** | Dx con **CIE-10**, nombre, texto; M2M síntomas | **Único vínculo estructural a catálogo CIE** en modelo auditado: depende de `Consulta` HC | ClinicalEvidence | canonical (para **codificación CIE** en ese eje); **duplicated** (conceptualmente vs texto en `ConsultaAmbulatoria`) |
| **Sintoma** | Catálogo de síntomas para asociar a diagnósticos | Referencia léxica / taxonómica | Administrative | canonical |
| **Tratamiento** | Tratamiento descrito ligado a `Consulta` HC | Truth de **plan terapéutico estructurado por consulta HC** | ClinicalEvidence | canonical en eje HC; **no** enlazado a `Atencion` en modelo |
| **Prescripcion** | Prescripción por medicamento de catálogo ligada a `Consulta` HC | Truth de **prescripción medicamentosa estructurada** en ese eje | ClinicalEvidence | canonical en eje HC; **no** enlazado a `Atencion` en modelo |
| **historias_clinicas.Internacion** | Internación “ricca”: estado, cama catalogada, centro/área, motivo/plan/número, opcional origen Turno | Truth de **gestión de internación** expuesta por `/api/internaciones/` | ClinicalEncounter | duplicated (nombre y dominio concurrente); **unclear** qué proceso debe usar cada API cliente |

### 2.5 Internación (app `internacion`)

| Entidad | Responsabilidad | Source of Truth (rol) | Tipo | Estado |
|---------|-----------------|------------------------|------|--------|
| **internacion.Sector** | Sectores de camas | Configuración de infraestructura | Administrative | canonical **en ese módulo** |
| **internacion.Cama** | Cama dentro de sector | Inventario de **cama física** | Administrative | canonical **en ese módulo** |
| **internacion.Internacion** | Ocupación de cama simplificada, Dx texto/CIE, alta | Episodio de internación ligado al modelo de **camas** de esa app | ClinicalEncounter | **duplicated** (vs `historias_clinicas.Internacion`) |

### 2.6 Órdenes y laboratorio

| Entidad | Responsabilidad | Source of Truth (rol) | Tipo | Estado |
|---------|-----------------|------------------------|------|--------|
| **solicitudes.Solicitud** | Órdenes genéricas (lab, imagen, etc.) por paciente; integración LIMS vía metadata | Truth de **pedido “capa aplicación”** cuando se usa `/api/solicitudes/` y `lims_*` | OrderManagement | **transitional** (paralela a modelo lab nativo); **unclear** relación dominante proyecto a proyecto |
| **laboratorio.SolicitudExamen** | Orden de laboratorio con workflow y protocolo LAB | Truth de **solicitud y estado de proceso LIMS EMR** en ese módulo | OrderManagement | canonical **para lab nativo EMR** en código auditado |
| **laboratorio.ResultadoExamen** | Resultado por tipo de examen | Truth del **valor validado/reportado** en ese flujo | ClinicalEvidence | canonical (dentro del flujo `SolicitudExamen`) |

### 2.7 Infraestructura de laboratorio (catálogo)

| Entidad | Responsabilidad | Source of Truth (rol) | Tipo | Estado |
|---------|-----------------|------------------------|------|--------|
| **TipoMuestra**, **TipoExamen**, **PanelExamen** | Catálogo de muestras, tests y paneles | **Catálogo** de trabajo de laboratorio | Administrative | canonical (en ese dominio) |

### 2.8 Archivos y documentos EMR

| Entidad | Responsabilidad | Source of Truth (rol) | Tipo | Estado |
|---------|-----------------|------------------------|------|--------|
| **archivos_medicos.ArchivoMedico** | Binario/metadata con **Paciente** y opcional **Consulta HC** | Truth de archivo **paciente‑centrado**, contextualizable por consulta HC **no por Atención** | ClinicalEvidence | duplicated (vs `Documento` por encounter); canonical **para permisos actuales** basados en `Consulta` HC |
| **emr.Documento** | Documento por **tipo** ligado obligatoriamente a `Atencion` | Truth del **adjunto/documento formal del encuentro EMR operativo** | ClinicalEvidence | canonical **en sentido encuentro‑operativo** |
| **emr.SignosVitales** | Medidas ligadas a `Atencion` | Truth esperable de **SV por encuentro operativo** (si el API está expuesto por completo al cliente) | ClinicalEvidence | **unclear**/transitional: modelo existe; Router principal **no registra** el ViewSet en auditoría |

### 2.9 Duplicidad de código fuente (no es tabla de BD)

| Artefacto | Responsabilidad | Source of Truth (rol) | Tipo | Estado |
|-------------|-----------------|------------------------|------|--------|
| **`models.py` (raíz) vs `emr/models.py`** | Definición duplicada con `Meta.app_label = 'emr'` | Divergencia potencial en `Documento.TipoDocumento`; **truth efectiva depende del import usado por el runtime** | Administrative | legacy (duplicado de definición fuente), **risk** de divergencia |
| **`api.views.AtencionViewSet` vs `turnos.views.AtencionViewSet`** | Dos implementaciones de API para mismo dominio conceptual | **`api/urls.py` registra la de `turnos.views`** — truth de **routing** es `turnos` | Administrative | legacy (código paralelo competidor) |

---

## 3. Source of Truth — resumen por concepto

| Concepto | Donde el modelo permite afirmación más fuerte hoy |
|----------|-----------------------------------------------------|
| **Encuentro operativo (workflow turno/atención)** | `Atencion` (+ registro hijo 1:1 según recurso). |
| **Consulta longitudinal en expediente por paciente** | `HistoriaClinica` → `Consulta` (HC). |
| **Codificación Dx CIE‑10 relacionada con consulta** | `Diagnostico` → `Consulta` (HC). |
| **Narrativa de consulta en el día (sin tabla Dx CIE ligada)** | `ConsultaAmbulatoria` (ligada solo a `Atencion`). |
| **Agenda/cupo** | `Turno` `Recurso`. |
| **Orden lab tipo protocolo LAB en app laboratorio** | `SolicitudExamen` / `ResultadoExamen`. |
| **Orden genérica integración LIMS (app solicitudes)** | `solicitudes.Solicitud`. |
| **Documento oficial del encuentro EMR (/documentos)** | `emr.Documento` → `Atencion`. |
| **Archivo clínico con permisos médico–paciente actuales (código revisado)** | `ArchivoMedico` contextualizado por **HC Consulta**, no por `Atencion`. |

Esto describe **truth por boundary**, **no** “una sola fila verdadera en todo el hospital” sin convenciones de proceso.

---

## 4. Boundaries declarados (sin eliminar HC)

### 4.1 Boundary A — **Operativo (scheduled encounter)**

```
Turno → Atencion → (ConsultaAmbulatoria | RegistroProcedimiento | RegistroQuirurgico | Documento | SignosVitales — modelo)
```

- **Ownership del “día en consultorio/imagen/quirófano”** en sentido código: **`Atencion`**.
- **Ownership del texto de esa consulta en consultorio**: **`ConsultaAmbulatoria`** (hijo único).

### 4.2 Boundary B — **Longitudinal (historia por paciente)**

```
Paciente ← HistoriaClinica ← Consulta → (Diagnostico, Prescripcion, Tratamiento …)
```

- **Ownership del expediente y de la línea temporal HC** cuando se usa ese API: **`Consulta`** y sus hijos.
- **`Consulta` no debe interpretarse desde este documento como “a eliminar”;** cumple función de **boundary B** separada **formalmente** del boundary operativo salvo vínculos opcional `Turno`.

### 4.3 Boundary paralelo implícito

- Un mismo `Turno` puede tener ** hasta dos “encuentros” modelados diferente** (`Consulta` HC y `Atencion`), sin FK cruzado entre contenidos narrativos. Eso es **boundary solapado**, no fusionado.

---

## 5. Validaciones obligatorias (respuestas explícitas)

### 5.1 ¿Cuál es el encounter clínico “oficial” del sistema?

- **Formal en código (documentado en el modelo):** **`Atencion`** es el único objeto explícitamente descrito como *“contenedor principal para un encuentro clínico”* y es el pivote API bajo **`/api/atenciones/`**.
- **Coexistente como encounter de expediente longitudinal:** **`historias_clinicas.Consulta`** es encuentro‑de‑consulta **en el modelo de historia clínica** (registro diferente).
- Por tanto hay **dos encounters “oficiales” en dominios distintos** (operativo vs longitudinal), no uno único fusionado.

### 5.2 ¿Qué entidades son puramente logísticas?

- **`Turno`**: gestión temporal y estado de reserva (**Scheduling**).
- **`Recurso`**: definición física/lógica de **dónde** se atiende (**Administrative**/operational master).
- **Partes administrativas** de catálogos (`TipoExamen`, `PanelExamen`, `Sintoma` como nomenclatura, etc.) (**Administrative**).

*Nota:* `motivo_reserva` en `Turno` es texto corto de agenda — **limitado** como evidencia frente al contenido de consulta formal.

### 5.3 ¿Qué entidades contienen evidencia clínica real?

Sin listar todas de nuevo: toda la fila marcada **`ClinicalEvidence`** en la tabla (incluye `ConsultaAmbulatoria`, `Diagnostico`, `Consulta` [campos texto], procedimientos, quirúrgico, presc/tratamiento, resultados lab, archivos/documentos donde aplique).

### 5.4 ¿Qué entidades duplican información clínica?

- **`Consulta`** (HC) **↔** **`ConsultaAmbulatoria`** (campos homónimos narrativos: anamnesis, examen, diagnostico texto, plan).
- **`historias_clinicas.Internacion` ↔ `internacion.Internacion`**: episodios de hospitalización paralelos sin unión en tabla.
- **`solicitudes.Solicitud`** **↔** **`laboratorio.SolicitudExamen`**: duplicidad de modelo de orden de laboratorio (**OrderManagement**, no contenido texto clínico ampli pero sí **intención** de orden).
- **Posibles varias capas de diagnóstico en texto** (`Consulta.diagnostico_presuntivo`, `ConsultaAmbulatoria.diagnostico_*`, quirúrgico, internación…).

### 5.5 ¿Qué entidades **deberían depender de `Atencion`**?

*Fraseado como consecuencia del boundary operativo objetivo (**Turno → Atencion → evidencias**); **no** es una orden de migración.*

| Si el boundary deseado es “toda evidencia generada durante la visita agendada cuelga del encuentro operativo…” | Estado actual relevante |
|---------------------------------------------------------------------------------------------------------------|-------------------------|
| **Ya dependen conceptualmente por FK** | `ConsultaAmbulatoria`, `RegistroProcedimiento`, `RegistroQuirurgico`, `Documento`. |
| **Modeladas con FK a Atención** | `SignosVitales` ( **`emr` ) |
| **No dependen de `Atencion` por modelo** | `Consulta`, `Diagnostico`, `Prescripcion`, `Tratamiento`; `ArchivoMedico` (solo `Paciente` + opcional HC `Consulta`); `Solicitud`, `SolicitudExamen` (solo `Paciente`; lab sin encounter). |

Eso marca ** donde el esquema actual **no fuerza dependencia física respecto del boundary operativo.**

### 5.6 ¿Qué entidades **no deberían** almacenar información clínica (ideal de separación conceptual)?

*Criterio: separación *clásica agenda vs clínico* — observación normativa ligera sin migración.*

- **`Turno`** y **`Recurso`**: están orientados a **scheduling**/config; el código las usa como soporte temporal, **no como repositorio primario del acto clínico narrativo**.
- **`Recurso`**: configuración únicamente **sin historia clínica**.
- **`Solicitud` / solicitudes**: son **órdenes y workflow** (**OrderManagement**); podrían contener texto en descripción pero la ** función primaria es pedido/seguimiento**, no el encuentro completo (**la auditoría ya notó orden desacoplada del encounter**).

---

## 6. Validación obligatoría: ¿Es correcto `Turno → Atención → evidencia / documentos / procedimientos / resultados`?

### 6.1 Lo que el código **confirma** en ese spine

Para el dominio **`turnos` + `emr`** + registros hijos:

- **`Atencion`** concentra el encuentro **operativo**.
- Los hijos 1:1 y los documentos bajo **`Atencion`** alinean con un **patrón spine claro** para esa parte del EMR.

**Ventajas (observables):**

- **Trazabilidad operativa fuerte**: un mismo ID de encuentro agrupa texto de consulta externa (`ConsultaAmbulatoria`), procedimiento, quirúrgico, documentos.
- **Compatibilidad con agenda**: `Turno` estados y realizacion encajan con ciclo RESERVADO → REALIZADO.
- **Extensibilidad por tipo_recurso** vía registros especializados.

**Riesgos:**

- Si el producto espera **única historia por paciente** sin bifurcar, coexisten **`Consulta` HC + `ConsultaAmbulatoria`**, generando **doble narrativa** para la misma cita física posiblemente.
- **Órdenes y resultados de lab** en gran parte **paciente‑centrados**, no encuentro‑centrados → el spine **se rompe conceptualmente** al salir del módulo `turnos/emr`.

**Inconsistencias actuales (ya documentadas, formalizadas como boundary clash):**

- Dx **CIE estructurado** en HC **`Diagnostico`**, Dx **libre** en **`ConsultaAmbulatoria`**.
- Archivos médicos **`ArchivoMedico`** autorizados en código por vínculo a **`Consulta` HC**, no **`Atencion`**.
- **Dos sistemas de internación** y **dos de solicitud lab‑like**.

---

## 7. Responsabilidades posiblemente incorrectas o frágiles (detección, no corrección)

| Fenómeno | Por qué se marca como problema de ownership |
|----------|--------------------------------------------|
| Mismo **`Turno`** puede anclar **dos encuentros diferentes** (`Consulta` HC y `Atencion`) | No hay unicidad conceptual de encounter a nivel modelo global. |
| **Permiso de archivo médico** basado solo en **`Consulta` HC**, no **`Atencion`** | Boundary de seguridad puede no alinearse con boundary operativo. |
| **`SignosVitales`** sin entrada en Router principal auditado | Evidencia de encuentro posiblemente **no expuesta uniformemente**. |
| **Implementación paralela `api.views`** de flujos de atención | Riesgo de **mantenimiento** y de “truth de comportamiento API” bifurcada. |

---

## 8. Entidades legacy / transicionales — lista corta

| Etiqueta | Entidades / artefactos |
|----------|------------------------|
| **legacy** (código) | Implementaciones duplicadas en `api.views` donde el router usa `turnos.views`; segundo archivo `models.py` raíz vs `emr/models.py`. |
| **transicional** | Coexistencia `solicitudes.Solicitud` y `laboratorio.SolicitudExamen`; co‑uso posible HC vs spine operativo. |
| **duplicated** dominio | Dos `Internacion`; campos paralelos HC vs `ConsultaAmbulatoria`; órdenes lab duales. |

---

*Documento cerrado como mapa formal de ownership. **Las decisiones sobre migraciones, consolidaciones o retiros de modelo quedan explícitamente fuera de alcance.***
