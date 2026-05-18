# Alineación runtime POST `/api/atenciones/` ↔ `AtencionService`

Documento técnico de la consolidación quirúrgica (sin cambio de contrato HTTP observable).

---

## Workflow antes

| Aspecto | Estado |
|---------|--------|
| **Endpoint** | `POST /api/atenciones/` → `turnos.views.AtencionViewSet.create` |
| **Transacción** | Sin `transaction.atomic`; un solo `INSERT` habitualmente |
| **Orquestación** | Inline en la vista: lectura turno/atención, validaciones, `resolve_tipo_intervencion_from_recurso`, `Atencion.objects.create` |
| **Idempotencia** | Si ya existía `Atencion` por `turno_id`, respuesta **200** sin nueva fila |
| **Turno.estado** | Sin cambios |
| **Registro hijo** | No (`ConsultaAmbulatoria`, etc.) |
| **Auditoría** | `log_create` solo en alta nueva, llamado desde la vista |

---

## Workflow después

| Aspecto | Estado |
|---------|--------|
| **Endpoint** | Igual (`POST /api/atenciones/`), mismo payload y mismos códigos **400 / 200 / 201** |
| **Transacción** | `transaction.atomic()` centralizado en **`AtencionService._iniciar_desde_turno_api_post`** (`api_post_compat=True`) |
| **Orquestación** | Delegada al **mismo** `AtencionService.iniciar_atencion_desde_turno` ya existente |
| **Retorno del service** | `IniciarAtencionOutcome(atencion=…, created_new=bool)` — la vista solo serializa y elige status |
| **Auditoría** | `log_create` dentro del service en alta nueva (metadata `{"view": "AtencionViewSet.create"}` igual que antes); idempotencia **sin** nuevo evento |
| **`transaction.on_commit`** | Sigue aplicando en `audit_service`: dentro del `atomic`, el `AuditEvent` persiste tras commit estable |

---

## Modo dual en `AtencionService.iniciar_atencion_desde_turno`

- **`api_post_compat=False`** (por defecto): comportamiento anterior del service — validación de estado RESERVADO/CONFIRMADO, paso del turno a REALIZADO, creación de `Atencion`, `_crear_registro_hijo`, **sin** idempotencia devolviendo éxito. Usado desde tests y desde código legacy **`api/views.TurnoViewSet.iniciar_atencion`** (no montado en el router principal de turnos).

- **`api_post_compat=True`**: comportamiento histórico de **POST `/api/atenciones/`** — idempotencia, texto de errores REST, sin cambio de `Turno`, sin registro hijo, auditoría solo en alta.

---

## Lógica extraída de la vista

- Obtención y bloqueo de datos en servicio (`select_for_update`).
- Creación de `Atencion` y `resolve_tipo_intervencion_from_recurso`.
- Auditoría `log_create`.
- Decisiones **201 vs 200** según `created_new`.

La vista conserva únicamente:

- Validación HTTP mínima: presencia de `turno`.
- Traducción de `BusinessLogicError` → **400** `{"error": …}`.
- Serialización DRF (`AtencionSerializer`) y mapping de status.

---

## Side effects explícitos (modo API POST)

| Entidad | Efecto |
|---------|--------|
| **`Turno`** | Solo lectura + bloqueo; estado **no** cambia |
| **`Atencion`** | INSERT si no existía; caso idempotente ningún write |
| **`ConsultaAmbulatoria` / otros hijos** | No |
| **`AuditEvent`** | INSERT en alta nueva (`CREATE`), misma infraestructura anterior |

---

## Side effects (modo orquestación completa, sin cambio previsto)

Igual que antes del refactor: REALIZADO en turno, alta `Atencion`, `_crear_registro_hijo` dentro del mismo `atomic`; **sin** auditoría añadida ahí (igual que antes del cambio).

---

## Transacciones

- **Antes (API path):** ningún `atomic` explícito.
- **Después:** un solo `transaction.atomic` por request de creación REST, evitando dispersión y permitiendo que la auditoría uses `on_commit` de forma coherente con el commit de `Atencion`.

---

## Riesgos conocidos

| Riesgo | Nota |
|--------|------|
| **Doble implementación de ViewSets en `api/views`** | Persiste; este cambio no la elimina. |
| **Idempotencia concurrente** | Sigue existiendo ventana entre comprobación e insert; el `OneToOne` en BD evita duplicados duros (posible `IntegrityError` en carrera, como antes en teoría). |

---

## Ventajas obtenidas

- Un solo lugar de verdad para alta de atención desde turno en cada modo (`api_post_compat` explícito).
- Transacción y auditoría alineadas sin lógica duplicada en la vista.
- View fina: HTTP + serialización únicamente.

---

## Archivos tocados (resumen)

- `turnos/services.py` — `IniciarAtencionOutcome`, `_iniciar_desde_turno_api_post`, refactor de `iniciar_atencion_desde_turno`.
- `turnos/views.py` — `AtencionViewSet.create`.
- `api/views.py` — uso de `outcome.atencion` y `turno.refresh_from_db()` en `iniciar_atencion`.
- `turnos/tests/test_services.py`, `turnos/tests/test_atencion_viewset.py` — cobertura nueva y ajustes `.atencion`.
