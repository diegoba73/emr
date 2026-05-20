# DOC_TRABAJO_SYNESIS_CURSOR_CODEX — Reglas de trabajo con SYNESIS, Cursor y Codex

**Versión:** 1.0 — 20 de mayo de 2026  
**Alcance:** Proceso operativo para coordinar cambios en el EMR/LIMS con IA. **No redefine** reglas clínicas, laboratoriales ni contratos API; complementa la documentación técnica existente en `docs_synesis/`.

**Audiencia:** SYNESIS A+D, implementadores (Cursor), auditor (Codex), usuario responsable del repositorio.

---

## Propósito

Establecer reglas claras para trabajar con IA sobre un sistema clínico/laboratorial con **datos sensibles**, de modo que cada cambio tenga:

- propósito y alcance acotados;
- fuentes de verdad consultadas antes de codificar;
- control de permisos, seguridad y auditoría;
- criterios de aceptación y pruebas;
- revisión por diff;
- validación humana antes de commit.

Este documento es **operativo y versionado**. No autoriza saltear auditoría, permisos ni validación funcional.

---

## Roles

### SYNESIS A+D

Arquitecto funcional-técnico y **supervisor del cambio**. Traduce necesidades en requisitos, detecta riesgos, define criterios de aceptación, genera prompts, revisa implementaciones y valida compatibilidad con las fuentes de verdad.

- No implementa código en el repositorio por defecto (salvo tareas documentales acordadas).
- Resuelve conflictos entre pedido del usuario, documentación y código propuesto.
- Valida el informe de Codex y el diff de Cursor antes de que el usuario pruebe y autorice commit.

### Cursor

**Codificador principal** dentro del repositorio. Implementa cambios mínimos, localizados y trazables siguiendo el prompt aprobado por SYNESIS.

- Lee documentación SoT **antes** de modificar archivos.
- No inventa roles, estados, columnas, rutas ni endpoints.
- Entrega resumen con diff acotado, riesgos y pruebas ejecutadas o justificadas.
- No compite con Codex en el mismo árbol de trabajo simultáneamente.

### Codex

**Auditor técnico** del diff o estado del repositorio. Revisa cumplimiento, inconsistencias, permisos, seguridad, rutas, datos, arquitectura y tests.

- **No es implementador en primera instancia** ni fuente de verdad funcional.
- Audita compatibilidad técnica contra documentación, código, diff y tests.
- **No redefine** reglas clínicas, laboratoriales, permisos, estados ni contratos API sin validación de SYNESIS y autorización explícita del usuario.
- Solo implementa correcciones cuando el usuario lo autorice **expresamente**, tras entregar informe clasificado (Crítico / Importante / Mejora / Sin problema).

---

## Flujo oficial de trabajo

Orden **obligatorio** para cambios que afecten comportamiento, datos, permisos o contratos:

```text
SYNESIS diseña → Cursor implementa → Codex audita → SYNESIS valida → usuario prueba → commit
```

| Etapa | Responsable | Entregable mínimo |
|-------|-------------|-------------------|
| Diseño | SYNESIS | Objetivo, alcance, SoT, restricciones, criterios de aceptación, prompt para Cursor |
| Implementación | Cursor | Diff acotado, sin desvíos; `git status` antes y después |
| Auditoría | Codex | Informe con severidades; sin ediciones salvo autorización |
| Validación | SYNESIS | Compatibilidad con SoT; resolución de conflictos |
| Prueba | Usuario | Flujo clínico/LIMS según impacto |
| Commit | Usuario (o quien autorice) | Checklist pre-commit cumplido |

Documentación operativa pura (como este archivo) puede omitir Codex si SYNESIS y el usuario acuerdan que no hay riesgo de código; **cualquier cambio en backend, frontend, migraciones o permisos exige el flujo completo**.

---

## Regla obligatoria de coordinación

**Cursor y Codex no deben modificar el mismo árbol de trabajo al mismo tiempo.**

- Una sola herramienta/agente **escribe** en el working tree por tarea.
- Codex en modo auditoría: **solo lectura** del diff (`git diff`, PR, rama) salvo autorización explícita para corrección.
- Si Codex debe corregir: Cursor **detiene** ediciones hasta que Codex termine y el usuario reasigne implementación a Cursor si hace falta iterar.

---

## Regla de control por cambio

Antes de iniciar y al cerrar **cada** tarea:

1. Ejecutar `git status` y registrar archivos tocados.
2. Definir **un objetivo** por sesión (evitar “mejorar todo”).
3. Limitar archivos y líneas al alcance aprobado.
4. Revisar diff completo antes de commit.
5. Mantener cambios **reversibles** (commits pequeños, sin destructivos sin plan).

Complemento existente: `docs_synesis/checklists/pre-commit-emr-lims.md` (dominio EMR/LIMS). Este documento añade coordinación SYNESIS / Cursor / Codex.

---

## Fuentes de verdad del proyecto

Ubicación canónica: **`docs_synesis/`** (no confundir con `_GEM_CONTEXT/`, que puede ser export histórico para Gem y **no sustituye** SoT salvo acuerdo explícito).

| Documento | Estado en repo (mayo 2026) | Mandato |
|-----------|----------------------------|---------|
| `DOC_REGLAS_NEGOCIO.md` | Presente | Comportamiento funcional, permisos, restricciones, estados y flujos |
| `DOC_MODELOS_DB.md` | Presente | Tablas, relaciones, campos, constraints e integridad |
| `DOC_API_ENDPOINTS.md` | Presente | Rutas, endpoints y contratos públicos |
| `DOC_PERMISOS_AUDITORIA.md` | Presente | Roles, permisos, auditoría y seguridad funcional |
| `DOC_BACKEND.md` | Presente | Arquitectura backend |
| `DOC_FRONTEND.md` | Presente | Frontend **real en el repositorio** (ver sección Frontend) |
| `DOC_TESTS.md` | Presente | Pruebas automatizadas existentes |
| `DOC_MAPA_SISTEMA.md` | Presente | Visión de conjunto e índice de lectura |
| `DOC_FLUJOS_EMR.md` | Presente | Flujos clínicos |
| `DOC_FLUJOS_LIMS.md` | Presente | Flujos laboratorio |
| `DOC_RIESGOS_DEUDA_TECNICA.md` | Presente | Riesgos y deuda |
| `DOC_BLUEPRINT_LIMS_FASE_B.md` | Presente | Blueprint fase B LIMS |
| `DOC_INVARIANTES.md` | Presente | Invariantes de dominio |
| `DOC_MODELO_FUNDAMENTAL_EMR_LIMS.md` | Presente | Modelo conceptual |
| `DOC_ESTADOS_TRANSICIONES.md` | Presente | Máquinas de estado conceptuales |
| `DOC_ENTIDADES_PRINCIPALES.md` | Presente | Entidades principales |
| `reglas/*.md` | Presente | Reglas modulares (complemento) |
| `prompts/prompt-maestro-cursor.md` | Presente | Prompt maestro legacy; alinear con este DOC |
| `README.md` (raíz) | **No presente** | Documento esperado si está presente en otras ramas |
| `_GEM_CONTEXT/DOC_*.md` | Puede existir | Export Gem; verificar fecha y no usar como única SoT |

Ante ausencia de un documento listado arriba: tratarlo como **“documento esperado si está presente”** y no afirmar comportamiento no verificado en código.

---

## Jerarquía de decisión

1. **Seguridad del paciente y datos sensibles** (confidencialidad, integridad, trazabilidad).
2. **`DOC_PERMISOS_AUDITORIA.md`** y **`DOC_REGLAS_NEGOCIO.md`** para permisos, estados y flujos.
3. **`DOC_MODELOS_DB.md`** para esquema e integridad.
4. **`DOC_API_ENDPOINTS.md`** para contratos públicos.
5. Código actual en el repositorio (si contradice docs, **reportar conflicto**; no “arreglar” en silencio).
6. Pedido del usuario.

**Reglas operativas:**

- `DOC_REGLAS_NEGOCIO.md` manda sobre comportamiento funcional.
- `DOC_MODELOS_DB.md` manda sobre tablas y constraints.
- `DOC_API_ENDPOINTS.md` manda sobre rutas y contratos.
- `DOC_PERMISOS_AUDITORIA.md` manda sobre roles, permisos y auditoría.
- **Codex** no redefine reglas clínicas ni laboratoriales.
- **Cursor** no inventa roles, estados, columnas, rutas ni endpoints.
- **SYNESIS** valida conflictos entre pedido, documentación y código.
- Ante conflicto entre pedido del usuario y documentación: prevalece la **alternativa segura** o se solicita **decisión explícita** del usuario (nunca relajar permisos por conveniencia).

---

## Seguridad clínica y datos sensibles

Dominio con **PHI/PII** y resultados laboratoriales. Priorizar: confidencialidad, integridad, disponibilidad, trazabilidad, mínimo privilegio, no repudio, preservación histórica y auditoría.

**Prohibido en prompts, diffs, logs y ejemplos:**

- Datos reales de pacientes, muestras, resultados, estudios, médicos o usuarios.
- Dumps productivos, backups con PHI, exports CSV clínicos reales.
- Logs sin anonimizar que contengan PHI/PII.
- Tokens, claves, `.env`, cookies de sesión, JWT, credenciales o URLs privadas con secretos.
- Rutas absolutas de máquinas personales con datos (`/Users/.../pacientes.csv`).

**Prohibido en implementación:**

- Relajar permisos para “hacer funcionar” una pantalla.
- `AllowAny` en endpoints sensibles (LIMS, HC, archivos, resultados).
- Acceso cruzado entre pacientes, médicos, órdenes, muestras o resultados.
- Modificar resultados **validados** sin trazabilidad y reglas de negocio.
- Borrado irreversible de datos clínicos/laboratoriales.
- Cambios destructivos sin backup, plan de reversión y autorización explícita.
- Registrar PHI innecesaria en metadata de auditoría o logs de aplicación.

Usar siempre **datos ficticios o anonimizados** en ejemplos y tests manuales.

---

## Permisos, auditoría y trazabilidad

En **cambios futuros** que toquen mutaciones clínicas o laboratoriales:

- Toda mutación crítica debe **preservar auditoría** (`auditoria.AuditEvent`, `log_*` en servicios).
- No desactivar auditoría para simplificar desarrollo.
- Eventos relevantes: actor, fecha, entidad, antes/después cuando aplique, metadata mínima **sin PHI** en texto libre.
- Transiciones de estado (turnos, atenciones, `SolicitudExamen`, muestras, validación de resultados, informes) deben ser **trazables** y alineadas con `DOC_FLUJOS_*` y código `*_estado.py`.
- Validación de resultados o informes debe quedar auditada según implementación actual.
- Toda corrección posterior se vincula a: diff, prompt aprobado, prueba ejecutada y criterio de aceptación cumplido.

Consultar siempre `DOC_PERMISOS_AUDITORIA.md` y `docs_synesis/reglas/auditoria.md` antes de tocar permisos o logging.

---

## Base de datos y migraciones

- No crear ni aplicar migraciones fuera de alcance aprobado.
- Migraciones **pequeñas**, revisables, con plan de reversión.
- No eliminar columnas con datos clínicos sin estrategia de archivo y autorización.
- No cambiar constraints que rompan integridad histórica sin migración de datos planificada.
- En tareas solo documentales: **no ejecutar** `migrate` ni generar migraciones.
- Antes de merge: revisar que el commit no incluya migraciones accidentales (`git diff --name-only`).

Validar contra `DOC_MODELOS_DB.md` y `DOC_INVARIANTES.md`.

---

## Backend

- Cambios vía acciones de negocio (`validar`, `tomar-muestra`, etc.) cuando existan, no CRUD genérico que bypass estados.
- Permisos explícitos; coherencia entre `permission_classes` y `get_queryset`.
- Transiciones en servicios/módulos `*_estado.py` cuando ya hay precedente.
- Transacciones: auditoría con `on_commit` cuando corresponda.
- No duplicar ViewSets legacy sin revisar `DOC_BACKEND.md` y `DOC_RIESGOS_DEUDA_TECNICA.md`.

Toda validación futura debe considerar: reglas de negocio, modelos, permisos por rol, auditoría, contratos API, tests y regresión.

---

## Frontend

Según **`DOC_FRONTEND.md`** (SoT en repo, mayo 2026):

- **No asumir** una SPA React/Vue versionada en este repositorio si la documentación indica que no está presente en el tree.
- Scripts en `backup_documentacion/` no son aplicación de producción.
- Si el frontend vive en **otro repositorio o rama**, debe **indicarse explícitamente** en el prompt (ruta, commit, contrato API).
- `docs/dev-start.md` describe arranque local; si menciona carpeta `frontend/`, contrastar con `DOC_FRONTEND.md` antes de implementar UI aquí.

**Cursor y Codex:**

- No inventar componentes, rutas, servicios ni guards inexistentes.
- Toda UI futura debe respetar permisos, contratos en `DOC_API_ENDPOINTS.md` y estados en `DOC_REGLAS_NEGOCIO.md` / `DOC_FLUJOS_*`.

---

## Tests y verificación

Esta tarea documental **no exige** tests automatizados.

En **tareas futuras**, según impacto, incluir o justificar omisión de:

- tests unitarios (modelos, servicios, `*_estado.py`);
- tests de API (acciones LIMS, turnos, atenciones);
- tests de permisos por rol;
- tests de auditoría (`auditoria/tests/`);
- tests de migraciones (si aplica);
- pruebas manuales de flujo clínico/LIMS;
- verificación de regresión sobre endpoints existentes (`DOC_TESTS.md`).

Comandos habituales (solo cuando el alcance lo incluya): `pytest`, `python manage.py test <app>` en el módulo afectado.

---

## Uso correcto de Cursor

1. Recibir prompt de SYNESIS con apartados completos (plantilla abajo).
2. `git status` → leer SoT indicadas → plan acotado.
3. Implementar **solo** cambios permitidos.
4. Ejecutar pruebas del alcance.
5. Resumen: archivos, diff conceptual, riesgos, comandos, pendientes.
6. **No commit** salvo pedido explícito del usuario.
7. Ceder el árbol a Codex para auditoría antes de nueva ronda de edición.

Referencia complementaria: `docs_synesis/prompts/prompt-maestro-cursor.md` (alinear siempre con este DOC y SoT).

---

## Uso correcto de Codex

1. Modo por defecto: **auditoría de solo lectura** sobre diff o rama indicada.
2. Contrastar con SoT listadas en el prompt de auditoría.
3. Clasificar hallazgos (ver abajo).
4. **No modificar código** hasta autorización explícita del usuario.
5. Si autorizan corrección: alcance mínimo, un hallazgo o grupo acotado; luego devolver control a Cursor para el resto.
6. No competir con Cursor en el mismo directorio/archivos simultáneamente.

**Codex no es fuente de verdad funcional.** Audita compatibilidad técnica; no redefine reglas sin SYNESIS + usuario.

---

## Cuándo Codex puede modificar código

Solo si se cumplen **todas** las condiciones:

1. El usuario autoriza **por escrito** (chat, ticket, comentario de PR) tras ver el informe de auditoría.
2. Codex entregó informe previo con clasificación **Crítico / Importante / Mejora / Sin problema**.
3. Cursor **no está editando** el mismo árbol.
4. El alcance de la corrección está acotado (archivos y líneas nombrados).
5. SYNESIS valida que la corrección no contradice SoT.

Fuera de eso, Codex **solo informa**.

---

## Plantilla de prompt para Cursor

Copiar y completar antes de cada implementación:

```markdown
# Objetivo funcional
(Qué problema resuelve; criterios de aceptación numerados)

# Alcance
(Archivos/módulos permitidos; qué queda fuera)

# Fuentes de verdad
(Listar DOC_* y reglas/*.md a leer)

# Restricciones
(Seguridad, no migraciones, no refactors masivos, etc.)

# Archivos a revisar
(Rutas concretas antes de editar)

# Cambios permitidos
(Qué sí se puede hacer)

# Cambios prohibidos
(Qué no tocar: permisos, otros módulos, datos reales, etc.)

# Validaciones
(Reglas de negocio, estados, constraints, API, auditoría)

# Permisos y seguridad
(Roles, queryset, sin AllowAny, sin PHI en logs)

# Auditoría
(Qué eventos deben registrarse)

# Tests requeridos
(pytest/apps; pruebas manuales)

# Pasos de implementación
(Orden sugerido)

# Comandos sugeridos
(git status, pytest, manage.py test, etc.)

# Resultado esperado
(Comportamiento observable al terminar)

# Resumen final requerido
(Archivos tocados, diff, pruebas, riesgos, git status final)
```

---

## Plantilla de prompt para Codex auditor

```markdown
# Objetivo de auditoría
(Revisar diff/PR X por cumplimiento SoT y seguridad)

# Contexto
(Tarea SYNESIS, alcance, sin implementar)

# Fuentes de verdad
(DOC_* aplicables)

# Diff o rama a revisar
(Comando: git diff main...branch o archivos listados)

# Qué verificar
(Permisos, estados, auditoría, PHI, tests, migraciones, API)

# Hallazgos esperados
(Tipos de riesgo según módulo)

# Clasificación de severidad
(Usar Crítico / Importante / Mejora / Sin problema)

# Restricciones
(Solo lectura; no editar código; no redefinir reglas)

# Salida requerida
(Informe estructurado + recomendación; sin parches salvo autorización)
```

---

## Plantilla de prompt correctivo para Codex

Solo tras **autorización explícita** del usuario:

```markdown
# Autorización
(Cita textual del usuario autorizando corrección)

# Hallazgos a corregir
(Solo IDs/items Crítico o Importante acordados)

# Alcance de edición
(Archivos y líneas máximas)

# Fuentes de verdad
(DOC_* que no deben violarse)

# Restricciones
(Mismo árbol: Cursor detenido; sin migraciones no aprobadas)

# Validación post-corrección
(Tests a ejecutar)

# Entrega
(Diff + informe breve de qué se corrigió)
```

---

## Clasificación de hallazgos (Codex)

| Severidad | Definición |
|-----------|------------|
| **Crítico** | Rompe seguridad, permisos, datos clínicos/laboratoriales, auditoría, integridad de BD, migraciones o contratos públicos. Bloquea merge. |
| **Importante** | Incumple requerimiento, regresión probable, duplica lógica sensible, omite tests relevantes o introduce deuda riesgosa. Debe resolverse o aceptarse explícitamente. |
| **Mejora** | Ajuste recomendable sin bloqueo funcional. |
| **Sin problema** | Aspecto revisado y compatible con SoT y diff. |

---

## Checklist antes de pedir implementación

- [ ] Objetivo y alcance escritos por SYNESIS.
- [ ] SoT identificadas y leídas (al menos reglas + permisos + módulo afectado).
- [ ] Criterios de aceptación numerados.
- [ ] Riesgos conocidos documentados (`DOC_RIESGOS_DEUDA_TECNICA.md` si aplica).
- [ ] Prompt Cursor completo (plantilla).
- [ ] `git status` limpio o cambios previos entendidos.
- [ ] Confirmado: Codex **no** editará en paralelo.
- [ ] Sin datos reales ni secretos en el prompt.

---

## Checklist antes de aceptar un diff

- [ ] Diff revisado archivo por archivo.
- [ ] Alcance del prompt respetado; sin archivos colaterales.
- [ ] Coherente con `DOC_REGLAS_NEGOCIO.md` y flujos `DOC_FLUJOS_*`.
- [ ] Permisos y `get_queryset` alineados con `DOC_PERMISOS_AUDITORIA.md`.
- [ ] Auditoría preservada o mejorada; no desactivada.
- [ ] Sin PHI, credenciales ni dumps en el diff.
- [ ] Migraciones: solo si estaban en alcance y son seguras.
- [ ] Tests ejecutados o omisión justificada por escrito.
- [ ] Informe Codex revisado por SYNESIS (si hubo cambio de código).
- [ ] Riesgos pendientes listados.

---

## Checklist antes de commit

- [ ] `git status` revisado.
- [ ] Diff entendido.
- [ ] Alcance respetado.
- [ ] Sin cambios fuera de alcance.
- [ ] Fuentes de verdad respetadas.
- [ ] Permisos revisados.
- [ ] Auditoría revisada.
- [ ] Datos sensibles protegidos.
- [ ] Migraciones revisadas si aplica.
- [ ] Tests ejecutados o justificación documentada.
- [ ] Riesgos pendientes informados.
- [ ] Usuario validó funcionalmente.
- [ ] Checklist `docs_synesis/checklists/pre-commit-emr-lims.md` (si aplica dominio clínico/LIMS).

---

## Riesgos prohibidos

- Convertir a Codex en **segundo implementador** paralelo sin control.
- Cursor y Codex editando el **mismo árbol** a la vez.
- Inventar documentación o features como confirmadas.
- Relajar permisos, `AllowAny` o auditoría.
- Refactors masivos mezclados con features.
- Omitir revisión de diff o `git status`.
- Incluir datos reales, credenciales o dumps en repo/chat.
- Modificar código funcional “por error” en tareas solo documentales.
- Cambiar reglas clínicas/laboratoriales desde un DOC operativo.
- Prompts ambiguos (“mejorar todo”, “revisar el proyecto”).
- Commits con `git add .` sin revisión.
- Habilitar a Codex para editar sin autorización explícita.

---

## Resumen operativo

| Actor | Función principal |
|-------|-------------------|
| SYNESIS | Diseña, valida, no compite con implementación salvo docs acordadas |
| Cursor | Implementa diff mínimo trazable |
| Codex | Audita; corrige solo con autorización |
| Usuario | Prueba funcionalmente y autoriza commit |

**Flujo:** SYNESIS diseña → Cursor implementa → Codex audita → SYNESIS valida → usuario prueba → commit.

**Regla de oro:** Una sola herramienta escribe a la vez; la documentación en `docs_synesis/DOC_*.md` manda sobre el comportamiento; la seguridad del paciente manda sobre la velocidad de entrega.

---

## Documentos relacionados

- Índice y lectura: `DOC_MAPA_SISTEMA.md`
- Pre-commit dominio: `checklists/pre-commit-emr-lims.md`
- Prompt histórico Cursor: `prompts/prompt-maestro-cursor.md`
- Arranque local (no sustituye SoT frontend): `docs/dev-start.md`
