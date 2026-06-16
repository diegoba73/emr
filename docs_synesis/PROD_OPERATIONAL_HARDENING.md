# PROD-13 — Hardening operativo sostenido

**Fase:** PROD-13 — marco documental para sostener operación segura posterior a PROD-12  
**Estado:** documentación + plantillas + tests estáticos  
**Fecha:** junio 2026

---

## Objetivo

Documentar el **marco operativo sostenido** para mantener el piloto con datos reales mínimos **solo si existe autorización externa PROD-12**, con foco en monitoreo externo/APM, alertas, rotación de secretos, TLS end-to-end, WAF/rate limiting, validación frontend separada y mantenimiento recurrente.

**PROD-13 no habilita producción clínica abierta desde el repositorio.** No sustituye despliegue real de APM, acta institucional ni go-live clínico general.

---

## Alcance

| Incluye | No incluye |
|---------|------------|
| Requisitos mínimos monitoreo externo / APM | Producción clínica abierta |
| Plantilla alertas operativas sanitizada | DSN, API keys, tokens, webhooks reales en git |
| Runbook rotación de secretos (sin valores reales) | SDKs o dependencias Sentry/Datadog/Prometheus |
| Señales críticas y umbrales orientativos | Dashboards reales con datos sensibles |
| TLS end-to-end, headers, WAF/rate limiting | Modificar modelos, permisos, endpoints |
| Mantenimiento recurrente semanal/mensual | Configuración real de monitoreo versionada |
| Criterios GO/NO-GO operativo sostenido | Validación UX frontend en este repo |
| Evidencia sanitizada fuera del repo | PHI en repo o plantillas rellenadas |

---

## Fuera de alcance explícito

- **Producción clínica abierta** a población general.
- Versionar DSN, API keys, tokens, webhooks, credenciales o secretos.
- Versionar dashboards reales, logs reales, backups, dumps o evidencia operativa sensible.
- Declarar monitoreo externo desplegado si solo se creó documentación.
- Modificar reglas EMR/LIMS, permisos, estados, modelos, migraciones o frontend.
- Ejecutar comandos contra producción real desde el IDE.

---

## Precondiciones

Antes de aplicar hardening operativo sostenido con datos reales mínimos:

| # | Precondición | Referencia |
|---|--------------|------------|
| 1 | GO post-piloto PROD-11 | `PROD_POST_PILOT_REVIEW.md` |
| 2 | Autorización institucional PROD-12 vigente | Fuera del repo |
| 3 | Alcance funcional limitado activo | `PROD_MIN_REAL_DATA_SCOPE_TEMPLATE.md` externo |
| 4 | Observabilidad mínima PROD-9 operativa | `PROD_OBSERVABILITY_MIN.md` |
| 5 | Backups programados y restore PROD-7 referenciado | `deploy/backup/` |
| 6 | Responsables designados fuera del repo | Acta PROD-12 |
| 7 | **Producción clínica abierta: FUERA DE ALCANCE** | Confirmación acta |

---

## Monitoreo externo / APM

PROD-9 cubre observabilidad mínima manual. PROD-13 exige **monitoreo externo definido** o **decisión institucional documentada fuera del repo** que justifique herramienta alternativa.

### Opciones compatibles (elegir una o combinar según política institucional)

| Herramienta | Uso típico | Configuración real |
|-------------|------------|-------------------|
| **Sentry** | Errores 5xx, excepciones, trazas | DSN en gestor secretos — **no en git** |
| **Datadog** | APM, métricas infra, alertas | API keys en gestor secretos — **no en git** |
| **Prometheus** + **Grafana** | Métricas, dashboards, alertas | Credenciales fuera del repo |
| Herramienta institucional | Según política interna | Documentar decisión externa |

**No agregar SDKs ni dependencias** en este repo sin pedido explícito. La integración real se configura en despliegue mediante variables seguras no versionadas.

Ruta sugerida decisión/herramienta:

```text
../synesis_ops_hardening/PROD-13-monitoring-decision-YYYYMMDD.md
```

---

## Señales mínimas de monitoreo

### Endpoints (smoke / synthetic monitoring)

| Señal | Endpoint / check | Criterio |
|-------|------------------|----------|
| Health backend | `GET /api/health/` | `200` |
| Media privada | `GET /media/` | ≠ `200` |
| API protegida | `GET /api/pacientes/` anónimo | `401` o `403` |
| Auth smoke controlado | `POST /api/auth/login/` | `200` con usuario sintético o interno autorizado (sin credenciales en evidencia) |
| Sesión válida | `GET /api/auth/current-user/` | `200` en smoke autenticado |
| Descargas protegidas | `download-adjunto-resultado/`, `download-consentimiento-informado/` | Solo fixture sintético o autorización formal |

### Infraestructura

| Señal | Fuente | Notas |
|-------|--------|-------|
| Errores **5xx** | Logs backend/Gunicorn, APM | Alerta sostenida |
| Errores **4xx** anómalos | Logs Nginx, APM | Picos vs baseline |
| **Healthcheck** fallido | Docker, synthetic probe | Contenedor unhealthy |
| **Backend caído** | Health, APM, contenedor | Sin respuesta `/api/health/` |
| **DB caída** | `pg_isready`, conexiones | PostgreSQL no responde |
| **Proxy caído** | Nginx status, synthetic | Sin respuesta externa |
| **Nginx** errores | Logs proxy | 502/503/504 |
| **PostgreSQL** | Conexiones, locks, tamaño | Agregados sin PHI |
| **Contenedores** | Docker/K8s | Estado, **restarts** |
| **Disco** alto/crítico | Host/volúmenes | DB, media, backups, logs |
| **Backups fallando** | Job backup, checksums | Sin artefacto reciente OK |
| **Latencia** anómala | APM / synthetic | Si herramienta lo soporta |

---

## Alertas mínimas

Usar plantilla: `PROD_MONITORING_ALERTS_TEMPLATE.md` (**completar fuera del repo**).

| Alerta | Severidad orientativa | Umbral orientativo |
|--------|----------------------|-------------------|
| Errores **5xx** sostenidos | crítica | > N en ventana T (definir externamente) |
| **Healthcheck** fallido | crítica | 2+ fallos consecutivos |
| **Backend caído** | crítica | Sin `200` en `/api/health/` |
| **DB caída** | crítica | `pg_isready` falla |
| **Nginx/proxy caído** o 502/503 | crítica | Synthetic fail |
| **Disco** alto/crítico | alta/crítica | > 85% warning, > 95% crítica |
| **Backups fallando** | alta | Job fallido o sin artefacto reciente |
| **Contenedores reiniciando** | alta | Restart count > umbral |
| **Latencia** anómala | media/alta | p95 > baseline (si APM disponible) |
| **4xx** anómalos | media | Pico vs baseline |

Cada alerta debe tener: responsable, canal de notificación, acción esperada — **sin PHI ni secretos** en mensajes.

---

## Responsables

Designar **fuera del repo**:

| Rol | Responsabilidad PROD-13 |
|-----|-------------------------|
| Responsable técnico/operativo | Monitoreo, alertas, mantenimiento, rotación secretos |
| Responsable de incidentes | Respuesta alertas críticas |
| Responsable institucional | Aprobación excepciones, GO/NO-GO sostenido |
| On-call (si aplica) | Primer respondedor fuera de horario |

---

## Evidencia permitida

| Permitido | Ubicación |
|-----------|-----------|
| Plantillas sanitizadas del repo | Git (sin rellenar) |
| Decisión herramienta monitoreo | Fuera del repo |
| Registro alertas configuradas (nombres, umbrales) | Fuera del repo |
| Evidencia mantenimiento recurrente sanitizada | Fuera del repo |
| Evidencia rotación secretos (fechas, OK/FAIL — sin valores) | Fuera del repo |
| Revisión TLS/WAF (resultado agregado) | Fuera del repo |

Ruta sugerida:

```text
../synesis_ops_hardening/PROD-13-hardening-evidence-YYYYMMDD.md
```

---

## Evidencia prohibida en git

- DSN reales, API keys, tokens, webhooks, passwords, cookies, `SECRET_KEY`
- Dashboards exportados con datos reales o PHI
- Logs completos sensibles, dumps, backups
- Autorizaciones, actas, listados nominales reales
- Capturas con datos clínicos

---

## Logs y PHI

| Requisito | Acción |
|-----------|--------|
| Revisión periódica de logs **sin PHI** | Semanal mínimo; agregados en reportes |
| No registrar secretos ni PHI en logs/alertas | Política operador |
| Nivel INFO/WARNING en producción | Sin payloads clínicos |
| Acceso restringido a logs | Solo roles autorizados |
| **Sospecha PHI expuesta en logs** | NO-GO + incidente + suspensión |

---

## Auditoría crítica

Revisión periódica **sin exponer PHI**:

| Área | Frecuencia orientativa |
|------|------------------------|
| Auditoría descargas PROD-4-B (si alcance incluye adjuntos) | Mensual |
| Auditoría LIMS crítica (si alcance incluye LIMS) | Mensual |
| Eventos autenticación y errores (sin credenciales) | Semanal |
| Accesos admin | Mensual |
| Request ID, entorno, commit HEAD en reportes | Por revisión |

**No modificar** la app `auditoria`. **No agregar** logging de PHI.

---

## Rotación de secretos

Runbook: `PROD_SECRET_ROTATION_RUNBOOK.md`.

Inventario mínimo a rotar periódicamente:

| Secreto | Notas |
|---------|-------|
| `SECRET_KEY` / `DJANGO_SECRET_KEY` | Requiere plan de sesiones; ventana controlada |
| Credenciales **DB** | PostgreSQL usuario/contraseña |
| Credenciales **admin** Django | Usuarios nominales fuera del repo |
| **Tokens** / **API keys** externas | Sentry, Datadog, SMTP, storage |
| Credenciales proxy/TLS (si aplica) | Fuera del repo |

**Prohibición:** no registrar valores reales en evidencia ni repo.

---

## TLS end-to-end

| Check | Criterio |
|-------|----------|
| HTTPS end-to-end o TLS terminado en proxy confiable | Certificados válidos fuera del repo |
| `X-Forwarded-Proto=https` | Proxy envía header; Django `USE_PROXY_SSL_HEADER` |
| Cookies seguras | `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` |
| HSTS | Solo tras validar HTTPS completo |
| Cadena certificados | Revisión periódica expiración |
| Mixed content | Sin recursos HTTP en páginas HTTPS |

Revisión TLS documentada en evidencia externa sanitizada.

---

## Headers de seguridad

Verificar en **Nginx/proxy** (`deploy/nginx/nginx.prod.example.conf` como referencia):

| Header | Propósito |
|--------|-----------|
| `X-Frame-Options` / CSP | Clickjacking |
| `X-Content-Type-Options` | MIME sniffing |
| `Strict-Transport-Security` | HSTS (si TLS validado) |
| `Referrer-Policy` | Filtrado referrer |
| Headers proxy | `X-Forwarded-For`, `X-Forwarded-Proto` |

Revisión periódica en mantenimiento mensual.

---

## WAF / rate limiting

Requisito de **infraestructura** (no implementado en app Django en PROD-13):

| Control | Objetivo |
|---------|----------|
| **WAF** | Filtrado OWASP, bots, payloads maliciosos |
| **Rate limiting** | Protección login, API abuse, DDoS básico |
| Evaluación | Documentar decisión institucional externa |
| Excepciones | Whitelist IPs internas si aplica — fuera del repo |

Sin WAF/rate limiting validado → **riesgo residual** documentado; no bloquea documentación PROD-13 pero puede afectar GO operativo sostenido.

---

## Backups y restore

| Check | Frecuencia |
|-------|------------|
| Backups programados ejecutándose | Diario mínimo |
| Checksums verificados | Por backup |
| Alerta **backups fallando** | Inmediata |
| Restore drill PROD-7 | Revisión trimestral |
| Espacio disco backups | Semanal |

Ver `deploy/backup/README.md`, `RESTORE_DRILL_STAGING.md`.

---

## Revisión de contenedores

| Check | Señal |
|-------|-------|
| Estado running/healthy | Docker compose / orchestrator |
| **Restarts** elevados | Restart count > umbral |
| Recursos CPU/memoria | APM o `docker stats` agregado |
| Imagen desactualizada | Plan de actualización patch |

---

## Revisión de DB

| Check | Herramienta orientativa |
|-------|-------------------------|
| Conectividad | `pg_isready` |
| Conexiones activas | Agregado sin queries clínicas |
| Tamaño DB | Tendencia disco |
| Locks prolongados | Alerta si APM/DB monitor disponible |

---

## Revisión de disco

| Volumen | Umbral orientativo |
|---------|-------------------|
| PostgreSQL data | > 85% warning |
| Media clínica privada | > 85% warning |
| Backups | > 85% warning |
| Logs | Rotación/compresión |

---

## Frontend separado

**Este repositorio no contiene SPA React versionada en la raíz.**

| Hecho | Implicación PROD-13 |
|-------|---------------------|
| No hay `package.json` / `frontend/src` canónico | Monitoreo UX no cubierto por este repo |
| Si existe frontend real | Monitoreo, alertas y validación en **repositorio/despliegue separado** |
| PROD-13 backend/documental | **No valida UX productiva** |
| Sin evidencia frontend externa | **Riesgo residual** — excluir frontend del alcance sostenido |

Revisión fuera del repo: errores JS, performance UI, sesiones frontend, CSP frontend, seguridad UI.

---

## Mantenimiento recurrente

### Semanal

- [ ] Revisar alertas disparadas (sanitizado)
- [ ] Revisar logs agregados **sin PHI**
- [ ] Verificar healthcheck y contenedores
- [ ] Verificar último backup OK
- [ ] Revisar disco (agregado)
- [ ] Smoke mínimo opcional (`prod_readiness_smoke.example.sh` o synthetic)

### Mensual

- [ ] Revisión **auditoría crítica** (PROD-4-B, LIMS si aplica)
- [ ] Revisión accesos admin
- [ ] Revisión headers seguridad / TLS
- [ ] Revisión umbrales alertas
- [ ] Actualizar registro riesgos operador
- [ ] Evidencia sanitizada archivada fuera del repo

### Trimestral

- [ ] Restore drill referencia PROD-7
- [ ] Revisión rotación secretos (o según runbook)
- [ ] Revisión WAF/rate limiting
- [ ] Revisión frontend externo (si aplica)

---

## Incidentes

Ante alerta crítica o sospecha PHI:

1. Clasificar severidad.
2. Contener (suspensión si seguridad/PHI).
3. Registrar acta incidente **fuera del repo**.
4. Escalar responsables.
5. Resolver y documentar evidencia sanitizada.
6. Re-evaluar GO/NO-GO operativo sostenido.

Referencia: `PROD_OBSERVABILITY_MIN.md`, `PROD_MIN_REAL_DATA_AUTH.md` (suspensión).

---

## Matriz GO / NO-GO operativo sostenido

### GO (operación sostenida aceptable — decisión externa)

- Monitoreo externo definido o decisión institucional documentada
- Alertas mínimas configuradas (evidencia externa)
- Responsables y on-call definidos
- Rotación secretos planificada (`PROD_SECRET_ROTATION_RUNBOOK.md`)
- TLS end-to-end revisado
- WAF/rate limiting evaluados (implementados o riesgo aceptado formalmente)
- Backups OK; restore PROD-7 referenciado
- Mantenimiento recurrente en calendario
- Logs/auditoría revisados sin PHI expuesta
- Frontend monitoreado externamente **o** excluido explícitamente
- Autorización PROD-12 vigente
- **Producción clínica abierta: FUERA DE ALCANCE**

### NO-GO

- Sin monitoreo ni decisión institucional
- Alertas críticas sin responsable
- Backups fallando sin mitigación
- PHI o secretos en logs/evidencia
- Autorización PROD-12 vencida o suspendida
- Intento de producción clínica abierta

---

## Confirmación: producción clínica abierta fuera de alcance

| Afirmación | Estado |
|------------|--------|
| PROD-13 es marco documental de hardening sostenido | **Sí** |
| Este commit habilita producción clínica abierta | **No** |
| Monitoreo externo real requiere configuración fuera del repo | **Sí** |
| Uso sostenido con datos reales mínimos depende de PROD-12 + decisión externa | **Sí** |

---

## Referencias

| Documento | Fase |
|-----------|------|
| `PROD_OBSERVABILITY_MIN.md` | PROD-9 |
| `PROD_MIN_REAL_DATA_AUTH.md` | PROD-12 |
| `PROD_MONITORING_ALERTS_TEMPLATE.md` | Alertas PROD-13 |
| `PROD_SECRET_ROTATION_RUNBOOK.md` | Secretos PROD-13 |
| `deploy/observability/check_observability.example.sh` | Checks manuales |
| `deploy/nginx/nginx.prod.example.conf` | Headers/TLS proxy |
| `DOC_RIESGOS_DEUDA_TECNICA.md` | Deuda técnica |

---

## Siguiente fase recomendada

Tras GO operativo sostenido documentado externamente: evaluar ampliación controlada del alcance institucional, object storage privado (S3/MinIO), automatización ACME/TLS y — solo con autorización institucional ampliada explícita — planificar fases posteriores. **Producción clínica abierta permanece fuera de alcance.**
