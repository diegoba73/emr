# Flujo recepción → médico → TV + app (prueba local)

## Flujo acordado

1. **QR papel:** paciente elige solo recepción (**puesto 1**) o sala de extracción → DNI/apellido → código. Sin «ya tengo turno» en el QR.
2. **App:** **Estoy en sala** (turno consulta/estudio de hoy) o **Anunciarme al laboratorio**.
3. Queda en **cola de recepción** o laboratorio (TV / área correspondiente).
4. **L**: usuario laboratorio en `/recepcion` → **Llamar** / Atendido.
5. **T/S/E/P**: secretaría en `/recepcion` gestiona; con turno y OK admin → **Pasar a médico** (pasa a cola del médico).
6. Médico: **Llamar** (app + TV mitad derecha) → paciente **Ya voy** o médico **En atención** (abre consulta). Al guardar la consulta → **Atendido**.

## Web — producción CEHTA / ICPL (mismo EMR)

| Rol | URL |
|-----|-----|
| Secretaría / Lab / Médico | https://emr.icpueblodeluis.com.ar:8080/recepcion |
| QR imprimible | https://emr.icpueblodeluis.com.ar:8080/recepcion/qr-anuncio |
| Anuncio QR (puesto 1 / lab) | https://emr.icpueblodeluis.com.ar:8080/kiosco-recepcion |
| TV | https://emr.icpueblodeluis.com.ar:8080/pantalla-sala |

Requiere `PUBLIC_API_BASE_URL=https://emr.icpueblodeluis.com.ar:8080` en el servidor.

## Web — solo desarrollo local

| Rol | URL |
|-----|-----|
| Secretaría / Lab / Médico | http://192.168.x.x:3000/recepcion |
| Anuncio QR | http://192.168.x.x:3000/kiosco-recepcion |

(Ver `docs/recepcion-lan.md`. No usar IP LAN en el cartel de CEHTA.)

## App móvil local

En `mobile/.env`:

```env
EXPO_PUBLIC_ALLOW_LOCAL_HTTP=true
EXPO_PUBLIC_API_URL=http://192.168.1.56:8000/api/movil
```

(Actualizá la IP si cambió la de Windows: `ipconfig` / Wi‑Fi.)

Paciente logueado:

- **Estoy en sala** si tiene turno de consulta/estudio hoy → cola recepción.
- **Anunciarme al laboratorio** → cola extracción.
- Turnos a más de 1 día: **Confirmar turno** (y push); cerca del día: **Confirmar asistencia**.

Backend `.env` (prod):

```env
PUBLIC_API_BASE_URL=https://emr.icpueblodeluis.com.ar:8080
MOBILE_PUSH_ENABLED=true
```

Backend `.env` (solo dev LAN):

```env
MOBILE_PUSH_ENABLED=true
EMR_LAN_IPS=192.168.1.56
EMR_DEV_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,backend,192.168.1.56
EMR_KIOSCO_LAN_ORIGIN=http://192.168.1.94:3000
```

Reiniciá backend (`docker compose up -d backend`).

### Metro desde WSL (importante)

No uses solo `npm start`: el QR sale con IP de WSL (`172…`) y el celular no la alcanza.  
El túnel (`--tunnel` / `*.exp.direct`) a veces falla con “página no encontrada”; preferí LAN:

1. En **PowerShell como Administrador** (una vez por sesión WSL / si cambió la IP de WSL):

```powershell
$wsl = (wsl hostname -I).Trim().Split()[0]
netsh interface portproxy add v4tov4 listenport=8081 listenaddress=0.0.0.0 connectport=8081 connectaddress=$wsl
```

2. En WSL, desde `mobile/`:

```bash
npx expo start --lan --port 8081
```

3. En el celular (misma Wi‑Fi): escanear el QR de Expo o abrir `exp://192.168.x.x:8081`.

## Checklist rápido

0. Si cambió la Wi‑Fi: `powershell -File scripts\sync_lan_ip.ps1`
1. Imprimir QR desde `/recepcion/qr-anuncio`.
2. Anunciar por QR (puesto 1 o lab) → aparece en TV con código.
3. App: **Estoy en sala** con turno hoy → cola recepción; secretaría hace **Pasar a médico**.
4. Médico Llamar → TV mitad médico + app.
5. Ya voy o En atención → sale del destacado TV; rellamar si hace falta.
6. App o QR: anuncio L → laboratorio (**Cola extracciones**) llama a Sala de extracción.
7. Varios llamados: el último queda grande; los otros en «También llamando» + bip en TV.
