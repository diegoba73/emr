# Recepción y kiosco: URL pública (CEHTA/ICPL) y LAN opcional (dev)

CEHTA e ICPL usan el **mismo EMR**. El QR de la pared y las pantallas de recepción
deben apuntar a la URL pública:

`https://emr.icpueblodeluis.com.ar:8080`

No uses `localhost` ni la IP privada del servidor ICPL en el cartel de CEHTA.

## Producción (recomendado)

En el `.env` del servidor:

```env
PUBLIC_API_BASE_URL=https://emr.icpueblodeluis.com.ar:8080
# Opcional si el origen del QR debe diferir:
# EMR_KIOSCO_PUBLIC_ORIGIN=https://emr.icpueblodeluis.com.ar:8080
```

| Pantalla | URL |
|----------|-----|
| Secretaría / Lab / Médico | `https://emr.icpueblodeluis.com.ar:8080/recepcion` |
| QR imprimible | `…/recepcion/qr-anuncio` |
| Kiosco (anuncio) | `…/kiosco-recepcion` |
| TV sala | `…/pantalla-sala` |

El backend expone ese origen en `/api/recepcion/kiosco-config/` (`espera_origin`) y en
`/api/movil/institucion/` (`kiosco_anuncio_url`).

Tras cambiar la variable: reiniciar backend y **reimprimir** el QR.

## Solo desarrollo local (Wi‑Fi de tu PC)

Si estás probando en casa sin publicar HTTPS:

```env
EMR_LAN_IPS=192.168.1.94
EMR_KIOSCO_LAN_ORIGIN=http://192.168.1.94:3000
EMR_KIOSCO_FRONTEND_PORT=3000
EMR_API_PORT=8000
EMR_DEV_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,backend,192.168.1.94
```

Atajo Windows cuando cambia la IP:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\sync_lan_ip.ps1
```

Eso **no** reemplaza la config de producción para CEHTA.

## Prioridad del origen del QR

1. `EMR_KIOSCO_PUBLIC_ORIGIN` o `PUBLIC_API_BASE_URL` (prod / CEHTA)
2. `EMR_KIOSCO_LAN_*` / `EMR_LAN_IPS` (dev)
3. Detección / request LAN (último recurso)
