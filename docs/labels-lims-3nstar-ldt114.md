# Etiquetas físicas LIMS — 3nStar LDT114 (40 × 23 mm)

## Estrategia de sizing ZPL (sin validación física aún)

Modelo conservador de ancho:

```text
MAX_CONTENT_WIDTH_DOTS = 320 − 2×12 = 296
estimated_width = len(texto) × w   # ^A0N,h,w
requerido: estimated_width ≤ 296
```

- Línea 1 (`codigo_barra`): **nunca se trunca**; se elige el mayor `w` ≤ preferido que cumpla la desigualdad.
- Línea 2 (paciente): **apellido completo siempre** (nunca se trunca). Si no cabe, se omite la inicial del nombre y se baja `w`; DNI íntegro.
- Líneas 3–4: se acorta primero el fragmento abreviable (lugar / tipo; no DNI ni fecha), luego se maximiza `w`.
- Márgenes: `MARGIN_X=12`, apilado vertical con `MARGIN_Y` + gaps dentro de `LL=184`.

Ejemplo `00458127` (8): `w=28` → 224 ≤ 296.
Ejemplo `LAB-2026-00001-01` (17): `w=17` → 289 ≤ 296.
`PEREZ J. | DNI 23123456` (25): `w=11` → 275 ≤ 296.

## Hardware objetivo

| Ítem | Valor |
|------|--------|
| Impresora | 3nStar LDT114 |
| Conexión | USB en la PC del operador (no en el servidor EMR) |
| Lenguaje | ZPL |
| Resolución | 203 dpi |
| Etiqueta | 40 × 23 mm |
| Perfil software | `3nstar_ldt114_203_40x23` (320 × 184 dots) |

## Cómo imprime (agente local)

El servidor **no** habla con la impresora. El navegador pide el ZPL al EMR y lo manda a un agente en `http://127.0.0.1:18181` que corre **solo en la PC donde está el USB**.

- PC con agente + impresora USB instalada → imprime ahí.
- PC sin agente o sin impresora → el botón se ve igual; al imprimir: *En esta PC no hay agente de impresión…* o *No se encontró impresora de etiquetas en esta PC.*

Scripts:

- **Una vez en LABORATORIO:** `scripts/label_print_agent_instalar.bat` — registra una tarea de Windows y arranca el agente **oculto**. Desde entonces se inicia solo al iniciar sesión; el operador no toca ningún `.bat`.
- Diagnóstico (ventana visible): `scripts/label_print_agent.bat`.
- Quitar: `scripts/label_print_agent_desinstalar.bat`.

### Instalar en LABORATORIO (una vez)

1. Instalar rollo 40 × 23 mm y driver Windows de la 3nStar (emulación ZPL).
2. Calibrar sensor gap/black mark según consumible.
3. Confirmar que Windows ve la impresora (nombre con `3nStar`, `LDT114` o `ZDesigner`). Si el nombre es otro, copiar `scripts/label_print_agent.config.json.example` a `label_print_agent.config.json` (mismo directorio) y poner `printerName`.
4. Copiar la carpeta `scripts` del agente a esa PC (p. ej. `C:\EMR\label_print_agent\`: `.ps1`, `.bat`, opcional `.config.json`).
5. Ejecutar **`label_print_agent_instalar.bat` una sola vez** (usuario de LABORATORIO). Debe aparecer un aviso de que ya está corriendo. No hace falta dejar ninguna ventana abierta.
6. En el servidor EMR, `LIMS_LABEL_PRINTER_ENABLED` puede quedar `false` (ya no se usa HOST:9100 para el botón).
7. Desde el navegador **en esa misma PC**, abrir el EMR (`http://192.168.10.240` o el puerto que usen) e imprimir una etiqueta de prueba.
8. Verificar dimensiones, márgenes, Ñ/tildes, apellido largo, CAMA/GUARDIA.
9. Si no imprime: ver `label_print_agent.log` en la misma carpeta, o correr `label_print_agent.bat` (ventana visible).
10. Reimprimir y confirmar un segundo `AuditEvent` (`muestra_etiqueta_print`, `transport=local_agent`).

Si hay otra PC con su propia etiquetadora USB, repetir 1–5 ahí. No hace falta tocar el servidor.

## Endpoints

- `GET /api/lab/muestras-transaccionales/{id}/etiqueta/` — PDF legacy (tubo Code128); **sin cambios**.
- `GET /api/lab/muestras-transaccionales/{id}/etiqueta-zpl/` — vista previa JSON + ZPL 40×23 (PHI).
- `POST /api/lab/muestras-transaccionales/{id}/imprimir-etiqueta/` — prepara snapshot lugar/fecha y **devuelve ZPL** (no envía a impresora; no muta FSM).
- `POST /api/lab/muestras-transaccionales/{id}/imprimir-etiqueta/confirmar/` — auditoría de impresión local OK.
- `GET /api/lab/solicitudes/{id}/etiqueta/` — ZPL simulado a nivel solicitud (**legacy**, no tocar).

Permisos ZPL/impresión: `admin`, `laboratorio`, `bioquimico`, `superuser`. No médico/secretaría/enfermería/paciente.

## Identidad y datos

- Código impreso = `Muestra.codigo_barra` (SoT; autogenerado si vacío).
- **Imprimir no es tomar ni recibir:** la muestra sigue `PENDIENTE_TOMA` y la orden `PENDIENTE` («Esperando recepción»). No hay `aplicar_tomar` ni transición a `EN_PROCESO`.
- Lugar: snapshot `lugar_extraccion` si ya existe; si no, se resuelve desde origen/procedencia de la solicitud al preview/print (sin FSM).
- Fecha: snapshot `fecha_toma` si ya existe; si no, preview usa `now()` solo en el payload; al **preparar impresión** se persiste `fecha_toma=now` sin cambiar `estado`.
- Tipo línea 4 = aditivo/código de `TipoContenedor` (p.ej. EDTA); fallback `TipoMuestra.codigo`.
- Validar orden: bloqueado mientras existan tubos `PENDIENTE_TOMA`/`TOMADA`. Cancelar/rechazar
  los no recepcionados y tener cargados los resultados de los tubos recibidos habilita validar.
  Cargar resultados del tubo ya `RECIBIDA` está permitido aunque queden otros pendientes.

## Variables de entorno (legado, no usadas por el botón)

El transporte TCP `LIMS_LABEL_PRINTER_HOST:9100` quedó fuera del flujo del botón (impresora USB local). Las variables pueden existir en `.env` sin efecto:

```bash
LIMS_LABEL_PRINTER_ENABLED=false
LIMS_LABEL_PRINTER_HOST=
LIMS_LABEL_PRINTER_PORT=9100
LIMS_LABEL_PRINTER_TIMEOUT_SECONDS=5
LIMS_LABEL_PRINTER_PROFILE=3nstar_ldt114_203_40x23
```
