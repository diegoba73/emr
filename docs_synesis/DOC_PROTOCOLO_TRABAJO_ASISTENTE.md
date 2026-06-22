# DOC_PROTOCOLO_TRABAJO_ASISTENTE — Cómo trabajar con el asistente (SYNESIS A+D)

**Versión:** 1.0 — 21 de junio de 2026  
**Alcance:** Guía práctica para el **usuario responsable del repo** al pedir diseño, tickets de implementación, revisión de diffs y reportes de avance.  
**No sustituye:** `DOC_TRABAJO_SYNESIS_CURSOR_CODEX.md` (flujo SYNESIS ↔ Cursor ↔ Codex); lo complementa desde el lado del pedido y la validación humana.

**Audiencia:** Diego (owner), cualquier colaborador que coordine cambios clínicos/LIMS con IA.

---

## Propósito

Unificar **cómo pedir**, **cómo revisar** y **cuándo avanzar** para que cada interacción con el asistente arquitecto produzca entregables accionables: diseño acotado, prompt listo para Cursor/Codex, checklist verificable y criterio explícito de go/no-go.

---

## Documentos relacionados

| Documento | Cuándo usarlo |
|-----------|---------------|
| `DOC_TRABAJO_SYNESIS_CURSOR_CODEX.md` | Flujo oficial, roles, plantillas Cursor/Codex, jerarquía SoT |
| `DOC_MAPA_SISTEMA.md` | Índice del sistema y orden de lectura |
| `checklists/pre-commit-emr-lims.md` | Antes de commit (dominio clínico/LIMS) |
| `DOC_ESTADO_ACTUAL_VERIFICADO.md` | Qué está probado en local/CI hoy |
| `prompts/prompt-maestro-cursor.md` | Referencia legacy para Cursor (alinear con SoT) |

**SoT canónica:** `docs_synesis/DOC_*.md` y `docs_synesis/reglas/*.md`. El código prevalece si contradice la doc; el conflicto debe reportarse, no ignorarse.

---

## Flujo resumido

```text
Usuario pide → Asistente diseña (arquitectura + ticket) → Cursor implementa
→ Codex audita (si hubo código) → Usuario revisa diff + checklist → prueba manual → commit
```

Regla de oro: **una sola herramienta escribe en el working tree a la vez** (Cursor *o* Codex, nunca en paralelo).

---

## 1. Cómo pedir arquitectura

Usá este formato cuando necesitás **decidir antes de codificar** (nuevo módulo, cambio de estado, permisos, integración, deuda técnica).

### Plantilla mínima

```markdown
## Contexto
(Qué problema clínico/operativo hay hoy; módulo EMR o LIMS)

## Objetivo
(Qué debería poder hacer el usuario al terminar — observable)

## Restricciones conocidas
(Seguridad, plazos, no migraciones, no tocar X, frontend en otro repo, etc.)

## SoT ya consultadas (opcional)
(Qué leíste vos; el asistente igual contrastará con docs_synesis/)

## Preguntas concretas
1. ...
2. ...

## Formato de respuesta deseado
( ej. "opciones A/B con trade-offs", "diagrama de estados", "solo alcance para ticket Cursor" )
```

### Qué debe devolver el asistente

1. **Alcance acotado** — qué entra y qué queda fuera.
2. **Impacto** — modelos, endpoints, permisos, auditoría, frontend, tests.
3. **Riesgos** — referencia a `DOC_RIESGOS_DEUDA_TECNICA.md` si aplica.
4. **Recomendación** — una opción preferida con justificación breve.
5. **Siguiente paso** — ticket Cursor listo para copiar *o* lista de dudas bloqueantes.

### Pedidos que funcionan bien

- "Diseñá la transición X→Y para `SolicitudExamen` respetando `DOC_FLUJOS_LIMS.md`."
- "Compará implementar acción `validar` vs PATCH genérico; recomendá una."
- "¿Qué tocaría agregar rol `bioquimico` sin romper LIMS actual?"

### Pedidos a evitar

- "Mejorá el proyecto" (sin módulo ni criterio).
- "Implementá ya" mezclado con arquitectura abierta (separar diseño e implementación).
- Pedidos que piden relajar permisos o saltear auditoría "temporalmente".

---

## 2. Cómo pedir ticket Cursor / Codex

Un **ticket** es el prompt completo que copiás a Cursor (implementación) o Codex (auditoría). El asistente lo genera a partir de arquitectura aprobada o de un pedido acotado directo.

### Cuándo pedir ticket Cursor

- Ya hay objetivo claro y alcance acordado.
- Las SoT relevantes están identificadas.
- Sabés qué archivos/módulos pueden tocarse.

**Frase tipo:**  
*"Generá ticket Cursor para [objetivo]. Alcance: [apps/archivos]. No tocar: [lista]. Tests mínimos: [módulo]."*

### Cuándo pedir ticket Codex

- Cursor terminó y hay diff para revisar.
- Querés auditoría **solo lectura** antes de merge/commit.

**Frase tipo:**  
*"Generá ticket Codex para auditar el diff de [rama/archivos]. Enfocá permisos y auditoría LIMS."*

### Estructura obligatoria del ticket (Cursor)

El asistente debe incluir estos apartados (detalle en `DOC_TRABAJO_SYNESIS_CURSOR_CODEX.md`):

| Apartado | Contenido |
|----------|-----------|
| Objetivo funcional | Problema + criterios de aceptación numerados |
| Alcance | Archivos/módulos permitidos |
| Fuentes de verdad | `DOC_*` y `reglas/*.md` concretas |
| Restricciones | Seguridad, PHI, migraciones, refactors |
| Cambios permitidos / prohibidos | Lista explícita |
| Permisos y auditoría | Roles, queryset, eventos `log_*` |
| Tests requeridos | pytest / Jest focal / manual |
| Comandos sugeridos | Ver sección 5 de este documento |
| Resultado esperado | Comportamiento observable |
| Resumen final requerido | Archivos, diff, pruebas, riesgos, `git status` |

### Estructura obligatoria del ticket (Codex auditor)

| Apartado | Contenido |
|----------|-----------|
| Objetivo de auditoría | Qué diff/rama revisar |
| SoT a contrastar | Lista `DOC_*` |
| Qué verificar | Permisos, estados, PHI, migraciones, tests |
| Restricciones | **Solo lectura** salvo autorización explícita |
| Clasificación | Crítico / Importante / Mejora / Sin problema |
| Salida | Informe estructurado; sin parches no autorizados |

### Coordinación Cursor ↔ Codex

Antes de lanzar Codex: confirmar que **Cursor no está editando**.  
Si Codex debe corregir: autorización **por escrito** del usuario + alcance mínimo de archivos.

---

## 3. Cómo revisar respuestas de Cursor

No aceptes un diff por el resumen del chat. Revisá en este orden:

### 3.1 Revisión rápida (5 minutos)

- [ ] ¿El diff respeta el **alcance** del ticket? (sin archivos colaterales)
- [ ] ¿Hay **`git status`** coherente con lo declarado?
- [ ] ¿Inventó roles, estados, columnas, rutas o endpoints no pedidos?
- [ ] ¿Aparecen secretos, PHI, dumps o rutas personales (`/Users/...`)?

### 3.2 Revisión funcional (10–20 minutos)

- [ ] Coherente con `DOC_REGLAS_NEGOCIO.md` y `DOC_FLUJOS_*` del dominio.
- [ ] Permisos: `permission_classes` + `get_queryset` alineados con `DOC_PERMISOS_AUDITORIA.md`.
- [ ] Estados: transiciones vía acciones/servicios (`*_estado.py`), no PATCH arbitrario de campos read-only.
- [ ] Auditoría: mutaciones críticas con `log_*` / `on_commit` donde corresponda.
- [ ] API: contratos en `DOC_API_ENDPOINTS.md` (nombres, métodos, payloads).
- [ ] Modelos: campos/constraints vs `DOC_MODELOS_DB.md` e `DOC_INVARIANTES.md`.

### 3.3 Revisión técnica

- [ ] Migraciones: solo si estaban en alcance; revisar reversibilidad e impacto en datos clínicos.
- [ ] Tests: ejecutados o omisión **justificada por escrito**.
- [ ] Sin `AllowAny` nuevo en endpoints sensibles (LIMS, HC, archivos, resultados).
- [ ] Sin refactors masivos mezclados con el fix/feature.

### 3.4 Señales de alerta (rechazar o pedir corrección)

| Señal | Acción |
|-------|--------|
| Relaja permisos "para que funcione la UI" | **No-go** — corregir |
| Modifica resultados validados sin trazabilidad | **No-go** |
| `git add .` implícito / muchos archivos no relacionados | Pedir diff acotado |
| Doc `docs_synesis/` desactualizada sin que el código cambió | Pedir alinear o revertir doc |
| Tests no corridos en cambio de permisos/estados | Exigir pytest mínimo |

### 3.5 Después de Cursor: Codex

Para cambios en backend, frontend, migraciones o permisos, pedir **auditoría Codex** antes del commit. El asistente valida el informe Codex contra SoT.

---

## 4. Formato de checklist manual

Usá checklists **copiables** en el chat, en la descripción del PR o en notas de sesión. Marcá `[x]` solo con evidencia (comando ejecutado, captura, diff visto).

### 4.1 Pre-implementación (usuario + asistente)

```markdown
## Checklist — Pre-implementación

- [ ] Objetivo escrito en una frase
- [ ] Alcance: módulos/archivos permitidos listados
- [ ] Alcance: exclusiones explícitas ("no tocar")
- [ ] SoT identificadas: DOC_REGLAS / DOC_MODELOS / DOC_API / DOC_PERMISOS / DOC_FLUJOS_*
- [ ] Criterios de aceptación numerados (≥3 si el cambio es funcional)
- [ ] Riesgos conocidos (DOC_RIESGOS o nuevos anotados)
- [ ] Ticket Cursor generado y revisado
- [ ] git status limpio o cambios previos entendidos
- [ ] Confirmado: Codex NO editará en paralelo
- [ ] Sin PHI ni secretos en el prompt
```

### 4.2 Post-implementación (revisión de diff)

```markdown
## Checklist — Revisión de diff

- [ ] Diff revisado archivo por archivo
- [ ] Alcance del ticket respetado
- [ ] Reglas de negocio y flujos respetados
- [ ] Permisos y queryset revisados
- [ ] Auditoría preservada o mejorada
- [ ] Sin PHI/credenciales en el diff
- [ ] Migraciones: solo si aprobadas y revisadas
- [ ] Tests ejecutados (comando + resultado) u omisión justificada
- [ ] Informe Codex revisado (si hubo código)
- [ ] Riesgos pendientes listados
```

### 4.3 Pre-commit

Completar también `checklists/pre-commit-emr-lims.md` si el cambio toca dominio clínico o LIMS.

```markdown
## Checklist — Pre-commit

- [ ] git status revisado
- [ ] Diff entendido por el usuario
- [ ] Sin cambios fuera de alcance
- [ ] SoT respetadas o conflicto documentado
- [ ] Prueba manual del flujo afectado (describir pasos)
- [ ] Usuario autoriza commit explícitamente
- [ ] pre-commit-emr-lims.md cumplido (si aplica)
```

---

## 5. Comandos estándar de validación

Ejecutar desde la **raíz del repo** con venv activo (`emr_env/` o equivalente). Adaptar la app según el ticket.

### 5.1 Estado del repositorio

```bash
git status
git diff
git diff --name-only
```

Antes y después de cada tarea de implementación.

### 5.2 Django — smoke general

```bash
python manage.py check
```

### 5.3 Backend — pytest rápido (SQLite in-memory)

Recomendado en desarrollo local. **No sustituye** PostgreSQL para constraints avanzados.

```bash
# Módulo afectado (ejemplos)
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: pytest laboratorio/tests/ -q
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: pytest usuarios/tests/ -q
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: pytest auditoria/tests/ -q

# Archivo focal
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: pytest path/to/test_file.py -q
```

### 5.4 Backend — PostgreSQL (smoke focal)

Cuando el cambio toca constraints, transacciones o `select_for_update`:

```bash
python manage.py test laboratorio.tests.test_microbiologia_estudio_id_filter -v 2
# o equivalente pytest sin vars SQLite:
pytest laboratorio/tests/test_microbiologia_estudio_id_filter.py -q
```

### 5.5 Backend — Django TestRunner por app

```bash
python manage.py test laboratorio.tests -v 2
python manage.py test usuarios.tests -v 2
python manage.py test auditoria.tests -v 2
```

### 5.6 Frontend (submódulo `frontend/`)

```bash
cd frontend
npm test -- --watchAll=false path/to/test.test.tsx
# Suite focal LIMS (referencia verificada):
npm test -- --watchAll=false limsMicroApi.test.ts MicrobiologiaEstudioDetalle.test.tsx
```

**Nota:** la suite Jest completa puede fallar por deuda preexistente (`App.test.tsx` / `react-big-calendar`). Preferir tests **focales** del módulo tocado. Ver `DOC_ESTADO_ACTUAL_VERIFICADO.md`.

### 5.7 Checkpoints (snapshots git)

Solo cuando el usuario pide **checkpoint** explícitamente:

```bash
bash scripts/checkpoint.sh checkpoint   # commit + tag incremental
bash scripts/checkpoint.sh last         # último checkpoint
bash scripts/checkpoint.sh volver       # reset al último checkpoint (destructivo)
bash scripts/checkpoint.sh listar       # listado de tags
```

### 5.8 Qué reportar al asistente

Copiar en el reporte de avance:

- Comando exacto ejecutado
- Pass/fail y conteo (ej. `328 passed`)
- Si no se corrieron tests: **motivo** (alcance solo docs, bloqueo de entorno, etc.)

---

## 6. Reglas de "no tocar"

Salvo ticket explícito que las incluya en **alcance permitido**:

### 6.1 Seguridad y datos

| Prohibido | Motivo |
|-----------|--------|
| Datos reales de pacientes, resultados, usuarios | PHI/PII |
| `.env`, tokens, JWT, claves, dumps productivos | Secretos |
| Relajar permisos, `AllowAny` en endpoints sensibles | Mínimo privilegio |
| Desactivar auditoría para simplificar dev | Trazabilidad clínica |
| Borrado irreversible de datos clínicos/laboratoriales | Integridad histórica |

### 6.2 Código y arquitectura

| Prohibido | Motivo |
|-----------|--------|
| Refactors masivos mezclados con un fix puntual | Diff irrevisable |
| Duplicar ViewSets legacy sin revisar `DOC_BACKEND.md` | Deuda / solapamiento |
| CRUD genérico que bypass acciones de negocio (`validar`, etc.) | Máquinas de estado |
| PATCH directo de campos de estado read-only | Invariantes |
| Migraciones fuera de alcance o sin plan de reversión | Riesgo BD |
| Modificar resultados **VALIDADOS** sin regla de negocio | Seguridad analítica |
| `git add .` sin revisión archivo por archivo | Commits contaminados |

### 6.3 Documentación

| Prohibido | Motivo |
|-----------|--------|
| Usar `_GEM_CONTEXT/` como única SoT | Export histórico Gem |
| Afirmar features **[OBJETIVO]** como **[IMPLEMENTADO]** | Desalineación |
| Cambiar reglas clínicas desde un DOC operativo | Jerarquía SoT |

### 6.4 Coordinación IA

| Prohibido | Motivo |
|-----------|--------|
| Cursor y Codex editando el mismo árbol a la vez | Conflictos / pérdida de control |
| Codex implementando sin informe previo + autorización | Segundo implementador sin control |
| Commit sin pedido explícito del usuario | Protocolo git del proyecto |

### 6.5 Zonas de alto riesgo (extra cuidado)

Pedir arquitectura + auditoría obligatoria si se toca:

- `api/permissions.py`, `get_queryset` en ViewSets LIMS/HC
- `auditoria/`, `*_estado.py`, validación de resultados
- `integracion_lims/`, webhooks, envío externo LIMS
- Migraciones en apps con datos clínicos
- Roles en `usuarios/models.py`

---

## 7. Criterios de go / no-go

### 7.1 Go — se puede commitear y seguir

Todas deben cumplirse:

| # | Criterio |
|---|----------|
| G1 | Objetivo del ticket cumplido; criterios de aceptación verificados |
| G2 | Diff acotado al alcance; `git status` limpio de sorpresas |
| G3 | SoT respetadas o conflicto documentado con decisión explícita |
| G4 | Permisos y auditoría revisados (sin relajaciones) |
| G5 | Tests mínimos ejecutados **o** omisión justificada y aceptada |
| G6 | Informe Codex sin hallazgos **Críticos** abiertos (si hubo código) |
| G7 | Prueba manual del flujo afectado realizada por el usuario |
| G8 | Usuario autoriza commit explícitamente |
| G9 | Checklist pre-commit cumplido |

### 7.2 No-go — detener hasta corregir

Cualquiera de estas condiciones **bloquea** merge/commit:

| # | Condición | Acción |
|---|-----------|--------|
| N1 | Hallazgo Codex **Crítico** sin resolver | Ticket correctivo Cursor o Codex autorizado |
| N2 | Permisos relajados o acceso cruzado entre pacientes/órdenes | Revertir o rediseñar |
| N3 | PHI o secretos en diff, logs o tests | Eliminar y rotar secretos si aplica |
| N4 | Migración no aprobada o destructiva sin plan | Revertir migración del diff |
| N5 | Estados terminales violados (`VALIDADO`, `INFORMADO`, `CANCELADO`, …) | Corregir lógica |
| N6 | Alcance del ticket excedido sin acuerdo | Revertir archivos fuera de alcance |
| N7 | Tests de permisos/estados omitidos sin justificación | Exigir pytest |
| N8 | Conflicto doc ↔ código no discutido | Reportar al asistente; no "arreglar en silencio" |

### 7.3 Go condicional — avanzar con deuda documentada

Permitido solo con **aceptación explícita** del usuario:

- Hallazgos Codex **Importantes** con plan de seguimiento y ticket futuro.
- Tests PostgreSQL completos pendientes pero smoke focal OK (`DOC_ESTADO_ACTUAL_VERIFICADO.md`).
- Deuda frontend preexistente no relacionada con el cambio.

Registrar en el reporte de avance (sección **Deuda / seguimiento**).

---

## 8. Plantilla para reportar avances

Copiar al cerrar una sesión o al pedir revisión al asistente.

```markdown
# Reporte de avance — [ID o título corto]

**Fecha:** YYYY-MM-DD  
**Fase:** Diseño | Implementación | Auditoría | Validación | Commit  
**Ticket / objetivo:** (una línea)

---

## Estado general

- [ ] En curso
- [ ] Bloqueado
- [ ] Listo para commit
- [ ] Commiteado (hash: ______)

---

## Qué se hizo

- ...
- ...

## Archivos tocados

| Archivo | Cambio breve |
|---------|--------------|
| `ruta/archivo.py` | ... |

## Comandos ejecutados

| Comando | Resultado |
|---------|-----------|
| `python manage.py check` | OK / FAIL — detalle |
| `DB_ENGINE=... pytest ...` | N passed / FAIL |

## Prueba manual

1. ...
2. ...
**Resultado:** OK / FAIL — observación

## Checklists

- Pre-implementación: [ ] completo
- Revisión diff: [ ] completo
- Pre-commit / pre-commit-emr-lims: [ ] completo / N/A

## Codex (si aplica)

| Severidad | Cantidad | Resumen |
|-----------|----------|---------|
| Crítico | 0 | |
| Importante | 0 | |
| Mejora | 0 | |

## Riesgos / deuda / seguimiento

- ...

## Decisiones pendientes (necesito del asistente o mía)

1. ...

## Siguiente paso propuesto

- ...
```

---

## 9. Frases útiles para el chat

| Intención | Ejemplo |
|-----------|---------|
| Arquitectura | "Diseñá opciones para X; no generes ticket todavía." |
| Ticket Cursor | "Con la opción B aprobada, generá ticket Cursor completo." |
| Ticket Codex | "Auditoría Codex del diff actual; foco permisos LIMS." |
| Revisión | "Cursor terminó — guiame la revisión del diff según sección 3." |
| Go/no-go | "Con este diff y pytest OK, ¿go o no-go para commit?" |
| Avance | "Armá reporte de avance con la plantilla sección 8." |
| Checkpoint | "checkpoint" (dispara `scripts/checkpoint.sh`) |

---

## 10. Resumen operativo

| Paso | Quién | Entregable |
|------|-------|------------|
| Pedir diseño | Usuario | Plantilla §1 |
| Ticket | Asistente | Prompt Cursor/Codex §2 |
| Implementar | Cursor | Diff + tests + resumen |
| Auditar | Codex | Informe severidades |
| Revisar | Usuario | Checklists §4 |
| Validar | Usuario | Prueba manual + comandos §5 |
| Decidir | Usuario + asistente | Go/no-go §7 |
| Commit | Usuario (explícito) | Checklist pre-commit |

**Prioridad absoluta:** seguridad del paciente y datos sensibles > SoT en `docs_synesis/` > código actual > pedido del usuario (si el pedido contradice lo anterior, prevalece la **alternativa segura** o decisión explícita).

---

## Changelog

| Versión | Fecha | Cambio |
|---------|-------|--------|
| 1.0 | 2026-06-21 | Creación inicial |
