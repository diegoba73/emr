# Reporte de revisión — catálogo micro LabWin

Generado a partir de reglas conocidas en
`laboratorio/labwin_micro_catalog_corrections.py`.
Complementar con la salida de `import_labwin_micro_catalogos` (pendientes de la corrida).

## ANTIB

| Código | Original típico | Propuesta / acción | Motivo |
|--------|-----------------|--------------------|--------|
| AS | AMPINICILINA-SULBACTAMA | Ampicilina/sulbactam | Ortografía inequívoca |
| TS | TRIMETOP.+SULFAMETOXAZOL | Trimetoprima/sulfametoxazol | Ortografía inequívoca |
| TTT | Esto es de prueba | (inactivo) | Registro de prueba LabWin |
| NI | NITROFURANOS | Pendiente revisión | Ambiguo (¿nitrofurantoína?) |
| TA | TAZOBACTAMA | Pendiente revisión | Nombre incompleto (¿pip/tazo?) |

## BACTE

| Código | Original típico | Propuesta | Motivo |
|--------|-----------------|-----------|--------|
| ENTC | Enteroccocus… | Enterococcus faecalis | Ortografía inequívoca |

## NEMOTEC

| Código | Acción | Notas |
|--------|--------|-------|
| ENTC | Ortografía | Enterococcus faecalis. |
| CONT, col, stha, KLEBBLEE | Categoría FENOTIPO | Interpretación / fenotipo; no sustituye ID de especie |
| gr1, gr2, gr3, gr4, gr5, uf+ | UMBRAL pendiente | Umbrales cuantitativos históricos; validar texto clínico |

## Checklist operativo

1. Dry-run con fixtures: `import_labwin_micro_catalogos --fixtures --dry-run`
2. Dry-run sobre exportación real
3. Revisar pendientes NI/TA y umbrales gr*/uf+
4. Import solo tras OK profesional
5. Editar en UI lo que deba quedar fijo (`editado_manualmente`)
