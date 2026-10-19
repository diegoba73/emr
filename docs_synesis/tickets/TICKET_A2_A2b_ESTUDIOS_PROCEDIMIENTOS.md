# Ticket A2 / A2b — Campos de indicación, snapshot y corrección auditada

**Estado:** implementado en código (pendiente review/merge) — no producción  
**Depende de:** A0 cerrado + A1 (`clasificacion_quirurgica` en `ProcedimientoCatalogo`)  
**SoT diseño:** `docs_synesis/DOC_DISENO_ESTUDIOS_PROCEDIMIENTOS.md` §§1.2–1.3, 5.A2 — **este ticket prevalece** sobre el resumen A2 del diseño cuando hay diferencia  
**Restricción absoluta:** LIMS intocable (`laboratorio/**`, reglas/flujos LIMS, comportamiento lab vía dependencias compartidas).

---

## 0. Decisiones resueltas (pre-implementación)

| # | Decisión |
|---|----------|
| D1 | Correspondencia **exacta**: `PROCEDIMIENTO`↔`NO_QUIRURGICO`; `CIRUGIA`↔`QUIRURGICO`; `ESTUDIO` sin `procedimiento_catalogo` ni snapshot quirúrgico. |
| D2 | A2b **no** puede dejar snapshot vs `tipo_actividad` contradictorios ni reclasificar actos ya realizados. Correcciones incompatibles con `tipo_actividad` → **bloquear**. Reclasificación completa = diseño futuro explícito (fuera de A2b). |
| D3 | A2b: permiso **admin**; condiciones previas; **misma TX** snapshot + auditoría; PATCH genérico **no** muta `procedimiento_catalogo` ni `clasificacion_quirurgica_snapshot` (ni `tipo_actividad`). |
| D4 | A2 **prepara estructura**; **no** habilita altas UI/API de `PROCEDIMIENTO`/`CIRUGIA` hasta circuitos propios. Estudios legacy siguen. Nuevos tipos **no** atraviesan acciones legacy de realización/informes. `permite_multi_sesion` queda `False` y **no** se puede activar hasta A3/A4. |
| D5 | Verificar nullabilidad real de `tipo_estudio` / legacy; migraciones **solo EMR** (`estudios` / FE tipos-API estudios) si hace falta para el modelo. |
| D6 | FK nueva `procedimiento_catalogo` → **`PROTECT`** (no `SET_NULL`). Baja de catálogo = desactivar (`activo=False`); delete físico bloqueado si hay referencias. Revisar consumidores existentes (p. ej. `RegistroProcedimiento` / `RegistroQuirurgico` ya usan `SET_NULL` — **no cambiarlos** en A2 salvo decisión aparte). |
| D7 | Backfill idempotente: conserva campos/relaciones previos y conteos; reejecutar no pisa datos ya migrados/nuevos. |
| D8 | Suite de pruebas: combinaciones contradictorias, PATCH protegido, corrección post-realización, altas deshabilitadas, delete catálogo referenciado. |

---

## 1. Objetivo

Extender `EstudioComplementario` con `tipo_actividad`, FK de catálogo, snapshot y flag de multisesión — **estructura lista**, create/update legacy de **ESTUDIO** intacto, **sin** exponer aún el circuito clínico de procedimiento/cirugía.

**A2b:** corrección admin del snapshot **compatible** con `tipo_actividad`, atómica con auditoría; nunca vía PATCH genérico.

---

## 2. Fuera de alcance

- Habilitar producto/UX de alta o flujo clínico completo de `PROCEDIMIENTO` / `CIRUGIA` (ticket/etapa posterior cuando existan circuitos).
- Reclasificación completa (cambiar `tipo_actividad` + snapshot + catálogo + actos realizados) → diseño futuro.
- `SesionActividad`, espejo turno, `sesion_id` → **A3/A4** (única etapa que podrá **activar** `permite_multi_sesion`).
- UI bandejas/filtros tipo → **A5**
- Cualquier cambio en `laboratorio/` o comportamiento LIMS vía compartidos.
- Alterar `on_delete` de FKs **existentes** a `ProcedimientoCatalogo` en `turnos` (consumidores legacy) sin ticket explícito.
- Producción / merge automático.

---

## 3. Correspondencia exacta (invariante)

| `tipo_actividad` | `procedimiento_catalogo` | `clasificacion_quirurgica_snapshot` | Catálogo.exigible (cuando el tipo esté habilitado) |
|------------------|--------------------------|-------------------------------------|-----------------------------------------------------|
| `ESTUDIO` | **null** | **null/blank** (sin snapshot quirúrgico) | N/A |
| `PROCEDIMIENTO` | FK obligatoria | **`NO_QUIRURGICO`** | Debe ser `NO_QUIRURGICO` (no `SIN_ASIGNAR`, no `QUIRURGICO`) |
| `CIRUGIA` | FK obligatoria | **`QUIRURGICO`** | Debe ser `QUIRURGICO` |

Toda combinación fuera de esta tabla (p. ej. `PROCEDIMIENTO` + snapshot `QUIRURGICO`, `ESTUDIO` + FK, `CIRUGIA` + `NO_QUIRURGICO`) → **rechazo 4xx** en validación de servicio/`clean`.

---

## 4. Cambios previstos (A2) — estructura

### 4.1 Modelo (`estudios/models.py`)

| Campo | Tipo | Default / null | Notas |
|-------|------|----------------|-------|
| `tipo_actividad` | choices `ESTUDIO`\|`PROCEDIMIENTO`\|`CIRUGIA` | default `ESTUDIO`, index | Inmutable tras create |
| `procedimiento_catalogo` | FK → `ProcedimientoCatalogo`, **`on_delete=PROTECT`**, null/blank | null | Solo proc/cirugía (cuando habilitados) |
| `clasificacion_quirurgica_snapshot` | CharField choices `NO_QUIRURGICO`\|`QUIRURGICO` o blank | blank/null | Solo proc/cirugía; exacto según §3 |
| `permite_multi_sesion` | BooleanField | **`False`** | Escritura/API/UI: **rechazar** intentar `True` hasta A3/A4 |

### 4.2 Nullabilidad legacy (verificar e incluir migraciones EMR si aplica)

**Estado actual del código (referencia):**

- `tipo_estudio`: ya `null=True`, `blank=True`, `SET_NULL`.
- `practica`: `CharField` **sin** null (obligatorio a nivel modelo); create serializer exige `tipo_estudio` **o** `practica`.

**Decisiones A2:**

1. Documentar en implementación el resultado de la verificación sobre datos reales de prueba (¿hay estudios con `tipo_estudio` null? ¿`practica` siempre poblada?).
2. Para filas `ESTUDIO` (únicas creadas/operables en A2): **mantener** reglas legacy actuales (`tipo_estudio` y/o `practica` como hoy).
3. Preparar esquema para futuros `PROCEDIMIENTO`/`CIRUGIA`: `practica` y/o constraints que **no** obliguen práctica de estudio cuando `tipo_actividad ≠ ESTUDIO`. Si hace falta → migración aditiva **solo** en app `estudios` (p. ej. `practica` blank/null + validación condicional). **No** migraciones LIMS.
4. No endurecer nullabilidad de forma que rompa estudios existentes.

### 4.3 Migración + backfill

1. `AddField` aditivos con defaults seguros.  
2. Data migration **idempotente**:
   - Solo toca filas que aún no fueron backfilleadas de forma canónica (p. ej. filtro explícito / sentinel documentado), **o** usa `Update` condicional que no sobrescriba valores ya distintos del default de “pendiente de backfill”.
   - Resultado esperado en primera corrida: existentes → `tipo_actividad=ESTUDIO`, `procedimiento_catalogo=null`, snapshot blank/null, `permite_multi_sesion=False`.
   - **Conservar** todos los campos y relaciones previos (`paciente`, `tipo_estudio`, `practica`, `turno`, atenciones, informes, etc.) y el **conteo** de filas.
   - Reejecutar la herramienta/migración de datos **no** debe pisar datos nuevos (p. ej. si en el futuro ya existiera un `PROCEDIMIENTO` legítimo, no forzar `ESTUDIO`).
3. Verificación post-migrate: conteo igual; sample de FKs/campos legacy intactos; ningún snapshot/FK espurio en backfill.

### 4.4 Servicios / API — altas y mutaciones

| Pieza | Regla |
|-------|--------|
| Create `ESTUDIO` (legacy / default) | Como hoy; forzar/aceptar solo `ESTUDIO`; sin FK ni snapshot quirúrgico; `permite_multi_sesion=False` |
| Create `PROCEDIMIENTO` / `CIRUGIA` | **Deshabilitado** en API (4xx fijo, p. ej. 400/501 con mensaje de “tipo no habilitado”) aunque el modelo ya tenga campos |
| `actualizar_estudio` / PATCH | **Read-only protegidos:** `tipo_actividad`, `procedimiento_catalogo`, `clasificacion_quirurgica_snapshot`, `permite_multi_sesion`. Intento de cambio → 400 |
| Acciones legacy (`marcar-realizado`, informes, validar, entregar, etc.) | Solo sobre `tipo_actividad=ESTUDIO`. Si por cualquier vía existiera otro tipo → **bloquear** con 4xx (no reutilizar circuito de estudio) |
| List/detail | Pueden **exponer** campos nuevos (lectura) para preparación FE/A5 |

### 4.5 Frontend (A2)

| Pieza | Regla |
|-------|--------|
| Tipos / API client | Tipar campos nuevos (lectura) |
| Alta UI | **Solo** flujo estudio legacy. **No** selector ni submit de `PROCEDIMIENTO`/`CIRUGIA` |
| Multisesión | No control UI; no enviar `permite_multi_sesion=true` |

---

## 5. A2b — Corrección de snapshot (restringida)

### 5.1 Contrato

| | |
|--|--|
| **Endpoint** | `POST .../estudios-complementarios/{id}/corregir-clasificacion-snapshot/` |
| **Permiso** | **Solo `admin`** (staff/rol admin del EMR). Otros roles → 403 (o 404 si el módulo oculta; documentar el patrón elegido y testearlo). |
| **Body** | `clasificacion_quirurgica_snapshot` ∈ {`NO_QUIRURGICO`,`QUIRURGICO`}, `motivo` (string no vacío, obligatorio) |
| **Efecto** | Actualiza **únicamente** el snapshot de esa indicación. **No** muta `ProcedimientoCatalogo`. **No** cambia `tipo_actividad` ni `procedimiento_catalogo`. |

### 5.2 Condiciones previas (todas requeridas)

1. Indicación con `tipo_actividad` ∈ {`PROCEDIMIENTO`,`CIRUGIA`} (si en A2 aún no hay altas, el endpoint puede existir pero solo tendrá sentido cuando existan filas; mientras tanto tests con fixture forzada en DB de prueba).  
2. Snapshot solicitado **compatible** con `tipo_actividad` (§3):  
   - `PROCEDIMIENTO` → solo `NO_QUIRURGICO`  
   - `CIRUGIA` → solo `QUIRURGICO`  
   Incompatible → **400** (no dejar estado contradictorio).  
3. **No** reclasificar actos realizados: si `estado` ∈ {`REALIZADO`,`INFORMADO`,`VALIDADO`,`ENTREGADO`} (y cualquier otro estado post-realización que el módulo use) → **409/400** bloqueando la corrección. Corrección administrativa de acto cerrado = **otro diseño**.  
4. Motivo presente y no blank.

*(Estados `SOLICITADO` / `CONFIRMADO` / análogos pre-realización: permitidos si cumplen 1–2–4. `ANULADO`: bloquear salvo decisión explícita documentada en implementación — default **bloquear**.)*

### 5.3 Transacción y auditoría

- Una sola `@transaction.atomic`: persistir snapshot **y** evento de auditoría.
- Si falla audit o save → rollback completo (sin snapshot huérfano sin audit, ni audit sin cambio).
- Evento: p. ej. `estudio_clasificacion_correccion` con actor, id estudio, valor anterior/nuevo, motivo, `tipo_actividad` (contexto). Sin PHI innecesario.

### 5.4 Fuera de A2b

- Cambiar `tipo_actividad` o FK de catálogo.  
- “Corregir” a un snapshot que contradiga el tipo.  
- Corregir tras realización/cierre documental.  
- PATCH genérico / edición de catálogo que dispare reclasificación de indicaciones.

---

## 6. Catálogo: PROTECT y consumidores

| Referencia | Decisión A2 |
|------------|-------------|
| `EstudioComplementario.procedimiento_catalogo` | **`PROTECT`** — delete del catálogo con FKs → error integridad; operador debe **desactivar** (`activo=False`) |
| `RegistroProcedimiento.procedimiento` / `RegistroQuirurgico.procedimiento` | Hoy `SET_NULL` — **no modificar** en A2; documentar como deuda/consumidor existente |
| Tests | Intentar `ProcedimientoCatalogo.delete()` con estudio (fixture) que referencia → falla; `activo=False` OK |

---

## 7. Compatibilidad / no-regresión

| Escenario | Esperado |
|-----------|----------|
| Estudios existentes | Listan/abren/informan/realizan igual; backfill `ESTUDIO` |
| POST legacy | Solo `ESTUDIO`; sin campos nuevos o ignorando tipo proc/cirugía |
| POST con `tipo_actividad` proc/cirugía | **Rechazado** (no habilitado) |
| LIMS / turnos globales | Sin cambios |
| `permite_multi_sesion=true` | Rechazado en create/update |

---

## 8. Criterios de aceptación

### A2

- [ ] Migración + backfill idempotente; conteo y sample de relaciones legacy intactos.
- [ ] Tests legacy `estudios/tests` de create/flujo estudio en verde.
- [ ] API/UI **no** permiten alta `PROCEDIMIENTO`/`CIRUGIA`.
- [ ] PATCH no muta `tipo_actividad` / `procedimiento_catalogo` / snapshot / `permite_multi_sesion`.
- [ ] Acciones legacy de realización/informes rechazan no-`ESTUDIO`.
- [ ] FK nueva con `PROTECT`; delete catálogo referenciado falla; desactivación OK.
- [ ] Diff vacío en `laboratorio/`.
- [ ] Nullabilidad legacy verificada; migraciones EMR aplicadas solo si necesarias y documentadas.

### A2b

- [ ] Solo admin; motivo obligatorio.
- [ ] Snapshot incompatible con `tipo_actividad` → 400.
- [ ] Post-realización → bloqueado.
- [ ] TX atómica snapshot + audit; catálogo intacto.

---

## 9. Pruebas previstas (obligatorias)

| Caso | Esperado |
|------|----------|
| Combinaciones contradictorias (matriz §3) en `clean`/API | 4xx |
| PATCH con `tipo_actividad` / FK / snapshot / `permite_multi_sesion` | 400; DB sin cambio |
| Create API `PROCEDIMIENTO` / `CIRUGIA` | Deshabilitado (4xx) |
| Acciones legacy sobre fixture no-`ESTUDIO` | 4xx |
| A2b snapshot incompatible | 400 |
| A2b tras `REALIZADO` (u homólogo) | Bloqueado |
| A2b admin + motivo + pre-realización compatible | OK + audit en misma TX |
| A2b no-admin | 403/404 |
| Delete `ProcedimientoCatalogo` referenciado por estudio | IntegrityError / 4xx admin |
| Desactivar catálogo referenciado | OK |
| Backfill reejecutado | Sin overwrite de filas ya canónicas / sin pérdida de FKs |
| Regresión A0 (referencia post-A2) | Documentar; **no** parchear LIMS |

Ubicación: `estudios/tests/` (ampliar `test_models` / `test_api` + módulo dedicado A2). Sin tests nuevos bajo `laboratorio/`.

---

## 10. Orden de implementación sugerido

1. Verificar nullabilidad + migración modelo (`PROTECT`, fields) + backfill idempotente.  
2. Validaciones §3 + create/update protegidos + rechazo altas proc/cirugía + guardas en acciones legacy.  
3. Tests matriz + PATCH + altas deshabilitadas + PROTECT.  
4. A2b (admin, precondiciones, TX+audit) + tests.  
5. FE: tipos lectura; alta solo estudio.  
6. Corrida A0 de referencia (documentar).  
7. Docs EMR (`DOC_DISENO` / `DOC_FLUJOS_EMR` / `DOC_API_ENDPOINTS`) — sin docs LIMS.

---

## 11. Riesgos / bloqueantes

- Habilitar proc/cirugía “un poco” en FE por error → regresión de producto; mantener kill-switch API.  
- Acciones legacy que no pasen por un único guard de `tipo_actividad`.  
- Tentación de usar `SET_NULL` en la FK nueva → **prohibido** en este ticket.  
- Reclasificación post-acto pedida por negocio → **no** resolver en A2b; nuevo diseño.  
- “Arreglar” fallos LIMS/turnos preexistentes en el mismo PR → **prohibido**.
