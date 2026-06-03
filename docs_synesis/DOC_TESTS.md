# DOC_TESTS — Pruebas existentes

**Fecha de generación:** 30 de abril de 2026  
**Actualización (rol laboratorio, tests LIMS API):** 2 de mayo de 2026  
**Actualización (Fase A LIMS — máquina de estados):** 3 de mayo de 2026  
**Actualización (Fase B3.4 LIMS — Informes microbiológicos):** 14 de mayo de 2026  
**Actualización (Frontend UI-2 — microbiología LIMS):** 17 de mayo de 2026  

**Alcance:** Tests automatizados bajo el repositorio; excluye deliberadamente la carpeta `backup_documentacion/` salvo mención como no-canónica.

**Fuentes revisadas:** `conftest.py`, `glob **/test*.py`, exclusiones por convención.

---

## Infraestructura de tests

- **`conftest.py` (raíz):** configura `DJANGO_SETTINGS_MODULE=synesis.settings` y `django.setup()` para pytest.
- **Fixtures/factories:** uso de **Faker** listado en `requirements.txt`; no hay factory_boy explícito en requirements (pendiente de confirmar si se usa en algún test).

---

## Tests backend (por app / área)

| Ubicación | Contenido inferido |
|-----------|-------------------|
| `pacientes/tests/` | `test_models.py`, `test_api.py` |
| `medicos/tests/` | `test_models.py` |
| `turnos/tests/` | `test_api.py`, `test_models.py`, `test_services.py`, `test_consulta_ambulatoria.py`, `test_atencion_viewset.py` |
| `historias_clinicas/tests/` | `test_api.py`, `test_models.py` |
| `laboratorio/tests/` | `test_models.py`, `test_api.py` |
| `archivos_medicos/tests/` | `test_models.py`, `tests.py` |
| `auditoria/tests/` | `test_audit_event_model.py`, `test_audit_integration.py`, `test_auditoria_hardening.py` |
| `integracion_lims/tests.py` | app-level |
| `solicitudes/tests/` | `test_models.py`, `tests.py` |
| `internacion/tests/` | `test_infraestructura.py`, `test_admision.py`, `tests.py` |
| `usuarios/tests/` | `test_models.py`, `test_health.py`, **`test_laboratorio_rol.py`** (rol `laboratorio`, login/current-user/JWT) |
| `api/tests.py` | app api |
| `catalogos/tests.py` | app catalogos |
| `backend/tests/test_registro_paciente.py` | registro paciente |
| `pacientes/tests.py`, `medicos/tests.py`, `solicitudes/tests.py`, `archivos_medicos/tests.py`, `internacion/tests.py`, `historias_clinicas/tests.py` | ficheros legacy `tests.py` |

**`backup_documentacion/`:** numerosos scripts `test_*.py` / `test_*.js` — **no son suite pytest estándar** del proyecto; tratar como experimentos.

---

## Tests frontend

La suite vive en el **submódulo** `frontend/` (Create React App + Jest + Testing Library). No hay tests E2E de microbiología aún.

**Comandos validados (UI-2, commit `d46d276`, mayo 2026):**

```bash
export PATH="$HOME/.nvm/versions/node/v18.20.8/bin:$PATH"  # si aplica
cd frontend
npx tsc --noEmit
npm run build
CI=true npm test -- --watchAll=false --runInBand
```

**Resultado documentado:** TypeScript OK, build OK, **11 test suites / 25 tests** passed (incluye regresión UI-1; **sin** tests unitarios dedicados a pantallas `Microbiologia*`).

**Pendiente:** tests frontend específicos de microbiología (panels, permisos por rol, manejo 400/403).

---

## Cobertura funcional inferida

- **Modelos:** varias apps con `test_models.py`.
- **API:** `turnos`, `pacientes`, `historias_clinicas`, `laboratorio`, `test_atencion_viewset`.
- **Servicios:** `turnos/tests/test_services.py` (AtencionService / negocio).
- **Auditoría:** modelo append-only + integración + hardening.

**Huecos probables (sin exhaustividad de grep):** flujo completo `Solicitud`+LIMS externo, webhooks `integracion_lims` no cableados, duplicación `Internacion`. ~~Permisos LIMS `AllowAny`~~ cubiertos por hardening + `laboratorio/tests/test_api.py`. Transiciones de estado `SolicitudExamen` (Fase A) cubiertas en **`TestSolicitudExamenEstadoAPI`**, **`TestSolicitudExamenEstadoAuditoria`** y ajustes en **`TestLimsAuthorization`** dentro de `laboratorio/tests/test_api.py`; cancelación con resultados vacíos en `laboratorio/tests/test_models.py`.

---

## Módulos con tests

`pacientes`, `medicos`, `turnos`, `historias_clinicas`, `laboratorio`, `archivos_medicos`, `auditoria`, `solicitudes`, `internacion`, `usuarios`, `api`, `catalogos`, `integracion_lims`, `backend/tests`.

---

## Módulos sin tests (o solo stubs)

- **`core`:** sin tests dedicados vistos.
- **`emr` (app):** no se listó `emr/tests` en el glob (pendiente: verificar si existe).
- **`integracion_lims`:** solo `tests.py` genérico — cobertura probablemente superficial vs `lims_service`.

---

## Comandos para correr tests

Desde la raíz del repo (con entorno virtual y DB configurada):

```bash
pytest
```

O por app:

```bash
pytest turnos/tests/ laboratorio/tests/ auditoria/tests/
```

**Comandos validados post-hardening LIMS / rol laboratorio:**

```bash
python manage.py check
python -m pytest usuarios/tests/test_laboratorio_rol.py usuarios/tests/test_models.py -q
python manage.py test laboratorio.tests.test_api
```

**Comando validado post–Fase A (máquina de estados + rol laboratorio):**

```bash
emr_env/bin/python manage.py check
emr_env/bin/pytest laboratorio/tests/test_api.py laboratorio/tests/test_models.py usuarios/tests/test_laboratorio_rol.py -q --reuse-db
```

**Resultado documentado (3 may 2026):** `45 passed` (sin fallos en ese subconjunto).

- **`laboratorio.tests.test_api`:** incluye `TestSolicitudExamenAPI` (flujo crear/cargar/validar/etiqueta), **`TestLimsAuthorization`**, **`TestLimsAuditTrail`**, **`TestSolicitudExamenEstadoAPI`** (transiciones, PATCH de `estado`, permisos médico), **`TestSolicitudExamenEstadoAuditoria`** (metadata `cancelar`), y alias `/api/laboratorio/...`.
- **`laboratorio.tests.test_models`:** principalmente modelos; suele ejecutarse con **`pytest`** si usas marcadores `pytest.mark.django_db` (`manage.py test` puede no recoger todos los métodos pytest-style según versión).

**Pendiente de confirmar:** si CI ejecuta `manage.py test` vs pytest; no hay `.github/workflows` analizado en este documento.

---

## Riesgos por falta de pruebas

- Regresiones en **filtros por rol** (`get_queryset` en múltiples ViewSets).
- Regresiones en **transiciones de estado** LIMS más allá de la Fase A (p. ej. futura cancelación desde `VALIDADO`).
- **Doble modelo de internación** sin tests de consistencia cruzada.

---

## Tests recomendados para EMR

1. Creación idempotente `POST /api/atenciones/` con mismo `turno`.
2. Paciente sin ficha: error en `TurnoViewSet.perform_create` para rol paciente.
3. `HistoriaClinicaViewSet` / `ConsultaViewSet` límites por médico/paciente.
4. Subida y descarga `ArchivoMedico` por rol (secretaría bloqueada).

---

## Tests recomendados para LIMS

1. `SolicitudExamenCreateSerializer`: creación de `ResultadoExamen` por paneles con solapamiento (**cubierto en parte** por `test_api`).
2. `cargar_resultados` con solicitud `VALIDADO` / `CANCELADO` / `ENTREGADO` (**cubierto** en `TestSolicitudExamenEstadoAPI`).
3. `validar`: solo `EN_PROCESO`, resultados vacíos rechazados; `bulk update` en resultados + auditoría (**cubierto** en `test_api` + estado).
4. ~~Permisos finales (sustituir `AllowAny` y testear roles)~~ — **cubierto** por `TestLimsAuthorization` + usuario `rol=laboratorio` en setup de `test_api`.
5. Acciones `tomar-muestra`, `cancelar`, `marcar-entregado`, `PATCH` sin mutar `estado`, auditoría de transición (**cubierto** en `TestSolicitudExamenEstadoAPI` / `TestSolicitudExamenEstadoAuditoria`).

**Fase B0/B1:** `laboratorio/tests/test_muestras_models.py` (catálogos, `crear_muestra`, transiciones y coordinación solicitud); `laboratorio/tests/test_muestras_api.py` (permisos catálogo, CRUD muestra, acciones, PATCH `estado` ignorado, auditoría con `captureOnCommitCallbacks`).

**Fase B2 [IMPLEMENTADO]:** `test_resultados_muestras_models.py` (FK, integridad, `PROTECT`, no rechazar con resultados); `test_resultados_muestras_api.py` (carga con/sin `muestra_id`, CONSERVADA→EN_PROCESO, `PROCESAMIENTO`, rechazo con resultados, resultado validado sin cambio de muestra, permisos).
**Fase B2-B [IMPLEMENTADO]:** `laboratorio/tests/test_tipo_examen_muestra_requerida.py` (legacy sin muestra, obligatoriedad por tipo, tipo de muestra incorrecto/correcto, estados no procesables, auditoría en fallo/éxito); `test_resultados_muestras_models.py` (`requiere_muestra` configurable). Migración `0012_tipo_examen_requiere_muestra`.
**Fase B2-B-A [IMPLEMENTADO]:** mismos tests con `TipoMuestra.codigo` ≤10 (PostgreSQL); `test_tipo_no_requiere_muestra_pero_si_se_envia_muestra_debe_coincidir_tipo`; validación tipo muestra con `requiere_muestra=False` si hay `muestra_id`.
**Fase B2-C [frontend]:** `frontend/src/utils/limsCargaMuestra.test.ts` (validación requiere_muestra, payload con/sin `muestra_id`, filtro procesables); verificación manual `npm exec tsc --noEmit` y `npm run build` en submódulo `frontend/`.
**Fase B2-A [IMPLEMENTADO]:** `auditoria/tests/test_audit_integration.py` (`test_resultado_examen_snapshot_redacta_valor_clinico`); `test_resultados_muestras_api.py` (`test_cargar_resultados_con_muestra_no_audita_codigo_barra_ni_valor_clinico` — metadata y snapshots sin PHI/codigo_barra).

**Fase B3-audit [IMPLEMENTADO]:** `laboratorio/tests/test_microbiologia_auditoria.py` — metadata micro sin `codigo_barra`/CIM/diámetro/interpretación/texto de informe; snapshots redactados; conservación de IDs técnicos.

**Fase B3-frontend-validación [IMPLEMENTADO — jun 2026]:** relevamiento SPA microbiología (UI-2); contrato `limsMicroApi.ts` verificado; `tsc` + `build` + Jest focal `limsCargaMuestra.test.ts` OK; backend micro **161/161** OK. Corrección bug crecimiento `AUSENTE`→`SIN_DESARROLLO`/`MIXTO`. Sin suite Jest micro dedicada (gap documentado en `DOC_FRONTEND.md`).

**Fase B3-frontend-validación-A [VALIDADO — jun 2026]:** bloqueo operación técnica micro en estados cerrados `CANCELADO`/`VALIDADO`/`INFORMADO`. Backend: `TestEstudioMicroCerradoOperacionAPI` (4 tests); suite `test_microbiologia_*` 165 passed; regresión LIMS 315 passed (PostgreSQL). Frontend: `limsAccess.test.ts`. Auditoría Codex: `B3_VALIDACION_A_CODEX_AUDIT.md`.

**B3-frontend-UX [PARCIAL — jun 2026]:** `limsMicroUx.test.ts` (muestras procesables, labels, validación crear estudio); ampliación matriz roles en `limsAccess.test.ts`. **[GAP]** E2E LIMS micro sin framework.

**Fase B4.1:** `laboratorio/tests/test_resultados_clinicos_models.py` (TipoExamen rangos/críticos/sección; ResultadoExamen numérico, snapshots, patológico/crítico, pendiente); `laboratorio/tests/test_resultados_clinicos_api.py` (payload viejo, `valor_numerico`, unidad default, cálculo patológico/crítico, validar, permisos laboratorio/médico).

**Fase B3.1 (Microbiología base):**

- `laboratorio/tests/test_microbiologia_models.py`: alta de `MedioCultivo` (incluido `codigo` único), creación de `EstudioMicrobiologia` con muestras `RECIBIDA`/`CONSERVADA`/`EN_PROCESO`, rechazo con muestras `PENDIENTE_TOMA`/`TOMADA`/`RECHAZADA`/`DESCARTADA`/`CANCELADA`, consistencia solicitud/paciente, validaciones de `SiembraMicrobiologia` (medio activo, misma muestra que el estudio) y `LecturaCultivo` (siembra y estudio coincidentes, no cancelados, fecha coherente).
- `laboratorio/tests/test_microbiologia_api.py`: permisos del catálogo medios (admin escribe, laboratorio no), permisos sobre estudios/siembras/lecturas por rol (laboratorio opera, médico solo ve sus estudios, paciente/anónimo bloqueados), creación de estudio con auditoría `CREATE`, fallas con muestras inválidas, idempotencia de `iniciar`, cancelación con/sin motivo, PATCH sin cambio de `estado`, transiciones automáticas `SEMBRADO` / `LECTURA_PRELIMINAR`, bloqueos por estudio/siembra cancelados, aliases `/api/laboratorio/microbiologia/...`. Las aserciones de auditoría usan `captureOnCommitCallbacks(execute=True)` para materializar los eventos `on_commit`.

**Fase B3.1-gap [IMPLEMENTADO]:** tests `test_estudio_microbiologia_permite_muestra_conservada`, `test_siembra_microbiologia_permite_muestra_conservada` (modelos); `test_api_crear_estudio_microbiologia_con_muestra_conservada`, `test_api_crear_siembra_con_muestra_conservada` (API).

**Fase B3.2 (Microorganismos / aislados / identificación):**

- `laboratorio/tests/test_microbiologia_models.py` (clases nuevas `TestMicroorganismoModel`, `TestAisladoModel`, `TestIdentificacionModel`): alta de `Microorganismo` (con `codigo` único), creación de aislado desde lectura válida, validaciones (lectura del estudio incorrecto, estudio cancelado, microorganismo inactivo, `IDENTIFICADO` exige microorganismo), `requiere_antibiograma` se registra sin disparar antibiograma, creación de identificación, bloqueos por microorganismo inactivo y aislado descartado, y verificación end-to-end con el servicio `crear_identificacion` para confirmar que actualiza el aislado a `IDENTIFICADO` y el estudio a `IDENTIFICACION`.
- `laboratorio/tests/test_microbiologia_api.py` (clases nuevas `TestMicroorganismoAPI`, `TestAisladoAPI`, `TestIdentificacionAPI`): catálogo de microorganismos (admin escribe, laboratorio no, paciente/anónimo bloqueados, alias), aislados (laboratorio crea, médico/paciente no, lectura de otro estudio rechazada, estudio cancelado bloquea, microorganismo inactivo bloquea, `descartar` con/sin motivo, PATCH no toca `estado`, alias), identificaciones (crea + actualiza aislado y estudio con auditoría `auto_identificacion`, microorganismo inactivo bloquea, aislado descartado y estudio cancelado bloquean, médico no crea, append-only via 405 en PATCH, alias). Continúa usando `captureOnCommitCallbacks(execute=True)` para auditoría.

**Fase B3.3 (Antibiograma microbiológico):**

- `laboratorio/tests/test_microbiologia_models.py` (clases nuevas `TestAntibioticoModel`, `TestAntibiogramaModel`, `TestResultadoAntibioticoModel`, `TestServiciosAntibiograma`): alta de `Antibiotico` con `codigo` único; creación de `Antibiograma` para aislado `IDENTIFICADO` y rechazo para aislados `SOSPECHADO`/`DESCARTADO` y para estudios `CANCELADO`; creación de `ResultadoAntibiotico` con interpretaciones válidas; bloqueo por antibiótico inactivo, interpretación inválida, antibiograma `COMPLETO`/`CANCELADO` y duplicado de antibiótico (UniqueConstraint); servicio `aplicar_completar_antibiograma` falla sin resultados, completa setea `fecha_resultado`; servicio `crear_antibiograma` mueve el estudio a `ANTIBIOGRAMA` y el primer resultado lleva el antibiograma a `EN_PROCESO`.
- `laboratorio/tests/test_microbiologia_api.py` (clases nuevas `TestAntibioticoAPI`, `TestAntibiogramaAPI`, `TestResultadoAntibioticoAPI`): catálogo de antibióticos (admin escribe y desactiva con auditoría `actualizar_antibiotico`, laboratorio lista pero no crea, paciente/anónimo bloqueados, sin DELETE, alias `/api/laboratorio/microbiologia/antibioticos/`); antibiogramas (laboratorio crea con auditoría `crear_antibiograma` + `auto_antibiograma`, médico/paciente/anónimo bloqueados para crear, fallas 400 con aislado descartado/no identificado/estudio cancelado, completar sin resultados falla, cancelar con/sin motivo, PATCH bloqueado si `COMPLETO`, médico vinculado lee solo su antibiograma —ajeno 404—, alias); resultados (laboratorio carga con auditoría y avanza a `EN_PROCESO`, duplicar antibiótico 400, antibiótico inactivo 400, no se carga si antibiograma `COMPLETO`/`CANCELADO`, completar con resultados funciona, PATCH bloqueado si antibiograma `COMPLETO`, alias). Auditoría sigue verificada con `captureOnCommitCallbacks(execute=True)`.

**Fase B3.4 (Informes microbiológicos):**

- `laboratorio/tests/test_microbiologia_models.py` (`TestInformeMicrobiologiaModel`): informes preliminares múltiples; unicidad de `FINAL` vigente; emisión con texto obligatorio; completitud (lecturas, aislados, antibiograma `COMPLETO` cuando `requiere_antibiograma`); transiciones de estudio `LISTO_PARA_VALIDAR` / `VALIDADO` / `INFORMADO`; anulación con motivo; bloqueos PATCH tras `VALIDADO`; etc.
- `laboratorio/tests/test_microbiologia_api.py` (`TestInformeMicrobiologiaAPI`): permisos lab/admin/médico/paciente; `validar` solo admin; `marcar-informado`; anulación con motivo; alias de rutas; auditoría con `captureOnCommitCallbacks(execute=True)`.

**Fase B2.1:** ampliación de `laboratorio/tests/test_resultados_muestras_api.py`:
- `test_carga_muestra_descartada_400`, `test_carga_muestra_cancelada_400` (matriz API completa de estados inválidos).
- `test_carga_primer_resultado_transiciona_muestra_a_en_proceso` (transición automática `RECIBIDA→EN_PROCESO` + `EventoMuestra` + `AuditEvent`, usando `captureOnCommitCallbacks`).
- `test_carga_segundo_resultado_misma_muestra_idempotente` (no duplica evento si muestra ya `EN_PROCESO`).
- `test_validar_muestra_descartada_falla`, `test_validar_muestra_cancelada_falla`, `test_validar_releyendo_muestras_con_select_for_update` (TOCTOU defensivo: mutación de muestra entre carga y validar bloquea la validación).

---

## Pruebas mínimas antes de cambios importantes

- `pytest turnos/tests/test_services.py turnos/tests/test_atencion_viewset.py`
- `pytest auditoria/tests/`
- `pytest laboratorio/tests/`
- Smoke `pytest pacientes/tests/test_api.py`

---

## Riesgos o inconsistencias

- Duplicación de lógica entre `api/views.py` y viewsets de apps puede hacer que los tests ejerciten **rutas equivocadas** si no importan el mismo módulo que el router.

---

## Pendiente de confirmar

- Configuración CI/CD y umbral de cobertura.
- Base de datos de test (SQLite vs PostgreSQL) en entornos locales.
