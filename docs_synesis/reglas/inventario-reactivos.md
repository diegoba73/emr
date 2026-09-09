# Reglas — Inventario (reactivos vs insumos)

**Versión:** sep 2026  
**SoT:** `laboratorio/models_inventario.py`, `laboratorio/inventario_service.py`, UI `/laboratorio/inventario`.

---

## Dos familias distintas

| | **Reactivos** | **Insumos** |
|---|----------------|-------------|
| Qué son | Kits / cartuchos / diluyentes de determinaciones | Tubos, medios de cultivo, otros |
| Tipo en BD | `InsumoLab.tipo = REACTIVO` | `TUBO`, `MEDIO`, `OTRO` |
| Cuándo baja el stock | Al **cargar el primer valor** del ensayo (si hay vínculo) | Toma de muestra / siembra (hooks previos) |
| Pantalla | Pestaña Reactivos + Consumo por ensayo | Pestaña Insumos |

En código el modelo sigue llamándose `InsumoLab` (histórico); en la UI se habla de **reactivo** vs **insumo** según el tipo.

---

## Presentación

- **Unidad** (`unidad`): en qué contás el stock — `cartucho`, `ml`, `test`, `pack`.
- **ml / envase** (`volumen_por_unidad`): volumen de cada cartucho o pack (dato del producto; no es otra unidad de stock).
- Contenido (solo A / A+B) y línea (dedicada / abierta): visibles en el alta, no ocultos.

Al cargar un lote ingresás la cantidad **en esa unidad** (ej. 10 cartuchos, o 500 ml).

---

## Consumo por ensayo (antes “receta”)

No es una fórmula química. Es la pregunta: **“cuando cargo este ensayo, ¿de qué reactivo resto stock y cuánto?”**

- 0 vínculos → no descuenta.
- 1 vínculo típico (un cartucho).
- N vínculos si hay varios envases físicos distintos (ej. diluyente + lisante).

Tabla `ConsumoInsumoExamen`: ensayo → reactivo + cantidad por determinación.

---

## Contenido y línea

`composicion` (solo A / A+B) y `canal_analizador` (dedicada / abierta) van en el formulario de alta, siempre visibles. No son exclusivos de un solo equipo.

---

## Cuándo descuenta (reactivos)

| Acción | ¿Descuenta reactivo? |
|--------|----------------------|
| Primera carga de valor (vacío → valor) | Sí, según vínculos |
| Edición posterior del mismo resultado | No |
| Validar / FINALIZADO | No |

Soft si falta stock (`LAB_INVENTARIO_STRICT` puede endurecer). FEFO por vencimiento de lote.

---

## Pedidos / alertas

`GET …/insumos/alertas/` → `bajo_minimo`, `por_vencer`, `pedidos` (la UI separa reactivos vs insumos).

---

## Editar / eliminar (catálogo)

Reactivos, insumos, lotes y vínculos de consumo se editan/eliminan en la UI. Si DELETE falla por movimientos u otras FK (`409 PROTECTED`), se ofrece **desactivar** (`activo=false`). Los **movimientos** son historial: solo lectura.
