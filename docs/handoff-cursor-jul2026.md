# Briefing para Arquitecto — SYNESIS EMR+LIMS

**Fecha:** 5 jul 2026  
**Origen:** iteraciones rápidas en **Cursor** (Diego + agente local), fuera del flujo formal de tickets  
**Propósito:** sincronizar conocimiento con lo implementado/modificado en terreno

---

## 1. Contexto operativo

- Proyecto: **SYNESIS EMR + LIMS** (Django/DRF/PostgreSQL + React/TypeScript).
- El arquitecto venía emitiendo tickets formales (PERM, QA, AUD, etc.) que se implementaron y **pushearon a `master`**.
- Después, Diego usó **Cursor** para ajustes puntuales de uso real (LIMS, turnos, consultas, catálogos, UX) con ciclos muy cortos: probar → corregir → refinar.
- **Estado del repo hoy:**
  - **Último commit en `master`:** `5dbd68f` — `chore(seed): add demo data for controlled QA smoke`
  - **Trabajo importante SIN commitear:** ~118 archivos, +6959 / −5241 líneas (LIMS, turnos, estudios, consultas, catálogos, roles, infra Docker).
  - El arquitecto debe asumir que **`master` remoto NO refleja todo lo hecho en Cursor**.

---

## 2. Lo que YA está en `master` (tickets cerrados / hardening)

| Área | Qué se hizo |
|------|-------------|
| **Permisos backend** | Laboratorio bloqueado de PHI EMR general; hardening de bypass `is_staff`; atenciones reforzadas |
| **Permisos frontend** | Guards/rutas alineados con backend; sanitización de errores clínicos en UI |
| **Auditoría** | Redacción PHI en snapshots genéricos |
| **Solicitudes legacy** | Deshabilitado auto-envío LIMS (`LIMS_AUTO_SEND`) |
| **CI/QA** | Smoke checks mínimos; seed demo básico; tests internación determinísticos |
| **Ops** | Runbook backup/restore; protocolo workflow asistente |

Commits representativos: `4e9f970`, `3ae7546`, `fbb7680`, `59347c7`, `85636c2`, `9d98eb3`, `5dbd68f`.

---

## 3. Trabajo hecho en Cursor — LIMS (bloque más grande)

### 3.1 Flujo operativo de órdenes

- **Estados simplificados** de solicitud/orden: `Pendiente` → `En proceso` (muestra tomada) → `Enviado`/`Finalizado` (resultados cargados e informados). Se eliminaron estados intermedios confusos tipo "muestra tomada" como estado separado.
- **Menú reordenado:** arriba **Órdenes pendientes** (`OrdenesLimsPendientes`), abajo historial por días.
- **Resumen de orden** muestra: paciente, médico solicitante, **origen/procedencia** de la muestra.
- Al cargar resultados: desaparecen botones "Tomar muestra" / "Cancelar"; queda "Descargar informe" y envío.

### 3.2 Origen / procedencia clínica

Nuevo modelo de **origen de solicitud** (`laboratorio/origen_solicitud.py`):

- Internación: **UCO**, **UCE**
- **Guardia**
- Ambulatorio interno: **CEHTA**, **ICPL**
- Ambulatorio **externo** (receta externa presentada en CEHTA o ICPL)

Incluye display de procedencia para externos (médico externo, sede).

### 3.3 Carga de resultados — hemograma Sysmex

- Entrada compatible con **ticket Sysmex**: el operador ingresa valores "abreviados" (ej. `93` → 9300 leucocitos; `237` → 2.37 mill/mm³ hematíes).
- Módulos: `laboratorio/entrada_resultados.py`, `laboratorio/sysmex_hemograma.py`, defaults en catálogo.
- **UX de carga:**
  - Enter salta al siguiente campo
  - Indicador de fórmula leucocitaria (% restante para 100%) al lado del campo activo
  - Observaciones **únicas por muestra/orden**, no por fila
  - Unidades visibles en formulario e informe
  - Se quitaron columnas confusas "patológico/crítico" del formulario de carga
- **Orden hemograma fijado:** Hematíes, Hematocrito, Hemoglobina, RDW, Leucocitos, Neutrófilos cayados/segmentados, Eosinófilos, Basófilos, Linfocitos, Monocitos, Plaquetas.

### 3.4 Catálogo de exámenes

- Pantalla **ExamenesCatalogo**: método, unidades, valores de referencia, tipo de muestra, **modo de entrada** configurable por examen.
- Pantalla **TiposMuestraCatalogo** para ABM de tipos de muestra.
- Correcciones de bugs al editar exámenes existentes vs crear nuevos.

### 3.5 Guardado parcial e informe parcial

- Se habilitó **guardar resultados parcialmente**.
- Estado visual de **"informado parcialmente"** cuando el médico necesita resultados antes del cierre total.
- Ajustes en validación backend que antes bloqueaban el guardado.

### 3.6 Informe PDF

- Rediseño del PDF para parecerse al informe real `informa_resultado.pdf` y luego estilo "laboratorio de referencia".
- Incluye: logo, método y valores de referencia en tipografía menor, paneles **sin salto de página**, hemograma **siempre primero** si está pedido.
- Ajustes iterativos: recuadros, firmas/sellos +30%, agrupación por paneles (`orden_grupos_informe.py`, `informe_pdf_layout.py`).

### 3.7 Solicitud de análisis (papel → digital)

- Formulario basado en PDF **"Solicitud de análisis"** del médico en papel.
- **14 paneles** clínicos relevantes (hemograma, perfil hepático, etc.).
- Usable desde **consulta médica** y desde **laboratorio** (carga directa).
- Catálogo semilla: `catalogo_solicitud_papel.py`, comando `seed_catalogo_solicitud_papel`.

### 3.8 Tomar muestra

- Al tomar muestra: elegir **tipo(s) de muestra** (sangre, orina, etc.) según lo pedido.
- Si hay 2–3 tipos requeridos, opción de registrar todos.

### 3.9 Envío de informes

- Envío por **email** y **WhatsApp** (token de entrega).
- Se configuró SMTP Gmail para pruebas (`diegobaulde@gmail.com`).
- Bugs corregidos: "no se pudo actualizar", WhatsApp enviaba mensaje pero no adjunto PDF.
- Archivos: `services_envio_informe.py`, `informe_entrega_token.py`.

### 3.10 Menú / naming

- **"Solicitudes" → "Laboratorio"** en navegación.
- Listado de análisis muestra pedidos reales de médicos (bug: no aparecían).

---

## 4. Trabajo hecho en Cursor — EMR clínico

### 4.1 Turnos

- **Bug:** modal de turno congelado al clic en calendario → corregido.
- **Paciente obligatorio** al crear turno médico.
- **Turnos para estudios complementarios**, no solo médicos:
  - Selector explícito: turno **médico** vs turno **estudio**
  - Validación de **sala/recurso** (no solapamiento en misma hora ni ±30 min)
  - Colores por **estado** en calendario
  - Estudios visibles en calendario de turnos
- Se intentó **drag & drop** para mover turnos → **se descartó** (poco fluido, dificultaba editar).
- Se removieron buscador superior y botón "Turnos" del header (UX más limpia).

### 4.2 Consultas / Atenciones

- Flujo corregido: al **Guardar**, la consulta queda persistida/cerrada según reglas acordadas.
- **Tabs** (detalle clínico / pedidos / archivos): ya **no borran** el borrador al cambiar de solapa.
- **Pedidos desde consulta:**
  - Select con búsqueda (lab y estudios complementarios)
  - Borrador local hasta guardar consulta; recién al guardar se generan registros
  - Posibilidad de eliminar pedidos antes de guardar
- **Archivos médicos:** documentos adjuntos en consulta ahora aparecen en módulo **Archivos** (migración `archivos_medicos` vinculada a `atencion`).
- Eliminada página legacy **MisConsultas**.

### 4.3 Estudios complementarios

- Búsqueda por paciente (un solo campo, se quitó duplicado).
- Click en listado navega al detalle (se quitó "vincular" confuso).
- Roles nuevos con acceso operativo (ver pacientes + turnos):

```python
# usuarios/roles.py
kinesiologo, radiologo, ecografista, fonoaudiologo
```

### 4.4 Internación

- Posibilidad de **editar camas** (`ModalCrearCama` extendido).

### 4.5 Pacientes

- Formulario para **editar datos del paciente** (`PacienteFormDialog`, `PacienteDemographicsForm`).

---

## 5. Catálogos poblados (comandos management)

| Catálogo | Comando / módulo |
|----------|------------------|
| CIE-10 | `poblar_cie10.py` |
| Estudios (RadLex, traducción ES) | `poblar_estudios.py`, `radlex_traduccion_es.py` |
| Procedimientos | `poblar_procedimientos.py` |
| Medicamentos | refactor `poblar_medicamentos.py` |
| Especialidades | `poblar_especialidades.py` |
| Microbiología (medios, microorganismos, antibióticos) | `poblar_microbiologia_*.py` |
| Meta | `poblar_todos_catalogos.py` |

---

## 6. Infra / dev experience

- **`emrctl`**: script unificado Docker (`up`, `down`, `seed`, `status`, logs por servicio).
- **`docker-compose.yml`** + `frontend/Dockerfile.dev` actualizados.
- **`docs/dev-start.md`**: guía con usuarios demo:

| Usuario | Clave | Rol |
|---------|-------|-----|
| admin | admin123 | superuser |
| medico1 | medico123 | médico |
| laboratorio1 | laboratorio123 | laboratorio |
| paciente1 | paciente123 | paciente |
| enfermeria1 | enfermeria123 | enfermería |
| secretaria1 | secretaria123 | secretaría |

- Orden LIMS demo: `LAB-DEMO-QA-00001`.

---

## 7. Consulta evaluada pero NO implementada

**MedGemma 1.5** para asistir diagnóstico/observaciones en hemogramas:

- Se analizó viabilidad contra `docs_synesis/reglas/ia.md`.
- Conclusión: factible como **asistente no autoritativo** (sugerencias en observaciones), pero **aún no hay código integrado**.
- Requeriría: servicio async, opt-in médico, auditoría, sin PHI en logs externos.

---

## 8. Decisiones de negocio tomadas en terreno

1. **Estados LIMS mínimos:** Pendiente → En proceso → Enviado/Finalizado (+ informado parcial).
2. **Origen clínico obligatorio** en órdenes (UCO/UCE/Guardia/Ambulatorio/Externo).
3. **Entrada Sysmex** es el modo default del hemograma (operador ingresa como en ticket).
4. **Paneles de informe** no se parten entre páginas; hemograma va primero.
5. **Pedidos de consulta** son borrador hasta guardar la consulta.
6. **Documentos de consulta** = archivos médicos del paciente/atención.
7. **Turnos de estudio** comparten calendario pero con tipo diferenciado y validación de sala.
8. **Drag & drop de turnos:** descartado por ahora.
9. **Roles de estudio** son lectura operativa (pacientes + agenda), sin PHI EMR completo.

---

## 9. Riesgos / deuda técnica detectada

- **Gran batch sin commit:** todo el bloque LIMS+turnos+consultas está local; riesgo de divergencia con blueprint del arquitecto.
- **Migraciones nuevas sin aplicar en remoto:** `laboratorio/0013`–`0022`, `estudios/0003`, `archivos_medicos/0006`–`0007`, `usuarios/0008`.
- **Credenciales SMTP** en `.env` local (no commitear).
- Posible **desalineación documental** con `docs_synesis/` (blueprint LIMS Fase B vs runtime actual).
- Código paralelo legacy en `api/views.py` (ya documentado en `docs/workflow-audit.md`) — no tocar sin auditoría.

---

## 10. Próximos pasos sugeridos para el arquitecto

1. **Revisar diff local completo** y decidir estrategia de commits (¿1 mega-commit LIMS-FASE-C o PRs por dominio?).
2. **Actualizar blueprint** (`docs_synesis/DOC_BLUEPRINT_LIMS_FASE_B.md` y reglas LIMS) con decisiones de §8.
3. **Ticket formal** para MedGemma si se aprueba (IA asistente, no diagnóstico automático).
4. **QA smoke** sobre flujos: solicitud consulta → orden LIMS → tomar muestra → carga Sysmex → informe parcial → envío email/WhatsApp.
5. **Revisar permisos** de nuevos roles (`kinesiologo`, etc.) contra matriz PERM existente.

---

## 11. Cómo reproducir localmente

```bash
./emrctl up --seed    # primera vez
./emrctl up           # siguientes
# Frontend: http://localhost:3000
# API: http://localhost:8000
```

---

**Nota para el arquitecto:** Este documento resume trabajo hecho **directamente con Cursor** para iteración rápida. No reemplaza `docs_synesis/` ni los tickets formales previos; complementa el gap entre `master` remoto y el estado real del workspace de Diego.

**Documentación técnica complementaria:** carpeta `_GEM_CONTEXT/` (modelos DB, frontend, reglas de negocio) generada el mismo día.
