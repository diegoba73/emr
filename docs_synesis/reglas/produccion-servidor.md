# Reglas — Producción y servidor compartido

**Complemento operativo:** `PROD_RUNTIME.md`, `docs/demo-stack.md`.

## Acceso EMR-LIMS

```bash
ssh -p 2223 server@emr.sytes.net
```

- Código y compose de prod: `/srv/emr/app` + `docker-compose.server.yml`.
- No confundir con Docker local (`emr_backend` / `emr_postgres`).
- Imports o `manage.py` en producción: **en ese host** (vía SSH), no en contenedores locales.
- Antes de escribir en la BD de prod: backup + `--dry-run` cuando el comando lo soporte.

## Avisos obligatorios antes de rebuild / recreate

Prod es de uso diario: **no proponer ni lanzar** comandos largos o que recrean servicios sin avisar antes en el chat y esperar OK explícito.

Avisar siempre (con **tiempo estimado** y si el sistema sigue usable) cuando se trate de:

| Acción | Impacto típico | ¿Sistema usable mientras tanto? |
|--------|----------------|----------------------------------|
| `docker compose build --no-cache nginx` (o rebuild frontend completo) | ~30–45+ min | Sí: contenedores actuales siguen hasta el `up` |
| `build` backend/nginx con caché | minutos | Sí hasta el recreate |
| `up --force-recreate` backend y/o nginx | breve corte (segundos–1–2 min) | Interrupción corta al recrear |
| recreate de todo el stack / `down`+`up` | corte mayor | No |
| migraciones en prod | suele ser rápido; riesgo de bloqueo si falla | Preferible ventana acordada |

Regla del asistente:

1. Decir en el chat: qué se va a hacer, cuánto puede tardar, si hay downtime.
2. Ofrecer alternativa más corta si existe (hotfix sin `--no-cache`, solo backend, etc.).
3. **No** pegar el comando de build/recreate “para que lo corran ya” sin ese aviso, salvo que el usuario lo pida explícitamente en ese mensaje.

## Aislamiento: no mezclar con la otra app

En `emr.sytes.net` conviven dos sistemas. Al trabajar con **EMR-LIMS**, usar solo sus puertos. No tocar, reiniciar ni redeployar la otra aplicación.

| | EMR-LIMS | Otra aplicación |
|---|---|---|
| SSH | puerto **2223** | puerto **22** |
| URL pública (canónica) | `https://emr.icpueblodeluis.com.ar:8080` | puerto **80** público |
| Acceso legacy / NAT | `http://emr.sytes.net:8080` (router **`:8080` → host `:80`**) | — |
| Docker nginx en la PC EMR | publicar como **`80:80`** | fuera de alcance |
| Código | `/srv/emr/app` | fuera de alcance |

**Enlaces de informe (WhatsApp / mail):** `PUBLIC_API_BASE_URL=https://emr.icpueblodeluis.com.ar:8080` en el `.env` de prod. No usar `emr.sytes.net` en esos mensajes.

El router reenvía **público `:8080` → `192.168.1.253:80`**.  
Por eso el compose del EMR debe publicar nginx como **`80:80`**, no `8080:80`.

Demo marketing (aislado): público **8081** — ver `docs/demo-stack.md`. No usar el volumen ni el compose clínicos.

## Compatibilidad con órdenes y exámenes ya existentes

En producción **ya hay pacientes con órdenes y resultados** (en curso, informados, validados). Todo cambio de LIMS/EMR debe pensarse contra esa base viva, no solo contra catálogo “limpio”.

### Obligatoriedad

1. **No romper órdenes abiertas ni cerradas** por un cambio de catálogo, validación, tubos, estados o payload de carga.
2. Preferir cambios **aditivos / retrocompatibles**: default seguro, flags, exenciones por código/`modo_entrada`, migraciones que no invaliden FK ni dejen resultados huérfanos.
3. Seeds/sync/reparar deben poder correrse en prod **sin invalidar** `ResultadoExamen` / `Muestra` / paneles ya pedidos.
4. Si un cambio puede alterar comportamiento de órdenes ya creadas (p. ej. exigir muestra donde antes no, quitar tubo, renombrar código, endurecer validación), el asistente **no lo aplica en silencio**:
   - **avisar antes** (impacto + órdenes/exámenes afectados + mitigación);
   - **esperar decisión explícita** del usuario (hacer / no hacer / hacer solo para órdenes nuevas).

### Ejemplos de riesgo alto (pedir OK)

- `requiere_muestra`, `tipo_muestra_requerida`, `tipo_contenedor`, `modo_entrada`
- Validaciones nuevas en `cargar-resultados` / validar / cierre de orden
- Remapeo de tubos u orina 24 h que cambie material efectivo
- Renombrar/desactivar códigos de examen o componentes de panel
- Migraciones que toquen FKs de `ResultadoExamen` / `Muestra` / catálogo usado por órdenes vivas

Procedimiento del asistente: `DOC_PROTOCOLO_TRABAJO_ASISTENTE.md` §6.6.

### Pedidos LIMS multi-material (oct 2026)

- Campo aditivo `material_pedido` (nullable/vacío en legacy): **no** muta órdenes históricas; anti-dup infiere materiales.
- Desplegar **backend + frontend juntos** (confirmación médica solo `POST /api/lab/pedidos-completos/`; create/agregar/micro granular médico → 403).
- Reversión: no rehabilitar flush parcial médico; no borrar órdenes ya creadas por el atómico. Preferir hotfix forward o rollback BE+FE acoplado.
- Smoke post-deploy: confirmación multi-material; médico create directo 403; lab/bio agregar-quitar en orden no finalizada; clearance con creatininemia en informe; hoy≠mañana; impresión guardia/consulta/internación/LIMS.

### Ambulatorio unificado SANGRE/ORINA/MATERIA_FECAL (oct 2026)

- Solo orígenes ambulatorio/externo: una orden real si el pedido mezcla ≥2 de esos materiales; guardia/internación siguen partiendo.
- Órdenes históricas no se fusionan en batch; sí se pueden **ampliar** vía `agregar-examenes` (vacía `material_pedido`).
- Desplegar BE+FE juntos. Smoke: ambulatorio sangre+orina(+MF) → 1 protocolo / 1 informe; guardia misma selección → 2–3 órdenes; agregar orina a sangre ambulatoria abierta; anti-dup si ya hay orina activa el mismo día.
