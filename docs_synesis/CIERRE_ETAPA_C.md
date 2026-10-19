# Cierre — Etapa C (Procedimientos no quirúrgicos)

**Fecha:** 2026-10-16  
**Estado:** cerrado con evidencias de verificación; **sin merge ni producción**  
**Dependencia:** A0–A6 + B  
**Ticket:** `docs_synesis/tickets/TICKET_C_PROCEDIMIENTOS_NO_QUIRURGICOS.md`  
**Paquete:** `/home/diego/proyectos/emr-a0-compare-artifacts/c_package/`  
**Migración:** `estudios.0009_sesion_atencion_informe_registro_c`  
**Siguiente (solo revisión):** `tickets/TICKET_D_CIRUGIA_BASICA.md`

---

## Coherencia (modelo)

`RegistroProcedimiento` **exige** `Atencion` (PK).

| Caso | Resultado al realizar |
| --- | --- |
| Con turno o sala (`recurso_id`) | `Atencion` + `RegistroProcedimiento`; vínculo `SesionActividad.atencion` |
| Sin turno ni sala | REALIZADO sin atención/registro; docs = indicación + sesión + informe |
| Atencion incompatible | Bloqueo; sin escrituras parciales |

---

## 1. Comparación A0 post-C

Referencia: `results_b.txt`. Corrida: `results_c.txt` / `run_a0_c_console.txt`  
Artefactos: `/home/diego/proyectos/emr-a0-compare-artifacts/`.

| Suite | EXIT B | EXIT C |
| --- | --- | --- |
| LIMS_Authorization | 0 | 0 |
| LIMS_Flujo_critico | 1 | 1 |
| Turnos_solapamiento | 0 | 0 |
| Turnos_estado_turnos | 1 | 1 |

Filtro `FAILED|ERROR|passed|failed|EXIT`: **`results_c.txt` ≡ `results_b.txt`** (diff vacío).  
**Mismos 4 fallos preexistentes**; sin regresiones nuevas; LIMS no tocado; fallos no “arreglados”. Diff exclusivo C sin paths `laboratorio/`.

---

## 2. Mapa de pruebas (referencia; sin duplicar)

Suite: `estudios/tests/test_c_procedimientos.py` — **15 passed** (2026-10-16).

| Requisito | Prueba(s) |
| --- | --- |
| Informe proc: emitir → validar → entregar → rectificar (+ archivo) | `test_informe_proc_emitir_validar_entregar_rectificar` |
| Informe + archivo sin turno/sala (sin Atencion) | `test_circuito_sin_turno_ni_sala_con_informe` |
| Informe vinculado a registro | `test_informe_vincula_registro_cuando_existe` |
| Secretaría registra realización (profesional ≠ actor) | `test_secretaria_marca_realizado_profesional_distinto` |
| Secretaría valida (política operativa actual) | `test_secretaria_valida_informe` |
| Secretaría emite y rectifica (política operativa actual) | `test_secretaria_emite_y_rectifica` |
| Idempotencia (reintento) | `test_idempotencia_marcar_realizado` |
| Concurrencia sin duplicar Atencion/Registro | `test_concurrencia_marcar_realizado_no_duplica` |
| Fallo auditoría → rollback completo | `test_marcar_realizado_rollback_si_falla_auditoria` |
| Atencion incompatible sin parciales | `test_atencion_incompatible_bloquea` |
| Con turno / sala sin turno / sin ambos | `test_realizar_con_turno_crea_atencion_y_registro`, `test_realizar_con_sala_sin_turno`, `test_realizar_sin_turno_ni_sala_sin_atencion` |

Regresión previa (no re-ejecutada en este cierre): A3+A5+API 40 passed; frontend `modules/estudios` 7 passed.

---

## 3. Evidencia UI (recorridos)

No hay E2E UI aparte; los circuitos están cubiertos por las pruebas de §2 y el código de UI (sin duplicar flujos).

| Recorrido | UI | Prueba de circuito |
| --- | --- | --- |
| **Con turno** | Alta proc (`EstudiosComplementarios`) → asignar turno → «Marcar realizado» usa sala del turno (`EstudioComplementarioDetalle` ~L437–465, ~L861–865) → informe/archivos/validar/entregar/rectificar | `test_realizar_con_turno_*` + `test_informe_proc_emitir_validar_entregar_rectificar` |
| **Sin turno / sin sala** | Diálogo realización: profesional obligatorio, sala «Sin sala» (~L823–887) → informe/archivos sin Atencion | `test_circuito_sin_turno_ni_sala_con_informe` |
| **Sala sin turno** | Mismo diálogo con sala opcional → Atencion+Registro | `test_realizar_con_sala_sin_turno` |

Filtro listado Estudios/Procedimientos; reprogramar/anular B conservados. Cirugías / multisesión **off**.

---

## 4. Fuera de este cierre

- Etapa D: ticket de revisión `tickets/TICKET_D_CIRUGIA_BASICA.md` — **no implementado**  
- Multisesión / merge / producción / LIMS  
- Cambiar PK de `RegistroProcedimiento`
