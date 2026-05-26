# DOC_MODELOS_DB — Estructura de datos

**Fecha de generación:** 30 de abril de 2026  
**Actualización (LIMS resultados pendientes / rol laboratorio):** 2 de mayo de 2026  
**Actualización (Fase B3.1 — Microbiología base):** 13 de mayo de 2026  
**Actualización (Fase B3.2 — Microorganismos / aislados / identificación):** 13 de mayo de 2026  
**Actualización (Fase B3.3 — Antibiograma microbiológico):** 13 de mayo de 2026  
**Actualización (Fase B3.4 — Informes microbiológicos):** 14 de mayo de 2026  

**Alcance:** Modelos Django presentes en el repositorio; tablas inferidas por convención `app_label` salvo `db_table` explícito.

**Fuentes revisadas:** `*/models.py`, `auditoria/models.py`, migraciones no listadas exhaustivamente.

---

## Apps o módulos backend con modelos

`pacientes`, `usuarios`, `medicos`, `catalogos`, `turnos`, `historias_clinicas`, `emr`, `archivos_medicos`, `estudios`, `solicitudes`, `integracion_lims`, `internacion`, `laboratorio`, `auditoria`

**Sin modelos de negocio:** `core`, `api` (vacíos).

---

## usuarios

### User (AUTH_USER_MODEL, `db_table='usuarios'`)

- Campos: `AbstractUser` + `rol` (choices: paciente, medico, secretaria, enfermeria, **laboratorio**, admin), `telefono`, `email_verificado`, `telefono_verificado`, `fecha_registro`, `ultima_actividad`
- Relaciones: OneToOne inversas `paciente`, `medico`, `secretaria`, `profile`

### UserProfile (`usuarios_profile`)

- OneToOne `User`; datos demográficos y médicos auxiliares

### Secretaria

- OneToOne `User`; `legajo` unique, `sector`

---

## pacientes.Paciente

- `user` OneToOne SET_NULL → User, `related_name='paciente'`
- Identificación: `nombre`, `apellido`, `dni` **unique**, `fecha_nacimiento`, `sexo` (M/F/O)
- Contacto: `telefono`, `email`, `direccion`
- Obra social: `obra_social`, `numero_afiliado`
- Clínico: `observaciones`, `antecedentes_*`
- `fecha_registro`, `ultima_actualizacion`
- FK User nullable `creado_por`, `modificado_por` (`related_name` `pacientes_creados` / `pacientes_modificados`) — operador staff; distinto de `user` portal
- **Índices:** apellido, nombre

---

## medicos

### Especialidad

- `nombre` unique

### Medico

- `user` OneToOne CASCADE null → User, `related_name='medico'`
- `nombre`, `apellido`, `matricula` **unique**
- `especialidad` FK SET_NULL → Especialidad, `related_name='medicos'`
- `areas_interes_ia`, timestamps

### DisponibilidadMedico

- FK `medico`; `dia_semana`, horas, `duracion_slot_min`, `activo`
- **unique_together:** medico, dia_semana, hora_inicio, hora_fin

### ExcepcionMedico

- FK `medico`; `fecha`, `tipo` BLOQUEO/AJUSTE; horas opcionales
- **unique_together:** medico, fecha, tipo, hora_inicio, hora_fin

---

## catalogos (extracto)

| Modelo | Notas clave |
|--------|-------------|
| DiagnosticoCIE10 | codigo unique; índice descripción |
| Medicamento | catálogo fármacos |
| Procedimiento | FK Especialidad |
| CentroAtencion | tipo centro |
| CentroFisico | codigo choices unique |
| TipoAtencion | codigo choices unique; FK CentroFisico |
| AreaInternacion | codigo unique; FK CentroFisico |
| CamaInternacion | FK AreaInternacion; **unique_together** area+numero |
| EstudioDiagnostico | nombre unique |
| ProcedimientoCatalogo | nombre unique |

---

## turnos

### Recurso (abstract TimestampedModel)

- `Ubicacion` CEHTA/ICPL; `TipoRecurso` consultorio/salas/quirófano
- `nombre` unique, `ubicacion`, `tipo_recurso` indexed, `activo`

### Turno

- FK `paciente` SET_NULL; `medico` SET_NULL; `recurso` CASCADE null
- `fecha_hora_inicio` indexed, `fecha_hora_fin`, `estado` (TextChoices) indexed, `motivo_reserva`
- `clean`/`save` validan intervalo temporal

### Atencion

- `turno` OneToOne SET_NULL null → Turno, `related_name='atencion'`
- `paciente` PROTECT; `medico_principal` PROTECT
- `tipo_atencion` (choices Recurso.TipoRecurso), `tipo_intervencion`, `estado_clinico`
- `fecha_admision` indexed, `fecha_cierre`, `observaciones_generales`

### ConsultaAmbulatoria, RegistroProcedimiento, RegistroQuirurgico

- OneToOne PK = Atencion; campos específicos + FKs a catálogos/médicos; archivos en procedimiento/quirúrgico

---

## historias_clinicas

### HistoriaClinica

- `paciente` OneToOne CASCADE PK

### Consulta

- FK HistoriaClinica; FK Medico null; **Turno** OneToOne null SET_NULL
- Textos clínicos, timestamps; índice `-fecha_hora_consulta`

### Sintoma, Diagnostico, Tratamiento, Prescripcion, Internacion

- Ver archivo fuente para campos (Internacion con FK CamaInternacion catalogos, `numero_internacion` unique, estados alta, etc.)

---

## emr

### SignosVitales

- FK Atencion CASCADE; FK User SET_NULL `registrado_por`; medidas vitales numéricas

### Documento

- FK Atencion CASCADE; `tipo_documento`; `FileField`; FK `usuario_cargador`
- **C6.2:** API sin URL `/media/`; bytes vía `GET /api/documentos/{id}/download/`; DELETE HTTP no permitido (405)

---

## archivos_medicos.ArchivoMedico

- FK Paciente CASCADE; FK Consulta null; `FileField` con validators; `tipo_archivo` choices; `subido_por`
- **C6.2:** API expone `download_url`, `archivo_nombre`, `archivo_size`; `GET …/archivos/{id}/download/`; DELETE → 405

---

## estudios (C6.4.1)

### TipoEstudioComplementario

- Catálogo EMR: `modalidad` (IMAGEN_RX, IMAGEN_TC, IMAGEN_RM, IMAGEN_US, PDF_INFORME_EXTERNO, OTRO); `requiere_informe`, `activo`

### EstudioComplementario

- FK Paciente PROTECT; FK opcional `TipoEstudioComplementario`, `catalogos.EstudioDiagnostico`
- Estados: SOLICITADO → REALIZADO → INFORMADO → VALIDADO → ENTREGADO; ANULADO terminal
- FK opcional Atencion, Consulta HC, solicitudes.Solicitud EMR; placeholders PACS (`study_instance_uid`, `pacs_metadata`)
- Validación `clean()`: coherencia paciente en vínculos

### ArchivoEstudioComplementario

- FK Estudio CASCADE; FK ArchivoMedico PROTECT; `tipo_rol`; unique (estudio, archivo_medico)

### InformeEstudioComplementario

- Versionado; estados BORRADOR/EMITIDO/VALIDADO/ANULADO; `es_vigente` (default False); FK `reemplaza_a` (rectificación)
- `archivo_pdf` FileField — snapshot auditoría sin path/nombre; descarga vía endpoint protegido (C6.4.3)
- **Constraint (C6.4.3):** `uniq_informe_vigente_por_estudio` — `UniqueConstraint` parcial: un solo `es_vigente=True` por `estudio`

---

## solicitudes.Solicitud

- FK Paciente; FK Medico solicitante; M2M medicos_asignados
- Estados, tipo_solicitud, prioridad, fechas, `lims_id` unique nullable, JSON `lims_paneles`, `lims_tipos_examen`
- FK User `creado_por`, `modificado_por`
- **Índices:** estado+fecha, paciente+estado, medico+estado

---

## integracion_lims

### SolicitudExamenLims

- `lims_id` unique; FK paciente, medico; datos texto de sync

### ResultadoExamenLims

- `lims_id` unique; FK solicitud_lims; valores numérico/texto

---

## internacion

### Sector, Cama

- Cama FK Sector; **unique_together** nombre+sector

### Internacion

- FK Paciente, Cama CASCADE; FK Medico; FK DiagnosticoCIE10; fechas; `activo`
- Lógica en `save()` que muta estado de **Cama** (disponibilidad)

---

## laboratorio

### TipoMuestra

- `codigo` unique

### TipoExamen

- `codigo` unique; FK TipoMuestra CASCADE; `precio` decimal; `rango_referencia_texto` (sigue válido para rangos no estructurados)
- **B4.1:** FK opcional `seccion` → `SeccionLaboratorio`; `tipo_resultado` (`TEXTO`/`NUMERICO`/`CUALITATIVO`, default `TEXTO`); `unidad_default`; `rango_min`/`rango_max`; `valor_critico_min`/`valor_critico_max`; `permite_resultado_texto` (default True). Validaciones: rangos y críticos coherentes; sección activa si se asigna.

### PanelExamen

- `codigo` unique; M2M TipoExamen

### SolicitudExamen

- `numero` unique nullable (generado LAB-…); FK Paciente CASCADE; FK Medico interno null; medico externo texto
- M2M tipos_examen, paneles; `estado` choices; índices compuestos
- `clean` coherencia cancelado/resultados

### ResultadoExamen

- FK Solicitud CASCADE; FK TipoExamen PROTECT; FK **`Muestra` opcional** (`null=True`, `blank=True`, `on_delete=PROTECT`, `related_name='resultados'`) — **Fase B2** (`0004_lims_b2_resultado_muestra`); índices `(muestra)` y `(solicitud, muestra)`.
- **`EventoMuestra.accion`:** incluye **`PROCESAMIENTO`** (inicio técnico RECIBIDA/CONSERVADA → EN_PROCESO).
- `valor_obtenido` (**puede estar vacío** mientras el resultado está pendiente: `blank=True`, `default=''` en modelo; migración `laboratorio` 0002+); `es_patologico`; FK User `validado_por`; `fecha_validacion`
- **B4.1:** `valor_numerico` opcional; `unidad`; snapshots `rango_referencia_snapshot`, `rango_min_snapshot`, `rango_max_snapshot`, `valor_critico_min_snapshot`, `valor_critico_max_snapshot`; `es_critico`. Pendiente si `valor_obtenido` vacío aunque exista `valor_numerico`. Snapshots se fijan al cargar (no se recalculan al cambiar el catálogo).
- `save()` llama `full_clean()` (incluye coherencia solicitud–paciente–muestra si hay FK muestra); la **validación de orden** en vista `validar` impide cerrar protocolos con valores vacíos y **rechaza** muestras en estado incompatible si el resultado tiene muestra asociada.
- **unique_together** solicitud + tipo_examen

---

## auditoria.AuditEvent

- `db_table = auditoria_auditevent`
- Append-only; JSON `before_state`/`after_state`; índices entity, actor, action, request_id

---

## Señales

**Pendiente de confirmar** búsqueda global de `@receiver`; no se documentan señales específicas en este análisis.

---

## Migraciones relevantes

- Revisar carpeta `*/migrations/` por app al aplicar cambios; no se reprodujo numeración aquí.

---

## Reglas de eliminación / eliminación lógica

- **AuditEvent:** prohibido borrar por modelo.
- Varios FK **PROTECT** (integridad histórica: TipoExamen en resultados, Medicamento en prescripciones, Paciente en atención).
- **SET_NULL** en vínculos usuario–paciente/médico opcionales.

---

## Trazabilidad

- Auditoría central + logs en vistas; `creado_por` / `modificado_por` en solicitudes y pacientes (API activa); `subido_por` archivos; `validado_por` resultados.

---

## Modelos críticos EMR

`Paciente`, `User`, `Turno`, `Atencion`, `Consulta`, `HistoriaClinica`, `Diagnostico`, `ArchivoMedico`, `Documento`

---

## Modelos críticos LIMS

`SolicitudExamen`, `ResultadoExamen`, `TipoExamen`, `PanelExamen`, `TipoMuestra`

**Fase B0/B1 (app `laboratorio`, definidos en `laboratorio/models_catalog.py` y reexportados en `laboratorio.models`):**

- `AreaLaboratorio`, `SeccionLaboratorio` (unicidad `area`+`codigo`), `TipoContenedor` — catálogos maestros con `activo`.
- `Muestra` — material físico/transaccional: FK `SolicitudExamen` (PROTECT), `Paciente` (validado = paciente de la solicitud), `TipoMuestra`, `TipoContenedor` opcional, `estado` (máquina B1), fechas/usuarios de toma, recepción, rechazo, descarte, `codigo_barra` único (autogenerado `MUE-YYYY-NNNNNN` si vacío).
- `EventoMuestra` — historial append-only por muestra (`accion`, estados anterior/nuevo, `actor`, `metadata`, `request_id`); FK muestra con **PROTECT** para no borrar trazabilidad al intentar borrar la muestra si hay eventos.

---

## Posibles riesgos de integridad

- Dos sistemas de **Internación** + dos de **camas** (catalogos vs internacion app).
- `Solicitud` (app solicitudes) vs `SolicitudExamen` (lab) sin FK obligatoria entre sí.
- `lims_service` y modelos `integracion_lims` pueden duplicar información con `laboratorio`.

---

## Diagrama textual de relaciones principales

```
User ─┬─1:1─ Paciente ─┬─1:1─ HistoriaClinica ─1:N─ Consulta
      │                │                          ├─N:1─ Turno (opc)
      │                └─N:1─ Turno (paciente)
      └─1:1─ Medico ────┴─N:1─ Turno (medico)

Turno ─1:1─ Atencion ─1:1─ ConsultaAmbulatoria / Registro*
                ├─N─ Documento (emr)
                └─N─ SignosVitales

Paciente ─1:N─ SolicitudExamen ─1:N─ ResultadoExamen ─N:1─ TipoExamen ─N:1─ TipoMuestra  
`ResultadoExamen` ─N:1─ `Muestra` (opcional, Fase B2); `Muestra` ─N:1─ `SolicitudExamen`

`Muestra` ─1:N─ `EstudioMicrobiologia` ─1:N─ `SiembraMicrobiologia` ─1:N─ `LecturaCultivo`  (Fase B3.1)
`SiembraMicrobiologia` ─N:1─ `MedioCultivo`
`LecturaCultivo` ─1:N─ `AisladoMicrobiologico` ─1:N─ `IdentificacionMicroorganismo` ─N:1─ `Microorganismo`  (Fase B3.2)
```

### Microbiología base (Fase B3.1)

App: `laboratorio` — modelos definidos en `laboratorio/models_microbiologia.py` y reexportados desde `laboratorio/models.py` para registro.

| Modelo | Campos clave | Notas |
|--------|--------------|-------|
| `MedioCultivo` | `codigo` (unique), `nombre`, `tipo`, `descripcion`, `activo`, timestamps | Catálogo administrativo (escritura solo admin); se desactiva en vez de borrar. |
| `EstudioMicrobiologia` | `numero` (unique, autogenerado `MIC-YYYY-NNNNNN`), `solicitud` (PROTECT), `muestra` (PROTECT, `related_name=estudios_microbiologia`), `paciente` (PROTECT), `tipo_estudio` (choices), `estado` (choices), `observaciones`, `fecha_inicio`, `fecha_cierre`, `responsable`, `cancelado_por`, `fecha_cancelacion`, `motivo_cancelacion`, timestamps | Estados cableados (B3.1–B3.4): `PENDIENTE` → `RECIBIDO` → `SEMBRADO` → `LECTURA_PRELIMINAR` → `IDENTIFICACION` → `ANTIBIOGRAMA` → `LISTO_PARA_VALIDAR` → `VALIDADO` → `INFORMADO`, con `CANCELADO` desde no terminales; terminales: `CANCELADO`, `INFORMADO`. El estado **no** se modifica por PATCH. Validación en `clean`: muestra ∈ {`RECIBIDA`, `EN_PROCESO`} al crear; consistencia solicitud/paciente/muestra. Índices: `(solicitud, estado)`, `(muestra, estado)`, `(paciente, estado)`, `(estado, created_at)`, `(fecha_inicio)`. |
| `SiembraMicrobiologia` | `estudio` (PROTECT, `related_name=siembras`), `muestra` (PROTECT), `medio` (PROTECT), `fecha_siembra`, `sembrado_por`, `condicion_incubacion`, `temperatura_c`, `atmosfera`, `observaciones`, `estado` (SEMBRADA/CANCELADA), timestamps | Validación en `clean`: misma muestra del estudio; medio activo; estudio no cancelado; muestra `RECIBIDA`/`EN_PROCESO` al crear. Crear siembra dispara transición auto de estudio a `SEMBRADO`. |
| `LecturaCultivo` | `siembra` (PROTECT, `related_name=lecturas`), `estudio` (PROTECT), `fecha_lectura`, `leido_por`, `horas_incubacion` ≥ 0, `crecimiento` (choices), `descripcion_colonias`, `tincion_gram`, `observaciones`, `es_preliminar`, timestamps | Validación: `siembra.estudio_id == estudio_id`; estudio y siembra no cancelados; `fecha_lectura >= siembra.fecha_siembra`. `es_preliminar=True` sobre estudio `SEMBRADO` lo pasa a `LECTURA_PRELIMINAR`. |

**Fuera de modelo en B3.1**: `Microorganismo`, `AisladoMicrobiologico`, `IdentificacionMicroorganismo`, `Antibiotico`, `Antibiograma`, `ResultadoAntibiotico`, `InformeMicrobiologia` (postergados a B3.2/B3.3/B3.4). Microbiología **nunca** se serializa en `ResultadoExamen.valor_obtenido`.

Migración: `laboratorio/migrations/0005_lims_b3_1_microbiologia_base.py` (aditiva, no destructiva).

### Microbiología B3.2 — Microorganismos, aislados, identificación

App: `laboratorio` — modelos en `laboratorio/models_microbiologia.py`. Migración: `laboratorio/migrations/0006_lims_b3_2_microbiologia_aislados.py` (aditiva: 3 modelos nuevos + `AlterField` no destructivo sobre `EstudioMicrobiologia.estado` para sumar el choice `IDENTIFICACION`).

| Modelo | Campos clave | Notas |
|--------|--------------|-------|
| `Microorganismo` | `codigo` (unique), `nombre`, `genero`, `especie`, `grupo`, `descripcion`, `activo`, timestamps | Catálogo administrativo; escritura solo admin; se desactiva con `activo=False`. Índices: `(activo, nombre)`, `(genero, especie)`. |
| `AisladoMicrobiologico` | `estudio` (PROTECT, `related_name=aislados`), `lectura_origen` (PROTECT, `related_name=aislados`), `microorganismo` (PROTECT, opcional), `estado` (`SOSPECHADO`/`IDENTIFICADO`/`DESCARTADO`), `descripcion`, `cantidad`, `significancia` (choices), `requiere_antibiograma` (bool), `observaciones`, `creado_por`, `descartado_por`, `fecha_descarte`, `motivo_descarte`, timestamps | Estado cableado: `SOSPECHADO` → `IDENTIFICADO` (auto al crear primera identificación) o `DESCARTADO` (acción con motivo). `estado` y `microorganismo` no se editan vía PATCH. Validaciones `clean`: lectura del mismo estudio; estudio no cancelado; siembra de la lectura no cancelada; microorganismo activo si se asigna; `IDENTIFICADO` requiere microorganismo. Índices: `(estudio, estado)`, `(lectura_origen)`, `(microorganismo, estado)`, `(significancia)`. |
| `IdentificacionMicroorganismo` | `aislado` (PROTECT, `related_name=identificaciones`), `microorganismo` (PROTECT, `related_name=identificaciones`), `metodo`, `resultado`, `confianza` (0-100 opcional), `fecha`, `realizado_por`, `observaciones`, timestamps | **Append-only**: sin PATCH ni DELETE. Validaciones `clean`: microorganismo activo; aislado no `DESCARTADO`; estudio no `CANCELADO`; `confianza` ∈ [0, 100]. Índices: `(aislado, -fecha)`, `(microorganismo)`. |

Cambio adicional en `EstudioMicrobiologia.ESTADO_CHOICES`: se agrega `IDENTIFICACION` (cableado en B3.2). El servicio promociona el estudio desde `SEMBRADO` o `LECTURA_PRELIMINAR` cuando se crea la primera identificación válida.

**Fuera de modelo en B3.2**: `Antibiotico`, `Antibiograma`, `ResultadoAntibiotico`, `InformeMicrobiologia` (postergados a B3.3/B3.4).

### Microbiología B3.3 — Antibiograma

App: `laboratorio` — modelos en `laboratorio/models_microbiologia.py`. Migración: `laboratorio/migrations/0007_lims_b3_3_microbiologia_antibiograma.py` (aditiva: 3 modelos nuevos + `AlterField` no destructivo sobre `EstudioMicrobiologia.estado` para sumar el choice `ANTIBIOGRAMA` + `UniqueConstraint(antibiograma, antibiotico)` en `ResultadoAntibiotico`).

| Modelo | Campos clave | Notas |
|--------|--------------|-------|
| `Antibiotico` | `codigo` (unique), `nombre`, `familia`, `descripcion`, `activo`, timestamps | Catálogo administrativo; escritura solo admin; se desactiva con `activo=False` (sin DELETE). Índices: `(activo, nombre)`, `(familia)`. |
| `Antibiograma` | `aislado` (PROTECT, `related_name=antibiogramas`), `estado` (`PENDIENTE`/`EN_PROCESO`/`COMPLETO`/`CANCELADO`), `metodo`, `fecha_inicio` (default `now`), `fecha_resultado` (set al completar), `realizado_por`, `cancelado_por`, `fecha_cancelacion`, `motivo_cancelacion`, `observaciones`, timestamps | Validación `clean` en alta: aislado `IDENTIFICADO` con microorganismo y estudio no `CANCELADO`. PATCH solo `metodo`/`observaciones` y solo si no está `COMPLETO`/`CANCELADO`. Estado/fechas/motivo cambian solo por servicios (`crear_antibiograma`, `aplicar_completar_antibiograma`, `aplicar_cancelar_antibiograma`). Índices: `(aislado, estado)`, `(estado, created_at)`, `(fecha_inicio)`. |
| `ResultadoAntibiotico` | `antibiograma` (PROTECT, `related_name=resultados`), `antibiotico` (PROTECT, `related_name=resultados`), `halo_mm` (Decimal opcional), `mic`, `interpretacion` (`S`/`I`/`R`/`SDD`/`NO_APLICA`), `observaciones`, timestamps | `UniqueConstraint(antibiograma, antibiotico)`. Validaciones `clean`: antibiótico activo; antibiograma no `COMPLETO` ni `CANCELADO`; interpretación dentro de choices. PATCH solo `halo_mm`/`mic`/`interpretacion`/`observaciones` (no cambia `antibiograma`/`antibiotico`). Índices: `(antibiograma)`, `(antibiotico)`, `(interpretacion)`. |

Cambio adicional en `EstudioMicrobiologia.ESTADO_CHOICES`: se agrega `ANTIBIOGRAMA` (cableado en B3.3). El servicio promociona el estudio desde `IDENTIFICACION`, `LECTURA_PRELIMINAR` o `SEMBRADO` al crear antibiograma o primer resultado (idempotente).

### Microbiología B3.4 — Informes, validación, informado

App: `laboratorio` — modelo en `laboratorio/models_microbiologia.py`. Migración: `laboratorio/migrations/0008_lims_b3_4_microbiologia_informes.py` (aditiva: `InformeMicrobiologia` + `AlterField` no destructivo sobre `EstudioMicrobiologia.estado` para sumar los choices `LISTO_PARA_VALIDAR`, `VALIDADO`, `INFORMADO` + `UniqueConstraint` condicional: a lo sumo un informe `FINAL` con `estado ≠ ANULADO` por estudio).

| Modelo | Campos clave | Notas |
|--------|--------------|-------|
| `InformeMicrobiologia` | `estudio` (PROTECT, `related_name=informes`), `tipo` (`PRELIMINAR`/`FINAL`), `estado` (`BORRADOR`/`EMITIDO`/`VALIDADO`/`ANULADO`), `texto`, `version`, `emitido_por`, `fecha_emision`, `validado_por`, `fecha_validacion`, `reemplaza_a` (self FK), `observaciones`, `motivo_anulacion`, `anulado_por`, `fecha_anulacion`, timestamps | Alta vía servicio `crear_informe_borrador`; PATCH solo en `BORRADOR`. Emisión/anulación/validación solo por servicios y acciones API. `ANULADO` en `FINAL` libera el cupo del constraint único. |

Cambio adicional en `EstudioMicrobiologia.ESTADO_CHOICES`: se agregan `LISTO_PARA_VALIDAR`, `VALIDADO`, `INFORMADO` (cableados en B3.4 vía informe final + `validar` + `marcar-informado`). `ESTADOS_TERMINALES` incluye `INFORMADO` además de `CANCELADO`.

---

## Riesgos o inconsistencias

- Modelo `Internacion` en **historias_clinicas** vs **internacion** — relaciones distintas.
- Permisos de datos no reflejados a nivel DB (todo en capa API).

---

## Pendiente de confirmar

- Señales Django registradas.
- Políticas de retención y borrado de archivos en media.
