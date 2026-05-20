# DOC_PERMISOS_AUDITORIA — Seguridad funcional

**Fecha de generación:** 30 de abril de 2026  
**Actualización (hardening mínimo LIMS):** 2 de mayo de 2026  
**Actualización (Fase A LIMS — acciones y auditoría de estado):** 3 de mayo de 2026  
**Actualización (Fase B3.4 LIMS — Informes microbiológicos):** 14 de mayo de 2026  

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
| `CanManageTurnos` | `user.puede_gestionar_turnos()`; **no aplicado** al `TurnoViewSet` activo (`turnos.views`); ver C5.8.1 en `perform_create`/`perform_update` |
| `IsEMRClinician` | medico, secretaria, admin — **no** incluye `laboratorio` (operador LIMS) |
| `IsEMRClinicianOrReadOnly` | GET para autenticados; escritura como EMR clinician |
| `CanUpdatePacienteDemographics` | staff/admin/secretaria; médico cualquier paciente GET/PATCH; paciente solo su ficha |
| **`LimsCatalogReadPermission`** | Lectura GET de catálogos LIMS (tipos muestra/examen/panel): roles admin, laboratorio, medico, secretaria, enfermeria + superuser; **no** paciente ni anónimos |
| **`LimsSolicitudExamenPermission`** | `SolicitudExamenViewSet` y acciones `cargar_resultados`, `validar`, `etiqueta`, **`tomar_muestra`**, **`cancelar`**, **`marcar_entregado`** (`view.action` en snake_case): matriz en `DOC_FLUJOS_LIMS.md`. `validar` solo **admin** (+ superuser); `tomar_muestra`, `cancelar`, `marcar_entregado` y `cargar_resultados`: **admin** y **laboratorio** |

**Nota:** Muchos ViewSets **no usan** estas clases y aplican lógica en `get_queryset` con comparación manual de `user.rol`.

---

## Permisos frontend

La aplicación React/TypeScript vive en el **submódulo Git** `frontend/` (referenciado desde el repo padre). Los permisos **no** se delegan al cliente: el backend (DRF + `get_queryset` + acciones) sigue siendo la fuente de verdad.

Guards visuales relevantes (ejemplos):

| Área | Archivo | Notas |
|------|---------|--------|
| Turnos agenda | `frontend/src/utils/turnoPermissions.ts` | C5.8.2: crear/editar por rol; C5.9.1: `confirmar`/`cancelar`; PATCH `estado` solo admin/secretaría en UI |
| LIMS | `frontend/src/utils/limsAccess.ts` | Lectura vs operación vs validar |

Ocultar botones o campos en UI **no sustituye** controles de API; un cliente malicioso puede llamar endpoints directamente.

---

## Auditoría

### Modelo `auditoria.AuditEvent`

- **Append-only:** `save` impide UPDATE; `delete` impide borrado; QuerySet bloquea `delete()` y `update()` masivos.
- Campos: `actor`, `action`, `module`, `entity_type`, `entity_id`, `before_state`, `after_state`, `request_id`, `ip_address`, `user_agent`, `metadata`, `success`, `error_message`.

### Servicio

- `auditoria/audit_service.py` — `log_create`, `log_update`, `log_delete` (usados en p. ej. turnos, laboratorio, solicitudes).

**LIMS Fase B2 (`cargar_resultados`):** metadata de `log_update` sobre `ResultadoExamen` puede incluir `resultado_id`, `solicitud_id`, `numero_solicitud`, `muestra_id`, `codigo_barra`, y si cambió la vínculación `muestra_anterior_id` / `muestra_nueva_id` (sin PHI de paciente en texto libre).

**LIMS Fase B4.1 (`cargar_resultados`):** metadata adicional: `tipo_examen_id`, `valor_anterior`/`valor_nuevo`, `valor_numerico_anterior`/`valor_numerico_nuevo`, `unidad_anterior`/`unidad_nueva`, `es_patologico_anterior`/`es_patologico_nuevo`, `es_critico_anterior`/`es_critico_nuevo`, `actor_id`. Si `es_critico_nuevo=True`, queda visible en `after_state` del snapshot del resultado.

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

- Alta/edición de turnos (`TurnoViewSet`): `log_create` / `log_update` con actor y snapshot (best-effort). Mutaciones restringidas por rol desde C5.8.1; ver `turnos/tests/test_permissions_mutations.py`.
- Borrado físico de turnos: **bloqueado** (405); no genera `log_delete`.
- Transiciones de estado de turno: **`POST .../confirmar/`**, **`POST .../cancelar/`** con metadata `accion`, `estado_anterior`, `estado_nuevo`, `motivo` (C5.9.1). PATCH `estado` bloqueado para médico/paciente; admin/secretaría aún pueden PATCH **[DEUDA]**.
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

## LIMS B3.1 (microbiología base)

- **`LimsMicrobiologiaCatalogPermission`** (`MedioCultivoViewSet`): lectura GET para roles `admin`, `laboratorio`, `medico`, `secretaria`, `enfermeria` (+ superuser); POST/PATCH **solo admin** (+ superuser); paciente y anónimo bloqueados. `destroy` 405 (los medios se desactivan con `activo=False`).
- **`LimsMicrobiologiaPermission`** (`EstudioMicrobiologiaViewSet`, `SiembraMicrobiologiaViewSet`, `LecturaCultivoViewSet`):
  - **admin** / **superuser**: list/retrieve/create/partial_update y acciones `iniciar` / `cancelar`.
  - **laboratorio**: list/retrieve/create/partial_update + acciones `iniciar` / `cancelar`.
  - **medico**: solo list/retrieve y únicamente sobre estudios/siembras/lecturas cuya `solicitud.medico_interno.user` = usuario actual (filtrado en `get_queryset` + `has_object_permission`).
  - **secretaria**, **enfermeria**, **paciente**, **anónimo**: sin acceso a operación técnica de microbiología en esta fase.
  - **`destroy`** siempre denegado a nivel permiso.
- Cancelación de estudio: **motivo obligatorio**; auditado vía `log_update` con `metadata.accion="cancelar"` y `motivo_cancelacion` truncado a 200 chars.
- Auditoría de microbiología:
  - `log_create` para `MedioCultivo`, `EstudioMicrobiologia`, `SiembraMicrobiologia`, `LecturaCultivo` al crear.
  - `log_update` en `iniciar`, `cancelar`, transiciones automáticas (`auto_sembrado`, `auto_lectura_preliminar`), PATCH administrativo.
  - Metadata estable incluye: `accion`, `estudio_id`, `numero_estudio`, `solicitud_id`, `numero_solicitud`, `muestra_id`, `codigo_barra`, `siembra_id` / `lectura_id` cuando aplica, `estado_anterior`, `estado_nuevo`, `actor_id`, `view`, `request_id`. **No** se registra nombre/PHI del paciente en metadata.

## LIMS B3.2 (microorganismos / aislados / identificación)

- **`LimsMicrobiologiaCatalogPermission`** reutilizado para `MicroorganismoViewSet`: lectura amplia (admin/lab/medico/secretaria/enfermeria + superuser); escritura **solo admin/superuser**; sin destroy (`activo=False`).
- **`LimsMicrobiologiaPermission`** extendido para `AisladoMicrobiologicoViewSet` e `IdentificacionMicroorganismoViewSet`:
  - **admin / superuser**: acceso total (list/retrieve/create/partial_update/acciones).
  - **laboratorio**: list/retrieve/create + PATCH limitado (no toca `estado` ni `microorganismo` del aislado) + acción `descartar` (con motivo obligatorio).
  - **medico**: solo list/retrieve y solo de aislados/identificaciones cuya `estudio.solicitud.medico_interno.user` = usuario actual.
  - **secretaria / enfermeria / paciente / anónimo**: sin acceso operativo.
  - `destroy` siempre denegado.
- **`IdentificacionMicroorganismoViewSet`** es **append-only**: `http_method_names = ["get","post","head","options"]`. Sin PATCH ni DELETE (405).
- Cancelar estudio sigue siendo solo admin/laboratorio (sin cambios).
- Auditoría B3.2:
  - `log_create` para `Microorganismo`, `AisladoMicrobiologico`, `IdentificacionMicroorganismo`.
  - `log_update` para PATCH de microorganismo/aislado y para transiciones automáticas (`auto_identificado` del aislado, `auto_identificacion` del estudio) y para `descartar_aislado`.
  - Metadata estable agrega: `aislado_id`, `microorganismo_id`, `lectura_id`, `identificacion_id` (cuando aplica), `significancia`, `requiere_antibiograma`, `motivo_descarte` (truncado). Sin PHI del paciente.

## LIMS B3.3 (antibiograma)

- **`LimsMicrobiologiaCatalogPermission`** reutilizado para `AntibioticoViewSet`: lectura amplia (admin/lab/medico/secretaria/enfermeria + superuser); escritura **solo admin/superuser**; sin destroy (`activo=False`).
- **`LimsMicrobiologiaPermission`** extendido para `AntibiogramaViewSet` y `ResultadoAntibioticoViewSet`:
  - **admin / superuser**: acceso total (list/retrieve/create/partial_update/`completar`/`cancelar`).
  - **laboratorio**: list/retrieve/create + PATCH limitado (antibiograma solo `metodo`/`observaciones` y siempre que no esté `COMPLETO`/`CANCELADO`; resultado solo `halo_mm`/`mic`/`interpretacion`/`observaciones` y solo si antibiograma editable) + acciones `completar` y `cancelar`.
  - **medico**: solo list/retrieve, filtrado por `aislado.estudio.solicitud.medico_interno.user` del usuario actual (resolución vía `antibiograma → aislado → estudio` y `resultado → antibiograma → aislado → estudio`).
  - **secretaria / enfermeria / paciente / anónimo**: sin acceso operativo.
  - `destroy` siempre denegado (405).
- Acciones agregadas al permiso de microbiología: `completar` (admin/lab) además de `iniciar`, `cancelar`, `descartar` ya existentes.
- B3.3 **no** introduce roles nuevos, **no** habilita validación profesional final ni emisión de informe.
- Auditoría B3.3:
  - `log_create` para `Antibiotico`, `Antibiograma`, `ResultadoAntibiotico` (acciones: `crear_antibiotico`, `crear_antibiograma`, `crear_resultado_antibiotico`).
  - `log_update` para PATCH de antibiótico (`actualizar_antibiotico`, incluye `activo_nuevo`), PATCH de antibiograma (`actualizar_antibiograma`), PATCH de resultado (`actualizar_resultado_antibiotico`), transiciones (`auto_en_proceso` del antibiograma, `auto_antibiograma` del estudio), `completar_antibiograma`, `cancelar_antibiograma`.
  - Metadata estable agrega: `antibiograma_id`, `resultado_antibiotico_id`, `antibiotico_id`, `antibiotico_codigo`, `interpretacion`, `motivo_cancelacion` (truncado). Sin PHI del paciente.

## LIMS B3.4 (informes microbiológicos)

- **`LimsMicrobiologiaInformePermission`** para `InformeMicrobiologiaViewSet`:
  - **admin / superuser**: todas las acciones del viewset, incluida **`validar`** (único rol no superuser con `has_permission` para `action=validar`).
  - **laboratorio**: `list`, `retrieve`, `create`, `partial_update`/`update`, **`emitir`**, **`anular`**; **no** `validar`.
  - **medico**: solo `list`/`retrieve`; en objeto, solo si `estudio.solicitud.medico_interno.user` coincide con el usuario.
  - **secretaria / enfermeria / paciente / anónimo**: sin acceso (`has_permission` false).
  - **`destroy`**: siempre denegado en `has_permission`.
  - Cualquier otra `action` no listada arriba cae en `return False` en `has_permission` (p. ej. si se agregara una `@action` nueva habría que extender el permiso).
- **`LimsMicrobiologiaPermission`**: acción **`marcar_informado`** permitida a **admin** y **laboratorio** (además de `iniciar`, `cancelar`, `descartar`, etc.).
- **secretaria / enfermeria**: siguen **sin** lectura de informes ni del resto de microbiología LIMS en B3.4 (misma política que B3.1–B3.3).
- Auditoría B3.4: eventos de creación/actualización/emisión/validación/anulación de informe y de `marcar_informado` (acciones y metadata acotada en `microbiologia_estado.py` — sin PHI del paciente en metadata estable).
