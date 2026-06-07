# DOC_RIESGOS_DEUDA_TECNICA — Riesgos y deuda

**Fecha de generación:** 30 de abril de 2026  
**Actualización (post-hardening LIMS):** 2 de mayo de 2026  
**Actualización (post–Fase A máquina de estados LIMS):** 3 de mayo de 2026  
**Actualización (Fase B2 LIMS — riesgo TOCTOU en `validar`):** 5 de mayo de 2026  
**Actualización (Fase B2.1 LIMS — TOCTOU mitigado + transición auto):** 13 de mayo de 2026  
**Actualización (Fase B3.1 LIMS — Microbiología base):** 13 de mayo de 2026  
**Actualización (Fase B3.2 LIMS — Microorganismos / aislados / identificación):** 13 de mayo de 2026  
**Actualización (Fase B3.3 LIMS — Antibiograma microbiológico):** 13 de mayo de 2026  
**Actualización (Fase B3.4 LIMS — Informes microbiológicos):** 14 de mayo de 2026  
**Actualización (Fase B4.1 LIMS — Resultados clínicos estructurados):** 16 de mayo de 2026  
**Actualización (PROD-2-A — runtime Gunicorn):** 7 de junio de 2026  
**Actualización (PROD-1-A — SECRET_KEY productiva):** 7 de junio de 2026  
**Actualización (PROD-1 — hardening configuración):** 7 de junio de 2026  
**Actualización (Frontend UI-2 — microbiología LIMS):** 17 de mayo de 2026  

**Alcance:** Consolidación de riesgos funcionales, técnicos y de seguridad detectados en el análisis estático del repositorio.

**Fuentes revisadas:** conjunto de archivos citados en `docs_synesis/*.md`.

---

## Riesgos funcionales

- **Doble flujo de consulta/atención** (HC vs consulta ambulatoria por `Atencion`) — riesgo de registros clínicos duplicados o incompletos en reporting.
- **Dos modelos de internación** (`historias_clinicas.Internacion` vs `internacion.Internacion`) — datos pueden divergir.
- ~~Estados **TOMA_MUESTRA** / **ENTREGADO** sin acciones en API~~ — **mitigado (Fase A):** acciones `tomar-muestra`, `cargar-resultados` (incl. desde `TOMA_MUESTRA`), `marcar-entregado`; ~~tubos/muestra transaccional~~ — **mitigado (B1/B2):** `Muestra` + vínculo opcional `ResultadoExamen.muestra`; sigue pendiente informe PDF y obligatoriedad de muestra para órdenes nuevas.
- **Solicitud** EMR vs **SolicitudExamen** LIMS nativo sin vínculo obligatorio — doble entrada operativa.

---

## Riesgos de backend

- **`api/views.py` muy grande** con ViewSets potencialmente duplicados respecto a apps; riesgo de mantener lógica en el archivo equivocado.
- **`SignosVitalesViewSet`** definido pero **no registrado** en `api/urls.py` — funcionalidad incompleta o muerta.
- **`integracion_lims/urls.py`** no montado — webhooks inaccesibles desde `synesis.urls`.
- **`lims_service`** URL fija `localhost:8001` — fallo de configuración por entorno.

---

## Riesgos de frontend

- ~~**Ausencia de aplicación versionada**~~ — **parcialmente mitigado:** submódulo `frontend/` con consola LIMS UI-1/UI-1.2 y microbiología UI-2 (`d46d276`). Siguen sin tests E2E ni cobertura de pantallas micro.
- **Drift UI/API:** el cliente usa prefijo `/lab/...`; el backend expone alias `/laboratorio/...` — documentar y no mezclar en nuevas pantallas.

### Frontend UI-2 — Microbiología (deuda / riesgos pendientes)

| Riesgo | Impacto | Mitigación sugerida |
|--------|---------|---------------------|
| Sin filtros server-side en detalle de estudio | Lentitud / carga excesiva con muchos registros | Query params `?estudio=` cuando el backend los exponga |
| Alta de estudio con IDs manuales | Errores operativos, mala UX | Selector orden/muestra desde UI-1 |
| `prompt()` para motivos | UX pobre, sin validación inline | Diálogos MUI con campo obligatorio |
| Sin tests Jest de microbiología | Regresiones silenciosas en permisos y transiciones | Tests de `limsAccess` + smoke de panels |
| PDF / firma / QC | Expectativa clínica no cubierta | Fuera de alcance UI-2; backend B3.4 ya lo marca |

**No modificado en UI-2:** backend, migraciones, `/solicitudes` EMR, `integracion_lims`, endpoints legacy.

---

## Riesgos de base de datos

- Integridad referencial bien usada en puntos clave (PROTECT), pero **redundancia semántica** entre tablas de internación y solicitudes.
- Generación de números (LAB-*, INT-*) por lógica en `save()` — riesgo de condición de carrera bajo concurrencia alta (no analizado con tests de carga).

---

## Riesgos de seguridad

- ~~**`AllowAny` en ViewSets de laboratorio**~~ — **mitigado** (hardening mínimo): permisos `LimsCatalogReadPermission` / `LimsSolicitudExamenPermission`; sin acceso anónimo a operación LIMS.
- **CORS** permisivo en `DEBUG=True` — **mitigado en producción (PROD-1):** `CORS_ALLOW_ALL_ORIGINS` solo con `DEBUG=True`; orígenes explícitos si `DEBUG=False`.
- ~~**SECRET_KEY** por defecto en settings~~ — **mitigado (PROD-1 / PROD-1-A):** arranque falla si `DEBUG=False` y clave placeholder o baja entropía; `.env.production.example` no contiene clave usable; usar `get_random_secret_key()` o gestor de secretos.
- ~~**Browsable API** siempre habilitada~~ — **mitigado (PROD-1):** solo con `DEBUG=True`.
- **`/media/` directo** — **mitigado (PROD-1):** solo `DEBUG=True`; producción debe usar endpoints protegidos.
- **Login** `@csrf_exempt` — entender implicancia CSRF en despliegue.
- ~~**Gunicorn productivo**~~ — **mitigado (PROD-2-A):** `DJANGO_RUNTIME=gunicorn` en entrypoint; dev mantiene `runserver`.
- **Pendiente:** WAF, rate limiting, rotación secretos, backups, storage privado, Nginx en compose.

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
- ~~Flujo **muestras/tubos** transaccional no modelado~~ — **mitigado (B1/B2/B2.1):** modelo `Muestra` + resultados asociables; transición automática `RECIBIDA`→`EN_PROCESO` al cargar primer resultado vinculado (B2.1). **Deuda remanente:** orden puede validarse con resultados sin muestra aunque existan muestras activas en la solicitud (política operativa explícita pendiente — no automatizado en B2.1).
- ~~**LIMS B2 — concurrencia en `validar` (TOCTOU):**~~ **mitigado (B2.1):** la acción `SolicitudExamenViewSet.validar` ahora hace `Muestra.objects.select_for_update().filter(pk__in=<muestras_referenciadas>)` dentro de la misma `transaction.atomic()` antes de leer el estado de cada muestra. Esto bloquea cualquier mutación concurrente entre la lectura del estado y el cierre de la transacción de validación. **Limitación conocida:** se asume PostgreSQL en producción; SQLite ignora `select_for_update` (solo afecta tests locales no concurrentes); no se testeó concurrencia real con hilos.

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

---

## LIMS B0/B1 (notas)

- Numerador `codigo_barra` (`MUE-YYYY-NNNNNN`) no usa bloqueo global explícito; bajo alta concurrencia podría requerir secuencia dedicada o bloqueo por año.
- Estado `EN_PROCESO` en `Muestra` reservado para fases futuras (conservación admite `RECIBIDA` o `EN_PROCESO` en servicio).
- Sin FK obligatoria resultado↔muestra: riesgo de desalineación operativa hasta B2.

---

## LIMS B3.1 — Microbiología base (notas / pendientes)

- Numerador `numero` de `EstudioMicrobiologia` (`MIC-YYYY-NNNNNN`) usa el mismo patrón que `codigo_barra` y comparte la limitación: sin bloqueo global; bajo alta concurrencia conviene migrar a secuencia dedicada.
- **No** se cableó el estado decorativo `INCUBANDO` (sigue sin transición operativa). Los estados `IDENTIFICACION`, `ANTIBIOGRAMA`, `LISTO_PARA_VALIDAR`, `VALIDADO` e `INFORMADO` se implementaron en **B3.2 / B3.3 / B3.4**.
- **Pendiente** (post–B3.4): PDF de informe, frontend dedicado microbiología, integración LIMS externa, QC/equipamiento, microbiología molecular, toxicología, anatomía patológica.
- `secretaria` y `enfermeria` quedan **sin lectura** de microbiología técnica ni de informes (decisión documentada — `LimsMicrobiologiaPermission` / `LimsMicrobiologiaInformePermission`). Revisar política si se requiere visibilidad clínica/secretaría.
- El `medico` ve estudios sólo si su `medico_interno.user` coincide; no se modela todavía visibilidad por equipo/servicio.
- Auditoría: metadata estable cubre `estudio_id`, `numero_estudio`, `solicitud_id`, `numero_solicitud`, `muestra_id`, `codigo_barra`, `siembra_id`, `lectura_id`, `estado_anterior`, `estado_nuevo`. No se registra PHI del paciente (solo `Paciente.pk` vía FK del estudio).
- Frontend: no se modificó. `/laboratorio/examenes-test` sigue siendo pantalla de prueba; `/solicitudes` corresponde al flujo EMR. Microbiología solo expone backend/API en B3.1.

---

## LIMS B3.2 — Microorganismos / aislados / identificación (notas / pendientes)

- **Pendientes B3.3** (no implementados en B3.2): `Antibiotico`, `Antibiograma`, `ResultadoAntibiotico` (implementados ya en B3.3). **Pendientes post–B3.4:** PDF, frontend dedicado, integración LIMS externa, QC/equipamiento, anatomía patológica.
- `AisladoMicrobiologico.requiere_antibiograma` queda registrado; **B3.3** no crea antibiograma automáticamente al marcar el flag (solo POST explícito). Evaluar en UI si se desea un atajo.
- `IdentificacionMicroorganismo` es **append-only** (sin PATCH/DELETE): una identificación errónea se corrige creando otra y/o descartando el aislado. Documentar a usuarios finales para evitar confusión cuando exista UI.
- `AlterField` sobre `EstudioMicrobiologia.estado` en `0006_lims_b3_2_microbiologia_aislados` es no destructivo (solo agrega el choice `IDENTIFICACION`); todos los registros previos se mantienen.
- Visibilidad para `medico`: igual patrón B3.1 (filtrado por `solicitud.medico_interno.user`). Cuando un aislado/identificación se cree fuera del flujo (admin), `medico` sigue requiriendo que la solicitud sea propia para verlo.
- `descartar` aislado **no borra** identificaciones existentes (PROTECT); preserva historia.
- El microorganismo de una identificación no puede estar inactivo en el momento de la creación; no se reevalúa si el catálogo se desactiva después (las identificaciones históricas se conservan tal cual). Evaluar en B3.3 si conviene "marcar como obsoleta" las identificaciones cuyo microorganismo se desactivó.
- `confianza` en identificación: rango 0-100 validado en `clean`; precisión `DECIMAL(5,2)`. No se exige obligatoriedad.
- Frontend: no se modificó. B3.2 sólo expone backend/API; las pantallas de microbiología quedan pendientes.

## LIMS B3.3 — Antibiograma microbiológico (notas / pendientes)

- **Pendientes post–B3.4** (no implementados): PDF de informe, frontend dedicado, integración LIMS externa, QC/equipamiento, anatomía patológica, biología molecular avanzada, toxicología.
- `AisladoMicrobiologico.requiere_antibiograma` sigue siendo informativo: B3.3 **no** crea antibiograma automáticamente al marcar el flag; sólo se crea por POST explícito. Evaluar en B3.4 si la UI debe ofrecer un atajo.
- Antibiograma **no** valida profesionalmente ni emite informe por sí solo; la obligatoriedad de antibiograma `COMPLETO` para **informe final** se aplica en **B3.4** (`verificar_completitud_para_informe_final`).
- `ResultadoAntibiotico` no admite mover `antibiograma`/`antibiotico` por PATCH (solo `halo_mm`/`mic`/`interpretacion`/`observaciones`); para corregir, eliminar (no soportado) o cancelar todo el antibiograma. Si se requiere "anular un resultado individual" se evaluará en B3.4 mediante motivo + nuevo registro.
- `actualizar_resultado_antibiotico` rechaza la edición si el `Antibiotico` está inactivo en el momento de la edición (defensivo): los resultados históricos se conservan, pero no se pueden modificar después de desactivado el catálogo. Documentar para evitar confusión.
- `AlterField` sobre `EstudioMicrobiologia.estado` en `0007_lims_b3_3_microbiologia_antibiograma` es no destructivo (solo agrega el choice `ANTIBIOGRAMA`); todos los registros previos se mantienen.
- `UniqueConstraint(antibiograma, antibiotico)` evita duplicados a nivel DB; la API devuelve 400 con mensaje claro antes de tocar la BD (verificación previa) además del INTEGRITY de Postgres.
- `select_for_update` se usa con `of=("self",)` para evitar el error de Postgres "FOR UPDATE cannot be applied to the nullable side of an outer join" cuando el `select_related` toca FKs nullable (`microorganismo`).
- Visibilidad para `medico` en informes: `LimsMicrobiologiaInformePermission` filtra por `estudio.solicitud.medico_interno.user` (consistente con B3.1–B3.3).
- ~~Frontend: no se modificó. B3.3 sólo expone backend/API; las pantallas de antibiograma quedan pendientes.~~ **UI-2 (mayo 2026):** consola frontend de antibiograma e informes en `frontend/` commit `d46d276`; ver sección «Frontend UI-2 — Microbiología».

## LIMS B3.4 — Informes microbiológicos (notas / pendientes)

- **Sin DELETE** de informes; **PATCH** solo en estado **`BORRADOR`** (no en `EMITIDO` ni `VALIDADO`).
- Anular un informe **FINAL** en `EMITIDO` deja el estudio en **`LISTO_PARA_VALIDAR`** hasta que laboratorio/admin emita un nuevo `FINAL` (diseño intencional).
- `marcar-informado` es explícito: no se asume entrega automática al validar.
- Numerador `MIC-YYYY-NNNNNN` comparte el patrón sin bloqueo global (misma nota que B3.1).
- **Pendientes post–B3.4:** PDF, integración LIMS externa, QC/equipamiento avanzado. ~~Frontend dedicado microbiología~~ cubierto por **UI-2** (sin PDF/firma).

## LIMS B4.1 — Resultados clínicos estructurados (notas / pendientes)

- Cálculo de `es_patologico`/`es_critico` es **global** por `TipoExamen` (sin edad, sexo ni condición clínica).
- No hay conversión de unidades ni fórmulas derivadas; `valor_obtenido` sigue siendo obligatorio para considerar el resultado cargado y para validar la orden.
- Cambiar rangos en catálogo **no** altera snapshots ya guardados en resultados históricos.
- **Pendientes post–B4.1:** PDF informe clínico general, frontend avanzado de carga, QC/equipamiento, rangos por demografía, Westgard.
