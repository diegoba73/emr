# PROD-11 — Revisión post-piloto y hardening operativo

**Fase:** PROD-11 — revisión formal posterior al piloto técnico controlado (PROD-10)  
**Estado:** documentación + plantilla de acciones + tests estáticos  
**Fecha:** junio 2026

---

## Objetivo

Proveer el **procedimiento de revisión** para analizar la evidencia sanitizada generada **fuera del repo** tras la ejecución real del piloto técnico (PROD-10), registrar **GO/NO-GO post-piloto**, identificar gaps operativos, definir **acciones correctivas** y preparar criterios para una eventual **autorización institucional** de uso con datos reales mínimos.

**PROD-11 no habilita producción clínica abierta.** No sustituye autorización legal, validación UX frontend ni go-live clínico.

---

## Alcance

| Incluye | No incluye |
|---------|------------|
| Revisión de evidencia externa del piloto PROD-10 | Producción clínica abierta |
| Verificación de aplicación PROD-8, PROD-9, PROD-10 | PHI en repo o plantillas rellenadas |
| Matriz GO/NO-GO post-piloto | Modificar modelos, permisos, endpoints |
| Riesgos residuales y acciones correctivas | Autorizaciones institucionales reales en git |
| Criterios mínimos para datos reales mínimos | Restore destructivo |
| Revisión frontend separada (si aplica UI) | Validación UX en este repo |

---

## Fuera de alcance explícito

- **Producción clínica abierta** a población general.
- Incluir autorizaciones institucionales firmadas en el repositorio.
- Declarar frontend validado sin evidencia externa.
- Modificar reglas EMR/LIMS, auditoría o configuración productiva ejecutable.

---

## Evidencia requerida (fuera del repo)

El revisor debe tener acceso a evidencia completada a partir de:

- `PROD_TECHNICAL_PILOT_EVIDENCE_TEMPLATE.md` (copia externa rellenada)
- Ruta sugerida: `../synesis_pilot_evidence/PROD-10-technical-pilot-YYYYMMDD.md`
- Evidencia PROD-7 restore drill si aplica: `../synesis_restore_evidence/`

### Campos mínimos a revisar

| Campo | Revisar |
|-------|---------|
| Ambiente piloto | Nombre interno, tipo staging/pilot |
| Commit HEAD | Hash desplegado durante piloto |
| Ventana piloto | Inicio y fin |
| Responsable operativo | Identificador interno (fuera del repo) |
| GO/NO-GO piloto | Resultado documentado |
| Smoke anónimo/autenticado | Códigos HTTP agregados |
| Observabilidad | Resultado `check_observability.example.sh` |
| Incidentes | Lista sanitizada |
| Riesgos residuales piloto | Texto sin PHI |

**No** importar evidencia al repositorio git.

---

## Evidencia prohibida

- PHI, DNI, nombres de pacientes, resultados clínicos
- Tokens, passwords, cookies, `SECRET_KEY`
- Dumps, backups, logs completos sensibles
- Autorizaciones institucionales reales (PDFs firmados)
- Paths de archivos clínicos

Si la evidencia externa contiene elementos prohibidos → **NO-GO** y abrir incidente de seguridad.

---

## Revisión de PROD-8 (pre-piloto)

Confirmar en evidencia externa que se aplicó `PROD_PREPILOT_CHECKLIST.md`:

- [ ] `DEBUG=False` confirmado
- [ ] `SECRET_KEY` real fuera del repo (sin valor en evidencia)
- [ ] `ALLOWED_HOSTS` explícito
- [ ] `CSRF_TRUSTED_ORIGINS` y CORS cerrados
- [ ] TLS/HTTPS o proxy con `X-Forwarded-Proto`
- [ ] `/media/` no público; backend sin `:8000` público
- [ ] Backups programados definidos
- [ ] Rollback documentado
- [ ] Usuarios nominales fuera del repo

**Gap:** marcar en riesgos residuales si algún ítem no fue verificado.

---

## Revisión de PROD-9 (observabilidad)

Confirmar aplicación de `PROD_OBSERVABILITY_MIN.md`:

- [ ] Logs backend/Gunicorn revisados
- [ ] Logs Nginx/proxy revisados
- [ ] Logs PostgreSQL revisados
- [ ] Errores **4xx** y **5xx** analizados (agregados, sin payloads clínicos)
- [ ] Contenedores: estado, **health**, **restart count**
- [ ] DB: conectividad (`pg_isready`), tamaño agregado
- [ ] Disco: DB, media, backups, logs
- [ ] Responsable de incidentes identificado

---

## Revisión de PROD-10 (ejecución piloto)

Confirmar conformidad con `PROD_TECHNICAL_PILOT_RUNBOOK.md`:

- [ ] Ventana piloto ejecutada según runbook
- [ ] `deploy/smoke/prod_technical_pilot.example.sh` ejecutado
- [ ] `deploy/observability/check_observability.example.sh` ejecutado
- [ ] Evidencia completada fuera del repo
- [ ] Smoke autenticado con usuario **sintético** o interno autorizado (sin credenciales en evidencia)

---

## Revisión de ambiente

| Check | Criterio revisión |
|-------|-------------------|
| Tipo entorno | staging/pilot controlado — no producción clínica abierta |
| Aislamiento | Sin tráfico de usuarios finales no autorizados |
| Commit HEAD | Coincide con artefactos desplegados |
| Configuración | Sin secretos versionados en repo |

---

## Revisión smoke anónimo

Verificar en evidencia externa:

| Endpoint | Criterio |
|----------|----------|
| `GET /api/health/` | `200` |
| `GET /media/` | ≠ `200` |
| `GET /api/pacientes/` anónimo | `401` o `403` |
| `GET /api/turnos/` anónimo | ≠ `200` |
| `GET /api/atenciones/` anónimo | ≠ `200` |

Cualquier `200` anónimo en API clínica → **NO-GO** seguridad.

---

## Revisión smoke autenticado

| Check | Criterio |
|-------|----------|
| `POST /api/auth/login/` | `200` (sin token en evidencia) |
| `GET /api/auth/current-user/` | `200` si smoke autenticado ejecutado |
| Usuario de prueba | Rol documentado; **sin** password/token |

Descargas protegidas (opcional, solo dato sintético):

- `GET /api/registros-procedimientos/{id}/download-adjunto-resultado/`
- `GET /api/registros-quirurgicos/{id}/download-consentimiento-informado/`
- Auditoría PROD-4-B: conteo agregado de eventos — sin metadata clínica

---

## Revisión media privada

- [ ] `/media/` no público durante todo el piloto
- [ ] Sin workaround exponiendo media por Nginx
- [ ] Evidencia sin nombres de archivos clínicos

---

## Revisión backups

- [ ] Política backups programados confirmada
- [ ] Artefactos recientes fuera del repo (checksum OK referenciado)
- [ ] PROD-7 restore drill referenciado como antecedente
- [ ] Sin fallos críticos de backup durante ventana piloto

---

## Revisión de incidentes

Para cada incidente en evidencia externa:

1. Clasificar: operativo / seguridad / disponibilidad
2. Evaluar impacto (sin PHI)
3. Verificar resolución o acción correctiva abierta
4. **Sospecha PHI expuesta** → **NO-GO** obligatorio

---

## Revisión seguridad / PHI

| Situación | Resultado revisión |
|-----------|-------------------|
| `/media/` público en algún momento | NO-GO |
| API clínica anónima 200 | NO-GO |
| PHI en evidencia externa | NO-GO + incidente |
| Secretos en evidencia | NO-GO |
| 5xx sostenido sin mitigación | NO-GO o condicionado según política |

---

## Revisión frontend separada

**Este repositorio no contiene SPA React canónica en la raíz.**

| Check | Resultado |
|-------|-----------|
| ¿Existe UI real en despliegue separado? | Sí / No / N/A |
| ¿Evidencia frontend externa revisada? | Sí / No |
| ¿Observabilidad frontend (errores JS, UX)? | Fuera de este repo |

**Sin evidencia frontend externa:** marcar como **riesgo residual** — no como validado.

---

## Matriz GO / NO-GO post-piloto

### GO post-piloto (hardening aceptable para siguiente etapa)

- Evidencia externa completa y sanitizada
- PROD-8, PROD-9, PROD-10 aplicados conforme runbooks
- Healthcheck OK; media privada; APIs protegidas OK
- Smoke autenticado OK (o SKIP justificado)
- Sin incidentes de seguridad abiertos
- Sin PHI/secretos en evidencia
- Acciones correctivas críticas cerradas o con plan fechado
- Riesgos residuales documentados y aceptados por responsable
- **Producción clínica abierta: FUERA DE ALCANCE**

### NO-GO post-piloto

- Evidencia incompleta o con elementos prohibidos
- Fallos de seguridad (media pública, APIs anónimas)
- PHI o secretos expuestos
- Backups/restore drill no verificados según política
- Incidentes críticos sin resolución
- Intento de avanzar a producción clínica abierta

### GO condicionado

- Piloto técnicamente exitoso con acciones correctivas menores pendientes
- Requiere cierre de acciones antes de datos reales mínimos
- Documentar en `PROD_POST_PILOT_ACTIONS_TEMPLATE.md` fuera del repo

---

## Riesgos residuales

Registrar en revisión (plantilla acciones o acta externa):

- TLS real no validado end-to-end
- APM externo no desplegado
- Frontend sin evidencia de revisión
- Gaps de cobertura operativa (horarios, escalamiento)
- Deuda técnica documentada en `DOC_RIESGOS_DEUDA_TECNICA.md`

---

## Acciones correctivas

Usar plantilla: `PROD_POST_PILOT_ACTIONS_TEMPLATE.md` (**completar fuera del repo**).

Toda acción crítica de seguridad debe cerrarse antes de considerar datos reales mínimos.

---

## Criterios mínimos para datos reales mínimos

**No son autorización institucional.** Son precondiciones técnicas documentales:

1. GO post-piloto (o GO condicionado con acciones cerradas)
2. Autorización institucional formal **fuera del repo** (acta/comité)
3. Minimización de datos; solo campos estrictamente necesarios
4. Usuarios nominales y roles revisados
5. Backups y restore drill verificados
6. Monitoreo operativo activo (mínimo PROD-9 + mejoras si aplica)
7. Frontend validado en despliegue separado si hay UI
8. Plan de incidentes y rollback probado
9. Evidencia sanitizada archivada
10. **Producción clínica abierta sigue sin habilitar**

---

## Cierre post-piloto

1. Completar revisión con matriz GO/NO-GO
2. Archivar acta de revisión fuera del repo
3. Comunicar resultado a stakeholders internos (sin PHI)
4. Actualizar registro de riesgos operativos del operador
5. **No** commitear evidencia ni autorizaciones al repositorio

Ruta sugerida acta revisión:

```text
../synesis_pilot_evidence/PROD-11-post-pilot-review-YYYYMMDD.md
```

---

## Referencias

| Documento | Fase |
|-----------|------|
| `PROD_PREPILOT_CHECKLIST.md` | PROD-8 |
| `PROD_OBSERVABILITY_MIN.md` | PROD-9 |
| `PROD_TECHNICAL_PILOT_RUNBOOK.md` | PROD-10 |
| `PROD_TECHNICAL_PILOT_EVIDENCE_TEMPLATE.md` | Evidencia piloto |
| `PROD_POST_PILOT_ACTIONS_TEMPLATE.md` | Acciones correctivas |
| `DOC_RIESGOS_DEUDA_TECNICA.md` | Deuda técnica |

---

## Siguiente fase recomendada

**PROD-12 — Autorización institucional y piloto con datos reales mínimos (documental):** solo tras GO post-piloto, acta externa y cierre de acciones críticas — **sin habilitar producción clínica abierta** desde el repo.
