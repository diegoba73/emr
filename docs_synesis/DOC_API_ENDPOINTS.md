# DOC_API_ENDPOINTS — APIs reales

**Fecha de generación:** 30 de abril de 2026  
**Actualización (permisos LIMS):** 2 de mayo de 2026  
**Actualización (Fase A LIMS — acciones de estado):** 3 de mayo de 2026  
**Actualización (Fase B3.1 — Microbiología base):** 13 de mayo de 2026  
**Actualización (query `estudio_id` en listados micro):** 20 de junio de 2026 — **[IMPLEMENTADO]**  
**Actualización (Fase B3.2 — Microorganismos / aislados / identificación):** 13 de mayo de 2026  

**Alcance:** Endpoints definidos por URLconf y routers bajo el prefijo del proyecto; métodos estándar DRF para `ModelViewSet` salvo donde se indica.

**Fuentes revisadas:** `synesis/urls.py`, `api/urls.py`, `usuarios/urls.py`, `archivos_medicos/urls.py`, `internacion/urls.py`, `auditoria/urls.py`, `catalogos/urls.py` (app no montada en raíz directamente), `laboratorio/views.py`, `laboratorio/serializers.py`, `laboratorio/solicitud_estado.py`, viewsets citados.

**Prefijos globales**

- API principal: **`/api/`** (incluye router grande + rutas auth).
- Usuarios/JWT: **`/api/usuarios/`**.
- Admin Django: **`/admin/`**.

---

## Routers y urls

| Archivo | Montaje | Notas |
|---------|---------|-------|
| `api/urls.py` | `path('api/', include('api.urls'))` | Router `DefaultRouter` + `catalogos_router` + includes |
| `usuarios/urls.py` | `path('api/usuarios/', include('usuarios.urls'))` | Router usuarios + JWT |
| `archivos_medicos/urls.py` | `path('api/archivos-medicos/', ...)` | Router archivos |
| `internacion/urls.py` | `path('api/internacion/', ...)` | Router internación |
| `auditoria/urls.py` | `path('api/auditoria/', ...)` | Solo eventos |
| `catalogos/urls.py` | **No incluido** en `synesis/urls.py` | Catálogo accesible vía `api/urls` duplicando ViewSets |
| `integracion_lims/urls.py` | **No incluido** en `synesis/urls.py` | Webhooks **no expuestos** |
| `solicitudes/urls.py` | **No incluido** en `synesis/urls.py` | `SolicitudViewSet` expuesto solo vía **`api/urls` router** |

---

## Endpoints sin router (api/urls.py)

| Método | Ruta | Vista | Permisos |
|--------|------|-------|----------|
| GET | `/api/health/` | `HealthCheckView` | AllowAny |
| GET | `/api/auth/csrf-token/` | `csrf_token_view` | AllowAny |
| POST | `/api/auth/login/` | `login_view` | AllowAny |
| POST | `/api/auth/logout/` | `logout_view` | IsAuthenticated |
| GET | `/api/auth/current-user/` | `current_user` | IsAuthenticated |
| GET | `/api/auth/users/` | `list_users` | (revisar en archivo; típicamente staff) |
| GET | `/api/auth/groups/` | `list_groups` | (idem) |
| POST | `/api/auth/register/` | `PacienteRegisterView` | público/registro |
| POST | `/api/auth/register/patient/` | `register_patient` | AllowAny típico |
| POST | `/api/auth/register/doctor/` | `register_doctor` | — |
| POST | `/api/auth/register/secretary/` | `register_secretary` | — |

**Nota:** `login_view` devuelve `rol` en **MAYÚSCULAS** en el payload (`user.rol.upper()`), distinto del almacenamiento en modelo.

---

## Router principal (`api/urls` → prefijo `/api/`)

Registros `router.register` (recurso → ViewSet). Convención DRF:  
`GET/POST /api/{recurso}/`, `GET/PUT/PATCH/DELETE /api/{recurso}/{id}/`.

| Recurso registrado | ViewSet (origen import) | Serializer principal (típico) | Permisos (típico) |
|--------------------|-------------------------|---------------------------------|-------------------|
| `pacientes` | `pacientes.views.PacienteViewSet` | Paciente / Light | IsAuthenticated + queryset |
| `medicos` | `medicos.views.MedicoViewSet` | (serializers medicos) | IsAuthenticated |
| `especialidades` | `medicos.views.EspecialidadViewSet` | — | — |
| `centros-fisicos` | `catalogos.views.CentroFisicoViewSet` | — | — |
| `tipos-atencion` | `catalogos.views.TipoAtencionViewSet` | — | — |
| `recursos` | `turnos.views.RecursoViewSet` | RecursoSerializer | IsAuthenticated; escritura IsAdminUser |
| `turnos` | `turnos.views.TurnoViewSet` | TurnoSerializer | IsAuthenticated + queryset |
| `atenciones` | `turnos.views.AtencionViewSet` | AtencionSerializer (api) | IsMedicoOrEnfermeriaOrAdmin |
| `historias-clinicas` | `historias_clinicas.views.HistoriaClinicaViewSet` | HistoriaClinicaSerializer | IsAuthenticated + queryset |
| `consultas` | `historias_clinicas.views.ConsultaViewSet` | Consulta / Create | IsMedicoOrEnfermeriaOrAdmin |
| `solicitudes` | `solicitudes.views.SolicitudViewSet` | Solicitud* | **`SolicitudPermission`** (PERM-01) + `get_queryset` por rol |
| `lab/solicitudes` | `laboratorio.views.SolicitudExamenViewSet` | SolicitudExamen* | **`LimsSolicitudExamenPermission`** (+ `get_queryset` por rol) |
| `lab/examenes` | `laboratorio.views.TipoExamenViewSet` | TipoExamenSerializer | **`LimsCatalogReadPermission`** |
| `lab/muestras` | `laboratorio.views.TipoMuestraViewSet` | TipoMuestraSerializer | **`LimsCatalogReadPermission`** |
| `lab/paneles` | `laboratorio.views.PanelExamenViewSet` | PanelExamenSerializer | **`LimsCatalogReadPermission`** |
| `laboratorio/tipos-examen` | `TipoExamenViewSet` | (alias duplicado) | Igual que `lab/examenes` (**misma clase**, misma protección) |
| `laboratorio/solicitudes` | `SolicitudExamenViewSet` | (alias duplicado) | Igual que `lab/solicitudes` (**misma clase**, misma protección) |
| `disponibilidades` | `api.views.DisponibilidadMedicoViewSet` | — | — |
| `excepciones` | `api.views.ExcepcionMedicoViewSet` | — | — |
| `diagnosticos` | `api.views.DiagnosticoViewSet` | — | — |
| `diagnosticos-cie10` | `api.views.DiagnosticoCIE10ViewSet` | — | — |
| `prescripciones` | `api.views.PrescripcionViewSet` | — | — |
| `medicamentos` | `api.views.MedicamentoViewSet` | — | — |
| `internaciones` | `api.views.InternacionViewSet` | (modelo historias_clinicas.Internacion típico) | — |
| `dashboard` | `api.views.DashboardViewSet` | ViewSet custom | — |
| `consultas-ambulatorias` | `api.views.ConsultaAmbulatoriaViewSet` | — | — |
| `registros-procedimientos` | `api.views.RegistroProcedimientoViewSet` | PROD-4-A **CERRADO**: `adjunto_resultado` write-only; `adjunto_resultado_download_url`; `GET {id}/download-adjunto-resultado/` | — |
| `registros-quirurgicos` | `api.views.RegistroQuirurgicoViewSet` | PROD-4-A **CERRADO**: `consentimiento_informado` write-only; `consentimiento_informado_download_url`; `GET {id}/download-consentimiento-informado/` | — |
| `estudios-diagnosticos` | `api.views.EstudioDiagnosticoViewSet` | — | — |
| `procedimientos-catalogo` | `api.views.ProcedimientoCatalogoViewSet` | — | — |
| `documentos` | `api.views.DocumentoViewSet` | Documentos EMR (C6.2: sin URL `/media/`; `GET {id}/download/`) | — |

**ViewSets definidos en `api/views.py` pero no registrados en `api/urls.py`:** p. ej. `SignosVitalesViewSet` — **sin ruta** en el router actual (no aparece `register` para signos).

**ViewSets duplicados en `api/views.py`:** existen `PacienteViewSet`, `TurnoViewSet`, etc. dentro de `api/views.py`; el **router importa** los de `pacientes.views` y `turnos.views`, **no** los del archivo api largo.

---

## Prefijo `catalogos/` bajo `/api/catalogos/`

Mismo `TipoAtencionViewSet`, `CentroFisicoViewSet`, más `ProcedimientoViewSet` como `catalogos-procedimientos`.

---

## Archivos médicos (`/api/archivos-medicos/`) — C6.2 [IMPLEMENTADO]

| Recurso | Notas |
|---------|-------|
| `archivos` | List/detail/create/update; **DELETE → 405**; serializer sin URL `/media/`; `download_url` + `GET archivos/{id}/download/` |
| `archivos/tipos_disponibles/` | Catálogo de tipos (autenticado) |
| `tipos/` | `tipos_archivo_publicos` AllowAny (metadatos de formulario) |

Ver `docs_synesis/reglas/documentos-e-imagenes.md`.

## Estudios complementarios (`/api/estudios-complementarios/`) — C6.4.1 [IMPLEMENTADO]

| Método | Ruta | Notas |
|--------|------|-------|
| GET/POST | `/` | List/create; filtro `paciente`, `estado`, `modalidad` |
| GET/PATCH | `/{id}/` | **PATCH no modifica `estado`**; DELETE → **405** |
| POST | `/{id}/marcar-realizado/` | SOLICITADO → REALIZADO |
| POST | `/{id}/anular/` | body `motivo_anulacion` obligatorio |
| POST | `/{id}/entregar/` | Requiere informe validado vigente |
| POST | `/{id}/agregar-archivo/` | body `archivo_medico_id` (mismo paciente) |
| GET | `/{id}/archivos/` | Sin URL `/media/`; `download_url` protegido |
| GET | `/{id}/archivos/{archivo_id}/download/` | Descarga vía `ArchivoMedico` |
| GET/POST | `/{id}/informes/` | Informes versionados |
| POST | `/{id}/informes/{informe_id}/emitir/` | Borrador → emitido; estudio → INFORMADO |
| POST | `/{id}/informes/{informe_id}/validar/` | Solo admin/superuser |
| POST | `/{id}/informes/{informe_id}/rectificar/` | Nueva versión; motivo obligatorio |
| GET | `/{id}/informes/{informe_id}/download-pdf/` | PDF del informe (C6.4.3); sin `/media/`; nombre seguro en `Content-Disposition` |

Informes en listado: `tiene_pdf`, `download_pdf_url` (ruta protegida anterior).

No LIMS. No PACS/visor. Ver `docs_synesis/reglas/documentos-e-imagenes.md`.

**Frontend (C6.4.2):** consumido desde `estudiosComplementariosApi.ts` — rutas listadas arriba; descarga `.../archivos/{archivo_estudio_id}/download/` con `responseType: blob`.

## Registros procedimiento / quirúrgico — PROD-4-A + PROD-4-B [CERRADO — jun 2026]

Descarga segura (PROD-4-A) + auditoría en descarga exitosa (PROD-4-B). `log_event` con `action='UPDATE'`, `after=None`, metadata mínima (sin path/filename/contenido).

| Método | Ruta | Notas |
|--------|------|-------|
| GET | `registros-procedimientos/{id}/` | Sin URL `/media/`; `adjunto_resultado_download_url` si hay adjunto |
| GET | `registros-procedimientos/{id}/download-adjunto-resultado/` | Descarga autenticada; auditoría `registro_procedimiento_adjunto_download` (PROD-4-B) |
| GET | `registros-quirurgicos/{id}/` | Sin URL `/media/`; `consentimiento_informado_download_url` si hay archivo |
| GET | `registros-quirurgicos/{id}/download-consentimiento-informado/` | Descarga autenticada; auditoría `registro_quirurgico_consentimiento_download` (PROD-4-B) |

Upload en create/update: campo `adjunto_resultado` / `consentimiento_informado` (multipart). Cliente **no** debe usar `/media/` ni `FileField.url`.

---

## Documentos EMR (`/api/documentos/`) — C6.2

| Método | Ruta | Notas |
|--------|------|-------|
| GET | `documentos/` | Filtrado por rol; sin URL media en JSON |
| POST | `documentos/` | Upload; auditoría `documento_create` |
| GET | `documentos/{id}/download/` | Descarga autenticada; auditoría `documento_download` |
| DELETE | `documentos/{id}/` | **405** — eliminación física no permitida |

---

## Internación (`/api/internacion/`)

| Recurso | ViewSet |
|---------|---------|
| `sectores` | `SectorViewSet` |
| `camas` | `CamaViewSet` |
| `internaciones` | `InternacionViewSet` (app `internacion`) |

---

## Auditoría (`/api/auditoria/`)

| Recurso | Métodos | Permiso |
|---------|---------|---------|
| `events` | GET list/detail | `IsAuditAdmin` |

---

## Usuarios (`/api/usuarios/`)

| Recurso | ViewSet |
|---------|---------|
| `users` | `UserViewSet` |
| `profiles` | `UserProfileViewSet` |
| `auth` | `AuthViewSet` |
| `token/` | `CustomTokenObtainPairView` |
| `token/refresh/` | `TokenRefreshView` |
| `register/` | `PacienteRegisterView` |

---

## Acciones custom detectadas (no exhaustivo)

| Ruta aproximada | Método | Descripción |
|-----------------|--------|-------------|
| `/api/pacientes/buscar/` | GET | Búsqueda `q` |
| `/api/historias-clinicas/{id}/resumen/` | GET | Resumen HC |
| `/api/lab/solicitudes/{id}/tomar-muestra/` | POST | Marca orden en toma de muestra (`PENDIENTE` → `TOMA_MUESTRA`) |
| `/api/lab/solicitudes/{id}/cargar-resultados/` | POST | Carga valores resultado; body `resultados[]` con `id`, `valor` (obligatorio para considerar cargado), `es_patologico`, `observaciones`, **`muestra_id`** opcional salvo que `TipoExamen.requiere_muestra=True` (B2-B: entonces obligatorio en payload o FK previa). **B4.1 (retrocompatible):** por ítem también `valor_numerico`, `unidad`, `es_critico`; si no viene `unidad` y el `TipoExamen` tiene `unidad_default`, se copia; si hay rango/críticos estructurados en catálogo, se calculan `es_patologico`/`es_critico` y snapshots de referencia. Respuesta de lectura incluye campos estructurados en `resultados[]`. |
| `/api/lab/solicitudes/{id}/validar/` | POST | Valida orden (`EN_PROCESO` → `VALIDADO`; solo admin/superuser) |
| `/api/lab/solicitudes/{id}/cancelar/` | POST | Cancela orden no final (`PENDIENTE` / `TOMA_MUESTRA` / `EN_PROCESO` → `CANCELADO`) |
| `/api/lab/solicitudes/{id}/marcar-entregado/` | POST | Marca entregada (`VALIDADO` → `ENTREGADO`; sin PDF) |
| `/api/lab/solicitudes/{id}/informe-pdf/` | GET | **PDF-1:** informe LIMS básico en PDF (generado en memoria; `Content-Type: application/pdf`; nombre `informe-lims-solicitud-{id}.pdf`; sin `/media/`; auditoría `lims_informe_pdf_download`; no modifica estado). **Frontend PDF-1-FE:** consumido desde `limsApi.downloadInformeLimsPdf` en detalle de orden (`OrdenLimsDetalle.tsx`) |
| `/api/lab/solicitudes/{id}/etiqueta/` | GET | JSON ZPL |
| `/api/atenciones/` | POST | **Compat/deprecated (C5.10.2):** alta idempotente de `Atencion` desde `turno`; no mueve estado del turno; headers `Deprecation`, `X-Synesis-Deprecated-Endpoint`, `X-Synesis-Replacement-Endpoint`, `Warning` |
| `/api/atenciones/{id}/cerrar/` | POST | Cerrar atención |
| `/api/turnos/{id}/iniciar-atencion/` | POST | **Flujo clínico activo (C5.10.1):** crea/obtiene atención, turno → `REALIZADO`, registro hijo; sin headers deprecated |
| `/api/turnos/` + query | GET | `start`, `end`, `all` |

**Alias:** mismas acciones bajo `/api/laboratorio/solicitudes/{id}/...` (mismo `SolicitudExamenViewSet` registrado dos veces en `api/urls.py`).

**CRUD estándar lab:** `PATCH` / `PUT` sobre `/api/lab/solicitudes/{id}/` usan `SolicitudExamenSerializer` con campo **`estado` en solo lectura** — no se debe usar para cambiar el estado de la orden; los cambios van solo por las acciones `POST` anteriores.

### Solicitudes genéricas EMR (`/api/solicitudes/`) — LIMS externo

**[DOC-01 — jun 2026]** Distinto de LIMS nativo (`/api/lab/solicitudes/`). Permiso: **`SolicitudPermission`** (PERM-01).

| Ruta | Método | Regla |
|------|--------|-------|
| `/api/solicitudes/{id}/enviar_lims/` | POST | Envío explícito a LIMS HTTP externo (`integracion_lims.lims_service`). **Solo admin/superuser.** Body opcional: `paneles`, `tipos_examen`. Auditado sin PHI en metadata. **No** se dispara desde `save()` ni `LIMS_AUTO_SEND`. |
| `/api/solicitudes/{id}/sincronizar_lims/` | POST | Sincronización explícita vía `_enviar_a_lims()`. **Solo admin/superuser.** Auditado sin PHI. |

Roles médico, secretaría, paciente, laboratorio, enfermería → **403**. Frontend puede no reflejar restricción (fase **FE-PERM-01**).

---

---

## Serializers usados

Inferidos por ViewSet en cada app; listados detallados en serializers de `pacientes`, `turnos`, `historias_clinicas`, `laboratorio`, `api/serializers.py` (Atencion enriquecido).

---

## Filtros

- `DjangoFilterBackend`, `SearchFilter`, `OrderingFilter` según ViewSet.
- Query params específicos: `numero`, `fecha` (lab), `start`/`end` (turnos), `historia_clinica_id`, `paciente_id`, etc.

---

## Payload / respuesta

- Crear orden lab: cuerpo con `paciente_id`, `examenes_ids`, `paneles_ids`, etc. → respuesta `SolicitudExamenSerializer` (resultados anidados incluyen **`muestra_id`**, **`muestra_estado`**, **`tipo_muestra_nombre`** — Fase B2).
- **`POST …/solicitudes/{id}/cargar-resultados/`** — cada ítem puede incluir opcionalmente **`muestra_id`** (misma orden; muestra en RECIBIDA/CONSERVADA/EN_PROCESO). Sin `muestra_id` = legacy **si** `requiere_muestra=False`. Con `requiere_muestra=True` → 400 sin muestra. **B2-B-A:** si se envía `muestra_id` (o queda muestra asociada), debe cumplir `tipo_muestra_requerida` aunque `requiere_muestra=False`. Catálogo `TipoExamen` vía API es read-only (`requiere_muestra` solo lectura en serializer).
- **B2-C (frontend):** `CargaResultadosLims` envía `resultados[]` con `muestra_id` numérico solo cuando el operador selecciona muestra; lista muestras vía `GET /lab/muestras-transaccionales/?solicitud=<id>`.
- Actualizar orden lab (`PATCH`/`PUT`): campos editables según serializer; **`estado` ignorado/no escribible** desde API estándar.
- Acciones `tomar-muestra`, `cancelar`, `marcar-entregado`: cuerpo típico `{}` (JSON vacío aceptable).
- Crear atención: `{ "turno": <id>, "observaciones_generales": "..." }` → `AtencionSerializer`.

---

## Endpoints críticos

- Auth: `/api/auth/login/`, `/api/usuarios/token/`
- Turnos/atenciones: `/api/turnos/`, `/api/atenciones/`
- Laboratorio: `/api/lab/solicitudes/` + acciones
- Auditoría: `/api/auditoria/events/`

---

## Endpoints usados por frontend

**No hay frontend en repo.** Scripts en `backup_documentacion/` usan login y turnos — ver `DOC_FRONTEND.md`.

---

## Endpoints no usados aparentemente

- Duplicados `laboratorio/*` vs `lab/*` (misma lógica).
- `dashboard` si no hay cliente.
- Webhooks `integracion_lims` (no montados).

---

## Riesgos de compatibilidad pública

- Múltiples alias de URL para el mismo ViewSet (`/api/lab/...` y `/api/laboratorio/...`): **misma** protección; duplicación sigue siendo deuda operativa (superficie doble).
- Respuesta login con `rol` mayúscula vs API resto con minúsculas.
- Tras hardening LIMS, **no** hay acceso anónimo a catálogos ni solicitudes LIMS; clientes que dependían de llamadas sin autenticación deben usar sesión/JWT.

---

## Inconsistencias entre frontend y backend

**No verificable** sin código SPA. A nivel API: duplicación de rutas y formatos de rol.

---

## Riesgos o inconsistencias

- `SignosVitalesViewSet` en código sin registro en `api/urls.py`.
- `api/views.py` masivo con ViewSets posiblemente legacy vs imports en router.

---

## Pendiente de confirmar

- Lista exacta de acciones en `SolicitudViewSet` y `DashboardViewSet`.
- Permisos finos en `list_users` / `list_groups`.

---

## LIMS Fase B0/B1 (catálogos y muestra transaccional)

Prefijos **`/api/lab/...`** y alias **`/api/laboratorio/...`** (mismos ViewSets).

| Ruta | Métodos | Rol típico |
|------|---------|------------|
| `/api/lab/areas/` | GET, POST | Lectura: lab/médico/secretaría/enfermería/admin. Escritura: **solo admin**. |
| `/api/lab/areas/{id}/` | GET, PATCH | Igual. |
| `/api/lab/secciones/` | GET, POST | Igual. |
| `/api/lab/secciones/{id}/` | GET, PATCH | Igual. |
| `/api/lab/contenedores/` | GET, POST | Igual. |
| `/api/lab/contenedores/{id}/` | GET, PATCH | Igual. |
| `/api/lab/muestras-transaccionales/` | GET, POST | Crear: admin/lab. Listar/ver: admin/lab/médico (médico: solo órdenes propias). |
| `/api/lab/muestras-transaccionales/{id}/` | GET, PATCH | PATCH solo campos administrativos (`tipo_contenedor`, `ubicacion_actual`, `observaciones`); **`estado` no se modifica por PATCH**. |
| `.../{id}/tomar/` | POST | admin/lab |
| `.../{id}/recibir/` | POST | admin/lab |
| `.../{id}/rechazar/` | POST | admin/lab (`motivo_rechazo` obligatorio) |
| `.../{id}/conservar/` | POST | admin/lab |
| `.../{id}/descartar/` | POST | admin/lab |
| `.../{id}/cambiar-ubicacion/` | POST | admin/lab (`ubicacion` obligatoria; estados `RECIBIDA`/`CONSERVADA`) |
| `.../{id}/cancelar/` | POST | admin/lab |
| `.../{id}/eventos/` | GET | admin/lab/médico (médico: solo muestras de órdenes propias) |

**DELETE** en catálogos y muestras: no soportado / 405 u objeto no expuesto a borrado (desactivar catálogos con `activo=false`).

Contrato de creación de muestra (JSON): `solicitud_id`, `tipo_muestra_id`, `tipo_contenedor_id` (opcional), `codigo_barra` (opcional; auto `MUE-YYYY-NNNNNN` si omitido), `observaciones` (opcional). El paciente se deriva de la solicitud (no se acepta paciente inconsistente).

**B1 [IMPLEMENTADO]:** trazabilidad física vía `Muestra` + `EventoMuestra`; `tomar-muestra` de orden (Fase A) coexiste sin crear tubos automáticamente.

---

## LIMS Fase B3.1 (microbiología base)

Prefijo **`/api/lab/microbiologia/...`** y alias **`/api/laboratorio/microbiologia/...`** (mismas clases ViewSet).

### Query param opcional `?estudio_id=` (jun 2026 — IMPLEMENTADO)

Filtro **opcional** en listados GET. Sin el parámetro se conserva el comportamiento previo (todos los registros visibles al rol). Aplica **después** del `get_queryset()` restringido por permisos.

| Recurso | Lookup interno |
|---------|----------------|
| `estudios/` | `pk` |
| `siembras/`, `lecturas/`, `aislados/`, `informes/` | `estudio_id` |
| `identificaciones/`, `antibiogramas/` | `aislado__estudio_id` |
| `resultados-antibiotico/` | `antibiograma__aislado__estudio_id` |

**No aplica** a catálogos sin relación con estudio: `medios/`, `microorganismos/`, `antibioticos/`.

Validación: el parámetro debe ser un **entero positivo**; valores no enteros, vacíos, cero o negativos devuelven **HTTP 400**. ID inexistente o no visible → lista vacía (200), sin revelar existencia de otros estudios.

Implementación: `_apply_estudio_id_query_filter()` en `laboratorio/views_microbiologia.py`. Frontend: `limsMicroApi.ts` + `MicrobiologiaEstudioDetalle.tsx`.

| Ruta | Métodos | Rol típico |
|------|---------|------------|
| `/api/lab/microbiologia/medios/` | GET, POST | Lectura: lab/médico/secretaría/enfermería/admin. Escritura: **solo admin**. |
| `/api/lab/microbiologia/medios/{id}/` | GET, PATCH | Igual. |
| `/api/lab/microbiologia/estudios/` | GET, POST | Crear: admin/lab. Listar/ver: admin/lab/médico (médico: solo estudios cuya solicitud tiene `medico_interno.user`=usuario actual). **Query opcional `?estudio_id=`** (filtra por `pk`). |
| `/api/lab/microbiologia/estudios/{id}/` | GET, PATCH | PATCH solo `tipo_estudio` y `observaciones`; **`estado` no se modifica por PATCH**. |
| `/api/lab/microbiologia/estudios/{id}/iniciar/` | POST | admin/lab. Transición `PENDIENTE→RECIBIDO` (idempotente). |
| `/api/lab/microbiologia/estudios/{id}/cancelar/` | POST | admin/lab. Requiere `motivo` no vacío. Transición a `CANCELADO`. |
| `/api/lab/microbiologia/siembras/` | GET, POST | Crear: admin/lab. Listar/ver: admin/lab/médico (filtrado por sus solicitudes). **Query opcional `?estudio_id=`** [IMPLEMENTADO jun 2026]. |
| `/api/lab/microbiologia/siembras/{id}/` | GET, PATCH | PATCH: `condicion_incubacion`, `temperatura_c`, `atmosfera`, `observaciones`. |
| `/api/lab/microbiologia/lecturas/` | GET, POST | Crear: admin/lab. Si `es_preliminar=True` y el estudio está `SEMBRADO`, lo pasa a `LECTURA_PRELIMINAR`. **Query opcional `?estudio_id=`**. |
| `/api/lab/microbiologia/lecturas/{id}/` | GET, PATCH | PATCH: `horas_incubacion`, `crecimiento`, `descripcion_colonias`, `tincion_gram`, `observaciones`, `es_preliminar`. |

**DELETE** no soportado (405).

Contrato `crear estudio` (JSON): `solicitud_id`, `muestra_id`, `tipo_estudio` (opcional, default `CULTIVO_RUTINA`), `observaciones`.
Contrato `crear siembra` (JSON): `estudio_id`, `medio_id`, `fecha_siembra` opcional, `condicion_incubacion`, `temperatura_c`, `atmosfera`, `observaciones`.
Contrato `crear lectura` (JSON): `siembra_id`, `fecha_lectura` opcional, `horas_incubacion`, `crecimiento` (choices), `descripcion_colonias`, `tincion_gram`, `observaciones`, `es_preliminar`.

**Fuera de alcance B3.1:** microorganismos, aislados, identificación, antibiograma, informes preliminares/finales, PDF, cierre/validación final microbiológico.

---

## LIMS Fase B3.2 (microorganismos / aislados / identificación)

Prefijo **`/api/lab/microbiologia/...`** y alias **`/api/laboratorio/microbiologia/...`** (mismas clases ViewSet).

| Ruta | Métodos | Rol típico |
|------|---------|------------|
| `/api/lab/microbiologia/microorganismos/` | GET, POST | Lectura: lab/médico/secretaría/enfermería/admin. Escritura: **solo admin**. |
| `/api/lab/microbiologia/microorganismos/{id}/` | GET, PATCH | Igual. Sin DELETE (desactivar con `activo=false`). |
| `/api/lab/microbiologia/aislados/` | GET, POST | Crear: admin/lab. Listar/ver: admin/lab/médico (médico solo sus solicitudes). **Query opcional `?estudio_id=`**. |
| `/api/lab/microbiologia/aislados/{id}/` | GET, PATCH | PATCH solo `descripcion`, `cantidad`, `significancia`, `requiere_antibiograma`, `observaciones`; **`estado` y `microorganismo` no se editan**. |
| `/api/lab/microbiologia/aislados/{id}/descartar/` | POST | admin/lab. Requiere `motivo` no vacío. Aislado → `DESCARTADO`. |
| `/api/lab/microbiologia/identificaciones/` | GET, POST | Crear: admin/lab. Listar/ver: admin/lab/médico (filtrado). **Query opcional `?estudio_id=`** (lookup `aislado__estudio_id`). |
| `/api/lab/microbiologia/identificaciones/{id}/` | GET | **Append-only**: PATCH/DELETE no soportados (405). |

**DELETE** no soportado en ningún endpoint B3.2 (405).

Contrato `crear aislado` (JSON): `estudio_id`, `lectura_id`, `microorganismo_id` (opcional), `descripcion`, `cantidad`, `significancia` (choices), `requiere_antibiograma` (bool), `observaciones`.
Contrato `crear identificación` (JSON): `aislado_id`, `microorganismo_id`, `metodo`, `resultado`, `confianza` (0-100 opcional), `fecha` (opcional), `observaciones`.
Contrato `descartar aislado` (JSON): `motivo` (obligatorio).

**Fuera de alcance B3.2:** antibiograma, `Antibiotico`, `ResultadoAntibiotico`, `InformeMicrobiologia`, informes preliminares/finales, PDF, frontend dedicado, cierre/validación profesional, integración LIMS externa.

## LIMS Fase B3.3 (antibiograma)

Prefijo **`/api/lab/microbiologia/...`** y alias **`/api/laboratorio/microbiologia/...`** (mismas clases ViewSet).

| Ruta | Métodos | Rol típico |
|------|---------|------------|
| `/api/lab/microbiologia/antibioticos/` | GET, POST | Lectura: lab/médico/secretaría/enfermería/admin. Escritura: **solo admin**. |
| `/api/lab/microbiologia/antibioticos/{id}/` | GET, PATCH | Igual. Sin DELETE (desactivar con `activo=false`). |
| `/api/lab/microbiologia/antibiogramas/` | GET, POST | Crear: admin/lab. Listar/ver: admin/lab/médico (médico solo sus solicitudes). **Query opcional `?estudio_id=`**. |
| `/api/lab/microbiologia/antibiogramas/{id}/` | GET, PATCH | PATCH solo `metodo`, `observaciones`; bloqueado si `COMPLETO` o `CANCELADO`. **`estado`, fechas y motivo se mueven solo por servicio**. |
| `/api/lab/microbiologia/antibiogramas/{id}/completar/` | POST | admin/lab. Requiere ≥1 `ResultadoAntibiotico`. Antibiograma → `COMPLETO`, setea `fecha_resultado`. |
| `/api/lab/microbiologia/antibiogramas/{id}/cancelar/` | POST | admin/lab. Requiere `motivo` no vacío. Antibiograma → `CANCELADO`. |
| `/api/lab/microbiologia/resultados-antibiotico/` | GET, POST | Crear: admin/lab. Bloqueado si antibiograma `COMPLETO`/`CANCELADO` o antibiótico inactivo; antibiótico no se duplica por antibiograma. **Query opcional `?estudio_id=`**. |
| `/api/lab/microbiologia/resultados-antibiotico/{id}/` | GET, PATCH | PATCH solo `halo_mm`, `mic`, `interpretacion`, `observaciones` (no `antibiograma`/`antibiotico`); bloqueado si antibiograma `COMPLETO`/`CANCELADO`. |

**DELETE** no soportado en ningún endpoint B3.3 (405).

Contrato `crear antibiograma` (JSON): `aislado_id`, `metodo`, `fecha_inicio` (opcional), `observaciones`.
Contrato `crear resultado` (JSON): `antibiograma_id`, `antibiotico_id`, `interpretacion` ∈ {`S`,`I`,`R`,`SDD`,`NO_APLICA`}, `halo_mm` (opcional), `mic`, `observaciones`.
Contrato `cancelar antibiograma` (JSON): `motivo` (obligatorio).
Contrato `completar antibiograma` (JSON): `{}` (sin payload obligatorio); requiere resultados existentes.

**Transiciones cableadas (B3.3):**
- `Antibiograma`: `PENDIENTE → EN_PROCESO` automático al cargar el primer `ResultadoAntibiotico` válido. `COMPLETO`/`CANCELADO` solo por acción explícita.
- `EstudioMicrobiologia`: `IDENTIFICACION | LECTURA_PRELIMINAR | SEMBRADO → ANTIBIOGRAMA` al crear antibiograma o primer resultado (idempotente).

**Fuera de alcance B3.3:** validación profesional final vía informe (pasa a B3.4), cierre `INFORMADO` (B3.4), PDF, frontend dedicado, integración LIMS externa, QC/equipamiento.

## LIMS Fase B3.4 (informes microbiológicos)

Prefijo **`/api/lab/microbiologia/...`** y alias **`/api/laboratorio/microbiologia/...`**.

| Ruta | Métodos | Rol típico |
|------|---------|------------|
| `/api/lab/microbiologia/informes/` | GET, POST | Crear: admin/lab. Listar/ver: admin/lab/médico (médico solo sus solicitudes). **Query opcional `?estudio_id=`**. |
| `/api/lab/microbiologia/informes/{id}/` | GET, PATCH | PATCH solo en `BORRADOR` (`texto`, `observaciones`, `version`). |
| `/api/lab/microbiologia/informes/{id}/emitir/` | POST | admin/lab. Body opcional `texto`; si falta, usa el del borrador. Texto emitido no vacío. |
| `/api/lab/microbiologia/informes/{id}/validar/` | POST | **Solo admin** (+ superuser). Solo informe `FINAL` en `EMITIDO` y estudio `LISTO_PARA_VALIDAR`. |
| `/api/lab/microbiologia/informes/{id}/anular/` | POST | admin/lab. `motivo` obligatorio. Solo `BORRADOR` o `EMITIDO` (no `VALIDADO`). |
| `/api/lab/microbiologia/estudios/{id}/marcar-informado/` | POST | admin/lab. Requiere estudio `VALIDADO` e informe final `VALIDADO`. |

**DELETE** no soportado en informes (405).

**Transiciones estudio (B3.4):** `… → LISTO_PARA_VALIDAR` al emitir informe final; `LISTO_PARA_VALIDAR → VALIDADO` al validar informe final; `VALIDADO → INFORMADO` con `marcar-informado`.

**Fuera de alcance B3.4:** PDF, frontend, firma digital avanzada, rectificación/addendum avanzado, QC/equipamiento, integración externa.
