# PROD-11 — Plantilla de acciones correctivas post-piloto (sanitizada)

**Instrucciones:** Copiar **fuera del repositorio git** antes de completar.  
**No commitear** la versión rellenada. **No incluir** PHI, secretos, tokens ni autorizaciones reales.

Ruta sugerida:

```text
../synesis_pilot_evidence/PROD-11-post-pilot-actions-YYYYMMDD.md
```

---

## Metadatos de revisión

| Campo | Valor |
|-------|-------|
| Fecha revisión | |
| Revisor (identificador interno) | |
| Referencia evidencia piloto PROD-10 | |
| Commit HEAD evaluado | |
| Entorno piloto | |
| GO/NO-GO post-piloto | GO / NO-GO / GO condicionado |

---

## Registro de acciones

Completar una fila por acción. **No incluir** PHI ni secretos en descripción.

| ID | Severidad | Descripción (sin PHI) | Responsable | Fecha objetivo | Impacto | Decisión | Bloquea GO | Estado |
|----|-----------|----------------------|-------------|----------------|--------|----------|------------|--------|
| ACT-001 | crítica / alta / media / baja | | | | operativo / seguridad / disponibilidad | corregir / aceptar riesgo / diferir | Sí / No | abierta / cerrada |
| ACT-002 | | | | | | | | |
| ACT-003 | | | | | | | | |

### Leyenda severidad

| Nivel | Criterio orientativo |
|-------|---------------------|
| **crítica** | Seguridad, PHI, media pública — bloquea GO |
| **alta** | Disponibilidad sostenida, backups fallando |
| **media** | Observabilidad incompleta, gaps operativos |
| **baja** | Mejoras documentales, deuda no bloqueante |

### Leyenda decisión

| Decisión | Uso |
|----------|-----|
| **corregir** | Acción obligatoria antes de datos reales mínimos |
| **aceptar riesgo** | Documentar en acta con aprobación responsable |
| **diferir** | Planificar en fase posterior; no para críticas de seguridad |

---

## Evidencia de cierre (por acción)

| ID acción | Fecha cierre | Evidencia de cierre (sanitizada, fuera repo) | Verificador |
|-----------|--------------|---------------------------------------------|-------------|
| ACT-001 | | | |
| ACT-002 | | | |

**Prohibido en evidencia de cierre:** tokens, passwords, dumps, logs con PHI, capturas clínicas.

---

## Resumen bloqueo GO/NO-GO

| Pregunta | Respuesta |
|----------|-----------|
| ¿Hay acciones críticas abiertas? | Sí / No |
| ¿Hay acciones alta severidad abiertas? | Sí / No |
| ¿Bloquean avance a datos reales mínimos? | Sí / No |
| ¿Bloquean producción clínica abierta? | Siempre Sí (fuera de alcance) |

---

## Riesgos residuales aceptados (si aplica)

| Riesgo | Justificación (sin PHI) | Aprobado por |
|--------|-------------------------|--------------|
| | | |

---

## Criterios datos reales mínimos

Marcar cuando la acción correspondiente esté **cerrada**:

- [ ] GO post-piloto registrado
- [ ] Acciones críticas cerradas
- [ ] Autorización institucional formal (referencia externa, sin adjuntar acta al repo)
- [ ] Backups verificados
- [ ] Frontend revisado por separado (si aplica)
- [ ] Monitoreo operativo activo
- [ ] **Producción clínica abierta: NO HABILITADA**

---

## Confirmaciones

- [ ] Sin PHI en este documento
- [ ] Sin secretos, tokens, passwords ni cookies
- [ ] Sin autorizaciones institucionales reales adjuntas
- [ ] Documento almacenado **fuera del repo git**
- [ ] Producción clínica abierta **fuera de alcance**

---

## Firma revisión (opcional)

Identificador revisor: _______________  
Fecha: _______________
