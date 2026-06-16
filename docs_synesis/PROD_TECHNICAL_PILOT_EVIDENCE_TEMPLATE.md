# PROD-10 — Plantilla de evidencia piloto técnico (sanitizada)

**Instrucciones:** Copiar este archivo **fuera del repositorio git** antes de completar.  
**No commitear** la versión rellenada. **No incluir** PHI, secretos, tokens ni passwords.

Ruta sugerida:

```text
../synesis_pilot_evidence/PROD-10-technical-pilot-YYYYMMDD.md
```

---

## Metadatos

| Campo | Valor |
|-------|-------|
| Fecha inicio ventana | |
| Fecha fin ventana | |
| Commit HEAD desplegado | |
| Entorno (nombre interno) | |
| Tipo entorno | staging / pilot técnico controlado |
| Responsable operativo | (identificador interno, no email personal si no es necesario) |
| Operadores presentes | (roles, sin nombres clínicos) |

---

## Configuración confirmada (sin exponer valores secretos)

| Check | Resultado OK/FAIL | Notas (sin secretos) |
|-------|-------------------|----------------------|
| `DEBUG=False` | | |
| `SECRET_KEY` real fuera del repo | | Solo confirmar Sí/No |
| `ALLOWED_HOSTS` explícito | | Sin listar secretos |
| `CSRF_TRUSTED_ORIGINS` | | |
| CORS cerrado | | |
| TLS/HTTPS o proxy productivo | | |
| `X-Forwarded-Proto=https` preservado | | |
| Backend sin `:8000` público | | |
| `/media/` no público | | Código HTTP: |

---

## PROD-8 / PROD-9 aplicados

| Fase | Aplicado | Referencia |
|------|----------|------------|
| PROD-8 pre-piloto | Sí / No | `PROD_PREPILOT_CHECKLIST.md` |
| PROD-9 observabilidad | Sí / No | `PROD_OBSERVABILITY_MIN.md` |
| PROD-7 restore drill | GO / excepción / N/A | Evidencia externa PROD-7 |

---

## Backups

| Check | Resultado |
|-------|-----------|
| Backups programados definidos | |
| Artefacto reciente verificado (checksum OK) | |
| Ubicación backups (genérica, fuera repo) | |

---

## Observabilidad

| Check | Resultado |
|-------|-----------|
| `check_observability.example.sh` | OK / FAIL |
| Logs backend accesibles | |
| Logs Nginx accesibles | |
| Logs PostgreSQL accesibles | |
| Contenedores healthy | |
| Restart counts normales | |
| Disco dentro de umbral | |

---

## Smoke — anónimo

| Endpoint | Código HTTP | OK/FAIL |
|----------|-------------|---------|
| `GET /api/health/` | | |
| `GET /media/` | | (debe ser ≠ 200) |
| `GET /api/pacientes/` anónimo | | (401/403) |
| `GET /api/turnos/` anónimo | | |
| `GET /api/atenciones/` anónimo | | |

---

## Smoke — autenticado (usuario sintético o interno autorizado)

| Check | Resultado |
|-------|-----------|
| `POST /api/auth/login/` | OK / FAIL / SKIP |
| `GET /api/auth/current-user/` | OK / FAIL / SKIP |
| Usuario de prueba (rol, sin credenciales) | ej. `sintetico_lab` |

**No registrar:** password, token, cookie, JWT completo.

---

## Descargas protegidas (opcional — solo dato sintético)

| Check | Resultado |
|-------|-----------|
| Download adjunto procedimiento | OK / SKIP / FAIL |
| Download consentimiento quirúrgico | OK / SKIP / FAIL |
| Auditoría PROD-4-B (conteo agregado eventos) | |

---

## Errores observados

| Tipo | Descripción (sin PHI) | Acción |
|------|----------------------|--------|
| 4xx | | |
| 5xx | | |

---

## Incidentes

| Hora | Tipo | Resolución (sanitizada) |
|------|------|-------------------------|
| | | |

---

## Rollback

| Ejecutado | Motivo | Resultado |
|-----------|--------|-----------|
| Sí / No | | |

---

## Frontend (validación separada)

| Check | Resultado |
|-------|-----------|
| Frontend validado en repo/despliegue separado | Sí / No / N/A |
| Observabilidad frontend separada | Sí / No / N/A |

---

## GO / NO-GO final

| Veredicto | |
|-----------|---|
| **GO / NO-GO** | |

### Motivo (sin PHI)

---

## Riesgos residuales

1.
2.
3.

---

## Confirmaciones

- [ ] Sin PHI en este documento
- [ ] Sin secretos, tokens, passwords ni cookies
- [ ] Sin dumps, backups ni logs sensibles adjuntos
- [ ] Evidencia almacenada **fuera del repo git**
- [ ] **Producción clínica abierta: NO HABILITADA**

---

## Firma operativa (opcional)

Identificador interno operador: _______________  
Fecha cierre: _______________
