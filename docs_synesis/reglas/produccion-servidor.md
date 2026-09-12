# Reglas — Producción y servidor compartido

**Complemento operativo:** `PROD_RUNTIME.md`, `docs/demo-stack.md`.

## Acceso EMR-LIMS

```bash
ssh -p 2223 server@dsachubut.sytes.net
```

- Código y compose de prod: `/srv/emr/app` + `docker-compose.server.yml`.
- No confundir con Docker local (`emr_backend` / `emr_postgres`).
- Imports o `manage.py` en producción: **en ese host** (vía SSH), no en contenedores locales.
- Antes de escribir en la BD de prod: backup + `--dry-run` cuando el comando lo soporte.

## Aislamiento: no mezclar con la otra app

En `dsachubut.sytes.net` conviven dos sistemas. Al trabajar con **EMR-LIMS**, usar solo sus puertos. No tocar, reiniciar ni redeployar la otra aplicación.

| | EMR-LIMS | Otra aplicación |
|---|---|---|
| SSH | puerto **2223** | puerto **22** |
| URL pública HTTP | `http://dsachubut.sytes.net:8080` | puerto **80** público |
| Docker nginx en la PC EMR | publicar como **`80:80`** | fuera de alcance |
| Código | `/srv/emr/app` | fuera de alcance |

El router reenvía **público `:8080` → `192.168.1.253:80`**.  
Por eso el compose del EMR debe publicar nginx como **`80:80`**, no `8080:80`.

Demo marketing (aislado): público **8081** — ver `docs/demo-stack.md`. No usar el volumen ni el compose clínicos.
