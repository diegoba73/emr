# PROD-13 — Plantilla de alertas operativas (sanitizada)

**Instrucciones:** Copiar **fuera del repositorio git** antes de completar.  
**No commitear** la versión rellenada. **No incluir** PHI, secretos, DSN, API keys, tokens, webhooks ni passwords.

Ruta sugerida:

```text
../synesis_ops_hardening/PROD-13-monitoring-alerts-YYYYMMDD.md
```

---

## Metadatos

| Campo | Valor |
|-------|-------|
| Herramienta monitoreo | Sentry / Datadog / Prometheus+Grafana / otra |
| Entorno | staging / pilot |
| Referencia PROD-13 | |
| Commit HEAD | |
| Responsable técnico | (identificador interno — fuera del repo) |
| Fecha revisión | |

---

## Registro de alertas

Completar una fila por alerta. **No incluir** PHI ni secretos en descripción ni mensajes.

| Nombre de alerta | Severidad | Señal | Umbral | Responsable | Canal de notificación | Acción esperada |
|------------------|-----------|-------|--------|-------------|----------------------|-----------------|
| backend-5xx-sostenido | crítica | errores 5xx backend/Gunicorn | > ___ en ___ min | | email/pager/on-call | Escalar incidente; revisar logs sin PHI |
| healthcheck-fallido | crítica | `GET /api/health/` | 2+ fallos consecutivos | | | Reiniciar contenedor; revisar ALLOWED_HOSTS |
| backend-caido | crítica | synthetic `/api/health/` | sin 200 | | | Incidente disponibilidad |
| db-caida | crítica | PostgreSQL `pg_isready` | fail | | | Escalar DBA; revisar conexiones |
| proxy-caido | crítica | Nginx synthetic / 502/503 | fail | | | Revisar proxy y upstream |
| nginx-errores | alta | logs Nginx 5xx | > umbral | | | Revisar upstream backend |
| disco-alto | alta | uso disco DB/media/backups | > 85% | | | Limpiar logs; expandir volumen |
| disco-critico | crítica | uso disco | > 95% | | | Acción inmediata |
| backups-fallando | alta | job backup | sin artefacto OK | | | Revisar script/credenciales (sin exponer) |
| contenedor-restarts | alta | Docker restart count | > ___ en ___ h | | | Revisar logs contenedor |
| latencia-anomala | media/alta | APM p95 latencia | > baseline | | | Revisar DB/carga |
| 4xx-anomalos | media | picos 4xx | > baseline | | | Revisar auth/rate limit |
| media-publica | crítica | `GET /media/` | 200 | | | **Suspensión inmediata** — incidente seguridad |

---

## Evidencia de resolución (por alerta)

| Nombre alerta | Fecha disparo | Fecha resolución | Evidencia resolución (sanitizada, fuera repo) | Verificador |
|---------------|---------------|------------------|-----------------------------------------------|-------------|
| | | | | |

**Prohibido en evidencia:** PHI, tokens, passwords, DSN, API keys, logs completos sensibles.

---

## Restricciones

- [ ] Mensajes de alerta **sin PHI**
- [ ] Mensajes de alerta **sin secretos**
- [ ] Canales de notificación con acceso restringido
- [ ] Dashboards con acceso restringido
- [ ] Configuración real (DSN, API keys) **fuera del repo**

---

## Revisión periódica

| Fecha revisión | Alertas ajustadas | Revisor | Notas (sin PHI) |
|----------------|-------------------|---------|-----------------|
| | | | |
