# MedGemma / Ollama (solo desarrollo local)

Asistente de **sugerencia** (conclusión de hemograma, interpretación de orden, informes de estudios).  
No valida, no firma, no escribe en HC hasta que un humano acepte/guarde.

## Producción

**No soportado** en `emr.sytes.net` (capacidad del host insuficiente).

- Dejar siempre `MEDGEMMA_ENABLED=false` (default).
- No instalar Ollama en el servidor EMR.
- Las mismas APIs responden con el **motor de reglas** (`fuente=reglas`).

## Local

### 1. Ollama + modelo (recomendado: Docker)

El Ollama instalado en WSL suele quedar en `127.0.0.1:11434` y el contenedor Django **no lo alcanza**. Preferí el servicio compose:

```bash
# Liberar puerto si hay ollama del host
sudo systemctl stop ollama 2>/dev/null || true
pkill ollama 2>/dev/null || true

cd ~/proyectos/emr
docker compose --profile medgemma up -d ollama
docker exec emr_ollama ollama pull medgemma:4b
```

Alternativa host (más frágil): `OLLAMA_HOST=0.0.0.0:11434 ollama serve` tras detener el servicio systemd.

`medgemma:4b` (~3.3 GB) es el modelo canónico local.

### 2. Variables en `.env`

```env
MEDGEMMA_ENABLED=true
MEDGEMMA_BASE_URL=http://host.docker.internal:11434
MEDGEMMA_MODEL=medgemma:4b
MEDGEMMA_TIMEOUT_SECONDS=90
```

- Por defecto Ollama escucha solo `127.0.0.1` → el contenedor ve **connection refused** en `172.17.0.1`.
- Hay que arrancarlo así: `OLLAMA_HOST=0.0.0.0:11434 ollama serve`
- En `.env`: `MEDGEMMA_BASE_URL=http://172.17.0.1:11434` (o servicio compose `http://ollama:11434` con profile `medgemma`).
- `host.docker.internal` en WSL2 suele fallar (apunta a Windows).
- En CPU el timeout conviene ≥ 60–90 s.
- El cliente usa `/api/chat` (fallback `/api/generate`).

Tras cambiar `.env`: **recrear** el contenedor (`docker compose up -d --force-recreate backend`).  
`docker restart` **no** recarga variables de `env_file`.

### 3. Smoke

Con una orden que tenga hemograma y valores cargados (o borrador en UI):

- LIMS → sugerir conclusión de hemograma → `fuente` debería ser `medgemma` si Ollama responde.
- Si Ollama está apagado: misma UI con `fuente=reglas` (sin error duro).

Reglas de producto: `docs_synesis/reglas/ia.md`.
