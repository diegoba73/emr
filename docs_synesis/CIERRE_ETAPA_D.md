# Cierre — Etapa D (Cirugía básica)

**Fecha:** 2026-10-16  
**Estado:** implementado en código; **sin merge ni producción**  
**Dependencia:** A0–A6 + B + C  
**Ticket:** `docs_synesis/tickets/TICKET_D_CIRUGIA_BASICA.md`  
**Paquete:** `/home/diego/proyectos/emr-a0-compare-artifacts/d_package/`  
**Migración:** `estudios.0010_cirugia_cierre_protocolo_d`  
**Multisesión:** off. **LIMS:** intocable (diff sin `laboratorio/`).

---

## Entregable

1. Alta `CIRUGIA` con catálogo quirúrgico **jerárquico** (especialidad → procedimiento → abordaje opcional); multi rechazado. Campos aditivos en `EstudioComplementario` (`cirugia_*` + snapshots); `procedimiento_catalogo` legacy conservado (sin backfill).  
2. Realización **siempre** `Atencion` + `RegistroQuirurgico` (con/sin turno; sin turno ficticio); profesional + **anestesista real** + dx pre; protocolo **no** exigido al acto.  
3. Protocolo canónico = `InformeEstudioComplementario` versionado; proyección en `RegistroQuirurgico.protocolo_quirurgico` solo vía sync del módulo.  
4. Protección de proyección en API/serializers (`protocolo_protegido_por_modulo`) y `CirugiaForm` — solo registros vinculados al circuito del módulo.  
5. Cierre administrativo (`POST …/cerrar/`): gate protocolo completo+validado en TX; secretaría puede cerrar (y, por política operativa posterior, también emitir/validar/rectificar como operador del módulo); idempotente por versión.  
6. Historial: `HistorialCierreEstudioComplementario` + `HistorialEntregaEstudioComplementario`; rectificación invalida cierre vigente y exige nuevo cierre antes de entrega.  
7. UI: filtro/alta cirugía (cascada esp→proc→abr), diálogo realización (anestesia/dx/sala), botón cerrar; admin `/catalogos/cirugias`.  
8. Seed: `manage.py poblar_cirugias_catalogo` desde `catalogos/data/cirugias.csv` (idempotente; LIMS intocable).

---

## Pruebas

| Suite | Resultado |
| --- | --- |
| `estudios/tests/test_d_cirugia.py` | alta jerárquica + abordaje ajeno rechazado |
| `catalogos/tests/test_cirugia_catalogo_api.py` | list/filtros, write admin OK, médico/secretaría denegados, seed dry-run |
| Regresión `test_c` + `test_b` + `test_d` | re-corrida local al empaquetar |
| A0 `results_d` vs `results_c` | ver §A0 (mismos fallos preexistentes; sin “arreglar”) |

---

## A0 post-D

Referencia: `results_c.txt`. Corrida: `results_d.txt` / `run_a0_d_console.txt`  
Artefactos: `/home/diego/proyectos/emr-a0-compare-artifacts/`.

Filtro `FAILED|ERROR|passed|failed|EXIT`: **`results_d.txt` ≡ `results_c.txt`** (diff vacío).  
Mismos EXIT (LIMS Auth 0, LIMS Flujo 1, Turnos solapamiento 0, Turnos estado 1); 4 fallos preexistentes; sin regresiones nuevas; LIMS no tocado.

---

## Verificación en navegador

Ver informe integrado: `docs_synesis/VERIFICACION_INTEGRADA_A_D.md` (**PENDIENTE** global).

- API live A–D: 44/44 PASS (datos ficticios).  
- UI parcial: listado/bandejas/detalle; secretaría cierra cirugía y ve Entregar (sin Emitir/Validar/Rectificar).  
- Alta UI Autocomplete: no cerrada en herramienta; no declarar e2e browser completo.

---

## Fuera de este cierre

- Etapas E/F, merge, producción, LIMS, multisesión, bloqueantes clínicos no acordados (consentimiento/recuento/etc.).
