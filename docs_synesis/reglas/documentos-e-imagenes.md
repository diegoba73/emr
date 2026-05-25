# Documentos e imágenes clínicas (C6.2)

**Estado:** C6.2 [IMPLEMENTADO] — hardening de seguridad y auditoría.  
**Incluye (C6.4.1):** backend `estudios.EstudioComplementario` (instancia clínica, estados, informes, archivos vía `ArchivoMedico`).  
**No incluye:** PACS/DICOM/RIS, visor OHIF, frontend estudios (C6.4.2), soft-delete con motivo en `ArchivoMedico`.

## Dos vías de adjuntos (sin unificar aún)

| Entidad | Vínculo | API | Uso |
|---------|---------|-----|-----|
| `archivos_medicos.ArchivoMedico` | `Paciente` (+ opcional `historias_clinicas.Consulta`) | `/api/archivos-medicos/archivos/` | Tomografías, DICOM, rayos, PDF clínico por paciente |
| `emr.Documento` | `turnos.Atencion` | `/api/documentos/` | Informes/estudios ligados a una atención |

`ArchivoMedico` / `Documento` no reemplazan el flujo profesional de estudios complementarios (ver C6.4.1).

## Integridad `consulta_id` (C6.2-B)

Al crear o actualizar `ArchivoMedico` con `consulta_id`:

- la consulta debe existir y pertenecer al mismo `paciente_id` (HC);
- el paciente no puede asociar consultas ajenas;
- el médico no puede asociar consulta de otro médico ni de paciente sin vínculo;
- cambiar `paciente_id` sin actualizar `consulta_id` incompatible → rechazo.

`Documento`: `atencion_id` validado en serializer y view; update no puede mover a atención ajena.

## Seguridad API (C6.2)

- **No** se expone URL directa `/media/` en list/detail de serializers.
- Lectura de bytes: `GET …/download/` autenticado (`FileResponse`, `Content-Disposition` con basename del storage, sin path interno).
- `archivo` en serializer: **write-only** (upload).
- Respuesta incluye: `archivo_nombre`, `archivo_size`, `download_url` (ruta al endpoint protegido).
- **DELETE** HTTP → **405** (sin borrado físico ni de registro).
- En **DEBUG**, `/media/` puede seguir existiendo a nivel Django; la API no debe facilitar bypass.

## Permisos

### ArchivoMedico

| Rol | Listar / descargar | Crear |
|-----|-------------------|-------|
| admin / superuser | Todos | Sí |
| médico | Pacientes vinculados por `Consulta` HC, `Atencion.medico_principal` o `Turno.medico` | Sí (solo pacientes vinculados; validado en `perform_create`) |
| paciente | Solo propios | Sí (solo `paciente_id` propio) |
| secretaría / enfermería / laboratorio | **Ninguno** | **403** (`CanWriteArchivoMedico`) |
| otros | Ninguno | No |

### Documento

| Rol | Listar / descargar | Crear |
|-----|-------------------|-------|
| admin / superuser | Todos | Sí |
| médico | Atenciones propias o documentos que cargó | Sí (solo `atencion` propia; `CanWriteDocumentoClinico` + queryset serializer) |
| paciente | Documentos de sus atenciones | No (`IsEMRClinicianOrReadOnly` bloquea POST) |
| secretaría / enfermería / laboratorio | **Ninguno** | **403** en POST |

Frontend: menú **Archivos** solo `medico`, `admin`, `paciente`.

## Auditoría (`AuditEvent`)

| Acción metadata | Cuándo |
|-----------------|--------|
| `archivo_medico_create` | POST archivo |
| `archivo_medico_update` | PATCH metadata |
| `archivo_medico_download` | GET download |
| `documento_create` | POST documento |
| `documento_update` | PATCH documento |
| `documento_download` | GET download |

Metadata: `entity_id`, `tipo`, `view`, `accion`. **Sin** path absoluto, URL `/media/`, contenido binario, nombres con PHI innecesarios.

## Estudios complementarios (C6.4.1)

| Entidad | Rol |
|---------|-----|
| `estudios.EstudioComplementario` | Instancia clínica por paciente (estados, vínculos atención/consulta/solicitud EMR) |
| `estudios.ArchivoEstudioComplementario` | Puente a `ArchivoMedico` (mismo paciente; descarga protegida) |
| `estudios.InformeEstudioComplementario` | Informe versionado (borrador → emitido → validado; rectificación) |
| `estudios.TipoEstudioComplementario` | Catálogo EMR (modalidad RX/TC/RM/US/PDF/OTRO) |

API: `/api/estudios-complementarios/`. Estados solo por acciones POST, no PATCH. **`paciente_id` no se cambia por PATCH** (C6.4.1-A).

**Informes (C6.4.1-A):** crear solo con estudio **REALIZADO** o **INFORMADO**; emitir solo borrador en esos estados (o ENTREGADO si es rectificación); validar solo con estudio **INFORMADO** e informe **EMITIDO**; **un solo informe vigente** (validado) por transacción de validación; rectificación crea borrador no vigente y reemplaza vigencia al validar la nueva versión.

**Hardening (C6.4.3):**

- Constraint DB PostgreSQL `uniq_informe_vigente_por_estudio`: como máximo un `InformeEstudioComplementario` con `es_vigente=True` por estudio (migración deduplica duplicados conservando validado de mayor versión).
- Descarga PDF del informe: `GET /api/estudios-complementarios/{id}/informes/{informe_id}/download-pdf/` — `FileResponse`, sin `/media/` ni path en API/auditoría.
- `Content-Disposition`: nombre generado `estudio-complementario-{estudio_id}-informe-v{version}.pdf` (sin PHI ni filename original).
- Serializer informe: `tiene_pdf`, `download_pdf_url` (URL protegida); nunca `archivo_pdf.url`.
- Paciente: descarga PDF solo si estudio **ENTREGADO**, informe **VALIDADO** y **vigente**.
- Médico/admin: descarga si acceso clínico al paciente; secretaría/enfermería/laboratorio: bloqueado.
- Auditoría: `estudio_informe_pdf_download` — metadata `estudio_id`, `informe_id`, `version_informe`; sin texto/filename/path.

| Rol | Acceso |
|-----|--------|
| admin / superuser | Completo |
| médico | Pacientes vinculados (misma regla que `ArchivoMedico`) |
| paciente | Solo estudios propios en estado **ENTREGADO** |
| secretaría / enfermería / laboratorio | Sin acceso (lista vacía) |

Validación de informe: **solo admin/superuser** en C6.4.1.

**ENTREGADO (C6.4.1-B):** estado terminal salvo **rectificación** — al emitir informe rectificador, el estudio pasa a INFORMADO (reapertura explícita, no PATCH ni acciones genéricas); el informe anterior sigue vigente hasta validar la nueva versión; luego VALIDADO → `entregar` → ENTREGADO.

**Frontend C6.4.2 [IMPLEMENTADO]:** rutas `/estudios-complementarios`, detalle con acciones por estado, informes y descarga protegida (blob). Sin visor ni `/media/`.

**[DEUDA]** Los títulos o nombres visibles de archivos existentes pueden contener PHI si el usuario los cargó así. El sistema evita exponer `/media/` y paths en API/auditoría, pero una fase futura debe normalizar nombres de descarga/visualización o imponer nombres seguros en servidor.

Auditoría: `estudio_complementario_*`, `estudio_estado_cambio`, `estudio_archivo_*`, `estudio_informe_*`, `estudio_informe_pdf_download` — sin filename/path/texto completo.

## Deuda (post C6.4.3)

- Soft-delete / anulación con motivo en `ArchivoMedico`.
- Hash/checksum e integridad de archivo.
- Escaneo MIME/malware.
- Nombres seguros en descarga de archivos de estudio (hoy solo PDF de informe usa nombre generado).
- PACS / DICOMweb / RIS y visor.
- URLs firmadas de corta duración si se expone storage externo.
