# PROD-12 — Autorización institucional y piloto con datos reales mínimos (documental)

**Fase:** PROD-12 — marco de gobernanza para evaluar autorización institucional externa y piloto acotado con datos reales mínimos  
**Estado:** documentación + plantilla de alcance + tests estáticos  
**Fecha:** junio 2026

---

## Objetivo

Documentar el **procedimiento formal** para evaluar una eventual **autorización institucional externa** y un **piloto limitado con datos reales mínimos**, solo si existe **GO post-piloto técnico PROD-11**, cierre de acciones críticas y acta/autorización **fuera del repo**.

**PROD-12 no habilita producción clínica abierta desde el repositorio.** No sustituye acta institucional firmada, validación UX frontend ni go-live clínico general.

---

## Alcance

| Incluye | No incluye |
|---------|------------|
| Precondiciones obligatorias antes de datos reales mínimos | Producción clínica abierta |
| Revisión de GO post-piloto PROD-11 | Modificar modelos, permisos, endpoints |
| Cierre de acciones correctivas críticas | PHI en repo o plantillas rellenadas |
| Autorización institucional externa (procedimiento) | Autorizaciones institucionales reales en git |
| Alcance funcional limitado y plantilla sanitizada | Actas reales en git |
| Usuarios internos autorizados (definición fuera del repo) | Restore destructivo |
| Datos reales mínimos permitidos / prohibidos | Ejecución real del piloto desde este commit |
| Criterios GO/NO-GO, suspensión, incidentes, rollback | Validación UX frontend en este repo |
| Verificaciones mínimas de endpoints (evidencia externa) | Cambios EMR/LIMS funcionales |

---

## Fuera de alcance explícito

- **Producción clínica abierta** a población general o usuarios no autorizados nominalmente.
- Incluir autorizaciones institucionales firmadas, actas reales o listados nominales reales en el repositorio.
- Declarar frontend validado sin evidencia externa en su propio despliegue.
- Modificar reglas EMR/LIMS, permisos funcionales, estados, modelos, migraciones o configuración productiva ejecutable.
- Ejecutar comandos contra producción real desde el IDE o versionar evidencia operativa sensible.

---

## Precondiciones obligatorias

Antes de **cualquier** uso con datos reales mínimos, deben cumplirse **todas** las siguientes condiciones. La ausencia de una sola condición implica **NO-GO**.

| # | Precondición | Evidencia |
|---|--------------|-----------|
| 1 | **GO post-piloto PROD-11** real (no solo documentación) | Acta revisión externa sanitizada |
| 2 | Evidencia PROD-10 piloto técnico revisada conforme `PROD_POST_PILOT_REVIEW.md` | Fuera del repo |
| 3 | **Acciones críticas cerradas** (registro PROD-11 acciones) | Evidencia de cierre sanitizada |
| 4 | Acciones **alta** severidad: cerradas o **aceptadas con mitigación** formal | Acta externa |
| 5 | **Autorización institucional formal externa** (comité, dirección, ética según política) | Acta firmada **fuera del repo** |
| 6 | **Responsable institucional** designado | Identificador interno fuera del repo |
| 7 | **Responsable clínico** designado | Identificador interno fuera del repo |
| 8 | **Responsable técnico/operativo** designado | Identificador interno fuera del repo |
| 9 | Alcance funcional limitado completado (`PROD_MIN_REAL_DATA_SCOPE_TEMPLATE.md` copiado fuera del repo) | Documento externo |
| 10 | Backups programados confirmados | Referencia operador |
| 11 | Restore drill **PROD-7** confirmado | Evidencia sanitizada |
| 12 | Observabilidad mínima **PROD-9** confirmada | Resultado checks |
| 13 | `/media/` no público confirmado | Smoke/evidencia |
| 14 | APIs protegidas confirmadas | Smoke/evidencia |
| 15 | Frontend validado por separado **si existe UI real** | Evidencia externa o exclusión explícita |
| 16 | **Producción clínica abierta: FUERA DE ALCANCE** | Confirmación en acta |

---

## GO post-piloto PROD-11

PROD-12 **exige** un **GO post-piloto** documentado externamente conforme `PROD_POST_PILOT_REVIEW.md`:

- Evidencia externa completa y **sanitizada** (sin PHI, secretos, tokens).
- PROD-8, PROD-9, PROD-10 aplicados conforme runbooks.
- Smoke anónimo/autenticado OK en evidencia.
- Sin incidentes de seguridad abiertos.
- Acciones correctivas críticas cerradas (o GO condicionado con plan fechado **antes** de datos reales).

**GO condicionado PROD-11:** no autoriza datos reales mínimos hasta cierre de acciones pendientes.

**NO-GO PROD-11:** bloquea PROD-12 operativo; solo aplica la guía documental para planificación futura.

Ruta sugerida acta PROD-11:

```text
../synesis_pilot_evidence/PROD-11-post-pilot-review-YYYYMMDD.md
```

---

## Acciones correctivas críticas

Revisar registro completado a partir de `PROD_POST_PILOT_ACTIONS_TEMPLATE.md` (**fuera del repo**):

| Estado acciones | Permite avance PROD-12 operativo |
|-----------------|----------------------------------|
| Críticas **abiertas** | **NO** |
| Críticas **cerradas** con evidencia sanitizada | Sí (si resto precondiciones OK) |
| Alta **abiertas** sin decisión formal | **NO** |
| Alta **aceptadas con mitigación** documentada | Sí (si autorización institucional OK) |

Toda acción que bloquea GO según plantilla PROD-11 debe resolverse antes de datos reales mínimos.

---

## Autorización institucional externa

La autorización institucional es **obligatoria** y debe existir **fuera del repositorio git**:

- Acta de comité, resolución de dirección, dictamen de ética o equivalente según política institucional.
- Debe referenciar alcance limitado, ventana temporal, responsables y datos permitidos.
- **No reemplaza** la plantilla `PROD_MIN_REAL_DATA_SCOPE_TEMPLATE.md`; la complementa.

### Prohibido versionar en git

- Autorizaciones institucionales reales (PDFs firmados).
- Actas reales de comité o dirección.
- Listados nominales reales de usuarios autorizados.
- Evidencia operativa con PHI.

Ruta sugerida autorización externa:

```text
../synesis_institutional_auth/PROD-12-authorization-YYYYMMDD.pdf
../synesis_institutional_auth/PROD-12-scope-YYYYMMDD.md
```

---

## Responsables

Designar **fuera del repo** (identificadores internos, sin PHI):

| Rol | Responsabilidad |
|-----|-----------------|
| **Responsable institucional** | Aprueba alcance, autoriza ventana, recibe reportes GO/NO-GO |
| **Responsable clínico** | Valida minimización de datos, criterios clínicos, suspensión por riesgo clínico |
| **Responsable técnico/operativo** | Ejecuta checks, observabilidad, backups, rollback, incidentes técnicos |
| **Responsable de incidentes** | Coordina respuesta según `PROD_OBSERVABILITY_MIN.md` |

Sin responsables designados → **NO-GO**.

---

## Alcance funcional limitado

El alcance debe ser **explícito, acotado y aprobado** en documento externo basado en `PROD_MIN_REAL_DATA_SCOPE_TEMPLATE.md`.

Principios:

- **Mínimo privilegio:** solo módulos y roles estrictamente necesarios.
- **Minimización de datos:** solo campos estrictamente necesarios para el objetivo del piloto.
- **Ventana limitada:** fecha de inicio y fin obligatorias.
- **Revisión periódica:** criterios de suspensión inmediata activos durante toda la ventana.

---

## Módulos habilitados (ejemplos orientativos — definir en alcance externo)

Marcar en alcance externo solo lo autorizado institucionalmente. Ejemplos **no exhaustivos**:

| Módulo | Notas |
|--------|-------|
| Auth / sesión | Login nominal autorizado; sin usuarios compartidos |
| Pacientes (lectura/edición limitada) | Solo si autorizado; datos mínimos |
| Turnos / agenda | Solo si autorizado y acotado |
| Atenciones | Solo si autorizado clínicamente |
| Descargas protegidas PROD-4-A | Solo si alcance incluye adjuntos; auditoría PROD-4-B |
| LIMS | Solo si autorizado **explícitamente**; rol `laboratorio` es operador LIMS, no clínico EMR general; acceso LIMS reservado a admin/superuser según reglas vigentes |

**Regla:** módulo no listado en alcance externo = **excluido**.

---

## Módulos excluidos (por defecto salvo autorización explícita)

| Módulo / capacidad | Motivo |
|--------------------|--------|
| Producción clínica abierta | Fuera de alcance PROD-12 |
| Registro masivo / importaciones no autorizadas | Riesgo de exceso de datos |
| Exportaciones bulk no auditadas | Riesgo PHI |
| Endpoints LIMS no incluidos en alcance | Complejidad y permisos reservados |
| Funcionalidades en desarrollo no validadas | Sin evidencia PROD-10 |
| Frontend no validado externamente | Riesgo residual UX/seguridad UI |

---

## Roles y usuarios

### Roles habilitados

Definir en alcance externo. Respetar reglas vigentes:

- Rol **`laboratorio`:** operador LIMS, **no** clínico EMR general.
- LIMS: reservado a admin/superuser salvo política institucional explícita documentada externamente.
- **Mínimo privilegio:** preferir roles específicos sobre admin.

### Usuarios nominales

- Lista de usuarios autorizados **fuera del repo** (identificadores internos).
- **Prohibición de usuarios compartidos.**
- Revisión de acceso admin antes de inicio.
- Revocación inmediata al cierre de ventana o suspensión.

---

## Datos reales mínimos permitidos

Solo datos estrictamente necesarios para el objetivo del piloto, autorizados en acta externa:

| Categoría | Ejemplo orientativo (sanitizado) |
|-----------|----------------------------------|
| Identificadores mínimos | ID interno institucional acordado |
| Datos demográficos mínimos | Solo campos aprobados en alcance |
| Datos clínicos acotados | Solo flujos y campos del alcance |
| Adjuntos clínicos | Solo si descargas protegidas PROD-4-A autorizadas |

Cantidad: **mínima** (p. ej. cohorte acotada acordada externamente, sin identificar en repo).

---

## Datos prohibidos

| Prohibido | Acción si detectado |
|-----------|---------------------|
| PHI no autorizada en alcance | Suspensión inmediata + incidente |
| DNI, nombres, resultados clínicos en repo/evidencia git | NO-GO + incidente |
| Dumps, backups, logs completos en repo | NO-GO |
| Tokens, passwords, cookies, `SECRET_KEY` | NO-GO + rotación |
| Datos de pacientes no incluidos en alcance | Suspensión + revisión clínica |
| Exportaciones no auditadas | Suspensión |

---

## Seguridad y confidencialidad

| Requisito | Verificación |
|-----------|--------------|
| Mínimo privilegio | Alcance externo + revisión roles |
| Autorización por rol | Permisos funcionales vigentes (sin modificar en PROD-12) |
| `/media/` no expuesto | Smoke + Nginx PROD-3/4 |
| APIs protegidas bloquean anónimos | `GET /api/pacientes/` → 401/403 |
| No exponer archivos clínicos directamente | Solo endpoints download protegidos |
| No exponer PHI en logs/evidencia | Revisión observabilidad PROD-9 |
| No versionar secretos | Política repo |
| Logs y evidencia bajo acceso restringido | Operador |
| **Sospecha PHI expuesta** | **Suspensión inmediata + NO-GO** |

---

## Auditoría y trazabilidad

Documentar en evidencia externa (sin PHI):

| Elemento | Uso |
|----------|-----|
| Auditoría descargas PROD-4-B | Si alcance incluye adjuntos clínicos |
| Auditoría LIMS crítica | Si alcance incluye LIMS |
| Request ID | Si disponible en logs |
| Hora de eventos relevantes | Timeline incidentes |
| Entorno | staging/pilot |
| Commit HEAD | Artefacto desplegado |
| Usuario de prueba/autorizado | Rol documentado; **sin credenciales** |
| Resultado de cada check | GO/NO-GO por ítem |
| Incidentes o anomalías | Clasificación sanitizada |
| Acciones correctivas | Referencia PROD-11 |
| Decisión GO/NO-GO | Acta externa |

**No modificar** la app `auditoria` en PROD-12. **No agregar** logging de PHI.

---

## Observabilidad

Confirmar aplicación de `PROD_OBSERVABILITY_MIN.md` y `deploy/observability/check_observability.example.sh`:

- [ ] Logs backend/Gunicorn, Nginx, PostgreSQL revisados
- [ ] Errores 4xx/5xx analizados (agregados)
- [ ] Healthcheck `GET /api/health/` OK
- [ ] Contenedores: estado, health, restart count
- [ ] DB conectividad; disco
- [ ] Responsable de incidentes identificado

Observabilidad frontend: **fuera de este repo** si existe UI real.

---

## Backups y restore

| Check | Criterio |
|-------|----------|
| Backups programados | Política operador confirmada |
| Artefactos recientes | Checksum OK referenciado externamente |
| Restore drill PROD-7 | Antecedente verificado |
| Rollback operativo | Documentado y probado en staging |

Ver `deploy/backup/README.md`, `deploy/backup/RESTORE_DRILL_STAGING.md`.

---

## Verificaciones mínimas de endpoints

Deben estar cubiertas por evidencia externa previa (PROD-10/11) o plan operativo del piloto mínimo. **No agregar endpoints nuevos.**

| Endpoint | Criterio |
|----------|----------|
| `GET /api/health/` | `200` |
| `GET /media/` | ≠ `200` |
| `GET /api/pacientes/` anónimo | `401` o `403` |
| `POST /api/auth/login/` | `200` con usuario sintético o interno autorizado (sin credenciales en evidencia) |
| `GET /api/auth/current-user/` | `200` con sesión/token válido del usuario de prueba |
| `GET /api/registros-procedimientos/{id}/download-adjunto-resultado/` | Solo si alcance autoriza y existe caso sintético o autorización formal |
| `GET /api/registros-quirurgicos/{id}/download-consentimiento-informado/` | Idem |
| Endpoints LIMS | Solo si módulo LIMS autorizado explícitamente en alcance institucional |

Cualquier `200` anónimo en API clínica → **NO-GO** y suspensión.

---

## Incidentes

Procedimiento:

1. **Detectar** — observabilidad PROD-9, usuarios autorizados, revisión logs (sin PHI en reportes).
2. **Clasificar** — operativo / seguridad / disponibilidad / clínico.
3. **Contener** — suspensión inmediata si seguridad o PHI.
4. **Registrar** — acta incidente **fuera del repo** (sanitizada).
5. **Escalar** — responsable institucional + clínico + técnico.
6. **Resolver** — acción correctiva; referenciar PROD-11 si aplica.
7. **Revisar GO/NO-GO** — puede requerir cierre de ventana.

**Sospecha de PHI expuesta en logs, evidencia o `/media/` público:** suspensión inmediata obligatoria.

---

## Suspensión inmediata

Activar **sin demora** si ocurre cualquiera de:

| Trigger | Acción |
|---------|--------|
| `/media/` público o accesible anónimamente | Suspender + rollback |
| API clínica responde `200` anónimo | Suspender + investigar |
| PHI en logs, evidencia o repo | Suspender + incidente seguridad |
| Secretos expuestos | Suspender + rotación |
| Incidente crítico sin contención | Suspender |
| Fin de ventana autorizada | Cierre programado |
| Orden responsable institucional/clínico | Suspender |
| Desviación del alcance funcional | Suspender + revisión |

Comunicar suspensión a responsables designados (sin PHI en comunicaciones).

---

## Rollback operativo

Pasos orientativos (ejecutar en staging/pilot según runbooks previos):

1. **Detener** ingreso de datos reales (suspensión ventana).
2. **Revocar** accesos de usuarios del piloto (fuera del repo — gestión identidad).
3. **Revertir** despliegue a commit HEAD conocido bueno si aplica.
4. **Verificar** `/media/` privado y APIs protegidas post-rollback.
5. **Ejecutar** smoke mínimo (`prod_readiness_smoke.example.sh` o `prod_technical_pilot.example.sh`).
6. **Documentar** resultado en acta externa.
7. **Evaluar** necesidad de restore desde backup (solo operador; no destructivo desde repo).

Referencia: `PROD_PREPILOT_CHECKLIST.md` (rollback), `PROD_TECHNICAL_PILOT_RUNBOOK.md`.

---

## Evidencia permitida

| Permitido | Ubicación |
|-----------|-----------|
| Plantillas sanitizadas del repo | Git (sin rellenar) |
| Actas, autorizaciones, alcance completado | **Fuera del repo** |
| Evidencia sanitizada (códigos HTTP agregados, timestamps, commit) | **Fuera del repo** |
| Registro acciones PROD-11 cerradas | **Fuera del repo** |
| Checksums de backups (sin contenido) | **Fuera del repo** |

---

## Evidencia prohibida en git

- PHI, DNI, nombres de pacientes, resultados clínicos
- Autorizaciones institucionales reales
- Actas reales
- Listados nominales reales de usuarios
- Tokens, passwords, cookies, `SECRET_KEY`
- Dumps, backups, logs completos sensibles
- Capturas con datos clínicos

---

## Frontend separado

**Este repositorio no contiene SPA React versionada en la raíz.**

| Hecho | Implicación PROD-12 |
|-------|---------------------|
| No hay `package.json` / `frontend/src` canónico en raíz | Validación UX no cubierta por este repo |
| Si existe frontend real | Validar y autorizar en **repositorio/despliegue separado** |
| PROD-12 backend/documental | **No valida UX productiva** |
| Sin evidencia frontend externa | **Riesgo residual** — excluir frontend del alcance con datos reales mínimos |

Revisión pendiente fuera del repo: navegador, errores JS, performance UI, sesiones frontend, seguridad UI.

---

## Matriz GO / NO-GO PROD-12

### GO (autoriza inicio piloto datos reales mínimos — decisión externa)

- Todas las precondiciones obligatorias cumplidas
- GO post-piloto PROD-11 documentado externamente
- Acciones críticas cerradas; altas con decisión formal
- Autorización institucional externa vigente
- Responsables institucional, clínico y técnico designados
- Alcance funcional limitado completado y aprobado externamente
- Módulos, roles y usuarios nominales definidos fuera del repo
- Datos permitidos/prohibidos explícitos
- Ventana de inicio/fin definida
- Backups, restore PROD-7, observabilidad PROD-9 confirmados
- `/media/` privado; APIs protegidas verificadas
- Plan incidentes y rollback documentado
- Frontend validado externamente **o** excluido explícitamente del alcance
- **Producción clínica abierta: FUERA DE ALCANCE**

### NO-GO

- Falta GO post-piloto PROD-11 o evidencia incompleta/no sanitizada
- Acciones críticas abiertas
- Sin autorización institucional externa
- Sin responsables designados
- Alcance funcional ambiguo o no aprobado
- PHI/secretos en evidencia
- Frontend requerido sin validación externa
- Intento de producción clínica abierta

### GO condicionado

No aplica operativamente a datos reales mínimos. Resolver condiciones antes de inicio.

---

## Confirmación: producción clínica abierta fuera de alcance

| Afirmación | Estado |
|------------|--------|
| PROD-12 es marco documental de gobernanza | **Sí** |
| Este commit habilita producción clínica abierta | **No** |
| Uso con datos reales mínimos depende de decisión externa | **Sí** |
| Cualquier piloto real requiere acta y autorización fuera del repo | **Sí** |
| El repo no debe contener PHI, actas reales ni autorizaciones reales | **Sí** |

---

## Cierre del piloto datos reales mínimos

1. Cierre de ventana o suspensión.
2. Revocación de accesos nominales.
3. Acta de cierre **fuera del repo** (sanitizada).
4. Revisión incidentes y lecciones aprendidas.
5. Actualización registro riesgos operador.
6. Decisión sobre siguiente fase (sin producción clínica abierta desde repo).
7. **No** commitear evidencia ni autorizaciones.

Ruta sugerida acta cierre:

```text
../synesis_institutional_auth/PROD-12-pilot-closure-YYYYMMDD.md
```

---

## Referencias

| Documento | Fase |
|-----------|------|
| `PROD_POST_PILOT_REVIEW.md` | PROD-11 |
| `PROD_POST_PILOT_ACTIONS_TEMPLATE.md` | Acciones correctivas |
| `PROD_MIN_REAL_DATA_SCOPE_TEMPLATE.md` | Alcance piloto |
| `PROD_PREPILOT_CHECKLIST.md` | PROD-8 |
| `PROD_OBSERVABILITY_MIN.md` | PROD-9 |
| `PROD_TECHNICAL_PILOT_RUNBOOK.md` | PROD-10 |
| `deploy/backup/RESTORE_DRILL_STAGING.md` | PROD-7 |
| `DOC_RIESGOS_DEUDA_TECNICA.md` | Deuda técnica |
| `DOC_PERMISOS_AUDITORIA.md` | Permisos y auditoría |

---

## Siguiente fase recomendada

Tras cierre exitoso del piloto con datos reales mínimos (decisión externa): evaluar hardening operativo sostenido, monitoreo externo desplegado, validación frontend completa y — solo con autorización institucional ampliada explícita — planificar fases posteriores. **Producción clínica abierta permanece fuera de alcance** hasta fase dedicada con requisitos legales y operativos adicionales.
