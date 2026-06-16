# PROD-13 — Runbook de rotación de secretos (documental)

**Fase:** PROD-13 — procedimiento de rotación sin valores reales  
**Instrucciones:** Ejecutar en ventana controlada. **No commitear** valores reales ni evidencia con secretos.

Ruta sugerida evidencia sanitizada:

```text
../synesis_ops_hardening/PROD-13-secret-rotation-YYYYMMDD.md
```

---

## Objetivo

Definir rotación periódica de secretos para operación sostenida con datos reales mínimos (solo con autorización PROD-12 vigente), **sin exponer valores reales** en repo ni evidencia versionada.

---

## Inventario de secretos

| ID | Tipo secreto | Ubicación (gestor/env) | Periodicidad rotación | Última rotación (fecha) | Próxima (fecha) |
|----|--------------|------------------------|----------------------|-------------------------|-----------------|
| SEC-001 | `SECRET_KEY` / `DJANGO_SECRET_KEY` | gestor secretos / `.env` prod | anual o post-incidente | | |
| SEC-002 | Credenciales **DB** PostgreSQL | gestor secretos | anual | | |
| SEC-003 | Credenciales **admin** Django | gestor / fuera repo | semestral | | |
| SEC-004 | **Tokens** / **API keys** Sentry | gestor secretos | según política | | |
| SEC-005 | **API keys** Datadog | gestor secretos | según política | | |
| SEC-006 | SMTP / servicios externos | gestor secretos | anual | | |
| SEC-007 | Certificados TLS | infra / ACME | antes expiración | | |
| SEC-008 | Webhooks alertas | gestor secretos | anual | | |

**Prohibición:** no registrar columnas con valores reales en git.

---

## Responsable

| Rol | Identificador interno (fuera del repo) |
|-----|----------------------------------------|
| Ejecutor rotación | |
| Verificador | |
| Aprobador ventana | |

---

## Periodicidad general

| Nivel | Frecuencia orientativa |
|-------|------------------------|
| Rutinaria | Según tabla inventario |
| Post-incidente seguridad | Inmediata para secretos comprometidos |
| Post-rotación personal | Credenciales individuales revocadas |

---

## Ventana de cambio

1. Notificar stakeholders (sin secretos en comunicación).
2. Definir ventana de mantenimiento (baja actividad piloto).
3. Confirmar backup reciente OK.
4. Tener plan **rollback** listo.
5. Registrar inicio en evidencia externa sanitizada.

---

## Procedimiento genérico (por secreto)

### SEC-001 — `SECRET_KEY`

1. Generar nueva clave (`get_random_secret_key()` — **no** commitear).
2. Actualizar en gestor secretos / `.env` prod (**fuera del repo**).
3. Reiniciar backend (Gunicorn) en ventana controlada.
4. Verificar `GET /api/health/` → `200`.
5. Verificar login smoke con usuario sintético (sin credenciales en evidencia).
6. **Rollback:** restaurar valor anterior en gestor; reiniciar.
7. Registrar OK/FAIL en evidencia sanitizada (sin valores).

### SEC-002 — Credenciales DB

1. Crear usuario/credencial nueva en PostgreSQL.
2. Actualizar `DB_*` en gestor secretos.
3. Reiniciar backend; verificar conectividad.
4. Revocar credencial anterior tras verificación.
5. **Rollback:** revertir credencial en gestor.
6. Evidencia: fecha, OK/FAIL — sin passwords.

### SEC-003 — Admin Django

1. Rotar password usuario admin nominal (fuera del repo).
2. Verificar acceso admin.
3. Revocar sesiones si aplica.
4. Evidencia sanitizada.

### SEC-004 / SEC-005 — Sentry / Datadog

1. Rotar **API keys** / DSN en consola proveedor.
2. Actualizar variables entorno (**no** en git).
3. Verificar recepción eventos/métricas de prueba (sin PHI en evento prueba).
4. Revocar clave anterior.
5. **No copiar DSN reales** a evidencia.

---

## Verificación post-rotación

| Check | Criterio |
|-------|----------|
| `GET /api/health/` | `200` |
| `GET /media/` | ≠ `200` |
| Login smoke | OK (usuario sintético) |
| DB conectividad | OK |
| Alertas monitoreo | Evento prueba recibido (sin PHI) |
| Sin secretos en logs | Revisión manual agregada |

---

## Rollback

Si verificación post-rotación falla:

1. Restaurar secreto anterior en gestor secretos.
2. Reiniciar servicios afectados.
3. Re-ejecutar checks mínimos.
4. Documentar incidente **fuera del repo**.
5. Reprogramar rotación.

---

## Prohibiciones

- [ ] No exponer valores reales de secretos en repo
- [ ] No exponer valores en evidencia versionada
- [ ] No enviar secretos por email/chat sin cifrado
- [ ] No registrar **SECRET_KEY**, passwords, **tokens**, **API keys** en logs
- [ ] No incluir PHI en evidencia de rotación

---

## Evidencia sanitizada (fuera del repo)

| Campo | Valor |
|-------|-------|
| Fecha ejecución | |
| Secretos rotados (IDs SEC-xxx) | |
| Resultado global | OK / FAIL / rollback |
| Verificador | |
| Incidentes | referencia externa |
| Próxima rotación programada | |

---

## Referencias

- `PROD_OPERATIONAL_HARDENING.md`
- `PROD_MIN_REAL_DATA_AUTH.md` (suspensión si compromiso)
- `.env.production.example` (nombres variables — sin valores reales)
