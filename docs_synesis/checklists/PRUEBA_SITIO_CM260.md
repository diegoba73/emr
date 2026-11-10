# Manual de prueba en sitio — CM260 → SYNESIS

**Para:** prueba en el laboratorio, en PCs que no son las de desarrollo.
**SoT técnico:** `docs_synesis/reglas/instrumentos-analizadores.md` (si hay conflicto, gana el código citado ahí).
**Objetivo:** comprobar worklist + carga de resultados como **borrador**. Nunca se auto-valida ni se informa solo.

---

## 1. Máquinas

| Nombre en este manual | Rol |
|---|---|
| **Servidor-SYNESIS** | Host del EMR (`/srv/emr/app`, Docker). Base y backend. |
| **PC-Lab** | PC de trabajo del lab (navegador a SYNESIS: órdenes, IQC, Analizadores). |
| **PC-CM260** | PC al lado del autoanalizador. Cable serie/USB del CM260 y red del lab. |

```
CM260 --(RS-232/USB)-- PC-CM260 --(LAN o túnel SSH)-- Servidor-SYNESIS
                          bridge COM → TCP :5000
PC-Lab --(LAN)-- navegador → SYNESIS
```

El medio de red (WiFi o cable) no importa: lo que importa es que PC-CM260 llegue por TCP al gateway.

---

## 2. Qué hacer / qué no hacer

**Sí**

- Usar **órdenes de prueba** (paciente demo o "PRUEBA CM260"), nunca una orden clínica real.
- Preparar **dos órdenes de prueba** (una para Paso A y otra para Paso B), cada una con **exactamente** GLU, UREA y CREATI.
- Mandar siempre los **3 valores** por orden.
- Probar primero **sin cable** (simulador JSON).
- Validar a mano en la UI para cerrar el circuito humano.
- Al terminar, **cancelar las órdenes de prueba** (que no queden en listas de trabajo ni estadísticas).

**No**

- No rebuild de frontend / nginx.
- No `docker compose down`, ni `prune`, ni tocar la otra app del servidor.
- No exponer el puerto del gateway a Internet (ver §7).
- No esperar que el CM260 valide o informe solo.

### Por qué dos órdenes y tres analitos

- La ingesta **solo llena resultados vacíos y sin validar** del tubo (`_pendientes_tubo` en `laboratorio/instrumentos_service.py`). Si repetís sobre el tubo del Paso A, el Paso B da `SIN_MATCH` ("Ningún analito coincide con la orden").
- Con la orden **completa** la ingesta la deja en `LISTO_PARA_VALIDAR`. Con la orden incompleta queda `EN_PROCESO`. En ningún caso pasa a `INFORMADO_PARCIAL` ni a `FINALIZADO`.
- **Ojo:** hasta que el servidor corra un backend con esa corrección, una orden incompleta cargada desde el analizador pasa a `INFORMADO_PARCIAL` (visible para el médico). Con órdenes de exactamente 3 analitos y 3 valores no ocurre.

---

## 3. Checklist rápido (imprimible)

- [ ] Orden de prueba **A** con GLU, UREA, CREATI — tubo recibido — código: `LAB-____-_____-__`
- [ ] Orden de prueba **B** con GLU, UREA, CREATI — tubo recibido — código: `LAB-____-_____-__`
- [ ] IQC CM260 **vigente** ACEPTADO, S1 y S2 (si no → `IQC_BLOQUEADO`). Ventana: lunes 08:00 → viernes 08:00 vale el del lunes; viernes 08:00 → lunes 08:00 vale el del viernes (`reglas/control-calidad.md`)
- [ ] Laboratorio → Analizadores muestra interfaz CM260
- [ ] Pre-chequeo (§4.2) OK
- [ ] Paso A (simulador JSON) OK
- [ ] Paso B (gateway TCP + simulador ASTM) OK — si hay tiempo
- [ ] Paso C (cable real CM260) — si hay bridge
- [ ] Órdenes de prueba canceladas al final

---

## 4. Preparación en Servidor-SYNESIS

```bash
ssh -p 2223 server@emr.sytes.net
cd /srv/emr/app
```

En prod, todos los `python manage.py …` se anteponen con:

```bash
docker compose -f docker-compose.server.yml exec backend
```

### 4.1 Sembrar interfaz CM260 + mapeos (idempotente)

```bash
docker compose -f docker-compose.server.yml exec backend \
  python manage.py seed_instrumentos
```

Esperado: `CM260: mapeos nuevos=… omitidos_sin_examen=…` y `seed_instrumentos listo.`

### 4.2 Pre-chequeo (solo lectura)

La causa más común de "worklist 0 analitos" es que los ensayos no estén asociados al **mismo equipo** que la interfaz (o que el IQC se haya cargado contra otro equipo).

```bash
docker compose -f docker-compose.server.yml exec backend python manage.py shell -c "
from laboratorio.models import TipoExamen
from laboratorio.models_instrumentos import InterfazInstrumento as I
i=I.objects.get(driver='CM260'); print('interfaz equipo:', i.equipo_id, i.equipo)
for t in TipoExamen.objects.filter(codigo__in=['GLU','UREA','CREATI']):
    print(t.codigo, 'equipo:', t.equipo_analizador_id, 'tubo:', t.tipo_contenedor)"
```

Los tres `equipo:` tienen que coincidir con `interfaz equipo:`. El IQC vigente tiene que estar cargado contra ese mismo equipo. Para verlo:

```bash
docker compose -f docker-compose.server.yml exec backend python manage.py shell -c "
from laboratorio.models_qc import EquipoAnalizador, CorridaQC
for e in EquipoAnalizador.objects.filter(codigo__icontains='CM'): print('equipo', e.id, e.codigo, e.activo)
for c in CorridaQC.objects.filter(equipo__codigo='CM260').order_by('-fecha')[:5]: print('corrida', c.fecha, c.estado, c.nivel)"
```

Las fechas salen en UTC (restar 3 h para hora local).

Para ver el ID compacto de un tubo (útil en Paso C):

```bash
docker compose -f docker-compose.server.yml exec backend python manage.py shell -c "
from laboratorio.models_catalog import Muestra
m=Muestra.objects.get(codigo_barra='LAB-2026-XXXXX-01'); print(m.codigo_instrumento, m.estado)"
```

### 4.3 Flag, token y `.env`

**No hace falta tocar `.env` ni recrear el backend** para esta prueba:

- Paso A habla con la BD en proceso; no usa flag ni TCP.
- El gateway TCP (Pasos B/C) no usa token (`LIMS_INSTRUMENT_TOKEN` solo aplica a los endpoints HTTP `/api/lab/instrumentos/…`). El flag `LIMS_INSTRUMENT_ENABLED=false` se saltea con `--force` solo para ese proceso.

---

## 5. Preparación en PC-Lab (navegador)

1. Entrar a SYNESIS con usuario de laboratorio.
2. Crear las **dos órdenes de prueba** (GLU, UREA, CREATI; nada más).
3. Imprimir etiquetas y anotar exactamente cada `LAB-AAAA-NNNNN-nn`.
4. Toma / recepción hasta tubo **RECIBIDA** (worklist acepta RECIBIDA / CONSERVADA / EN_PROCESO).
5. **IQC:** en Control de calidad, corrida **ACEPTADA** vigente (S1 y S2) para CM260. Martes a jueves vale la del lunes; no hace falta correr control nuevo.
6. **Laboratorio → Analizadores** (`/laboratorio/instrumentos`): debe listar la interfaz CM260. Después de cada paso, mirar excepciones `SIN_MATCH`, `IQC_BLOQUEADO`, `ERROR`.

---

## 6. Paso A — Prueba sin cable (obligatoria)

Con el tubo de la **orden A**:

```bash
cd /srv/emr/app
docker compose -f docker-compose.server.yml exec backend \
  python manage.py simular_instrumento \
    --driver CM260 \
    --sample-id LAB-2026-XXXXX-01 \
    --mode json \
    --resultados GLU:100,URE:30,CRE:0.9
```

**Éxito**

- Consola: `worklist estado=OK analitos=3` y `ingesta estado=OK cargados=3`.
- PC-Lab: orden A con GLU / UREA / CREATI cargados, sin validar, orden en **Listo para validar**.
- Analizadores: sin excepción nueva.

**Si falla**

| Síntoma | Qué revisar |
|---|---|
| `SIN_MATCH` / Tubo no encontrado | Sample-id ≠ código de barra del tubo |
| `IQC_BLOQUEADO` | IQC vigente de CM260: falta, está rechazado, o se cargó en otro equipo (§4.2) |
| Worklist 0 analitos | §4.2: equipo de los ensayos; o ya tienen valor; o tubo/orden en estado inválido |
| `ERROR` "Muestra en estado …" / "Orden en estado …" | Recepción del tubo / estado de la orden |
| `cargados` < 3 con `sin match` | Canal del equipo ≠ mapeo (URE vs UREA, etc.) |

---

## 7. Paso B — Gateway TCP + simulador ASTM (si hay tiempo)

### 7.1 Arrancar gateway sin tocar el backend en uso

Usar `tmux` en el servidor para que el gateway no muera si se corta el SSH:

```bash
tmux new -s cm260
cd /srv/emr/app
docker compose -f docker-compose.server.yml run --rm --no-deps --name cm260-gateway \
  --entrypoint python -p 127.0.0.1:5000:5000 \
  backend manage.py run_instrument_gateway --driver CM260 --force
```

- `run` crea un contenedor aparte con la misma imagen, red y env que `backend`; el backend productivo no se recrea.
- `--entrypoint python` es obligatorio: `entrypoint.sh` ignora los argumentos y arrancaría gunicorn.
- `-p 127.0.0.1:5000:5000` publica el puerto **solo en loopback del host** (alcanzable por túnel SSH, no desde Internet).
- Esperado: `Escuchando ASTM CM260 en 0.0.0.0:5000`.
- Salir de tmux sin cortar: `Ctrl-b d`. Volver: `tmux attach -t cm260`. Cortar el gateway: `Ctrl-c`.

### 7.2 Simular ASTM

Con el tubo de la **orden B** (no reusar el de A), en otra sesión SSH. El simulador corre dentro del mismo contenedor del gateway y le habla por loopback:

```bash
docker exec cm260-gateway python manage.py simular_instrumento \
  --driver CM260 \
  --sample-id LAB-2026-YYYYY-01 \
  --mode astm --host 127.0.0.1 --port 5000 \
  --resultados GLU:101,URE:31,CRE:1.0
```

Esperado en consola: `ASTM query+resultados enviados.`

**Éxito:** orden B con 3 borradores, en Listo para validar; consola del gateway sin errores; Analizadores sin excepción nueva.

---

## 8. Paso C — CM260 real (PC-CM260)

### 8.1 Lo que hay hoy

- El gateway habla **ASTM sobre TCP**. No hay listener serie dentro de Docker.
- PC-CM260 hace de **puente**: COM del CM260 → TCP hacia el gateway.
- El parser asume ASTM genérico (registro `Q` con `^sample`, registro `R` con `^^^CODIGO`). **No está confirmado** que el CM260 hable exactamente así: la traza real es lo más valioso del día.

### 8.2 Conexión de PC-CM260 al gateway

**Opción preferida (servidor fuera de la LAN del lab):** túnel SSH desde PC-CM260, sin abrir puertos nuevos:

```bash
ssh -p 2223 -N -L 5000:127.0.0.1:5000 server@emr.sytes.net
```

El bridge apunta a `127.0.0.1:5000` de PC-CM260.

**Solo si el servidor está en la misma LAN:** cambiar el publish a `-p <IP-LAN-servidor>:5000:5000` y en el firewall del servidor permitir solo la IP de PC-CM260. Nunca reenviar el 5000 en el router.

### 8.3 En PC-CM260

1. COM del CM260 (Administrador de dispositivos / software Wiener).
2. Parámetros serie (baud, 8N1, etc.) según manual/config del CM260; deben coincidir en el bridge.
3. Bridge serie→TCP en modo **cliente TCP** hacia el destino de §8.2, con **reconexión automática** (ver límites del gateway abajo).
4. En el CM260 / LIS:
   - Protocolo LIS: confirmar que sea ASTM.
   - Host Query / bidireccional si aplica. Si está apagado igual sirve: la ingesta funciona sin worklist, programando los ensayos a mano en el equipo.
   - Sample ID: el worklist devuelve el **ID compacto** (`codigo_instrumento`, ej. `20260004201`), no `LAB-…`. Si el equipo no acepta guiones o tiene límite de largo, cargar el compacto (§4.2). El LIMS acepta ambos.
   - Códigos de canal alineados al mapeo (GLU, URE/UREA, CRE/CREATI, …).

### 8.4 Límites del gateway a tener en cuenta

- Atiende **una conexión por vez**.
- Corta la conexión tras **30 s sin datos**. Un bridge con conexión persistente debe reconectarse solo; si no, se pueden perder mensajes.

### 8.5 Prueba con una muestra de prueba

1. PC-Lab: orden de prueba nueva (GLU, UREA, CREATI) + tubo recibido + IQC OK.
2. CM260: correr esa muestra (query → worklist → resultados).
3. PC-Lab: orden con borradores; Analizadores sin `SIN_MATCH` / `IQC_BLOQUEADO`.
4. Validar a mano un resultado.

### 8.6 Si no hay bridge o el parser no entiende al equipo

No bloquea el día:

- Completar Paso A (y B).
- En PC-CM260, con un monitor serie (RealTerm, PuTTY raw, etc.), grabar la traza **en ambos sentidos** al preguntar y al enviar resultados (incluir caracteres de control: ENQ/STX/ETX/EOT).
- Guardar el `.txt` / `.log`; con esa traza se ajusta parser / mapeo.

---

## 9. Dónde mirar

| Dónde | Qué ves |
|---|---|
| Orden LIMS (PC-Lab) | Valores cargados sin validar |
| Analizadores (`/laboratorio/instrumentos`) | Excepciones `SIN_MATCH`, `IQC_BLOQUEADO`, `ERROR` |
| Consola del gateway (tmux) | Conexiones ASTM, errores de frame |
| API (opcional) | `GET /api/lab/instrumentos/mensajes/?excepciones=1` |

La carga desde el analizador queda auditada con `fuente=INSTRUMENTO` y sin usuario. Los valores no se informan hasta validación humana.

---

## 10. Orden sugerido (30–90 min)

1. PC-Lab: dos órdenes + tubos + IQC (10–15 min).
2. Servidor: `seed_instrumentos` + pre-chequeo + Paso A (10 min).
3. Si Paso A OK → Paso B (10–15 min).
4. Si hay bridge → Paso C con una sola muestra de prueba.
5. Si no hay bridge → capturar traza serie.
6. Cancelar órdenes de prueba; cortar el gateway (`Ctrl-c` en tmux).

---

## 11. Datos para anotar (a mano)

```
Fecha: _______________
IP LAN Servidor-SYNESIS (o "túnel SSH"): _______________
IP LAN PC-CM260: _______________
COM del CM260: _______________
Baud / bits / paridad: _______________
Protocolo LIS del CM260: _______________
Sample-id orden A: _______________   compacto: _______________
Sample-id orden B: _______________   compacto: _______________
Paso A: OK / FALLÓ — detalle: _______________
Paso B: OK / FALLÓ / NO HECHO
Paso C: OK / FALLÓ / NO HECHO — detalle: _______________
¿Traza serie guardada?: Sí / No — archivo: _______________
¿Órdenes de prueba canceladas?: Sí / No
```

---

## 12. Referencias rápidas

```bash
# Semilla
python manage.py seed_instrumentos

# Sin red (orden A)
python manage.py simular_instrumento --driver CM260 --sample-id LAB-…-01 --mode json --resultados GLU:100,URE:30,CRE:0.9

# Gateway TCP en contenedor aparte (desde /srv/emr/app, dentro de tmux)
docker compose -f docker-compose.server.yml run --rm --no-deps --name cm260-gateway --entrypoint python \
  -p 127.0.0.1:5000:5000 backend manage.py run_instrument_gateway --driver CM260 --force

# ASTM contra el gateway (orden B)
docker exec cm260-gateway python manage.py simular_instrumento --driver CM260 --sample-id LAB-…-01 \
  --mode astm --host 127.0.0.1 --port 5000 --resultados GLU:101,URE:31,CRE:1.0

# Túnel desde PC-CM260
ssh -p 2223 -N -L 5000:127.0.0.1:5000 server@emr.sytes.net
```
