# Auditoría de workflows críticos (EMR + LIMS)

Auditoría **basada en código** de los flujos listados. Objetivo: localizar **orquestación**, **efectos secundarios**, **transacciones** y **dispersión**. **No implementa cambios.**

**Alcance documental:** este archivo es **auditoría complementaria de arquitectura**. La fuente de verdad operativa del proyecto es **`docs_synesis/`**. El detalle actualizado de **`POST /api/atenciones/`** (delegación en `AtencionService`, `api_post_compat`, transacciones) está en [`runtime-alignment-atencion.md`](./runtime-alignment-atencion.md).

**Nota de routing:** En `api/urls.py`, los ViewSets activos son **`turnos.views.TurnoViewSet`**, **`turnos.views.AtencionViewSet`**, **`solicitudes.views.SolicitudViewSet`**, **`laboratorio.views.SolicitudExamenViewSet`**. Existen **segundas implementaciones** muy extensas en **`api/views.py`** (`TurnoViewSet`, `AtencionViewSet`, etc.) que **no están registradas** en el router principal — se documentan como **código paralelo / riesgo de confusión**, no como comportamiento HTTP expuesto por defecto salvo otro `include` no auditado.

---

## 1. Señales Django y `save()` implícitos

| Origen | Comportamiento |
|--------|----------------|
| **`usuarios.signals.post_save(User)`** | Crea `UserProfile` al crear usuario. **No** afecta workflows clínicos principales. |
| **`solicitudes.models.Solicitud.save()`** | `clean()` siempre; si `LIMS_AUTO_SEND` y nuevo y tipo lab, llama `_enviar_a_lims()`; si estado `COMPLETADA` sin `fecha_completada`, segunda `save` de `fecha_completada`. **Side effect:** red externa / mutación post‑create. |
| **`laboratorio.models.SolicitudExamen.save()`** | Genera `numero` LAB‑YYYY‑XXXXX si vacío; `full_clean()`. |
| **`historias_clinicas.models.Internacion.save()`** (rico) | Genera `numero_internacion`. |
| **`turnos.models.Turno.save()`** | `full_clean()` validación fechas. |

**Señales sobre modelos clínicos de consulta/atención:** no halladas en la búsqueda acotada (`post_save`/`receiver` solo en `usuarios`).

---

## 2. Scheduling — Turnos (`turnos.views.TurnoViewSet` — **ruta activa**)

### 2.1 Reservar (`POST /api/turnos/`)

**Pasos:** `perform_create` → `serializer.save(...)` con paciente forzado si rol paciente → `log_create` auditoría.

**Entidades:** `Turno` (+ `Paciente`,`Medico`,`Recurso` por payload).

**Side effects:** **`AuditEvent`** (módulo turnos). Sin `transaction.atomic` explícito en view (comportamiento por defecto de vista DRF).

**Lógica dispersa:** permisos paciente/médico inline en view.

---

### 2.2 Confirmar / cancelar / realizar (estado)

En el **ViewSet activo** la transición es principalmente **`PATCH/PUT /api/turnos/:id/`** con campo `estado` (y filtros de queryset en `get_queryset`).  
**`perform_update`** en `turnos/views.py`: valida paciente si rol paciente → `serializer.save()` → `log_update` auditoría.

**No** aparece en **`turnos/views`** la creación automática de `Atencion` al pasar a CONFIRMADO/REALIZADO (eso está en **`api/views.TurnoViewSet.perform_update` — no enrutado**).

**Marcar REALIZADO tras consulta:** ocurre en **`turnos.views.AtencionViewSet.registrar_consulta`** (cuando hay contenido clínico), no en el `TurnoViewSet` solo.

**Ownership:** estado de agenda vive en **`Turno`**; coherencia “day of care” depende de llamadas posteriores a **atenciones**.

---

### 2.3 Diagrama — “Día de atención” (flujo enrutado real)

```
Cliente
  → PATCH /api/turnos/:id/  (cambiar estado, p.ej. CONFIRMADO)
       [ Turno actualizado ]
       [ AuditEvent UPDATE ]
  → POST /api/atenciones/  { turno }
       [ Atencion create o 200 idempotente ]
       [ AuditEvent CREATE ]
  → POST /api/atenciones/:id/registrar-consulta/
       [ transaction.atomic en view ]
       [ ConsultaAmbulatoria insert/update ]
       [ Atencion puede actualizar estado_clinico ]
       [ Turno → REALIZADO si contenido ]
       [ AuditEvent UPDATE ×2 (atención, turno si aplica) ]
  → POST .../cerrar/
       [ Atencion FINALIZADA + fecha_cierre ]
       [ AuditEvent UPDATE ]
```

| Paso | Transacción explícita | Entidades tocadas | Side effects |
|------|------------------------|-------------------|-------------|
| PATCH turno | No (por defecto request) | `Turno` | Auditoría |
| POST atención | No en create (salvo interno ORM) | `Turno`,`Atencion`,`Paciente`,`Medico` implícitos | Auditoría |
| registrar_consulta | **`@transaction.atomic`** | `ConsultaAmbulatoria`, `Turno`?, `Atencion` | Auditoría ×N, logs |
| cerrar | Implícita | `Atencion` | Auditoría |

---

## 3. Atención clínica (`turnos.views.AtencionViewSet` — activo)

### 3.1 Abrir atención (`POST /api/atenciones/`)

- Enrutado a **`turnos.views.AtencionViewSet.create`** (`api/urls.py`).
- La vista **delega** en **`AtencionService.iniciar_atencion_desde_turno(..., api_post_compat=True)`**; la orquestación y persistencia viven en el **servicio**, no en `objects.create` inline en la vista.
- La operación corre dentro de **`transaction.atomic()`** en el servicio (modo API POST).
- En **`api_post_compat=True`** (compatibilidad HTTP vigente):
  - crea o devuelve la atención según idempotencia (**201** alta nueva, **200** si ya existía para el mismo turno);
  - resuelve paciente, médico y tipología desde el **`Turno`**;
  - **no** crea registros hijos (`ConsultaAmbulatoria`, procedimiento, quirúrgico);
  - **no** cambia el estado del **`Turno`**;
  - **`log_create`** solo en alta nueva (idempotencia sin nuevo evento de auditoría).
- El modo **`api_post_compat=False`** del mismo servicio (turno → **REALIZADO**, registro hijo) se usa desde tests y desde **`api/views.TurnoViewSet.iniciar_atencion`** (**no enrutada** en el router principal de turnos).

---

### 3.2 Cerrar atención (`POST .../cerrar/`)

- Solo si `ABIERTA` → `FINALIZADA` + `fecha_cierre` → `log_update`.

---

### 3.3 Registrar consulta (`POST .../registrar-consulta/`)

- Decorador **`@transaction.atomic`**.
- Valida médico asignado / staff; no edita si `fecha_cierre`; exige `tipo_intervencion == CONSULTA`.
- Upsert `ConsultaAmbulatoria` vía serializer.
- Si hay contenido (`consulta_ambulatoria_tiene_contenido`): **`Turno.estado = REALIZADO`** (`save` turno).
- `log_update` atención y opcionalmente turno.

**Orchestration:** **concentrada en la view** (alto acoplamiento HTTP ↔ negocio).

---

### 3.4 Registro procedimiento / cirugía

- **`turnos/views.AtencionViewSet`** (activo para `/api/atenciones/`) incluye **`crear_registro_ambulatorio`**; **no** incluye en el mismo archivo acciones **`crear_registro_procedimiento` / `crear_registro_quirurgico`** (éstas están en **`api/views.AtencionViewSet`** — **no enrutado** en `api/urls.py`).
- **`/api/registros-procedimientos/`** y **`/api/registros-quirurgicos/`** registran **`ViewSet`** desde **`api.views`** — creación típica vía **`POST`** REST sobre el recurso ligando `atencion` en serializer, **alternativa** paralela al patrón “action sobre atención”.

**Duplicidad:** dos rutas concebibles (action en `AtencionViewSet` legacy **vs** POST en ViewSets de registro).

**Hecho verificado:** `api/urls.py` importa **`AtencionViewSet` desde `turnos.views`**, por tanto **`api/views.AtencionViewSet` NO atiende `/api/atenciones/`** en router principal.

---

## 4. Laboratorio (`laboratorio.views.SolicitudExamenViewSet`)

### 4.1 Crear solicitud

- `perform_create` → `serializer.save()` → `log_create` auditoría.

### 4.2 Cargar resultados (`POST .../cargar-resultados/`)

- Envuelto en **`transaction.atomic()`**.
- Para cada ítem: **`ResultadoExamen`** `select_for_update().get` → `save()` → `log_update` por resultado.
- Puede pasar `SolicitudExamen` `PENDIENTE` → **`EN_PROCESO`**.
- `log_update` de la solicitud al final.

### 4.3 Validar (`POST .../validar/`)

- **`transaction.atomic()`**.
- Comprueba no vacíos (`valor_obtenido == ''`).
- `SolicitudExamen.estado = VALIDADO`; **`ResultadoExamen.objects.filter(...).update(validado_por, fecha_validacion)`** → **bulk UPDATE sin `save()` por fila** → **auditoría** intenta `log_update` por resultado con `before=None` para eventos parciales.

**Riesgo:** mezcla **integridad transaccional** con **auditoría best‑effort** y **bulk update** sin snapshot “before” por resultado.

### 4.4 Entregar resultado

- Estado **`ENTREGADO`** existe en el modelo.
- Acción dedicada **`marcar_entregado`** en **`laboratorio.views.SolicitudExamenViewSet`** (`laboratorio/views.py`) — transición explícita con auditoría asociada (complemento de esta auditoría; permisos y reglas finas en **`docs_synesis/`**).
- Sigue siendo posible mutación vía **`PATCH`** REST del ViewSet si el serializer lo permite (comportamiento genérico paralelo).

---

## 5. Solicitudes (`solicitudes.views.SolicitudViewSet`)

### 5.1 Crear (`perform_create`)

**Side effects encadenados:**
1. Asigna `creado_por` / `modificado_por`; auto `medico_solicitante` si aplica.
2. `log_create` auditoría.
3. Si payload trae `lims_paneles` o `lims_tipos_examen` y tipo lab → **`lims_service.enviar_solicitud_a_lims`** → posible **segundo `save`** con `lims_id`.

**Transaccionalidad:** llamada LIMS **fuera** de `atomic`; fallo LIMS **capturado silenciosamente** (`except: pass`).

---

### 5.2 Cambiar estado / completar / cancelar / reabrir

- `cambiar_estado`, `marcar_como_completada`, `cancelar`, `reabrir` → mutan vía métodos del modelo o serializer → `log_update` en cada caso.
- **`reabrir`** / **`cancelar`** usan métodos `Solicitud.reabrir()`, `cancelar()` (estado + fechas).
- **`marcar_como_completada`** llama **`solicitud.marcar_como_completada()`** (que hace `save()`) y **otro** `solicitud.save()` en la view para `modificado_por` → **doble persistencia** en el mismo request.

---

## 6. Lógica por capa (dispersión observada)

| Capa | Ejemplos encontrados |
|------|----------------------|
| **Views** | Reglas de negocio largas en `registrar_consulta`, `perform_create` solicitudes+LIMS, filtros por rol en todos los ViewSets. **`api/views.TurnoViewSet`** con disponibilidad + creación `Atencion` al cambiar estado (**no enrutado**). |
| **Serializers** | Interpretación de datos y `create` anidado en `ConsultaCreateSerializer` (audit previo: nested diagnósticos/prescripciones en HC). |
| **Model `save()`** | Solicitud (LIMS_AUTO_SEND, fecha_completada), SolicitudExamen (numeración), Turno (validación), Internacion (numeración). |
| **Servicios** | `AtencionService.iniciar_atencion_desde_turno` (transacción atómica interna) — usado por la **ruta HTTP activa** `POST /api/atenciones/` (`api_post_compat=True`), además de tests y del modo completo (`api_post_compat=False`) en **`api/views.TurnoViewSet.iniciar_atencion`** (**no enrutada**). |
| **Señales** | Solo `usuarios` sobre `User`. |
| **Frontend** | Repo mínimo (`AuditEventsPage`) — **impacto UI no cuantificado** aquí. |

---

## 7. Violaciones de boundary (resumen)

| Boundary | Violación típica |
|----------|-------------------|
| **Scheduling** | Lógica disponibilidad/conflicto duplicada (**solo** en `api/views.TurnoViewSet` legacy, no en router activo). |
| **Clinical encounter** | Reglas de cierre + texto clínico en **view** `registrar_consulta`. |
| **Laboratory** | Resultados + estado solicitud + auditoría en mismo action; **`queryset.update`** en validación vs `save` en carga. |
| **Order management** | Solicitud: **HTTP + LIMS lateral** en `perform_create`; doble `save` en completar. |

---

## 8. Workflows transaccionales críticos

| Workflow | ¿Atomic explícito? | Riesgo |
|----------|---------------------|--------|
| `registrar_consulta` | **Sí** (`@transaction.atomic`) | Bajo inconsistencia interna; alto **acoplamiento** en un solo método. |
| `cargar_resultados` / `validar` (lab) | **Sí** | `validar`: **bulk update** resultados + auditoría parcial. |
| Crear `Solicitud` + LIMS | **No** (LIMS best effort) | Solicitud persistida sin LIMS sincronizado sin error visible. |
| `POST /api/atenciones/` → `AtencionService.iniciar_atencion_desde_turno` (`api_post_compat=True`) | **Sí** (`transaction.atomic()` en el servicio) | Idempotencia y auditoría acotadas al modo compat; sin registro hijo ni cambio de turno en este endpoint. |

---

## 9. Ownership (por workflow)

| Workflow | “Dueño” procesal en código hoy |
|----------|--------------------------------|
| Agenda | `Turno` (`turnos.views`) |
| Encuentro operativo | `Atencion` + hijos (`ConsultaAmbulatoria` / …) |
| Auditoría | `audit_service` invocado desde views (post‑commit donde aplicó hardening) |
| Orden solicitud app | `solicitudes.Solicitud` + side LIMS |
| Lab nativo | `SolicitudExamen` + `ResultadoExamen` |

---

## 10. Riesgos explícitos actuales

1. **Dos cuerpos `TurnoViewSet` / `AtencionViewSet`** (activo vs `api/views`) — divergencia perpetua y **orquestación distinta** (creación `Atencion` al confirmar solo en legacy).
2. **LIMS** en create solicitud: inconsistencia **solicitud local vs LIMS** sin transacción distribuida.
3. **Laboratorio `validar`:** `update()` en queryset de resultados puede **desalinear** auditoría “before” y reglas en `ResultadoExamen.save()` si existieran.
4. **Doble save** al completar solicitud.
5. **Orquestación pesada en views** dificulta pruebas unitarias y reutilización sin duplicar HTTP.

---

## 11. Diagrama consolidado — Registrar consulta (efectos)

```
[HTTP POST registrar-consulta]
        ↓
  @transaction.atomic {
        validar permisos / cerrado / tipo
        ConsultaAmbulatoriaSerializer.save(atencion=)
        → INSERT/UPDATE ConsultaAmbulatoria
        si contenido clínico:
            Turno.estado = REALIZADO
        si estado_clinico en body: Atencion.save
  }
        ↓ (post-commit si audit en atomic)
  log_update(Atencion)
  log_update(Turno) opcional
```

**Entidades:** `Atencion`, `ConsultaAmbulatoria`, `Turno`; **auditoría:** `AuditEvent`.

---

## 12. Validaciones obligatorias — respuestas

### 12.1 ¿Qué lógica debería salir de serializers?

- **Creación anidada** en HC (`ConsultaCreate` con diagnósticos/prescripciones/...) — orquestación multi‑entidad mejor **atestiguada** en un servicio para transacción única y política clara (cuando se decida migrar).
- **Cualquier serializer** que mezcle persistencia con **llamadas externas** (no visto en serializers auditados para LIMS — LIMS está en **view** solicitudes).

### 12.2 ¿Qué lógica debería salir de views?

- **`registrar_consulta`**: reglas de negocio + persistencia + transición de turno + auditoría.
- **`Solicitud.perform_create`**: asignación médico + segundo save LIMS.
- **Disponibilidad / solapamiento** de turnos (**en `api/views.TurnoViewSet`**) si algún día se reactiva esa rama — hoy **duplicación latente** vs activo.

### 12.3 ¿Qué workflows necesitan `transaction.atomic`?

- Ya lo usan: **`registrar_consulta`**, **`cargar_resultados`**, **`validar`** (lab), **`AtencionService.iniciar_atencion_desde_turno`**.
- **Candidatos futuros** (si centraliza orquestación): creación **HC anidada**, **cualquier** operación que combine **turno + atención + auditoría** en una sola operación de negocio atómica según reglas.

### 12.4 ¿Qué workflows requieren auditoría obligatoria (desde negocio)?

- Todo cambio sobre **turno, atención, solicitud, solicitud lab, resultados** ya instrumentado en vistas auditadas — política best‑effort.
- **Crítico regulatorio:** cambios de **estado clínico/lab** y **firma/validación** de resultados.

### 12.5 ¿Qué workflows son más peligrosos hoy?

1. **Solicitud create + LIMS** (estado externo desconocido al usuario).
2. **Validar resultados** (bulk update + posible desalineación con triggers futuros).
3. **Dos implementaciones de turno/atención** (riesgo de **activar código equivocado** en un refactor).
4. **registrar_consulta** (múltiples entidades + turno REALIZADO).

### 12.6 ¿Qué workflows tienen mayor acoplamiento?

- **Turno ↔ Atencion ↔ ConsultaAmbulatoria ↔ Turno REALIZADO ↔ auditoría** en una acción.
- **Solicitud ↔ LIMS**.
- **Laboratorio** resultados + estado solicitud + auditoría por fila.

---

*Fin de la auditoría de workflows (planificación / entendimiento). Para servicios propuestos y orden de adopción ver [`application-services-roadmap.md`](./application-services-roadmap.md).*
