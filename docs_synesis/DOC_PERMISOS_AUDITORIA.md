# DOC_PERMISOS_AUDITORIA — Seguridad funcional

**Fecha de generación:** 30 de abril de 2026  
**Actualización (hardening mínimo LIMS):** 2 de mayo de 2026  
**Actualización (Fase A LIMS — acciones y auditoría de estado):** 3 de mayo de 2026  

**Alcance:** Autenticación, autorización, auditoría y exposición de datos según código revisado.

**Fuentes revisadas:** `synesis/settings.py`, `api/permissions.py`, `auditoria/*`, `archivos_medicos/views.py`, `laboratorio/views.py`, `laboratorio/solicitud_estado.py`, `usuarios/models.py`, middleware.

---

## Sistema de autenticación

- **SessionAuthentication** (cookies de sesión Django).
- **JWT** (`rest_framework_simplejwt`) — configuración en `SIMPLE_JWT` (access ~5 min, refresh 1 día).
- **TokenAuthentication** (DRF legacy) registrada en `DEFAULT_AUTHENTICATION_CLASSES`.
- Endpoints dedicados: `/api/auth/login/`, `/api/auth/logout/`, `/api/auth/current-user/` (`api/views.py`).
- **JWT bajo `/api/usuarios/token/`** (`usuarios.urls` + `CustomTokenObtainPairView`).

**Default permission:** `IsAuthenticated` en `REST_FRAMEWORK`.

---

## Roles

Definidos en `usuarios.User.ROL_CHOICES`:

- `paciente`, `medico`, `secretaria`, `enfermeria`, **`laboratorio`**, `admin`

- **`laboratorio`:** operador del LIMS nativo (app `laboratorio`). **No** está en `IsEMRClinician` (personal clínico EMR general); el acceso LIMS va por `LimsCatalogReadPermission` / `LimsSolicitudExamenPermission` y `laboratorio/views.py`.

**EMR (mayo 2026):** el string inexistente **`tecnico`** fue retirado de `IsEMRClinician` y de los filtros por rol en `api/views.py` (atenciones y registros asociados). No se añadió `laboratorio` a permisos EMR generales.

Grupos Django mencionados en permisos: `Secretarias`, `Médicos`, `Pacientes` (por nombre de grupo).

---

## Permisos backend (clases custom)

Ubicación: `api/permissions.py`

| Clase | Comportamiento resumido |
|-------|-------------------------|
| `IsSecretariaOrAdmin` | Grupo Secretarias o `rol == secretaria` o superuser |
| `IsMedicoOrAdmin` | Grupo Médicos o `rol == medico` o superuser |
| `IsMedicoOrEnfermeriaOrAdmin` | roles medico, enfermeria, admin (minúsculas) |
| `IsPacienteOrStaff` | staff o grupo Pacientes / rol paciente; objeto: solo propio |
| `IsMedicoOrSecretariaOrAdmin` | medico, secretaria, admin |
| `CanManageTurnos` | `user.puede_gestionar_turnos()`; objeto: secretaria/admin todos; médico solo sus turnos |
| `IsEMRClinician` | medico, secretaria, admin — **no** incluye `laboratorio` (operador LIMS) |
| `IsEMRClinicianOrReadOnly` | GET para autenticados; escritura como EMR clinician |
| `CanUpdatePacienteDemographics` | staff/admin/secretaria; médico cualquier paciente GET/PATCH; paciente solo su ficha |
| **`LimsCatalogReadPermission`** | Lectura GET de catálogos LIMS (tipos muestra/examen/panel): roles admin, laboratorio, medico, secretaria, enfermeria + superuser; **no** paciente ni anónimos |
| **`LimsSolicitudExamenPermission`** | `SolicitudExamenViewSet` y acciones `cargar_resultados`, `validar`, `etiqueta`, **`tomar_muestra`**, **`cancelar`**, **`marcar_entregado`** (`view.action` en snake_case): matriz en `DOC_FLUJOS_LIMS.md`. `validar` solo **admin** (+ superuser); `tomar_muestra`, `cancelar`, `marcar_entregado` y `cargar_resultados`: **admin** y **laboratorio** |

**Nota:** Muchos ViewSets **no usan** estas clases y aplican lógica en `get_queryset` con comparación manual de `user.rol`.

---

## Permisos frontend

**No hay código frontend** en el repo. “Guards” no aplicables aquí.

---

## Auditoría

### Modelo `auditoria.AuditEvent`

- **Append-only:** `save` impide UPDATE; `delete` impide borrado; QuerySet bloquea `delete()` y `update()` masivos.
- Campos: `actor`, `action`, `module`, `entity_type`, `entity_id`, `before_state`, `after_state`, `request_id`, `ip_address`, `user_agent`, `metadata`, `success`, `error_message`.

### Servicio

- `auditoria/audit_service.py` — `log_create`, `log_update`, `log_delete` (usados en p. ej. turnos, laboratorio, solicitudes).

### API

- `GET /api/auditoria/events/` — `AuditEventViewSet` **solo lectura**.
- Permiso: `IsAuditAdmin` (superuser, `is_staff`, o `rol == admin`).

### Middleware

- `RequestContextMiddleware`: genera `request_id` (UUID), IP (X-Forwarded-For), User-Agent; header de respuesta `X-Request-ID`.

---

## Logs

- `LOGGING` en settings: consola, nivel INFO para `django` y root.

---

## Eventos registrados (ejemplos en código)

- Alta/edición/borrado de turnos (`TurnoViewSet`).
- Laboratorio: creación/actualización solicitud (sin cambio de `estado` vía PATCH si el campo es read-only), resultados en `cargar_resultados`, validación, **`tomar_muestra`**, **`cancelar`**, **`marcar_entregado`**.
- Transiciones de estado de `SolicitudExamen`: `log_update` con `metadata` que incluye **`accion`**, **`estado_anterior`**, **`estado_nuevo`**, **`solicitud_id`**, **`numero_solicitud`** (vía `laboratorio/solicitud_estado.apply_solicitud_estado_transition`); además `before_state`/`after_state` del snapshot.
- Solicitudes: `log_create` / `log_update` en flujos del ViewSet.

**Pendiente de confirmar:** cobertura completa de todas las mutaciones EMR (consultas, pacientes, etc.).

---

## Datos sensibles

- **PHI:** pacientes, consultas, resultados lab, archivos médicos, documentos EMR.
- **Credenciales:** sesión y JWT; `SECRET_KEY` por env (default inseguro si no se setea).
- Archivos: `Media` bajo `/media/` en DEBUG.

---

## Riesgos de exposición

1. ~~**`AllowAny` en laboratorio**~~ — **mitigado** en hardening mínimo: ViewSets LIMS usan `LimsCatalogReadPermission` / `LimsSolicitudExamenPermission`; anónimos no operan LIMS.
2. **CORS `DEBUG=True`:** `CORS_ALLOW_ALL_ORIGINS = True`.
3. **BrowsableAPIRenderer** habilitado por defecto — superficie HTML en APIs.
4. **Secretaría sin acceso** a archivos médicos (`queryset.none()`) pero **puede** tener acceso amplio a solicitudes según comentario “por ahora ven todas”.

---

## Acciones críticas que deberían auditarse (checklist)

- Borrado de turnos (sí en turnos).
- ~~Validación de protocolo lab sin `before_state` por resultado~~ — mitigado en `SolicitudExamenViewSet.validar`; borrado de orden con `before_state` en `perform_destroy` (admin).
- Descarga de archivos médicos (logging en views — revisar `archivos_medicos/views.py` completo).
- Cambios de rol de usuario / registro (`register_*`).

---

## Brechas detectadas

- ~~String `tecnico` en EMR~~ — **retirado**; roles EMR alineados con `ROL_CHOICES` (`laboratorio` sigue fuera de `IsEMRClinician` por diseño).
- `solicitudes.views` compara `rol_upper == 'ADMIN'` pero el modelo usa `'admin'` en minúsculas — riesgo de **denegación incorrecta** para usuarios con rol admin si la comparación falla en otros ramas (el branch ADMIN usa superuser o igualdad estricta).
- Webhooks LIMS en `integracion_lims/urls.py` **no montados** — no hay superficie documentada para autenticación de webhook.

---

## Recomendaciones técnicas (sin modificar código)

1. Unificar convención de roles (siempre `.lower()` vs mayúsculas).
2. ~~Sustituir `AllowAny` en LIMS~~ — hecho en código base actual; mantener autenticación obligatoria y revisar clientes legacy.
3. Deshabilitar Browsable API en producción.
4. Auditar que `IsAuditAdmin` alinee con política (¿staff debe ver todos los eventos?).
5. Añadir frontend versionado y política CORS explícita por entorno.

---

## Riesgos o inconsistencias

Ver tabla de brechas arriba y `DOC_RIESGOS_DEUDA_TECNICA.md`.

---

## Pendiente de confirmar

- Política real de grupos Django vs `rol` en BD.
- Si existe rate limiting o WAF frente a `/api/auth/login/`.

---

## LIMS B0/B1 (permisos añadidos)

- **`LimsB0CatalogPermission`** (`AreaLaboratorioViewSet`, `SeccionLaboratorioViewSet`, `TipoContenedorViewSet`): métodos seguros con roles `admin`, `laboratorio`, `medico`, `secretaria`, `enfermeria` (+ superuser). POST/PATCH solo **`admin`** (+ superuser). Anónimo denegado.
- **`LimsMuestraTransaccionalPermission`** (`MuestraTransaccionalViewSet`): list/retrieve `admin`/`laboratorio`/`medico`; create/update/partial y acciones `tomar`/`recibir`/… solo **`admin`**/**`laboratorio`**; `medico` solo lectura de muestras cuya solicitud tiene `medico_interno.user` = usuario actual; **paciente** y **secretaría** sin acceso a este endpoint; anónimo denegado; `destroy` denegado en permiso.
