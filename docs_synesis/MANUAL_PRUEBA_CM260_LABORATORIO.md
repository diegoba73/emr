# Manual de prueba en sitio — CM260 → SYNESIS

**Para:** mañana en el laboratorio, en PCs que no son las tuyas.  
**SoT técnico:** `docs_synesis/reglas/instrumentos-analizadores.md`.  
**Objetivo:** comprobar worklist + carga de resultados como **borrador**. Nunca se auto-valida ni se informa solo.

---

## 1. Máquinas (cómo las vamos a llamar)

| Nombre en este manual | Rol |
|-----------------------|-----|
| **Servidor-SYNESIS** | PC/servidor donde corre el sistema (`/srv/emr/app`, Docker). Tiene la base y el backend. |
| **PC-Lab** | PC de trabajo del lab (navegador a SYNESIS: órdenes, IQC, Analizadores). |
| **PC-CM260** | PC al lado del autoanalizador. Tiene el cable serie/USB del CM260 y WiFi a la red del lab. |

```
CM260  --(RS-232/USB)--  PC-CM260  --(WiFi LAN)--  Servidor-SYNESIS
                              \                      ^
                               \----(opcional)------/  bridge COM → TCP :5000
PC-Lab  --(WiFi/LAN)--  navegador → https://…:8080 (SYNESIS)
```

WiFi en PC-CM260 **sirve**: el medio de red no importa. Lo que importa es que PC-CM260 llegue por TCP al Servidor-SYNESIS.

---

## 2. Qué hacer / qué no hacer

**Sí**

- Usar una **orden de prueba** (paciente demo o “PRUEBA CM260”), no una orden clínica real.
- Sembrar interfaces / mapeos si faltan.
- Probar primero **sin cable** (simulador JSON).
- Dejar resultados en borrador y validar a mano en la UI si querés cerrar el circuito.

**No**

- No rebuild de frontend / nginx.
- No `docker compose down`, ni prune, ni tocar la otra app del servidor.
- No dejar el puerto del analizador abierto a Internet; solo LAN.
- No esperar que el CM260 valide o informe solo.

---

## 3. Checklist rápido (imprimible)

- [ ] Orden de prueba creada con química CM260 (ej. GLU, UREA, CREATI)
- [ ] Tubo tomado / **recibido**; anotaste el código de barra `LAB-AAAA-NNNNN-nn`
- [ ] IQC CM260 del día **ACEPTADO** (si no → `IQC_BLOQUEADO`)
- [ ] En SYNESIS: menú **Laboratorio → Analizadores** muestra interfaz CM260
- [ ] Paso A (simulador JSON) OK
- [ ] Paso B (gateway TCP + simulador ASTM) OK — si hay tiempo
- [ ] Paso C (cable real CM260) — si hay bridge o LIS Ethernet

---

## 4. Preparación en Servidor-SYNESIS

Trabajá por SSH en el host del EMR (no en tu PC de casa):

```bash
ssh -p 2223 server@emr.sytes.net
cd /srv/emr/app
```

### 4.1 Sembrar interfaz CM260 + mapeos

```bash
docker compose -f docker-compose.server.yml exec backend \
  python manage.py seed_instrumentos
```

Esperado: líneas `CM260: mapeos nuevos=…` y `seed_instrumentos listo.`

### 4.2 Flag y token (solo si vas a gateway / HTTP de instrumentos)

En el `.env` de prod del servidor (el que usa el compose), revisar:

```env
LIMS_INSTRUMENT_ENABLED=true
LIMS_INSTRUMENT_TOKEN=<token-largo-secreto>
LIMS_INSTRUMENT_LISTEN_HOST=0.0.0.0
LIMS_INSTRUMENT_LISTEN_PORT=5000
```

Si cambiás `.env`, hace falta **recreate del backend** (corte corto de API).  
**Antes de recrear:** avisar en el lab y acordar el momento. No hace falta rebuild de nginx/frontend.

> Si solo vas a hacer el **Paso A** (simulador JSON **dentro** del contenedor), el flag puede seguir en `false`: ese comando habla con la BD en proceso, no abre TCP.

### 4.3 Puerto 5000 (solo Pasos B/C)

Hoy el compose de servidor **no publica** el puerto `5000` por defecto.  
Para que PC-CM260 o el simulador ASTM lleguen al gateway hace falta:

1. Publicar `5000:5000` (o el puerto que elijan) en el servicio backend **o**
2. Correr el gateway en el host con acceso a la misma BD (más avanzado).

Si no pueden tocar compose mañana: quedate en **Paso A** + captura de traza serie; el cable real se deja para cuando el puerto esté publicado.

---

## 5. Preparación en PC-Lab (navegador)

1. Entrá a SYNESIS con usuario de laboratorio.
2. Creá (o abrí) la **orden de prueba** con determinaciones de química CM260.
3. Generá / imprimí etiqueta del tubo. Anotá exactamente:
   - `LAB-2026-XXXXX-01` (o el año/número que salga).
4. Marcá toma / recepción según el flujo habitual hasta tubo **RECIBIDA** (o estado que permita worklist: RECIBIDA / CONSERVADA / EN_PROCESO).
5. IQC: en **Control de calidad**, confirmá corrida **ACEPTADA** de hoy para CM260.
6. Abrí **Laboratorio → Analizadores**:
   - Debe listar interfaz **CM260**.
   - La tabla de excepciones arranca vacía o con basura vieja; después de pruebas mirá estados `SIN_MATCH`, `IQC_BLOQUEADO`, `ERROR`.

---

## 6. Paso A — Prueba sin cable (obligatoria)

En **Servidor-SYNESIS**, reemplazá el sample-id por el de tu tubo de prueba:

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

- Consola: `worklist estado=OK` y `ingesta estado=OK cargados=…` (idealmente 3).
- En PC-Lab, abrí la orden: GLU / UREA / CREATI con valores en **borrador** (sin validar solos).
- En Analizadores: sin excepción nueva, o mensajes OK (la UI lista sobre todo excepciones).

**Si falla**

| Mensaje / síntoma | Qué revisar |
|-------------------|-------------|
| Tubo no encontrado / `SIN_MATCH` | Sample-id ≠ código de barra del tubo |
| `IQC_BLOQUEADO` | Control del día en CM260 |
| Worklist 0 analitos | Ensayos no asociados al equipo CM260, ya tienen valor, o tubo/orden en estado inválido |
| `sin_match` en códigos | Canal del equipo ≠ mapeo (`URE` vs `UREA`, etc.) |

---

## 7. Paso B — Gateway TCP + simulador ASTM (si hay tiempo y puerto)

### 7.1 Arrancar gateway (Servidor-SYNESIS)

En una sesión SSH que **deje abierta**:

```bash
cd /srv/emr/app
docker compose -f docker-compose.server.yml exec backend \
  python manage.py run_instrument_gateway --driver CM260
```

Si dice que `LIMS_INSTRUMENT_ENABLED=false`, o bien activás el flag (y recreás backend) o, **solo prueba**,:

```bash
docker compose -f docker-compose.server.yml exec backend \
  python manage.py run_instrument_gateway --driver CM260 --force
```

Debe decir algo como: `Escuchando ASTM CM260 en 0.0.0.0:5000`.

> Ojo: si el puerto no está publicado al host/LAN, esto solo escucha **dentro** del contenedor. El Paso B “desde otra PC” requiere el publish del §4.3. Desde el **mismo** contenedor sí podés simular ASTM a `127.0.0.1`.

### 7.2 Simular ASTM (mismo contenedor)

Otra sesión SSH:

```bash
cd /srv/emr/app
docker compose -f docker-compose.server.yml exec backend \
  python manage.py simular_instrumento \
    --driver CM260 \
    --sample-id LAB-2026-XXXXX-01 \
    --mode astm \
    --host 127.0.0.1 \
    --port 5000 \
    --resultados GLU:101,URE:31,CRE:1.0
```

**Éxito:** mensaje de envío ASTM; en la orden aparecen/actualizan borradores; gateway sin error en consola.

Para repetir la prueba, usá otra orden/tubo o borrá/limpiá valores de borrador según el flujo del lab (no pises una orden clínica).

---

## 8. Paso C — CM260 real (PC-CM260)

### 8.1 Lo que hay hoy en el software

- El gateway SYNESIS habla **ASTM sobre TCP**.
- El modelo contempla RS-232, pero **no hay listener serie listo** dentro de Docker.
- Por eso PC-CM260 hace de puente: **COM del CM260 → TCP hacia el servidor:5000**.

### 8.2 En PC-CM260

1. Confirmá qué COM usa el CM260 (Administrador de dispositivos / software Wiener).
2. Parámetros serie típicos (confirmar en manual/config del CM260): baud rate, 8N1, etc. Deben coincidir en el bridge.
3. Instalá o usá un **bridge serie→TCP** (ej. herramientas tipo “serial to TCP”, `socat`, HW VSP, etc. — la que ya tengan en el lab).
4. Destino del bridge: `IP-LAN-del-Servidor-SYNESIS:5000` (la IP interna, no la URL pública si el router no reenvía 5000).
5. En el CM260 / software LIS:
   - Host Query / bidireccional activado si aplica.
   - Sample ID = código de la etiqueta SYNESIS (o el compacto cargado en la muestra).
   - Códigos de canal alineados al mapeo (`GLU`, `URE`/`UREA`, `CRE`/`CREATI`, …).

### 8.3 En Servidor-SYNESIS

- Gateway corriendo (§7.1).
- Puerto 5000 publicado a la LAN (§4.3).
- Firewall del servidor: permitir **solo** desde la IP de PC-CM260 (ideal).

### 8.4 Prueba con una muestra de prueba

1. En PC-Lab: orden de prueba + tubo recibido + IQC OK.
2. En CM260: pedí / corré esa muestra (query → worklist → resultados).
3. En PC-Lab: orden con borradores; Analizadores sin `SIN_MATCH` / `IQC_BLOQUEADO`.
4. Validá a mano un resultado para cerrar el circuito humano.

### 8.5 Si no hay bridge mañana

No bloquea el día:

1. Completá Paso A (y B interno si pueden).
2. En PC-CM260, con un monitor serie (RealTerm, PuTTY raw, etc.), **grabá una traza** de lo que manda el CM260 al preguntar y al enviar resultados.
3. Guardá el archivo `.txt` / `.log` y después se ajusta el parser / mapeo con esa traza real.

---

## 9. Dónde mirar resultados y fallos

| Dónde | Qué ves |
|-------|---------|
| Orden LIMS (PC-Lab) | Valores cargados como borrador |
| **Analizadores** | Excepciones: `SIN_MATCH`, `IQC_BLOQUEADO`, `ERROR` |
| Consola del gateway | Conexiones ASTM, errores de frame |
| API (opcional) | `GET /api/lab/instrumentos/mensajes/?excepciones=1` |

Los valores **no** quedan informados hasta validación humana.

---

## 10. Orden sugerido mañana (30–90 min)

1. **PC-Lab:** orden + tubo + IQC (10–15 min).  
2. **Servidor:** `seed_instrumentos` + Paso A (10 min).  
3. Si Paso A OK → **Paso B** dentro del contenedor (10–15 min).  
4. Si hay bridge y puerto → **Paso C** con una sola muestra de prueba.  
5. Si no hay bridge → capturar traza serie y listo.

---

## 11. Datos para anotar en el lab (rellenar a mano)

```
Fecha: _______________
IP LAN Servidor-SYNESIS: _______________
IP LAN PC-CM260: _______________
COM del CM260: _______________
Baud / bits: _______________
Sample-id de prueba: _______________
Orden / paciente prueba: _______________
Paso A: OK / FALLÓ — detalle: _______________
Paso B: OK / FALLÓ / NO HECHO
Paso C: OK / FALLÓ / NO HECHO — detalle: _______________
¿Traza serie guardada?: Sí / No — archivo: _______________
```

---

## 12. Referencias rápidas de comandos

```bash
# Semilla
python manage.py seed_instrumentos

# Soft (sin red ASTM)
python manage.py simular_instrumento --driver CM260 --sample-id LAB-…-01 --mode json --resultados GLU:100,URE:30,CRE:0.9

# Gateway TCP
python manage.py run_instrument_gateway --driver CM260
# o con --force si el flag está apagado (solo prueba)

# ASTM contra gateway local
python manage.py simular_instrumento --driver CM260 --sample-id LAB-…-01 --mode astm --host 127.0.0.1 --port 5000
```

En prod anteponer:

`docker compose -f docker-compose.server.yml exec backend`

UI: `/laboratorio/instrumentos`  
Regla: `docs_synesis/reglas/instrumentos-analizadores.md`
