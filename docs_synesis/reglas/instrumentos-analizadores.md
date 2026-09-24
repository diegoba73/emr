# Reglas — Interfaz de analizadores (CM260 / Sysmex XP-300)

**Versión:** sep 2026  
**SoT:** `laboratorio/instrumentos_service.py`, `laboratorio/instrumentos_astm.py`, `laboratorio/views_instrumentos.py`, `laboratorio/resultado_carga.py`.

Complementa `DOC_FLUJOS_LIMS.md`. Si hay conflicto, gana el código citado.

## Propósito

Hablar en ASTM con el autoanalizador de química **CM260** y el hemograma **Sysmex XP-300**:

1. El equipo pregunta qué ensayos correr (worklist / Host Query).
2. El LIMS responde solo lo pendiente de ese tubo y ese equipo.
3. Los resultados entran como **borrador** por el mismo camino que `cargar-resultados`.
4. El bioquímico **valida** en la UI actual. Nunca se auto-informa ni se pasa a `FINALIZADO`.

## Arquitectura

- Django expone HTTP: `POST /api/lab/instrumentos/consulta-trabajo/`, `POST /api/lab/instrumentos/ingesta/`.
- El **gateway ASTM** (`manage.py run_instrument_gateway`) vive fuera de gunicorn. TCP por defecto. RS-232 solo en un PC al lado del equipo (`pyserial`), no dentro de Docker.
- Token de servicio: header `X-LIMS-Instrument-Token` (`LIMS_INSTRUMENT_TOKEN`). No `AllowAny`.
- Flag `LIMS_INSTRUMENT_ENABLED=false` hasta la prueba en sitio.

## Matching de tubo

Etiqueta impresa: `LAB-YYYY-XXXXX-nn` (`Muestra.codigo_barra`).  
Alias compacto: `YYYY` + secuencia 5 dígitos + tubo 2 dígitos (ej. `20260004201`) en `Muestra.codigo_instrumento`, para sample ID corto del XP-300.

La consulta acepta código completo o compacto.

## IQC

Sin control ACEPTADO de hoy para el equipo de la interfaz:

- Worklist vacío (`IQC_BLOQUEADO`).
- Ingesta rechazada (mismo gate que `cargar-resultados`, sin override).

## Mapeo de analitos

Tabla `MapeoAnalitoInstrumento` por interfaz. Semilla: `manage.py seed_instrumentos`.

- Sysmex XP-300 es fórmula de **3 partes** (LYM / MXD / NEUT). **MXD no se mapea a `MONO`** (ni a EOS/BAS): la mezcla de células intermedias no es monocitos. Códigos `MXD` / `MXD%` / `MXD#` se omiten en el catálogo y se desactivan en seed si existía el legado. `NEUT_CAY` no sale del equipo.
- CM260: códigos de canal Wiener (`CRE` → `CREATI`, `URE` → `UREA`, etc.) editables.

Un analito que no está pedido en la orden **no crea** `ResultadoExamen`.

## Valores

Los números ASTM son **clínicos**. No aplicar `TICKET_ENTERO` (eso es tipeo del ticket impreso).

## Auditoría

`MensajeInstrumento` guarda crudo truncado. `AuditEvent` solo ids técnicos, `estado`, `sample_id_presente`; **sin** valores clínicos ni PHI.

## Simulador

```bash
python manage.py seed_instrumentos
python manage.py simular_instrumento --driver CM260 --sample-id LAB-2026-00001-01 --mode json
```

Hasta tener una traza ASTM real del puerto, el simulador es la prueba de regresión.
