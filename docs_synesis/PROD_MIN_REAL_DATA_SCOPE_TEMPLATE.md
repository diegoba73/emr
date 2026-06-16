# PROD-12 — Plantilla de alcance: piloto con datos reales mínimos (sanitizada)

**Instrucciones:** Copiar **fuera del repositorio git** antes de completar.  
**No commitear** la versión rellenada. **No incluir** PHI, secretos, tokens, DNI, nombres de pacientes ni listados nominales reales.

**Esta plantilla no reemplaza** el acta institucional real ni la autorización formal externa. Complementa la gobernanza documentada en `PROD_MIN_REAL_DATA_AUTH.md`.

Ruta sugerida:

```text
../synesis_institutional_auth/PROD-12-scope-YYYYMMDD.md
```

Autorización / firma externa (fuera del repo):

```text
../synesis_institutional_auth/PROD-12-authorization-YYYYMMDD.pdf
```

---

## Metadatos

| Campo | Valor |
|-------|-------|
| Referencia acta institucional | (ruta externa — no incluir PDF en git) |
| Referencia GO post-piloto PROD-11 | |
| Commit HEAD desplegado | |
| Entorno | staging / pilot controlado |
| **Fecha de inicio** | |
| **Fecha de fin** | |
| Estado alcance | borrador / aprobado / cerrado / suspendido |

---

## Objetivo

Describir el objetivo del piloto con datos reales mínimos (sin PHI en esta plantilla):

| Campo | Valor |
|-------|-------|
| Objetivo principal | |
| Hipótesis o necesidad institucional | |
| Criterio de éxito (medible, sin datos clínicos) | |
| **Producción clínica abierta** | **FUERA DE ALCANCE** |

---

## Alcance

| Elemento | Detalle (sin PHI) |
|----------|-------------------|
| Flujos EMR incluidos | |
| Flujos LIMS incluidos (si aplica) | |
| Volumen máximo orientativo (cohorte acotada) | |
| Ventana horaria de uso | |
| Entornos permitidos | |

---

## Fuera de alcance

Marcar explícitamente como excluido:

- [ ] Producción clínica abierta
- [ ] Usuarios no listados en sección usuarios autorizados
- [ ] Módulos no listados en módulos permitidos
- [ ] Importaciones masivas no autorizadas
- [ ] Exportaciones bulk no auditadas
- [ ] Frontend no validado externamente (si aplica)
- [ ] Endpoints LIMS no listados
- [ ] Otros: |

---

## Responsables

Designar identificadores internos **fuera del repo** (sin nombres clínicos de pacientes):

| Rol | Identificador interno | Contacto operativo |
|-----|----------------------|-------------------|
| **Responsable institucional** | | |
| **Responsable clínico** | | |
| **Responsable técnico/operativo** | | |
| **Responsable de incidentes** | | |

---

## Módulos permitidos

Completar solo módulos autorizados institucionalmente:

| Módulo | Habilitado (Sí/No) | Notas |
|--------|-------------------|-------|
| Auth / sesión | | |
| Pacientes | | |
| Turnos / agenda | | |
| Atenciones | | |
| Registros procedimiento | | |
| Registros quirúrgicos | | |
| Descargas protegidas (PROD-4-A) | | |
| Auditoría descargas (PROD-4-B) | | |
| LIMS | | Solo si autorización explícita; rol `laboratorio` ≠ clínico general |
| Otros | | |

---

## Módulos excluidos

| Módulo | Motivo exclusión |
|--------|------------------|
| Producción clínica abierta | Política PROD-12 |
| | |
| | |

---

## Usuarios autorizados

**Completar fuera del repo.** No incluir passwords ni tokens.

| Identificador usuario | Rol | Módulos permitidos | Fecha alta | Fecha baja |
|----------------------|-----|-------------------|------------|------------|
| (ej. usr-pilot-001) | | | | |
| | | | | |

Reglas:

- [ ] Sin usuarios compartidos
- [ ] Mínimo privilegio
- [ ] Revisión acceso admin completada
- [ ] Listado nominal real **no** versionado en git

---

## Datos permitidos

| Categoría | Campos / tipos permitidos | Justificación (sin PHI) |
|-----------|--------------------------|-------------------------|
| Identificadores | | |
| Demográficos mínimos | | |
| Clínicos acotados | | |
| Adjuntos | | Solo si descargas PROD-4-A autorizadas |
| LIMS | | Solo si módulo LIMS habilitado |

---

## Datos prohibidos

| Prohibido | Acción si detectado |
|-----------|---------------------|
| PHI fuera de alcance aprobado | Suspensión inmediata |
| DNI / nombres / resultados en repo o evidencia git | NO-GO + incidente |
| Dumps, backups, logs completos en git | NO-GO |
| Secretos, tokens, passwords | NO-GO + rotación |
| Datos de pacientes no incluidos en cohorte | Suspensión |

---

## Criterios GO / NO-GO (inicio piloto)

### GO inicio (decisión externa — ver `PROD_MIN_REAL_DATA_AUTH.md`)

- [ ] GO post-piloto PROD-11 confirmado
- [ ] Acciones críticas PROD-11 cerradas
- [ ] Autorización institucional externa vigente
- [ ] Responsables designados
- [ ] Alcance aprobado por responsable institucional
- [ ] Backups programados confirmados
- [ ] Restore drill PROD-7 referenciado
- [ ] Observabilidad PROD-9 confirmada
- [ ] `/media/` no público verificado
- [ ] APIs protegidas verificadas
- [ ] Plan incidentes y rollback documentado
- [ ] **Producción clínica abierta: FUERA DE ALCANCE**

### NO-GO inicio

- [ ] Falta algún ítem GO anterior
- [ ] Evidencia PROD-11 no sanitizada
- [ ] Frontend requerido sin validación externa

---

## Criterios de suspensión inmediata

Suspender piloto si ocurre:

- [ ] `/media/` público o accesible anónimamente
- [ ] API clínica `200` anónimo
- [ ] Sospecha PHI expuesta en logs/evidencia
- [ ] Secretos expuestos
- [ ] Desviación del alcance funcional
- [ ] Incidente crítico sin contención
- [ ] Fin de ventana (`fecha de fin`)
- [ ] Orden responsable institucional o clínico

---

## Evidencia requerida

Registrar **fuera del repo** (sanitizada):

| Evidencia | Ruta externa sugerida | Incluida (Sí/No) |
|-----------|---------------------|------------------|
| GO post-piloto PROD-11 | `../synesis_pilot_evidence/` | |
| Acciones críticas cerradas | `../synesis_pilot_evidence/` | |
| Autorización institucional | `../synesis_institutional_auth/` | |
| Smoke / checks endpoints | `../synesis_institutional_auth/` | |
| Observabilidad PROD-9 | `../synesis_institutional_auth/` | |
| Restore drill PROD-7 | `../synesis_restore_evidence/` | |
| Validación frontend (si aplica) | repositorio/despliegue frontend | |
| Acta cierre piloto | `../synesis_institutional_auth/` | |

**Prohibido en evidencia:** PHI, secretos, tokens, actas reales en git, autorizaciones reales en git.

---

## Verificaciones mínimas de endpoints

| Endpoint | Resultado esperado | Evidencia externa |
|----------|-------------------|-------------------|
| `GET /api/health/` | 200 | |
| `GET /media/` | ≠ 200 | |
| `GET /api/pacientes/` anónimo | 401/403 | |
| `POST /api/auth/login/` | 200 (sin credenciales en evidencia) | |
| `GET /api/auth/current-user/` | 200 | |
| Descargas protegidas (si aplica) | Según alcance | |
| Endpoints LIMS (si aplica) | Según alcance autorizado | |

---

## Rollback

| Paso | Responsable | Fecha prevista |
|------|-------------|----------------|
| Suspender ventana | | |
| Revocar accesos nominales | | |
| Revertir despliegue si aplica | | |
| Verificar media/APIs post-rollback | | |
| Smoke mínimo | | |
| Acta rollback externa | | |

---

## Restricciones de confidencialidad

- [ ] No PHI en comunicaciones de este alcance
- [ ] No secretos en documentación versionada
- [ ] No actas reales en repositorio git
- [ ] No autorizaciones reales en repositorio git
- [ ] Evidencia operativa bajo acceso restringido
- [ ] Frontend validado en repositorio separado si existe UI real

---

## Firma / autorización externa (fuera del repo)

| Campo | Valor |
|-------|-------|
| Aprobado por (responsable institucional) | |
| Fecha aprobación | |
| Referencia acta/comité | (documento externo — **no** commitear) |
| Vigencia hasta | |
| Condiciones especiales | |

**Importante:** La firma institucional real debe archivarse **fuera del repositorio git**. Esta plantilla sanitizada en repo no constituye autorización operativa.

---

## Cierre

| Campo | Valor |
|-------|-------|
| Fecha cierre efectiva | |
| Motivo cierre | fin ventana / suspensión / NO-GO |
| Incidentes registrados (referencia externa) | |
| Lecciones aprendidas (sin PHI) | |
| Decisión posterior | |
