# Ticket C — Procedimientos no quirúrgicos (habilitación controlada)

**Estado:** cerrado (implementado; sin merge ni producción)  

**Depende de:** Etapa A (A0–A6) + Etapa B  
**SoT diseño:** `docs_synesis/DOC_DISENO_ESTUDIOS_PROCEDIMIENTOS.md` §Etapa C — **este ticket prevalece**  
**Restricción:** LIMS intocable. Sin D+, merge ni producción.  
**Fuera de C:** cirugías, multisesión operativa, quirófano integral.

---

## 0. Coherencia de modelo (cerrada)

| Hecho | Consecuencia |
| --- | --- |
| `RegistroProcedimiento.atencion` es **OneToOne PK** | **No puede** existir registro sin `Atencion` |
| Sin turno **ni** sala | Realización **sin** atención ficticia ni registro huérfano |
| Documentación sin atención | Indicación + `SesionActividad` + **informe versionado** (canónico) |
| Con turno **o** sala | Crear/reutilizar `Atencion` + `RegistroProcedimiento` en la misma TX |
| Atencion incompatible | Bloquear; no eliminar ni crear otra automáticamente |
| Modelos compartidos | No se altera el esquema global de `RegistroProcedimiento`/`Atencion` para forzar registro sin atención |

Vínculo explícito: `SesionActividad.atencion` (aditivo, nullable) + `EstudioComplementario.atencion` espejo cuando aplica.  
Informe canónico: `InformeEstudioComplementario`; FK aditiva opcional `registro_procedimiento` cuando existe registro (sin duplicar texto en `informe_medico` del registro).

---

## 1. Decisiones vigentes

### 1.1 Atención y registro
| Caso | Al marcar realizado |
| --- | --- |
| Hay turno (vigente o histórico de sesión) | Crear/reutilizar Atencion+RegistroProcedimiento; paciente/tipo coherentes |
| Sala asignada **sin** turno (`recurso_id` en la acción) | Igual, Atencion sin turno, `tipo_atencion` sala procedimiento |
| Sin turno ni sala | Solo estado REALIZADO + sesión REALIZADA + identidad; **sin** Atencion/Registro |
| Atencion ya ligada incompatible | 4xx; sin escrituras parciales |

Preservar **realizar sin turno** (camino sin sala).

### 1.2 Identidad y responsable
- DNI y nombre desde **paciente vinculado** (sin duplicar carga ni tocar maestro).
- Si faltan nombre/apellido (o DNI vacío): impedir realización con mensaje claro.
- Profesional responsable: `profesional_id` (Medico) **obligatorio** en realización de PROCEDIMIENTO.
- Actor (quien registra) ≠ profesional: `modificado_por` = actor; `realizado_por` = user del médico (si existe) / no asignar secretaría como realizador.

### 1.3 Secretaría
- Puede: programar/anular (B) + **marcar realizado**.
- **No** adquiere emitir / validar / rectificar informes clínicos.

### 1.4 Informe
- Sí aplica a PROCEDIMIENTO (mismo circuito versionado, archivos, permisos clínicos).
- Canónico = informe versionado; vincular a RegistroProcedimiento **si existe**.
- Emisión → INFORMADO; validación → VALIDADO; entrega → ENTREGADO; rectificación = reglas actuales.
- REALIZADO puede quedar con documentación pendiente.
- No ampliar permisos clínicos por reutilizar matriz administrativa.

### 1.5 UI
- Etiqueta + filtro `tipo_actividad`: Estudios / Procedimientos (cirugías/multi off).
- Circuito: alta → programación opcional → realización → informe/archivos → validación/entrega.
- Conservar reprogramar/anular B.
- Filtros/contadores/paginación con mismos permisos y búsqueda.

### 1.6 Alcance de alta
- Solo `PROCEDIMIENTO` + catálogo `NO_QUIRURGICO` (+ snapshot).
- `CIRUGIA` / `SIN_ASIGNAR` / `QUIRURGICO` rechazados en altas.
- `ESTUDIO` intacto.

---

## 2. Pruebas
- Proc con turno; con sala sin turno; sin ambos (sin Atencion/Registro).
- Secretaría registra con profesional ≠ actor; sin permisos de validación clínica.
- Idempotencia/concurrencia: no duplicar atención, registro ni realización.
- Informe/archivos/rectificación/entrega; incompatibilidad; audit falla → rollback.
- Regresión estudios + B. A0 sin “arreglar”. Diff `laboratorio/` vacío.

---

## 3. Entregables
Paquete exclusivo C, migración(es) aditivas estudios, UI, `CIERRE_ETAPA_C.md`. Sin D+/merge/prod.
