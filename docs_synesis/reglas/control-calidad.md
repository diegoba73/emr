# Reglas — Control de calidad interno (IQC)

**Versión:** sep 2026  
**SoT:** `laboratorio/qc_service.py`, `laboratorio/qc_tablero.py`, `laboratorio/equipos_lab.py`, `laboratorio/views_qc.py`, `laboratorio/qc_westgard.py`, UI `frontend/src/pages/laboratorio/qc/`.

Este recorte complementa `DOC_REGLAS_NEGOCIO.md`. Si hay conflicto, gana el código citado.

---

## Propósito

Habilitar la **carga de resultados** y la **liberación clínica** de una orden solo si el control interno del día está **ACEPTADO** para los equipos/ensayos **de esa orden**.

No es EQC, no es CAPA, no es ISO 15189 completo. Es el ciclo: registrar control → aceptar/rechazar → desbloquear analítica.

---

## Dónde aplica el gate

| Acción | ¿IQC? | Override |
|--------|-------|----------|
| Toma / recepción de muestra | No | — |
| `POST …/cargar-resultados/` | Sí | **No** (`permitir_override=False`) |
| `POST …/validar/` (cierre `FINALIZADO`) | Sí | Solo **admin/superuser** + `confirmar_qc_override` + `motivo_qc_override` |

Ventana temporal: **hoy** en `America/Argentina/Buenos_Aires` (`timezone.localdate()`), de 00:00 a 24:00. Un control de ayer no vale. Un rechazo de hoy anula si es la **última** corrida del nivel; un ACEPTADA posterior el mismo día **sí** vale.

---

## Modelo híbrido (dos modos)

Fuente de equipos: `laboratorio/equipos_lab.py`.

### Multiparámetro (`EQUIPOS_MULTIPARAM`)

Equipos: **CM260**, **SYSMEX_XP300** (en prod el código físico suele ser **`HEMO`**), **COATRON**, **ERBA_EC90** (reemplaza al Diestro; alias `DIESTRO`/`EC90`), **EDAN_I15**.

Producto de control (Standatrol, control Sysmex, etc.) con lote y **targets** por ensayo/nivel.

**Regla de liberación:** última corrida de **hoy** en **S1 y S2** (`N1`/`N2`) del producto, en **ese equipo**, estado **`ACEPTADA`**.

Eso desbloquea **todos** los ensayos de la orden que el producto cubre (lista canónica `EXAMENES_POR_EQUIPO` **o** target en el lote). No hace falta un control por glucosa, urea, etc.

Un examen entra al modo multiparam solo si:

1. Tiene `TipoExamen.equipo_analizador` activo, y
2. Ese equipo es multiparam, y
3. Existe `ProductoControl` activo `MULTIPARAM` en ese equipo, y
4. El código está en la lista del equipo **o** hay `TargetLoteControl` en un lote activo del producto.

Si falta el mapeo de equipo en el catálogo, el ensayo **no** entra a este modo (cae a material por ensayo o a “no aplicable”).

### Por ensayo (`EQUIPOS_POR_ENSAYO`)

Equipos: **VIDAS_KUBE**, **FINECARE**.

**Regla:** para cada ensayo **presente en la orden**, material canónico activo **con `equipo` seteado**, niveles S1/S2: última corrida de hoy **ACEPTADA** en ese equipo.

- TSH **no** se exige si la orden no incluye TSH.
- Finecare (HBA1C, D-dímero, etc.) igual: solo lo pedido.
- Materiales inactivos o **sin equipo** se ignoran (`materiales_iqc_canonicos`). Evita spam de duplicados huérfanos (caso HBA1C 40/41/42).

### No aplicable

Si la orden no tiene ningún producto multiparam que cubra sus ensayos **ni** materiales canónicos, el gate devuelve `aplicable=False`, `ok=True`, `sin_configuracion=True`: **no bloquea** la carga. **No es control satisfactorio**: la UI debe etiquetar “Sin IQC” / “IQC no configurado” (nunca “IQC OK”). Hay que mapear el examen al analizador y cargar materiales/productos reales.

---

## Corridas: qué cuenta y qué no

- **Última del día** por (producto+equipo+nivel) o (material+equipo).
- Corrida **sin `equipo`:** no cuenta (mensaje: “use {codigo}”).
- Alias de código (`codigo_equipo_canonico`): `HEMO` / `SYSMEX` / `XP300` → `SYSMEX_XP300`; `VIDAS` → `VIDAS_KUBE`; `FINECARE` se normaliza a mayúsculas; `DIESTRO` / `EC90` → `ERBA_EC90`.
- **Control OK (operativo):** modo `ACEPTAR_NIVEL` (default en UI) o `VALORES` que Westgard no marca fuera de control.
- **No OK:** `RECHAZAR_NIVEL` o evaluación Westgard `fuera_control` → corrida `RECHAZADA`.
- **Calibración** (`Calibracion`): se muestra en el tablero Hoy; **no** desbloquea el gate ni lo invalida. Después de calibrar hay que **repetir el control** y dejarlo ACEPTADA.

---

## Westgard (modo VALORES)

Motor: `laboratorio/qc_westgard.py`.

| Regla | Efecto |
|-------|--------|
| `1-3s` | Fuera de control |
| `1-2s` | Warning (no rechaza solo) |
| `2-2s` | Fuera de control |
| `R-4s` | Fuera de control |
| `4-1s` | Fuera de control |
| `10-x` | Fuera de control |
| `SD_CERO` | Fuera de control |

Historial para reglas multi-punto: **omite** puntos `fuera_control` y corridas `RECHAZADA`. Un re-run en rango después de un rechazo **no** hereda R-4s del punto descartado.

El vencimiento de lote **no** se exige al cargar ni al liberar.

---

## Tablero Hoy vs gate

- UI: `/laboratorio/qc` (día) + **Catálogo / lotes** (configuración).
- API: `GET /api/lab/qc/tablero-hoy/` (`laboratorio/qc_tablero.py`).
- Multiparam: semáforo del **aparato** (S1+S2) y lista de ensayos cubiertos vs pedidos.
- Por ensayo: **una fila visual por ensayo** (S1/S2), no un combo de catálogo.
- Si Finecare/VIDAS **no tiene pedidos** en órdenes abiertas (curso + PENDIENTE últimos 14 días), el tablero puede mostrar **todos** los materiales del equipo. El **gate de una orden concreta no usa esa lista completa**: solo los exámenes de esa solicitud.
- **Lunes y viernes (TZ local):** aviso `aviso_valores` si falta corrida ACEPTADA **con puntos** (modo VALORES) en S1/S2. Aplica a **CM260, Sysmex, Coatron y ERBA EC90**. Es recordatorio: **no** bloquea el OK rápido (`ACEPTAR_NIVEL`) ni el gate de liberación.
- **Valores a demanda** (`EQUIPOS_VALORES_A_DEMANDA`): **VIDAS_KUBE** (control con el calibrador), **FINECARE** y **EDAN_I15**. No hay aviso lun/vie. Se cargan números al calibrar, vencer o cambiar lote. El gate sigue pidiendo S1+S2 **ACEPTADA hoy** (el OK rápido alcanza). El tablero marca `politica_valores=A_DEMANDA`.
- **Catálogo editable** en UI (equipos, productos, lotes, materiales, calibraciones): editar/eliminar; si DELETE falla por FK, se ofrece desactivar. **Corridas** (y puntos) son historial: solo alta, sin editar/borrar en pantalla.

---

## Setup de catálogo (obligatorio para que el gate y la UI funcionen)

1. `EquipoAnalizador` con código canónico (o alias conocido).
2. Cada `TipoExamen` analítico con `equipo_analizador` apuntando a ese equipo. Sin esto, la grilla “guardar targets” queda **vacía** (filtra por equipo del producto) y el save falla.
3. Producto MULTIPARAM + lote + targets (media/DE) por ensayo y nivel, **o** materiales por ensayo con equipo.
4. No mezclar materiales duplicados sin equipo: desactivar huérfanos.

**Producción:** no correr `manage.py seed_qc_demo`. Crea lotes `QC-DEMO` y desactiva materiales multiparam que no correspondan al seed.

---

## Permisos QC

Escritura de catálogo, corridas y tablero: operadores LIMS (`laboratorio`, `bioquimico`) + admin. Misma familia `ROLES_LIMS_WRITE`.

Override del gate de **cierre:** solo admin/superuser.

---

## Explicitamente fuera de alcance (pedido ISO no cableado)

Un control ACEPTADO **no** se invalida automáticamente por:

- cambio de lote de reactivo;
- calibración (solo registro);
- mantenimiento, falla, alarma, reinicio;
- tope de tiempo o de número de muestras de la serie;
- cierre manual de serie.

Esas reglas se documentaron como objetivo de especialista; **el código actual no las implementa**. La vigencia es “ACEPTADA hoy en el equipo correcto”.
