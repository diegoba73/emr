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

## Aislamiento: no mezclar con la otra app

En `emr.sytes.net` conviven dos sistemas. Al trabajar con **EMR-LIMS**, usar solo sus puertos. No tocar, reiniciar ni redeployar la otra aplicación.

| | EMR-LIMS | Otra aplicación |
|---|---|---|
| SSH | puerto **2223** | puerto **22** |
| URL pública HTTP | `http://emr.sytes.net:8080` | puerto **80** público |
| Docker nginx en la PC EMR | publicar como **`80:80`** | fuera de alcance |
| Código | `/srv/emr/app` | fuera de alcance |

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
