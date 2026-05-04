# DOC_TESTS — Pruebas existentes

**Fecha de generación:** 30 de abril de 2026  
**Actualización (rol laboratorio, tests LIMS API):** 2 de mayo de 2026  
**Actualización (Fase A LIMS — máquina de estados):** 3 de mayo de 2026  

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

**No detectados** (sin Jest/Vitest/Playwright config en repo).

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
