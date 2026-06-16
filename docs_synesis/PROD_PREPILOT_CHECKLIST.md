# PROD-8 — Checklist pre-piloto productivo / go-live técnico controlado

**Fase:** PROD-8 — decisión operativa **GO / NO-GO** antes de un piloto productivo técnico controlado  
**Estado:** documentación + tests estáticos  
**Fecha:** junio 2026

---

## Objetivo

Proveer un **checklist formal y repetible** para que el operador responsable decida si SYNESIS EMR/LIMS puede iniciar un **piloto productivo técnico controlado** (staging/pilot interno), integrando fases PROD-1 a PROD-7 ya cerradas o documentadas.

**PROD-8 no habilita producción clínica abierta.** No sustituye autorización institucional, validación legal ni go-live de usuarios finales.

---

## Alcance

| Incluye | No incluye |
|---------|------------|
| Precondiciones técnicas de configuración y seguridad | Producción clínica abierta |
| Usuarios internos nominales y roles permitidos (definición operativa) | Modificar modelos, migraciones, permisos o endpoints |
| Datos sintéticos por defecto; datos reales mínimos solo con autorización formal | PHI en documentación, evidencia o repo |
| Smoke backend/API (`PROD-6`) como verificación mínima | Validación UX completa del frontend |
| Backups programados y restore drill (PROD-5/5-A/7) | TLS/ACME real, WAF, monitoreo externo completo (→ PROD-9) |
| Rollback y ventana de prueba | Restore destructivo sobre DB/media activa |
| Criterios GO/NO-GO y evidencia sanitizada fuera del repo | Commits de secretos, dumps o backups |

---

## Fuera de alcance explícito

- **Producción clínica abierta** a población general o usuarios finales sin control.
- Cambios funcionales EMR/LIMS, estados LIMS, reglas clínicas o PDF LIMS cerrado.
- Ejecución de comandos contra producción real desde este documento.
- Asumir que el checklist backend equivale a validación frontend productiva.

---

## Precondiciones técnicas (obligatorias)

### Django / configuración

- [ ] `DJANGO_DEBUG=False` en el entorno piloto.
- [ ] `DJANGO_SECRET_KEY` **real** generada con `get_random_secret_key()` o gestor de secretos; **fuera del repo**; no usar valores de `.env.production.example`.
- [ ] `DJANGO_ALLOWED_HOSTS` — lista explícita de hosts/FQDN; **sin `*`** ni comodines inseguros.
- [ ] `DJANGO_CORS_ALLOWED_ORIGINS` — orígenes HTTPS del frontend autorizado únicamente; CORS **cerrado** (sin `CORS_ALLOW_ALL_ORIGINS` en prod).
- [ ] `DJANGO_CSRF_TRUSTED_ORIGINS` — consistente con dominio/URL final del frontend que consume cookies.
- [ ] `DJANGO_SECURE_SSL_REDIRECT=True` alineado al despliegue real.
- [ ] `DJANGO_SESSION_COOKIE_SECURE=True` y `DJANGO_CSRF_COOKIE_SECURE=True`.
- [ ] `DJANGO_USE_PROXY_SSL_HEADER=True` si TLS termina en Nginx/LB externo.
- [ ] `DJANGO_RUNTIME=gunicorn` (no `runserver`).
- [ ] `python manage.py check` y `manage.py check --deploy` sin errores bloqueantes en staging piloto.

### Dominio / URL final

- [ ] Dominio o URL final del API documentado por operador (ejemplo genérico: `https://api.example.internal`).
- [ ] Dominio frontend autorizado documentado (ejemplo: `https://app.example.internal`).
- [ ] `DJANGO_HEALTHCHECK_HOST` incluido en `ALLOWED_HOSTS`.

### TLS / HTTPS / proxy

- [ ] **TLS real** terminado en Nginx, balanceador o CDN **o** proxy que preserve `X-Forwarded-Proto=https` hacia Gunicorn.
- [ ] Plantilla `deploy/nginx/nginx.prod.example.conf` revisada; `nginx -t` OK.
- [ ] Map `X-Forwarded-Proto` no pisa header del LB externo (PROD-3).
- [ ] HSTS (`DJANGO_SECURE_HSTS_SECONDS`) solo tras validar HTTPS end-to-end.

### Red y exposición

- [ ] Backend **sin** puerto `8000` público; solo red interna (`expose` en compose prod).
- [ ] Nginx (o proxy equivalente) como único punto de entrada HTTP(S) documentado.
- [ ] `/media/` **no** expuesto públicamente (Nginx `deny`; Django sin `static(MEDIA_URL)` con `DEBUG=False`).

---

## Seguridad y permisos (pre-piloto)

- [ ] Principio de **mínimo privilegio** para cuentas del piloto.
- [ ] **Usuarios internos nominales** definidos por operador **fuera del repo** (lista nominal, no commitear).
- [ ] **No compartir** credenciales entre operadores.
- [ ] Rol **admin/superuser** restringido a responsables técnicos autorizados.
- [ ] Rol `laboratorio` — solo operador LIMS; **no** clínico EMR general (regla de negocio vigente).
- [ ] Validación LIMS (`validar`, transiciones críticas) reservada a **admin/superuser** (sin cambios en esta fase).
- [ ] APIs protegidas: anónimo **no** obtiene `200` en `/api/pacientes/`, `/api/turnos/`, `/api/atenciones/`, `/api/lab/solicitudes/`, `/api/auditoria/events/`.
- [ ] `GET /api/health/` responde `200` (público, no sensible).
- [ ] Auditoría PROD-4-B activa en descargas exitosas de adjuntos turnos.
- [ ] Auditoría LIMS crítica operativa (transiciones, PDF informe según fases cerradas).
- [ ] Logs operativos disponibles; **sin PHI** en logs, evidencia ni capturas.
- [ ] **No secretos** en repo: sin `.env` reales, tokens, passwords ni cookies en evidencia.

---

## Usuarios y roles (piloto controlado)

Definir **fuera del repo** antes del piloto:

| Rol | Permitido en piloto técnico | Restricción |
|-----|----------------------------|-------------|
| `admin` / superuser | Sí (mínimo necesario) | Solo responsables técnicos |
| `medico` | Opcional (sintético) | Sin datos reales salvo autorización formal |
| `paciente` | Opcional (sintético) | Solo flujos acotados |
| `laboratorio` | Sí | Operador LIMS únicamente |
| `secretaria` / `enfermeria` | Según alcance acordado | Documentar en acta operativa |

**Usuarios internos autorizados:** lista nominal mantenida por operador (RRHH/IT); no incluir en git.

---

## Datos permitidos

| Tipo | Permitido en piloto inicial | Condición |
|------|----------------------------|-----------|
| Datos **sintéticos** | **Sí** (por defecto) | Generados para prueba; sin PHI real |
| Datos reales mínimos | Solo con **autorización formal** institucional | Acta firmada; minimización; evidencia sanitizada |
| PHI en evidencia/commits | **No** | Nombres, DNI, resultados clínicos prohibidos |
| Backups con datos reales en repo | **No** | Artefactos fuera del repo |

---

## Módulos habilitados / no habilitados

### Habilitados para piloto técnico backend/API

- Healthcheck, autenticación JWT/sesión.
- APIs EMR/LIMS según permisos existentes (sin cambios).
- Descargas protegidas PROD-4-A (`download-adjunto-resultado`, `download-consentimiento-informado`).
- LIMS flujo crítico documentado (pytest API-level).
- Media privada vía API autenticada.

### No habilitados / fuera de alcance del piloto inicial

- Producción clínica abierta.
- Integración LIMS externa productiva (`integracion_lims` webhooks no montados).
- Object storage S3/MinIO real.
- WAF, rate limiting avanzado.
- Monitoreo externo completo (pendiente PROD-9).

---

## Frontend

**Este repositorio backend no contiene la SPA React canónica en la raíz del monorepo.** Puede existir submódulo `frontend/` o despliegue separado; **PROD-8 no valida UX productiva.**

Antes de piloto con usuarios que interactúen UI:

1. Confirmar **repositorio/despliegue frontend real** del operador.
2. Ejecutar `tsc`, `build` y tests Jest del frontend en su propio pipeline.
3. Validar `REACT_APP_API_URL` (o equivalente) apunta al API piloto.
4. No asumir rutas ni componentes no verificados.

**PROD-8 backend/checklist ≠ validación frontend productiva.**

---

## Backend / API — verificaciones operativas mínimas

Ejecutar en entorno piloto (no destructivo):

| Verificación | Endpoint / acción | Criterio |
|--------------|-------------------|----------|
| Health | `GET /api/health/` | `200` |
| Login sintético | `POST /api/auth/login/` | `200` con usuario de prueba |
| Sesión actual | `GET /api/auth/current-user/` | `200` autenticado |
| APIs protegidas anónimas | `GET /api/pacientes/`, etc. | ≠ `200` |
| Media bloqueada | `GET /media/` vía Nginx | ≠ `200` (404/403) |
| Descarga adjunto (opcional) | `GET .../download-adjunto-resultado/` | Autenticado; auditoría PROD-4-B |
| Descarga consentimiento (opcional) | `GET .../download-consentimiento-informado/` | Idem |

Script parametrizado: `deploy/smoke/prod_readiness_smoke.example.sh` (`BASE_URL` sin secretos en repo). Ver `PROD_READINESS_SMOKE.md`.

---

## DB / PostgreSQL

- [ ] Migraciones aplicadas en job controlado (`RUN_MIGRATIONS=false` en runtime prod; migrar en ventana).
- [ ] Credenciales `DB_*` fuera del repo.
- [ ] Conexión Postgres healthy en compose.
- [ ] **No** ejecutar restore sobre DB activa del piloto.

---

## Media privada

- [ ] `MEDIA_ROOT` solo en backend/volumen interno.
- [ ] Nginx **no** monta volumen media.
- [ ] Descargas clínicas solo vía endpoints autenticados (PROD-4).
- [ ] Evidencia de piloto **sin** nombres de archivos clínicos ni paths sensibles.

---

## Backups / restore

- [ ] Política de **backups programados** definida (frecuencia, retención, responsable) — operador.
- [ ] Scripts PROD-5: `deploy/backup/backup_postgres.example.sh`, `backup_media.example.sh`.
- [ ] Artefactos y checksums **fuera del repo**.
- [ ] **Restore drill real** ejecutado en staging controlado (PROD-7) **o** excepción formal documentada con motivo y fecha.
- [ ] Procedimiento: `deploy/backup/RESTORE_DRILL_STAGING.md`.
- [ ] Verificación no destructiva: `verify_restore.example.sh`.

---

## Monitoreo mínimo (pre-PROD-9)

Definir antes del piloto (documentación operativa; implementación completa → **PROD-9**):

- [ ] Responsable operativo y contacto de escalamiento identificados.
- [ ] Revisión periódica de logs de aplicación y contenedores.
- [ ] Healthcheck compose (`GET /api/health/`) como señal mínima de vida.
- [ ] Alertas externas (Sentry/Datadog/Prometheus) — **pendiente PROD-9** si no existen.

---

## Smoke requerido

1. Tests documentales pytest: `test_prod_prepilot_checklist.py`, `test_prod_readiness_smoke.py`, suites PROD-1 a PROD-7 relacionadas.
2. Smoke remoto: `deploy/smoke/prod_readiness_smoke.example.sh` contra URL piloto.
3. Regresión API mínima en CI/staging según `DOC_TESTS.md`.

---

## Ventana de prueba

Documentar **fuera del repo**:

- Fecha/hora inicio y fin de la ventana piloto.
- Equipo presente (roles, no PHI).
- Criterios de aborto anticipado.
- Comunicación a stakeholders internos.

---

## Rollback

Plan mínimo documentado por operador:

1. **Detener** tráfico al entorno piloto (Nginx upstream / DNS / LB).
2. **Revertir** imagen compose o tag anterior del backend documentado.
3. **No** restaurar backup sobre DB activa sin ventana y `CONFIRM_RESTORE` en DB temporal primero.
4. Conservar logs y evidencia sanitizada del incidente fuera del repo.
5. Registrar decisión GO/NO-GO post-rollback.

Referencias: `PROD_READINESS_SMOKE.md` (runbook reversión), `RESTORE_DRILL_STAGING.md`.

---

## Evidencia permitida / prohibida

### Permitida (fuera del repo, sanitizada)

- Fecha, commit, entorno (staging/pilot).
- Resultados agregados (`COUNT(*)`, códigos HTTP).
- Checksums de backups (sin contenido de dump).
- Resultado `manage.py check`, smoke, `nginx -t`.
- GO/NO-GO y riesgos pendientes.
- Identificador interno del operador (no email personal si no es necesario).

### Prohibida

- PHI, DNI, nombres de pacientes, resultados clínicos.
- Tokens, passwords, cookies, `SECRET_KEY`, `.env` reales.
- Dumps, backups, capturas con datos clínicos.
- Paths absolutos que revelen datos sensibles.

---

## Criterios GO / NO-GO

### GO (piloto técnico controlado)

Todos los ítems críticos cumplidos:

- `DEBUG=False`, secretos fuera del repo, CORS/CSRF/ALLOWED_HOSTS correctos.
- TLS o proxy con `X-Forwarded-Proto` validado.
- `/media/` no público; backend no expuesto en `:8000`.
- Nginx/proxy revisado (`nginx -t` OK).
- Backups programados definidos; restore drill PROD-7 OK o excepción formal.
- Usuarios/roles nominales definidos; datos sintéticos por defecto.
- Smoke PROD-6 OK en URL piloto.
- Auditoría crítica activa.
- Evidencia sanitizada archivada fuera del repo.
- **Confirmación explícita:** producción clínica abierta **sigue fuera de alcance**.

### NO-GO

Cualquiera de:

- `DEBUG=True` en piloto.
- Secretos o `.env` reales en repo.
- CORS abierto o `ALLOWED_HOSTS` con `*`.
- `/media/` público o APIs protegidas accesibles anónimas (`200`).
- Sin responsable operativo o sin ventana de prueba.
- Restore drill no ejecutado y sin excepción formal.
- PHI o secretos en evidencia.
- Intento de piloto clínico abierto sin autorización institucional.

---

## Checklist final (operador)

```
[ ] Entorno confirmado: staging/pilot controlado (no producción clínica abierta)
[ ] DEBUG=False
[ ] SECRET_KEY real fuera del repo
[ ] ALLOWED_HOSTS explícito
[ ] CSRF_TRUSTED_ORIGINS alineado
[ ] CORS cerrado al origen autorizado
[ ] TLS/proxy + X-Forwarded-Proto validados
[ ] /media/ no público
[ ] Backend sin :8000 público
[ ] Nginx/proxy revisado
[ ] Backups programados definidos
[ ] Restore drill PROD-7 OK o excepción formal
[ ] Monitoreo mínimo definido (PROD-9 pendiente si aplica)
[ ] Responsable operativo definido
[ ] Ventana de prueba definida
[ ] Usuarios internos nominales (fuera del repo)
[ ] Roles permitidos documentados
[ ] Datos sintéticos por defecto; autorización formal si datos reales
[ ] Smoke PROD-6 ejecutado
[ ] Frontend validado en repo/despliegue separado si aplica UI
[ ] Evidencia sanitizada fuera del repo
[ ] Rollback documentado
[ ] GO/NO-GO registrado
[ ] Producción clínica abierta: FUERA DE ALCANCE
```

---

## Referencias

| Documento | Contenido |
|-----------|-----------|
| `PROD_CHECKLIST.md` | Historial fases PROD-1 a PROD-8 |
| `PROD_RUNTIME.md` | Gunicorn, Nginx, media, backups |
| `PROD_READINESS_SMOKE.md` | Smoke PROD-6 |
| `deploy/backup/RESTORE_DRILL_STAGING.md` | Restore drill PROD-5-A/7 |
| `DOC_PERMISOS_AUDITORIA.md` | Permisos y auditoría |
| `DOC_RIESGOS_DEUDA_TECNICA.md` | Riesgos residuales |
| `.env.production.example` | Plantilla variables (sin secretos) |

---

## Siguiente fase recomendada

**PROD-9 — Observabilidad mínima:** monitoreo externo, alertas, métricas y trazas operativas más allá del healthcheck de contenedor.
