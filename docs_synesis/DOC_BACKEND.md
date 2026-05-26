# DOC_BACKEND — Arquitectura backend

**Fecha de generación:** 30 de abril de 2026  
**Actualización (LIMS permisos / rol laboratorio):** 2 de mayo de 2026  

**Alcance:** Estructura del proyecto Django `synesis`, responsabilidades de apps y patrones de implementación observados.

**Fuentes revisadas:** `synesis/settings.py`, `synesis/urls.py`, `api/urls.py`, apps en `INSTALLED_APPS`, módulos clave de `turnos`, `laboratorio`, `auditoria`, `integracion_lims`.

---

## Estructura general

```
synesis/          # proyecto Django
  settings.py
  urls.py
api/              # agregación de rutas DRF + vistas legacy voluminosas (views.py)
<domain_apps>/    # pacientes, turnos, laboratorio, ...
```

---

## Apps Django y responsabilidades

| App | Responsabilidad |
|-----|-----------------|
| `core` | `HealthCheckView` en `/api/health/` |
| `usuarios` | Usuario custom, perfiles, JWT auxiliar, ViewSets de usuario |
| `pacientes` | CRUD paciente, búsqueda, filtros por rol |
| `medicos` | Médicos, especialidades |
| `catalogos` | CIE-10, medicamentos, procedimientos, centros físicos, tipos atención, internación catálogo |
| `turnos` | Recursos, turnos, atenciones, consulta ambulatoria embebida, registros |
| `historias_clinicas` | Historia clínica, consultas, diagnósticos, tratamientos, prescripciones, modelo Internacion |
| `emr` | Signos vitales, documentos (modelos); parte de vistas en `api/views.py` |
| `archivos_medicos` | Upload/listado archivos médicos con políticas por rol |
| `estudios` | Estudios complementarios EMR (C6.4.1–C6.4.3): estados, informes versionados, constraint único vigente, descarga PDF protegida |
| `laboratorio` | LIMS nativo: órdenes/resultados (Fase A), muestras transaccionales (B1), vínculo `ResultadoExamen.muestra` (B2) |
| `api` | Router central, permisos compartidos, **archivo `views.py` muy grande** con ViewSets duplicados respecto a apps |
| `solicitudes` | Solicitudes transversales + integración opcional LIMS |
| `integracion_lims` | Cliente HTTP stub + modelos espejo; URLs webhook no montadas en raíz |
| `internacion` | API sectores/camas/internación simplificada |
| `laboratorio` | LIMS embebido |
| `auditoria` | AuditEvent, middleware, servicio de logging |

---

## Servicios de dominio

- **`turnos/services.py` — `AtencionService`:** transición turno→atención, mapeo tipo recurso→tipo intervención, idempotencia API.
- **`pacientes/services.py` — `ensure_paciente_linked_to_user`:** usado en turnos para pacientes.
- **`auditoria/audit_service.py`:** logging estructurado de eventos.
- **`auditoria/snapshot.py` — `safe_model_snapshot`:** captura estado para before/after.
- **`integracion_lims/lims_service.py`:** HTTP externo (config rígida).

---

## Lógica en views/viewsets

- **Filtros por rol** implementados predominantemente en **`get_queryset`** (no solo en permisos DRF).
- **Acciones custom:** ej. `cargar_resultados`, `validar`, `cerrar`, `buscar`, `resumen`, `etiqueta`.
- **Auth:** funciones `@api_view` para login/logout/current-user/registros en `api/views.py`.

---

## Lógica en serializers

- Validaciones de negocio y anidamiento (p. ej. `ConsultaCreateSerializer`, `SolicitudExamenCreateSerializer` con `@transaction.atomic`).
- Serializers ligeros para listados (`PacienteLightSerializer`, listas de archivos).

---

## Lógica en models

- `save()` / `clean()` en `Turno`, `SolicitudExamen`, `ResultadoExamen`, `Solicitud`, `AuditEvent`, `Internacion` (internacion app), etc.

---

## Validaciones

- Django `ValidationError` en modelos; DRF `ValidationError` en vistas.
- **Unique constraints** y **indexes** declarados en Meta.

---

## Transacciones

- `transaction.atomic` en carga de resultados lab, creación de orden+resultados, servicios de atención.

---

## Permisos

- Mix de `permission_classes` en clase + lógica en `get_queryset`.
- Ver `DOC_PERMISOS_AUDITORIA.md`.

---

## Autenticación

- Session + JWT + Token (config DRF).
- `archivos_medicos` reafirma `JWTAuthentication` y `SessionAuthentication`.

---

## Auditoría / logs

- `AuditEvent` append-only; middleware `RequestContextMiddleware` temprano en `MIDDLEWARE`.
- Python `logging` en views de laboratorio y pacientes.

---

## Manejo de errores

- Respuestas `Response({'error': ...}, status=4xx/5xx)` en acciones custom.
- Excepciones genéricas capturadas en algunos bloques lab con log y 500.

---

## Settings relevantes

- `AUTH_USER_MODEL = 'usuarios.User'`
- `REST_FRAMEWORK`: paginación 20 ítems, filtros globales.
- `SIMPLE_JWT`: tiempos cortos de access token.
- DB: PostgreSQL por variables de entorno.
- `MEDIA_ROOT`, `STATIC_ROOT`
- CORS y CSRF para desarrollo con frontend en :3000

---

## Dependencias importantes

`requirements.txt`: Django ≥5, DRF, cors-headers, django-filter, psycopg2-binary, dotenv, simplejwt, Faker, requests.

---

## Comandos custom

- Bajo `catalogos/management/commands/` (cargas CIE-10, datos de ejemplo, etc.) — ver carpeta para lista exacta.

**Pendiente de confirmar:** inventario completo ejecutando `python manage.py help`.

---

## Tareas programadas

**No detectado** Celery/cron en `settings.py` o dependencias típicas.

---

## Integración con archivos / documentos

- `FileField` en documentos EMR, registros quirúrgicos, archivos médicos.
- Servido `/media/` en DEBUG (`synesis/urls.py`).

---

## Riesgos técnicos

- **`api/views.py` tamaño** — deuda de mantenimiento y riesgo de divergencia con viewsets “canónicos” de apps.
- **URLs duplicadas** en router (`lab/` y `laboratorio/`) — doble superficie (mismos permisos; duplicación sigue siendo riesgo operativo).

---

## Deuda técnica detectada

- ViewSets duplicados entre `api/views.py` y apps (p. ej. historial de `PacienteViewSet` en ambos archivos; router usa el de `pacientes.views`).
- `integracion_lims` incompleto a nivel URLconf.
- ~~String **`tecnico`** en EMR~~ — retirado; `laboratorio` permanece para LIMS, no en `IsEMRClinician`.
- **LIMS (estado actual):** permisos mínimos en `api/permissions.py` (`LimsCatalogReadPermission`, `LimsSolicitudExamenPermission`) y `laboratorio/views.py`; **sin** `AllowAny` en ViewSets LIMS sensibles.

---

## Riesgos o inconsistencias

Ver `DOC_RIESGOS_DEUDA_TECNICA.md`.

---

## Pendiente de confirmar

- Proceso de despliegue (Gunicorn, Docker referenciado en comentarios media).
- Variables de entorno obligatorias en prod.
