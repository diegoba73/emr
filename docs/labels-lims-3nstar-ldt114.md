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
| Lenguaje | ZPL |
| Resolución | 203 dpi |
| Etiqueta | 40 × 23 mm |
| Perfil software | `3nstar_ldt114_203_40x23` (320 × 184 dots) |

## Endpoints

- `GET /api/lab/muestras-transaccionales/{id}/etiqueta/` — PDF legacy (tubo Code128); **sin cambios**.
- `GET /api/lab/muestras-transaccionales/{id}/etiqueta-zpl/` — vista previa JSON + ZPL 40×23 (PHI).
- `POST /api/lab/muestras-transaccionales/{id}/imprimir-etiqueta/` — envío a impresora de red.
- `GET /api/lab/solicitudes/{id}/etiqueta/` — ZPL simulado a nivel solicitud (**legacy**, no tocar).

Permisos ZPL/impresión: `admin`, `laboratorio`, `bioquimico`, `superuser`. No médico/secretaría/enfermería/paciente.

## Identidad y datos

- Código impreso = `Muestra.codigo_barra` (SoT; autogenerado si vacío).
- **Imprimir no es tomar ni recibir:** la muestra sigue `PENDIENTE_TOMA` y la orden `PENDIENTE` («Esperando recepción»). No hay `aplicar_tomar` ni transición a `EN_PROCESO`.
- Lugar: snapshot `lugar_extraccion` si ya existe; si no, se resuelve desde origen/procedencia de la solicitud al preview/print (sin FSM).
- Fecha: snapshot `fecha_toma` si ya existe; si no, preview usa `now()` solo en el payload; al **imprimir** se persiste `fecha_toma=now` sin cambiar `estado`.
- Tipo línea 4 = aditivo/código de `TipoContenedor` (p.ej. EDTA); fallback `TipoMuestra.codigo`.
- Validar orden: bloqueado mientras existan tubos `PENDIENTE_TOMA`/`TOMADA`. Cancelar/rechazar
  los no recepcionados y tener cargados los resultados de los tubos recibidos habilita validar.
  Cargar resultados del tubo ya `RECIBIDA` está permitido aunque queden otros pendientes.

## Variables de entorno

```bash
LIMS_LABEL_PRINTER_ENABLED=false
LIMS_LABEL_PRINTER_HOST=
LIMS_LABEL_PRINTER_PORT=9100
LIMS_LABEL_PRINTER_TIMEOUT_SECONDS=5
LIMS_LABEL_PRINTER_PROFILE=3nstar_ldt114_203_40x23
```

Sin auto-retry: un timeout puede significar que la etiqueta ya salió; el operador decide reimprimir (otra auditoría).

## Checklist al recibir la 3nStar LDT114

1. Instalar rollo 40 × 23 mm.
2. Calibrar sensor gap/black mark según consumible.
3. Confirmar modo/emulación ZPL.
4. Conectar por Ethernet.
5. Asignar IP según política de infraestructura.
6. Configurar HOST/PORT en el servidor SYNESIS.
7. Mantener `ENABLED=false`.
8. Generar preview de una muestra de prueba sin PHI real.
9. Activar `ENABLED=true`.
10. Imprimir etiqueta de prueba.
11. Verificar dimensiones físicas.
12. Verificar márgenes.
13. Verificar caracteres Ñ/tildes.
14. Verificar lectura visual.
15. Probar apellido largo.
16. Probar CAMA / GUARDIA.
17. Desconectar impresora y confirmar fallo seguro sin retry.
18. Reimprimir manualmente y confirmar segundo `AuditEvent`.
19. Confirmar que ninguna PHI/ZPL apareció en logs.
