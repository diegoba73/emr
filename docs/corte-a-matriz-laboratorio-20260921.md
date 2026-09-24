# Corte A — matriz laboratorio (21/09/2026)

**Alcance cerrado.** No avanza a Corte B/C automáticamente.

## Hecho en código

| Cambio | Archivos |
|--------|----------|
| B12/VITD → `VIDAS_KUBE`; PROBNP → `FINECARE` (solo catálogo de equipos) | `laboratorio/equipos_lab.py` |
| Eliminado mapeo Sysmex `MXD`/`MXD%`/`MXD#` → `MONO`; desactivación de mapeos legado en seed | `instrumentos_catalogo.py`, `instrumentos_seed.py`, `seed_instrumentos`, regla `instrumentos-analizadores.md` |
| Guardas lipídicas/hepáticas: sin TG o Friedewald no aplicable → `No calculable…`; BIL_I inválida igual | `calculos_derivados.py`, `calculosDerivados.ts` |
| Formulario QC: media/DE vacíos (sin 100/5); `seed_qc_demo` marcado DEMO | `QcHubPage.tsx`, `seed_qc_demo.py` |
| IQC sin materiales/productos: `sin_configuracion=True`; UI “Sin IQC” / alerta (no “IQC OK”) | `qc_service.py`, `views_qc.py`, carga/detalle/tabla, `control-calidad.md` |

## No tocado (explícito)

- Referencias / puntos de corte `TROP_US` y `DDIM`
- Importación de reactivos, lotes o valores asignados reales
- Fusión de códigos duplicados (p. ej. `NTPROBNP` ↔ `PROBNP`)
- Resultados históricos (`ResultadoExamen.valor_*`): `mapear_examenes_equipo` solo actualiza `TipoExamen.equipo_analizador`

## Operación local / prod (mapeo equipos)

Tras deploy del código:

```bash
python manage.py mapear_examenes_equipo --dry-run
python manage.py mapear_examenes_equipo
python manage.py seed_instrumentos   # también desactiva MXD→MONO legado
```

**No** correr `seed_qc_demo` en producción para “arreglar” targets.

## Matriz 81

Sigue como borrador editable (`docs/matriz_laboratorio.xlsm` + CSV de investigación). Incluir=SI / PENDIENTE hasta Corte B (reactivos, controles, lotes reales).

## Pendiente Corte B

1. Confirmar REF/kits Wiener (CM260) y controles Standatrol por lote real (reemplazar placeholders 100/5).
2. Materiales IQC VIDAS/Finecare por ensayo con media/DE de insertos vigentes (B12, VITD, PROBNP incluidos).
3. Resolver `Decisiones_multiples` / duplicados de catálogo sin fusionar historial.
4. Método persistido por plataforma (ELFA / inmunofluorescencia) vs texto genérico del catálogo.
5. Frecuencia/niveles QC y eventos que invalidan aceptación (calibración, cambio de lote).

## Pendiente Corte C (más adelante)

Informe/UI restante, validación clínica de referencias no-troponina/dímero, y cierre de la matriz Incluir.
