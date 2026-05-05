# DOC_API_ENDPOINTS — APIs reales

**Fecha de generación:** 30 de abril de 2026  
**Actualización (permisos LIMS):** 2 de mayo de 2026  
**Actualización (Fase A LIMS — acciones de estado):** 3 de mayo de 2026  

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
| `solicitudes` | `solicitudes.views.SolicitudViewSet` | Solicitud* | IsAuthenticated + queryset |
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
| `registros-procedimientos` | `api.views.RegistroProcedimientoViewSet` | — | — |
| `registros-quirurgicos` | `api.views.RegistroQuirurgicoViewSet` | — | — |
| `estudios-diagnosticos` | `api.views.EstudioDiagnosticoViewSet` | — | — |
| `procedimientos-catalogo` | `api.views.ProcedimientoCatalogoViewSet` | — | — |
| `documentos` | `api.views.DocumentoViewSet` | Documentos EMR | — |

**ViewSets definidos en `api/views.py` pero no registrados en `api/urls.py`:** p. ej. `SignosVitalesViewSet` — **sin ruta** en el router actual (no aparece `register` para signos).

**ViewSets duplicados en `api/views.py`:** existen `PacienteViewSet`, `TurnoViewSet`, etc. dentro de `api/views.py`; el **router importa** los de `pacientes.views` y `turnos.views`, **no** los del archivo api largo.

---

## Prefijo `catalogos/` bajo `/api/catalogos/`

Mismo `TipoAtencionViewSet`, `CentroFisicoViewSet`, más `ProcedimientoViewSet` como `catalogos-procedimientos`.

---

## Archivos médicos (`/api/archivos-medicos/`)

| Recurso | Notas |
|---------|-------|
| `archivos` | CRUD `ArchivoMedicoViewSet`; acción descarga si implementada |
| `tipos_disponibles/` | `tipos_archivo_publicos` (ruta explícita en `archivos_medicos/urls.py`) |

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
| `/api/lab/solicitudes/{id}/cargar-resultados/` | POST | Carga valores resultado; transiciones de estado según `DOC_FLUJOS_LIMS.md` |
| `/api/lab/solicitudes/{id}/validar/` | POST | Valida orden (`EN_PROCESO` → `VALIDADO`; solo admin/superuser) |
| `/api/lab/solicitudes/{id}/cancelar/` | POST | Cancela orden no final (`PENDIENTE` / `TOMA_MUESTRA` / `EN_PROCESO` → `CANCELADO`) |
| `/api/lab/solicitudes/{id}/marcar-entregado/` | POST | Marca entregada (`VALIDADO` → `ENTREGADO`; sin PDF) |
| `/api/lab/solicitudes/{id}/etiqueta/` | GET | JSON ZPL |
| `/api/atenciones/{id}/cerrar/` | POST | Cerrar atención |
| `/api/turnos/` + query | GET | `start`, `end`, `all` |

**Alias:** mismas acciones bajo `/api/laboratorio/solicitudes/{id}/...` (mismo `SolicitudExamenViewSet` registrado dos veces en `api/urls.py`).

**CRUD estándar lab:** `PATCH` / `PUT` sobre `/api/lab/solicitudes/{id}/` usan `SolicitudExamenSerializer` con campo **`estado` en solo lectura** — no se debe usar para cambiar el estado de la orden; los cambios van solo por las acciones `POST` anteriores.

---

## Serializers usados

Inferidos por ViewSet en cada app; listados detallados en serializers de `pacientes`, `turnos`, `historias_clinicas`, `laboratorio`, `api/serializers.py` (Atencion enriquecido).

---

## Filtros

- `DjangoFilterBackend`, `SearchFilter`, `OrderingFilter` según ViewSet.
- Query params específicos: `numero`, `fecha` (lab), `start`/`end` (turnos), `historia_clinica_id`, `paciente_id`, etc.

---

## Payload / respuesta

- Crear orden lab: cuerpo con `paciente_id`, `examenes_ids`, `paneles_ids`, etc. → respuesta `SolicitudExamenSerializer`.
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
| `.../{id}/cancelar/` | POST | admin/lab |

**DELETE** en catálogos y muestras: no soportado / 405 u objeto no expuesto a borrado (desactivar catálogos con `activo=false`).

Contrato de creación de muestra (JSON): `solicitud_id`, `tipo_muestra_id`, `tipo_contenedor_id` (opcional), `observaciones` (opcional). El paciente se deriva de la solicitud (no se acepta paciente inconsistente).
