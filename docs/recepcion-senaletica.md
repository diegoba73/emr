# Señalética física — recepción y destinos

Los carteles del edificio deben usar **exactamente** los mismos nombres que el sistema.

## Puestos de recepción

Configuración: menú **Recepción (config)** → campo **Etiqueta paciente**.

| Código seed | Etiqueta sugerida en cartel |
|-------------|-----------------------------|
| `puesto-1`  | Puesto 1 (adelante) |
| `puesto-2`  | Puesto 2 (atrás) |
| `sala-extraccion` | Sala de extracción (cola L; solo laboratorio) |

Los puestos de secretaría son **geografía**, no especialidad fija. Qué atiende cada ventanilla
(T/S/E/P) lo define la **cobertura del día** en `/recepcion` (cada secretaria elige puesto + tipos).

Si el admin cambia la etiqueta en el sistema, hay que actualizar el cartel el mismo día.

## Destinos clínicos (después del puesto)

Usar el campo **nombre** del recurso (`Recursos` en administración):

- Consultorios: mismo texto que `Recurso.nombre` (ej. «Consultorio 1»).
- Salas de estudio / procedimiento / hemodinamia.
- Quirófanos.
- **Extracciones / toma de muestra** (`tipo_recurso=EXTRACCIONES`).

La TV (`/pantalla-sala`) y el push al llamar muestran ese destino.

## Pantallas digitales

| URL | Uso |
|-----|-----|
| `/recepcion` | Tablero: secretaría (T/S/E/P) o laboratorio (L) o médico |
| `/recepcion/qr-anuncio` | Imprimir QR fijo de anuncio (cartel pared) |
| `/medico/cola` | Redirige a `/recepcion` |
| `/recepcion/config` | Admin: puestos y reglas |
| `/pantalla-sala` | TV sala: **2 mitades** (Recepción \| Médico) |
| `/kiosco-recepcion` | QR papel (URL **pública** del EMR): solo **puesto 1** o **sala de extracción** |
| `/espera/:token` | Opcional / legacy (ya no se pide un segundo QR tras anunciarse) |

## Flujo operativo

1. **Sin app (QR papel):** paciente escanea y elige solo:
   - Recepción / secretaría (**puesto 1**)
   - Sala de extracción / laboratorio
2. **Con app:** puede reservar consulta/estudio; **Estoy en sala** (turno de hoy) o **Anunciarme al laboratorio**.
3. Queda en cola de **recepción** o **laboratorio** con su código (ej. `S02`, `T03`, `L01`).
4. **L**: el usuario **laboratorio** llama y cierra (no secretaría).
5. **T/S/E/P**: cada secretaria configura su **cobertura** (puesto físico + tipos) y llama; el
   destino en TV es su puesto. Si está OK admin, **Check-in médico** → cola del médico.
6. El **médico** llama (T/E/P): push en la app + mitad derecha de la TV hasta «Ya voy» o **En atención**.

El anuncio (QR o app) **no** es el check-in al médico.

### Confirmación de turnos (app)

- Reserva para **hoy o mañana** → nace `CONFIRMADO`.
- Reserva a **más de 1 día** → nace `RESERVADO`; el paciente confirma desde la app (push).
- Cerca del día (~24 hs) → push de **asistencia** (`asistencia_confirmada_en`).

Guía de prueba local: [`recepcion-flujo-medico-local.md`](recepcion-flujo-medico-local.md).  
LAN: [`recepcion-lan.md`](recepcion-lan.md).
