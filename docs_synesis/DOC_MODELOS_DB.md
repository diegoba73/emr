# DOC_MODELOS_DB — Estructura de datos

**Fecha de generación:** 30 de abril de 2026  
**Actualización (LIMS resultados pendientes / rol laboratorio):** 2 de mayo de 2026  

**Alcance:** Modelos Django presentes en el repositorio; tablas inferidas por convención `app_label` salvo `db_table` explícito.

**Fuentes revisadas:** `*/models.py`, `auditoria/models.py`, migraciones no listadas exhaustivamente.

---

## Apps o módulos backend con modelos

`pacientes`, `usuarios`, `medicos`, `catalogos`, `turnos`, `historias_clinicas`, `emr`, `archivos_medicos`, `solicitudes`, `integracion_lims`, `internacion`, `laboratorio`, `auditoria`

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

---

## archivos_medicos.ArchivoMedico

- FK Paciente CASCADE; FK Consulta null; `FileField` con validators; `tipo_archivo` choices; `subido_por`

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

- `codigo` unique; FK TipoMuestra CASCADE; `precio` decimal; `rango_referencia_texto`

### PanelExamen

- `codigo` unique; M2M TipoExamen

### SolicitudExamen

- `numero` unique nullable (generado LAB-…); FK Paciente CASCADE; FK Medico interno null; medico externo texto
- M2M tipos_examen, paneles; `estado` choices; índices compuestos
- `clean` coherencia cancelado/resultados

### ResultadoExamen

- FK Solicitud CASCADE; FK TipoExamen PROTECT; FK **`Muestra` opcional** (`null=True`, `blank=True`, `on_delete=PROTECT`, `related_name='resultados'`) — **Fase B2** (`laboratorio` migración `0004_lims_b2_resultado_muestra`).
- `valor_obtenido` (**puede estar vacío** mientras el resultado está pendiente: `blank=True`, `default=''` en modelo; migración `laboratorio` 0002+); `es_patologico`; FK User `validado_por`; `fecha_validacion`
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

- Auditoría central + logs en vistas; `creado_por` en solicitudes; `subido_por` archivos; `validado_por` resultados.

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
```

---

## Riesgos o inconsistencias

- Modelo `Internacion` en **historias_clinicas** vs **internacion** — relaciones distintas.
- Permisos de datos no reflejados a nivel DB (todo en capa API).

---

## Pendiente de confirmar

- Señales Django registradas.
- Políticas de retención y borrado de archivos en media.
