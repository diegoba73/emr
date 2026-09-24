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

El EMR **sigue generando ZPL 40 × 23**. En la PC LABORATORIO el agente lo convierte a **TSPL** para la 4BARCODE.

| Ítem | Valor |
|------|--------|
| Impresora en LABORATORIO | 4BARCODE (TSPL); también matchea `4B-2054` / `EMR ZPL RAW` |
| Conexión | USB en la PC del operador (no en el servidor EMR) |
| Lenguaje en el agente | `tspl` (convierte el ZPL del EMR) |
| Perfil software (ZPL) | `3nstar_ldt114_203_40x23` (320 × 184 dots, 203 dpi, 40 × 23 mm) |

Otras PCs con USB propio: el agente también reconoce `3nStar` / `LDT114` / `ZDesigner`. Si el nombre de Windows es otro, fijarlo en `label_print_agent.config.json` (`printerName`).

## Cómo imprime (agente local)

El servidor **no** habla con la impresora. El navegador pide el ZPL al EMR y lo manda a un agente en `http://127.0.0.1:18181` que corre **solo en la PC donde está el USB**.

- PC con agente + impresora USB instalada → imprime ahí.
- PC sin agente o sin impresora → el botón se ve igual; al imprimir: *En esta PC no hay agente de impresión…* o *No se encontró impresora de etiquetas en esta PC.*

Scripts:

- **Una vez en LABORATORIO:** `scripts/label_print_agent_instalar.bat` — registra una tarea de Windows y arranca el agente **oculto**. Desde entonces se inicia solo al iniciar sesión; el operador no toca ningún `.bat`.
- **Tras copiar archivos nuevos:** `scripts/label_print_agent_reparar.bat` — mata el listener viejo en 18181, reescribe config TSPL y hace selftest. Si solo se corre `label_print_agent.bat` con el puerto ocupado, el `.ps1` sale con código 0 y **no** actualiza el agente.
- Diagnóstico (ventana visible): `scripts/label_print_agent.bat`.
- Quitar: `scripts/label_print_agent_desinstalar.bat`.

CORS del agente: el origen de la pestaña del navegador tiene que coincidir (p. ej. `http://192.168.10.240`, `http://emr.sytes.net:8080`, `http://dsachubut.sytes.net:8080`). Si usan otra URL, agregarla a `allowedOrigins` en `label_print_agent.config.json`.

### Copiar a LABORATORIO (obligatorio, misma carpeta)

Ejemplo: `C:\EMR\label_print_agent\`

| Archivo | Rol |
|---------|-----|
| `label_print_agent.ps1` | Agente (TSPL + CORS) |
| `EmrRawPrinter.cs` | RAW Win32; **sin este archivo el agente no arranca** |
| `label_print_agent.bat` | Arranque visible |
| `label_print_agent_reparar.bat` + `.ps1` | Recarga tras actualizar archivos |
| `label_print_agent_instalar.bat` + `label_print_agent_install.ps1` | Tarea al iniciar sesión (primera vez) |
| `label_print_agent.config.json.example` | Plantilla (`language: tspl`) |

### Instalar en LABORATORIO (una vez)

1. Instalar rollo 40 × 23 mm y driver Windows de la 4BARCODE (TSPL / Generic Text RAW si usan `EMR ZPL RAW`).
2. Calibrar sensor gap/black mark según consumible.
3. Confirmar que Windows ve la impresora (`4BARCODE`, `4B-2054` o `EMR ZPL RAW`). Si el nombre es otro, copiar `label_print_agent.config.json.example` a `label_print_agent.config.json` (mismo directorio) y poner `printerName`.
4. Copiar los archivos de la tabla anterior a esa PC.
5. Ejecutar **`label_print_agent_instalar.bat` una sola vez** (usuario de LABORATORIO). Debe aparecer un aviso de que ya está corriendo. No hace falta dejar ninguna ventana abierta.
6. En el servidor EMR, `LIMS_LABEL_PRINTER_ENABLED` puede quedar `false` (ya no se usa HOST:9100 para el botón).
7. Desde el navegador **en esa misma PC**, abrir el EMR (`http://192.168.10.240` o `http://dsachubut.sytes.net:8080`) e imprimir una etiqueta de prueba.
8. Verificar dimensiones, márgenes, Ñ/tildes, apellido largo, CAMA/GUARDIA.
9. Si no imprime: ver `label_print_agent.log` en la misma carpeta, o correr `label_print_agent_reparar.bat`.
10. Reimprimir y confirmar un segundo `AuditEvent` (`muestra_etiqueta_print`, `transport=local_agent`).

Si hay otra PC con su propia etiquetadora USB, repetir 1–5 ahí. No hace falta tocar el servidor.

### Actualizar el agente ya instalado

1. Copiar encima `label_print_agent.ps1`, `EmrRawPrinter.cs`, `label_print_agent.bat` y los `*_reparar.*`.
2. Ejecutar **`label_print_agent_reparar.bat`** (no basta el `.bat` de arranque si 18181 ya está ocupado).
3. Tiene que salir selftest + etiqueta de muestra `LAB-2026-00018-01`.

## Endpoints

- `GET /api/lab/muestras-transaccionales/{id}/etiqueta/` — PDF legacy (tubo Code128); **sin cambios**.
- `GET /api/lab/muestras-transaccionales/{id}/etiqueta-zpl/` — vista previa JSON + ZPL 40×23 (PHI).
- `POST /api/lab/muestras-transaccionales/{id}/imprimir-etiqueta/` — prepara snapshot lugar/fecha y **devuelve ZPL** (no envía a impresora; no muta FSM).
- `POST /api/lab/muestras-transaccionales/{id}/imprimir-etiqueta/confirmar/` — auditoría de impresión local OK.
- `GET /api/lab/solicitudes/{id}/etiqueta/` — ZPL simulado a nivel solicitud (**legacy**, no tocar).
- `GET /api/lab/microbiologia/estudios/{id}/etiqueta-zpl/` — misma geometría; preview sin mutar.
- `POST /api/lab/microbiologia/estudios/{id}/imprimir-etiqueta/` — asigna barcode/`etiquetas_impresas_at` (PENDIENTE) y devuelve ZPL.
- `POST /api/lab/microbiologia/estudios/{id}/imprimir-etiqueta/confirmar/` — auditoría `micro_etiqueta_print`.

Permisos ZPL/impresión: `admin`, `laboratorio`, `bioquimico`, `superuser`. No médico/secretaría/enfermería/paciente.

## Identidad y datos

- Código impreso = `Muestra.codigo_barra` (SoT; autogenerado si vacío).
- Pistola HID con teclado Windows en español: el frontend convierte `'` / `´` / `` ` `` a `-` (`normalizeBarcodeScan`) para que `LAB-2026-…` coincida con el código de la muestra.
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
