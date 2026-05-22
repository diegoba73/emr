# Documentos e imágenes clínicas (C6.2)

**Estado:** C6.2 [IMPLEMENTADO] — hardening de seguridad y auditoría.  
**No incluye:** PACS/DICOM/RIS, visor, `EstudioComplementario`, soft-delete con motivo.

## Dos vías de adjuntos (sin unificar aún)

| Entidad | Vínculo | API | Uso |
|---------|---------|-----|-----|
| `archivos_medicos.ArchivoMedico` | `Paciente` (+ opcional `historias_clinicas.Consulta`) | `/api/archivos-medicos/archivos/` | Tomografías, DICOM, rayos, PDF clínico por paciente |
| `emr.Documento` | `turnos.Atencion` | `/api/documentos/` | Informes/estudios ligados a una atención |

No son estudios realizados ni flujo orden → realización → informe → validación.

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
| médico | Pacientes vinculados por `Consulta` HC, `Atencion.medico_principal` o `Turno.medico` | Sí |
| paciente | Solo propios | Sí (solo `paciente_id` propio) |
| secretaría / enfermería / laboratorio | **Ninguno** | No |
| otros | Ninguno | No |

### Documento

| Rol | Listar / descargar | Crear |
|-----|-------------------|-------|
| admin / superuser | Todos | Sí (clínico EMR) |
| médico | Atenciones propias o documentos que cargó | Sí |
| paciente | Documentos de sus atenciones | No (C6.2) |
| secretaría / enfermería / laboratorio | **Ninguno** | No |

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

## Deuda (C6.3+)

- Soft-delete / anulación con motivo y trazabilidad.
- Hash/checksum e integridad de archivo.
- Escaneo MIME/malware.
- Entidad `EstudioComplementario` y flujo profesional de imágenes.
- Imágenes multiarchivo no-DICOM.
- PACS / DICOM / RIS y visor.
- URLs firmadas de corta duración si se expone storage externo.
