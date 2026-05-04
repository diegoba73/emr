# DOC_RIESGOS_DEUDA_TECNICA — Riesgos y deuda

**Fecha de generación:** 30 de abril de 2026  
**Actualización (post-hardening LIMS):** 2 de mayo de 2026  
**Actualización (post–Fase A máquina de estados LIMS):** 3 de mayo de 2026  

**Alcance:** Consolidación de riesgos funcionales, técnicos y de seguridad detectados en el análisis estático del repositorio.

**Fuentes revisadas:** conjunto de archivos citados en `docs_synesis/*.md`.

---

## Riesgos funcionales

- **Doble flujo de consulta/atención** (HC vs consulta ambulatoria por `Atencion`) — riesgo de registros clínicos duplicados o incompletos en reporting.
- **Dos modelos de internación** (`historias_clinicas.Internacion` vs `internacion.Internacion`) — datos pueden divergir.
- ~~Estados **TOMA_MUESTRA** / **ENTREGADO** sin acciones en API~~ — **mitigado (Fase A):** acciones `tomar-muestra`, `cargar-resultados` (incl. desde `TOMA_MUESTRA`), `marcar-entregado`; siguen pendientes tubos/muestra transaccional e informe PDF.
- **Solicitud** EMR vs **SolicitudExamen** LIMS nativo sin vínculo obligatorio — doble entrada operativa.

---

## Riesgos de backend

- **`api/views.py` muy grande** con ViewSets potencialmente duplicados respecto a apps; riesgo de mantener lógica en el archivo equivocado.
- **`SignosVitalesViewSet`** definido pero **no registrado** en `api/urls.py` — funcionalidad incompleta o muerta.
- **`integracion_lims/urls.py`** no montado — webhooks inaccesibles desde `synesis.urls`.
- **`lims_service`** URL fija `localhost:8001` — fallo de configuración por entorno.

---

## Riesgos de frontend

- **Ausencia de aplicación versionada** — imposible validar contrato UI/API ni regresiones de UX.

---

## Riesgos de base de datos

- Integridad referencial bien usada en puntos clave (PROTECT), pero **redundancia semántica** entre tablas de internación y solicitudes.
- Generación de números (LAB-*, INT-*) por lógica en `save()` — riesgo de condición de carrera bajo concurrencia alta (no analizado con tests de carga).

---

## Riesgos de seguridad

- ~~**`AllowAny` en ViewSets de laboratorio**~~ — **mitigado** (hardening mínimo): permisos `LimsCatalogReadPermission` / `LimsSolicitudExamenPermission`; sin acceso anónimo a operación LIMS.
- **CORS** permisivo en `DEBUG=True`.
- **SECRET_KEY** por defecto en settings si variables no definidas.
- **Browsable API** habilitada.
- **Login** `@csrf_exempt` — entender implicancia CSRF en despliegue.

---

## Riesgos de auditoría

- ~~Eventos en validación lab con `before=None` para resultados~~ — **mitigado** (snapshots antes del `update()` + audit por `ResultadoExamen` releído).
- Cobertura desigual: no todas las mutaciones EMR verificadas con `log_*` (fuera de LIMS).

---

## Riesgos de trazabilidad

- Modo **api_post_compat** de `AtencionService` que **no** mueve estado del turno — puede divergir agenda vs atenciones reales si el operador asume otro comportamiento.

---

## Riesgos de integración EMR/LIMS

- Tres vías: `laboratorio` nativo, `solicitudes`+`lims_service`, `integracion_lims` modelos espejo — complejidad y riesgo de sincronización inconsistente.
- Endpoint `ingesta` externo referenciado puede no existir.

---

## Deuda técnica

- Duplicación de rutas `lab/*` y `laboratorio/*` (misma protección; mayor superficie operativa).
- ~~String **`tecnico`** en EMR~~ — **retirado** de `IsEMRClinician` y `api/views.py`; `laboratorio` sigue acotado a LIMS (no añadido a permisos EMR generales).
- Comparaciones de rol inconsistentes (mayúsculas/minúsculas), p. ej. en `solicitudes.views`.
- Validación técnica / profesional **no** separada en estados distintos en LIMS nativo (un solo `VALIDADO`).
- Flujo **muestras/tubos** transaccional no modelado (solo catálogo + etiqueta ZPL).

---

## Duplicaciones

- Router registra los mismos ViewSets de laboratorio dos veces bajo prefijos distintos.
- `PacienteViewSet` / otros en `api/views.py` vs apps (router usa apps).

---

## Inconsistencias (lista corta)

| Tema | Detalle |
|------|---------|
| ~~`tecnico` vs `laboratorio`~~ | ~~Resuelto~~ — sin string `tecnico` en EMR; `laboratorio` solo en LIMS |
| Admin en solicitudes | `rol.upper() == 'ADMIN'` vs valor `'admin'` |
| Login API | `rol` mayúscula en respuesta |
| Internación | Dos apps/modelos |
| Webhooks LIMS | URLs no incluidas en proyecto |
| Doble vía pedidos | `solicitudes.Solicitud` vs `laboratorio.SolicitudExamen` sin FK obligatoria |

---

## Módulos frágiles

- `laboratorio/views.py` — lógica de negocio crítica (carga/validación); permisos ya acotados por rol pero siguen evolucionando.
- `solicitudes/views.py` — filtros por rol y ramas `except:` amplias en fragmento visto.
- Cualquier zona con **dos fuentes de verdad** (internación, solicitudes).

---

## Recomendaciones priorizadas (sin modificar código aquí)

1. ~~Cerrar permisos LIMS y catálogos sensibles~~ — **hecho** en hardening mínimo; revisar despliegue (HTTPS, auth obligatoria en clientes).
2. ~~`IsEMRClinician` / `api/views.py`: retirar `tecnico`~~ — **hecho**; sigue pendiente unificar mayúsculas/minúsculas en comparaciones de rol en toda la API.
3. ~~Documentar y testear transiciones de estado lab completas (Fase A mínima)~~ — **hecho** en `docs_synesis` + tests `laboratorio/tests/test_api.py` / `test_models.py`; siguen fases futuras (muestra, PDF, cancelar desde `VALIDADO`, etc.).
4. Decidir fuente única para internación y para “solicitud de examen”.
5. Partir `api/views.py` o eliminar ViewSets no usados del router para reducir confusión.
6. Montar o eliminar URLs de `integracion_lims` según estrategia real.

---

## Riesgos o inconsistencias

Este documento las agrupa; detalle en módulos específicos.

---

## Pendiente de confirmar

- Amenazas y controles en producción (HTTPS, WAF, backups).
- Concurrencia en numeradores de protocolo.
