# PROD-10 — Piloto técnico controlado (runbook de ejecución)

**Fase:** PROD-10 — ejecución formal del piloto técnico aplicando PROD-8 + PROD-9  
**Estado:** runbook + plantilla de evidencia + smoke no destructivo  
**Fecha:** junio 2026

---

## Objetivo

Proveer el **procedimiento operativo** para ejecutar un **piloto técnico controlado** de SYNESIS EMR/LIMS (staging/pilot interno), integrando:

- Checklist pre-piloto **PROD-8** (`PROD_PREPILOT_CHECKLIST.md`)
- Observabilidad mínima **PROD-9** (`PROD_OBSERVABILITY_MIN.md`)
- Smoke **PROD-6** + script piloto **PROD-10**

**PROD-10 no habilita producción clínica abierta.** Este documento es el runbook; la **evidencia real** del piloto se completa **fuera del repo** usando `PROD_TECHNICAL_PILOT_EVIDENCE_TEMPLATE.md`.

---

## Alcance

| Incluye | No incluye |
|---------|------------|
| Ventana piloto definida y responsable operativo | Producción clínica abierta |
| Aplicación checklist PROD-8 y PROD-9 | PHI en evidencia o repo |
| Smoke anónimo y autenticado (usuario sintético) | Modificar modelos, permisos, endpoints |
| Evidencia sanitizada fuera del repo | Restore destructivo |
| GO/NO-GO final del piloto técnico | Validación UX frontend en este repo |
| Riesgos residuales documentados | Tokens/passwords en git |

---

## Fuera de alcance explícito

- **Producción clínica abierta** a usuarios finales sin control institucional.
- Go-live clínico, autorización legal o uso con datos reales salvo autorización formal externa.
- Observabilidad de navegador / errores JS (frontend en despliegue separado).
- Ejecución automática del piloto desde CI sin operador autorizado.

---

## Precondiciones

Antes de iniciar la ventana piloto:

- [ ] PROD-8 checklist revisado (`PROD_PREPILOT_CHECKLIST.md`).
- [ ] PROD-9 observabilidad definida (`PROD_OBSERVABILITY_MIN.md`).
- [ ] PROD-7 restore drill GO técnico o excepción formal documentada fuera del repo.
- [ ] Ambiente **staging/pilot** aislado identificado (nombre interno fuera del repo).
- [ ] Commit HEAD del despliegue registrado en evidencia externa.
- [ ] Responsable operativo nominal definido **fuera del repo**.
- [ ] Datos **sintéticos** por defecto; datos reales mínimos solo con autorización formal externa.
- [ ] Plantilla de evidencia copiada fuera del repo.

---

## Checklist PROD-8 (aplicar antes del piloto)

Referencia completa: `PROD_PREPILOT_CHECKLIST.md`.

Resumen obligatorio:

- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` real **fuera del repo** (confirmar sin exponer valor)
- [ ] `DJANGO_ALLOWED_HOSTS` explícito (sin `*`)
- [ ] `DJANGO_CSRF_TRUSTED_ORIGINS` alineado al dominio final
- [ ] `DJANGO_CORS_ALLOWED_ORIGINS` cerrado al origen autorizado
- [ ] TLS/HTTPS o proxy con `X-Forwarded-Proto=https` si aplica
- [ ] `/media/` no público; backend sin `:8000` público
- [ ] Backups programados definidos fuera del repo
- [ ] Rollback documentado
- [ ] Usuarios internos nominales fuera del repo

---

## Checklist PROD-9 (aplicar durante el piloto)

Referencia completa: `PROD_OBSERVABILITY_MIN.md`.

- [ ] Logs backend/Gunicorn accesibles al operador autorizado
- [ ] Logs Nginx/proxy accesibles
- [ ] Logs PostgreSQL accesibles
- [ ] Procedimiento 4xx/5xx conocido
- [ ] `deploy/observability/check_observability.example.sh` ejecutado
- [ ] Monitoreo contenedores (estado, health, restart count)
- [ ] Monitoreo DB (`pg_isready`) y disco
- [ ] Responsable de incidentes identificado

---

## Ambiente objetivo

Registrar **solo en evidencia externa** (sin secretos):

| Campo | Ejemplo genérico |
|-------|------------------|
| Nombre entorno | `staging-pilot-01` |
| Tipo | staging / pilot técnico controlado |
| URL API (proxy) | `https://api.example.internal` |
| Commit HEAD | hash git del despliegue |
| Compose / orquestador | `docker-compose.prod.example.yml` adaptado |

**No** documentar passwords, tokens ni `.env` reales en el repo.

---

## Ventana piloto

Definir **fuera del repo**:

- Fecha/hora inicio (UTC o local acordado)
- Fecha/hora fin
- Equipo presente (roles internos, sin PHI)
- Criterios de aborto anticipado
- Comunicación a stakeholders

---

## Responsable operativo

- Nombre o identificador interno del operador — **fuera del repo**
- Contacto de escalamiento — **fuera del repo**
- Conservación de evidencia sanitizada — responsable designado

---

## Datos permitidos

| Tipo | Uso en piloto técnico |
|------|----------------------|
| Datos sintéticos | **Por defecto** |
| Datos reales mínimos | Solo con autorización formal externa; evidencia sanitizada |
| PHI en evidencia | **Prohibido** |

---

## Usuarios permitidos

| Rol | Uso smoke |
|-----|-----------|
| Usuario sintético | **Preferido** para login smoke |
| Usuario interno autorizado | Permitido si institución lo autoriza; credenciales **no** en repo |
| `laboratorio` | Solo flujos LIMS acotados; no EMR general |
| Admin | Mínimo necesario; restringido |

Definir `SMOKE_USERNAME` / `SMOKE_PASSWORD` vía entorno al ejecutar scripts — **nunca** commitear.

---

## Procedimiento de ejecución (paso a paso)

### 1. Pre-vuelo (T-30 min)

1. Confirmar ambiente staging/pilot (no producción clínica abierta).
2. Registrar commit HEAD en evidencia externa.
3. Revisar checklist PROD-8 ítems críticos.
4. Verificar backups programados (artefactos recientes fuera del repo).

### 2. Observabilidad (T-15 min)

```bash
export BASE_URL="https://staging-pilot.example.internal"
bash deploy/observability/check_observability.example.sh
```

Registrar en evidencia: códigos HTTP, health contenedores, disco (agregado).

### 3. Smoke anónimo (PROD-6 / PROD-10)

```bash
export BASE_URL="https://staging-pilot.example.internal"
bash deploy/smoke/prod_technical_pilot.example.sh
```

O por fases:

```bash
bash deploy/smoke/prod_readiness_smoke.example.sh
```

Verificar:

- `GET /api/health/` → `200`
- `GET /media/` → ≠ `200`
- `GET /api/pacientes/` anónimo → `401` o `403`

### 4. Smoke autenticado

```bash
export BASE_URL="https://staging-pilot.example.internal"
export SMOKE_USERNAME="<usuario_sintetico>"
# SMOKE_PASSWORD: definir vía entorno seguro del operador (no documentar en repo)
bash deploy/smoke/prod_technical_pilot.example.sh
```

Verificar:

- `POST /api/auth/login/` → `200` (token no imprimir en evidencia)
- `GET /api/auth/current-user/` → `200` con token/sesión

### 5. Descargas protegidas (opcional)

Solo si existe **fixture/dato sintético** autorizado en el entorno piloto:

- `GET /api/registros-procedimientos/{id}/download-adjunto-resultado/`
- `GET /api/registros-quirurgicos/{id}/download-consentimiento-informado/`

Verificar auditoría PROD-4-B con conteo agregado (`COUNT(*)` eventos) — sin listar metadata clínica.

### 6. Auditoría LIMS (opcional)

Si se ejecuta flujo sintético LIMS en ventana piloto: verificar eventos de auditoría con conteos agregados — sin PHI.

### 7. Cierre y GO/NO-GO

1. Completar plantilla `PROD_TECHNICAL_PILOT_EVIDENCE_TEMPLATE.md` **fuera del repo**.
2. Registrar GO/NO-GO final.
3. Documentar riesgos residuales.
4. Si NO-GO: ejecutar rollback según `PROD_PREPILOT_CHECKLIST.md`.

---

## Verificación media privada

| Check | Criterio |
|-------|----------|
| `GET /media/` vía proxy | ≠ `200` |
| Descargas clínicas | Solo vía API autenticada |
| Evidencia | Sin nombres de archivos clínicos |

---

## Verificación backups

- Política de backups programados confirmada (operador).
- PROD-7 restore drill referenciado en evidencia.
- Sin dumps ni `.sql` en working tree del repo.

---

## Verificación rollback

Ante fallo crítico durante piloto:

1. Detener tráfico al entorno piloto.
2. Revertir imagen/tag documentado.
3. **No** restore sobre DB activa sin ventana formal.
4. Registrar incidente sanitizado fuera del repo.

---

## Evidencia permitida

Completar plantilla fuera del repo (`PROD_TECHNICAL_PILOT_EVIDENCE_TEMPLATE.md`):

- Fecha/hora ventana piloto
- Commit HEAD
- Entorno (nombre interno)
- Resultados HTTP agregados
- Health contenedores, restart counts
- Resultado smoke anónimo/autenticado (sin tokens)
- GO/NO-GO
- Riesgos residuales
- Operador (identificador interno)

Ruta sugerida evidencia externa:

```text
../synesis_pilot_evidence/PROD-10-technical-pilot-YYYYMMDD.md
```

---

## Evidencia prohibida

- PHI, DNI, nombres de pacientes, resultados clínicos
- Tokens, passwords, cookies, `SECRET_KEY`
- Dumps, backups, logs completos sensibles
- Paths de archivos clínicos
- Capturas con datos de pacientes

---

## Incidentes

| Situación | Acción |
|-----------|--------|
| `/media/` → 200 | **NO-GO** inmediato; incidente seguridad |
| API clínica anónima → 200 | **NO-GO**; incidente seguridad |
| 5xx sostenido | Incidente operativo; evaluar rollback |
| Sospecha PHI expuesta | **NO-GO**; preservar logs fuera del repo; escalar seguridad |
| Backups fallando | Documentar; puede ser NO-GO según política |

Ver procedimientos detallados en `PROD_OBSERVABILITY_MIN.md`.

---

## Criterios GO / NO-GO final

### GO (piloto técnico controlado exitoso)

- PROD-8 y PROD-9 aplicados y documentados en evidencia externa.
- `DEBUG=False` y configuración seguridad confirmada (sin exponer secretos).
- Healthcheck externo OK.
- `/media/` no público; APIs protegidas anónimas ≠ 200.
- Smoke autenticado OK con usuario sintético o interno autorizado.
- Observabilidad y backups verificados.
- Evidencia sanitizada archivada fuera del repo.
- Frontend real validado **por separado** si aplica UI.
- **Producción clínica abierta: FUERA DE ALCANCE.**

### NO-GO

- Cualquier fallo de seguridad (media pública, APIs anónimas 200).
- PHI o secretos en evidencia.
- Healthcheck falla sostenidamente.
- Sin responsable operativo o ventana definida.
- Intento de declarar producción clínica abierta.

---

## Cierre de piloto

1. Archivar evidencia sanitizada fuera del repo.
2. Revocar credenciales temporales de smoke si aplica.
3. Registrar lecciones aprendidas (sin PHI).
4. Comunicar GO/NO-GO a stakeholders internos.
5. **No** commitear evidencia al repositorio git.

---

## Frontend

**Este repositorio backend no contiene la SPA React canónica en la raíz.** Submódulo `frontend/` o despliegue separado requiere validación y observabilidad **propias**.

PROD-10 valida backend/infra del piloto; **no** UX productiva.

---

## Referencias

| Documento | Contenido |
|-----------|-----------|
| `PROD_PREPILOT_CHECKLIST.md` | PROD-8 |
| `PROD_OBSERVABILITY_MIN.md` | PROD-9 |
| `PROD_READINESS_SMOKE.md` | PROD-6 smoke |
| `PROD_TECHNICAL_PILOT_EVIDENCE_TEMPLATE.md` | Plantilla evidencia |
| `deploy/smoke/prod_technical_pilot.example.sh` | Smoke piloto |
| `deploy/observability/check_observability.example.sh` | Checks observabilidad |

---

## Siguiente fase recomendada

**PROD-11 — Revisión post-piloto y hardening operativo:** analizar evidencia del piloto, cerrar riesgos residuales, planificar monitoreo externo desplegado y autorización institucional si se avanza hacia piloto con datos reales mínimos.
