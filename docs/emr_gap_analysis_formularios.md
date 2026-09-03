# Gap analysis — formularios físicos ICPL vs EMR

**Fecha:** 2026-08-24  
**Regla de esta entrega:** solo análisis. Sin cambios de código ni migraciones destructivas.  
**Fuente:** `docs/formularios_historia_clinica/` + paquete `emr_formularios_cursor` (transcripción, JSON e imágenes 01–10).

Las imágenes coinciden con la transcripción, con matices de papel:

- Hoja 02: checkboxes de antecedentes (IC, Angor-IAM, HTA, ACV, EAOP, valvulopatías, diabetes, etc.).
- Hoja 05: plan terapéutico + grilla horaria 6–4 (pasos de 2 h en el impreso visto).
- Hoja 06: gráficos de T / pulso / PA; catarsis y FR por turno; glucemia + pauta de insulina (médico).
- Hoja 07: MAR enfermería, horas 6→5, observaciones y firma.
- Hoja 08: catálogo A–G / H–J del día + tres turnos horarios + oral/orina/catarsis.
- Hoja 10: analitos en filas × fechas en columnas (hasta 7). Pedido de carga en papel: médico; en EMR el LIMS ya carga laboratorio.

---

## Inventario rápido del EMR actual

| Capa | Qué hay |
|---|---|
| Stack | Django 5.2 / DRF / JWT; React 19 + MUI 7; Postgres 15 (`emr_postgres` / `synesis_db`) |
| Internación viva | App `internacion`: `Sector`, `Cama`, `Internacion`, dieta, HC papel reciente |
| Episodio clínico | `Internacion` + `turnos.Atencion` (`contexto_atencion=INTERNACION`) + `EvolucionInternacion` SOAP |
| HC papel (2026-08) | `IndicacionMedica`, `MedicacionInternacion`, `ControlEnfermeria`, `BalanceHidrico`, `NotaEnfermeria`, `RegistroKinesiologia` |
| APIs HC | `/api/internacion/internaciones/{id}/indicaciones-medicas/` (y medicaciones, controles, balances, notas, kinesiología) |
| UI | Modal cama: Revista de sala + pestaña Formularios HC + administrativos |
| Roles | Lectura internación: admin, médico, enfermería, secretaría, kinesiólogo. Escritura HC: médico / enfermería / kinesiólogo. SOAP: médico. Alta: médico/admin |
| Laboratorio | LIMS: `TipoExamen` + `SolicitudExamen` + `ResultadoExamen` (catálogo, no tabla ancha). Origen `INTERNACION_UCO/UCE` inferido; **sin FK a internación** |
| Auditoría | `auditoria.AuditEvent` append-only (request). **No** hay firma clínica / inmutabilidad de notas HC |
| Duplicado | `historias_clinicas.Internacion` + `Prescripcion` sobre consulta: legado, no es el censo de camas |

---

## Tabla de gaps

| Formulario | Requisito/campo | Existe | Implementación actual | Problema | Cambio propuesto | Prioridad | Riesgo |
|---|---|---|---|---|---|---|---|
| 01 Ingreso | Nº HC / internación | PARCIAL | `Internacion.numero_internacion` | No se muestra como “H. Cl. Nº” de papel en todas las hojas | Alias de UI + cabecera compartida | P2 | Bajo |
| 01 | Nombre, edad, OS, DNI, dirección, teléfono | PARCIAL | `pacientes.Paciente` | Edad calculada; ficha no está en el formulario de ingreso de internación | Reusar paciente; mostrar cabecera read-only en HC | P2 | Bajo |
| 01 | Estado civil | NO EXISTE | — | No está en `Paciente` | Campo opcional en paciente (no en episodio) | P3 | Bajo |
| 01 | Familiar + teléfono | PARCIAL | En `usuarios.User` (`contacto_emergencia_*`), no en `Paciente` | No viaja con la ficha clínica de internación | Contacto de emergencia en `Paciente` (episodio puede copiar snapshot) | P2 | Medio |
| 01 | Médico tratante | COMPLETO | `Internacion.medico` | — | Mantener | P3 | Bajo |
| 01 | Fecha/hora internación y externación | PARCIAL | `fecha_ingreso` auto; `fecha_alta` | Hora de ingreso no editable; externación = alta | Permitir `fecha_ingreso` clínica; alta ya cubre externación | P2 | Medio |
| 01 | Alergias sí/no + ¿a qué? | PARCIAL | `Internacion.alergias` texto | Sin boolean; también hay alergias en User | Boolean + detalle en episodio; lectura global | P1 | Bajo |
| 01 | Motivo de consulta | PARCIAL | `motivo_ingreso` | No está en UI de Formularios HC | Mapear a motivo de consulta del ingreso | P1 | Bajo |
| 01 | Enfermedad actual | PARCIAL | `anamnesis_ingreso` texto libre | OK como narrativa; falta etiqueta de papel | Renombrar UI; no partir el modelo aún | P1 | Bajo |
| 01 | Medicación habitual (fármaco + mg/día, 0..n) | EXISTE PERO DEBE REFACTORIZARSE | `medicacion_habitual` texto | Papel es lista estructurada | Tabla `MedicacionHabitualInternacion` (nombre, dosis mg/día) | P1 | Medio |
| 02 Antecedentes | Check sí/no (IC, Angor-IAM, HTA, …) | PARCIAL | `Paciente.antecedentes_personales` texto | No hay checklist cardiológico de ingreso | JSON/catálogo de flags **por internación** (snapshot) | P1 | Medio |
| 02 | AHF | PARCIAL | `antecedentes_familiares` en paciente | No ligado al episodio de ingreso | Campo AHF en internación o snapshot | P2 | Bajo |
| 02 | Examen por sistemas (EG, piel, psiquis, …) | PARCIAL | `examen_fisico_ingreso` texto único | Papel es por aparato + pulsos R/L | Estructura `ExamenIngresoInternacion` (secciones + pulsos) | P1 | Medio |
| 02 | PA, FC, ritmo, R1–R4, soplos | PARCIAL | Texto / signos en `Atencion` | No hay examen CV de ingreso tipado | Campos en examen de ingreso | P1 | Medio |
| 02 | Diagnóstico + plan estudio/tto | PARCIAL | `diagnostico_ingreso` + CIE-10; plan SOAP | Plan de ingreso no es entidad propia | `plan_estudio_tratamiento` en internación | P1 | Bajo |
| 02 | Firma/sello | NO EXISTE | `registrado_por` en otras hojas | Notas de ingreso se pueden editar sin cierre | Estado borrador/firmado + autor (fase posterior) | P2 | Alto |
| 03 Evolución médica | Notas repetibles fecha/hora/autor/texto | PARCIAL | `EvolucionInternacion` SOAP vía `Atencion` | Papel es nota libre; digital es SOAP; 1 diaria | Mantener SOAP; permitir más de una nota/día si hace falta; no sobrescribir firmadas | P1 | Medio |
| 03 | Hab/cama histórica | PARCIAL | Cama actual en internación | Traslado pisa cama; no hay historial de ubicación | Evento de traslado (ya hay mover-cama; falta histórico UI) | P3 | Medio |
| 04 Kinesiología | Log fecha/hora/texto/profesional | PARCIAL | `RegistroKinesiologia` (FR, SpO2, O2, secreciones, técnica, movilización, evolución, plan) | Más estructurado que el papel (bien); falta `performed_at` editable y estado | Añadir `fecha_clinica`; no borrar logs; rol kine ya OK | P2 | Bajo |
| 05 Indicaciones | Orden médica (qué se indicó) | PARCIAL | `IndicacionMedica` (hidratación, O2, reposo, controles, texto) + `MedicacionInternacion` | Mezcla diet/O2 con plan; medicación sin catálogo ni vía tipada | Separar: orden no farmacológica vs `MedicationOrder`; dieta ya existe | P1 | Alto |
| 05 | Programación horaria | PARCIAL | `horario` string en medicación | No hay ocurrencias 06–24 | `MedicationSchedule` (hora prevista) | P1 | Alto |
| 05 | Prescriptor, fecha, estado | PARCIAL | `registrado_por`, `fecha`, `vigente`/`activa` | Sin suspendida/vencida/reemplazada | Estados de orden | P1 | Medio |
| 07 Cumplimiento | Administración real (MAR) | NO EXISTE | Grilla de papel no modelada | Enfermería no registra toma con hora real, dosis, vía, estado | `MedicationAdministration` ligado a la orden | P1 | Alto |
| 06 Controles | T, pulso, TAS/TAD como serie temporal | EXISTE PERO DEBE REFACTORIZARSE | `ControlEnfermeria`: un snapshot por turno (TA string, FC, FR, T, SpO2, dolor, glucemia) | Papel: un valor por hora, gráficos, TAS y TAD separados; catarsis | Observaciones (`VitalSign`) tipo+valor+unidad+`performed_at` | P1 | Alto |
| 06 | Catarsis por turno | NO EXISTE | — | — | Observación `catarsis` o campo en control | P2 | Bajo |
| 06 | Glucemia + equipo | PARCIAL | `glucemia` en control | Sin dispositivo ni hora independiente | `GlucoseMeasurement` | P1 | Medio |
| 06 | Pauta insulina (tipo, freq, escala) | NO EXISTE | Texto en indicaciones | Es orden médica, no del gráfico | Orden de insulina + escala; enfermería ejecuta | P1 | Medio |
| 08 Balance UTI | Ingresos/egresos individuales A–G, H–J, oral, orina, catarsis, por hora | EXISTE PERO DEBE REFACTORIZARSE | `BalanceHidrico`: totales VO/EV/diuresis/otros **por turno** | No hay movimientos horarios ni catálogo del día; totales no se calculan | `FluidBalanceDay` (peso, labels A–J) + `FluidBalanceEntry` + totales derivados | P1 | Alto |
| 08 | Peso previo/actual | NO EXISTE | `SignosVitales.peso` en atención | No en hoja de balance | Pesos en el día de balance | P2 | Bajo |
| 08 | BOX Nº | PARCIAL | `Cama.nombre` + sector | — | Mostrar en cabecera | P3 | Bajo |
| 09 Comentarios enf. | Notas repetibles | PARCIAL | `NotaEnfermeria` + tipo `NOTA_ENFERMERIA` en evolución | Dos canales; sin `performed_at` editable ni firma | Unificar en notas de episodio; no usar SOAP de médico | P2 | Medio |
| 10 Laboratorio | Grupo y factor | PARCIAL | `User.grupo_sanguineo` | No en `Paciente` ni hoja internación | Campo en paciente; mostrar en revista | P2 | Bajo |
| 10 | Resultados por analito y fecha | COMPLETO (LIMS) / PARCIAL (vista internación) | `TipoExamen` + `ResultadoExamen`; revista muestra labs del episodio por origen | Tabla ancha de papel **no** existe (correcto). Falta vista tipo “grilla de tendencia” y vínculo explícito internación | Reusar LIMS; UI de tendencia en internación; FK opcional `internacion` | P2 | Medio |
| 10 | Pedido desde internación | COMPLETO | Pedido lab en revista **sin** exigir evolución | — | Mantener | P3 | Bajo |
| Trasversal | Dato en episodio, no solo paciente | PARCIAL | Internación FK en hojas HC | Antecedentes/alergias mixtos paciente vs episodio | Snapshot de ingreso en internación | P1 | Medio |
| Trasversal | Autor, rol, created_at, estado, no overwrite firmado | PARCIAL | `registrado_por` + timestamps; AuditEvent HTTP | HC se puede PATCH/DELETE; SOAP editable | Soft-delete / adenda; prohibir delete de firmados | P1 | Alto |
| Trasversal | Roles papel (médico / enf / kine) | COMPLETO | `ROLES_HC_*` + UI | Secretaría lee; kine no admite | Mantener; MAR solo enfermería | P1 | Bajo |

---

## Mapa campo → modelo → tabla → API → pantalla

| Campo formulario | Modelo | Tabla | API | Pantalla |
|---|---|---|---|---|
| Identificación paciente | `Paciente` | `pacientes_paciente` | `/api/pacientes/` | Ficha paciente; cabecera modal internación |
| Nº internación | `Internacion` | `internacion_internacion.numero_internacion` | `/api/internacion/internaciones/{id}/` | Modal gestionar |
| Cama / sector | `Cama`, `Sector` | `internacion_cama` | `/api/internacion/camas/` | Dashboard camas |
| Médico tratante | `Internacion.medico` | FK medicos | PATCH internación | Datos administrativos |
| Motivo / anamnesis / alergias / examen / med. habitual | `Internacion` | columnas texto | PATCH internación | Formularios HC (médico) |
| Diagnóstico | `diagnostico_ingreso` + `diagnostico_cie` | internacion + catalogos | PATCH | Administrativo + revista |
| Dieta | `TipoDieta` | `internacion_tipodieta` | PATCH `tipo_dieta_id` | Administrativo |
| Evolución SOAP | `EvolucionInternacion` + `Atencion` | `turnos_evolucioninternacion` | `iniciar-evolucion`, atenciones | Revista de sala |
| Indicaciones | `IndicacionMedica` | `internacion_indicacionmedica` | `.../indicaciones-medicas/` | Formularios HC médico |
| Medicación internación | `MedicacionInternacion` | `internacion_medicacioninternacion` | `.../medicaciones/` | Formularios HC médico |
| MAR / cumplimiento | — | — | — | **No hay** |
| Controles enf. | `ControlEnfermeria` | `internacion_controlenfermeria` | `.../controles-enfermeria/` | Formularios HC enfermería |
| Signos en consulta | `emr.SignosVitales` | `emr_signosvitales` | atenciones | Evolución (no hoja 06) |
| Balance | `BalanceHidrico` | `internacion_balancehidrico` | `.../balances-hidricos/` | Formularios HC enfermería |
| Notas enf. | `NotaEnfermeria` | `internacion_notaenfermeria` | `.../notas-enfermeria/` | Formularios HC enfermería |
| Kine | `RegistroKinesiologia` | `internacion_registrokinesiologia` | `.../kinesiologia/` | Formularios HC kine |
| Laboratorio | `SolicitudExamen`, `ResultadoExamen`, `TipoExamen` | `laboratorio_*` | `/api/laboratorio/...` | Revista (pedir + historial); LIMS |
| Prescripción ambulatoria | `historias_clinicas.Prescripcion` | sobre `Consulta` | — | Consultorio; **no** internación cama |

---

## Plan por fases (esperar aprobación)

No hay migración gigante. Cada fase es reversible (`migrate` reverse de la app `internacion` / `pacientes` / `laboratorio` según el caso). Rollback: revertir migración + deploy previo; no `down -v`.

### Fase 0 — Cabecera y ficha de ingreso (médico)

Alinear UI al papel 01–02 **reusando** `Internacion` + `Paciente`.

1. Archivos: `internacion/serializers.py`, `FormulariosHcInternacion.tsx`, tipos frontend.  
2. Migraciones: `Paciente` contacto emergencia; internación `tiene_alergias`; `plan_estudio_tratamiento`; opcional `estado_civil`.  
3. Endpoints: PATCH internación (solo `ROLES_HC_MEDICO` en campos HC, ya hay validación).  
4. UI: sección ingreso con motivo, enfermedad actual, alergias sí/no, lista medicación habitual.  
5. Permisos: sin cambio de roles.  
6. Tests: patch enf 400; médico 200; kine GET.  
7. Aceptación: médico carga 01; todos leen; enf/kine no editan.  
8. Rollback: reverse migration; campos texto viejos se conservan.

### Fase 1 — Antecedentes y examen de ingreso estructurado

1. Modelo `ExamenIngresoInternacion` 1:1 internación + flags antecedentes JSON o tabla.  
2. Migración internacion.  
3. Nested `GET/PUT .../examen-ingreso/`.  
4. UI checklist + pulsos R/L.  
5. Solo médico escribe.  
6. Tests de rol y persistencia.  
7. Checklist papel 02 completo; texto libre `examen_fisico_ingreso` se migra como “otros”.  
8. Rollback: drop tabla nueva; conservar texto legado.

### Fase 2 — Indicaciones vs administración (crítico)

Separar orden / programación / cumplimiento.

1. `MedicationOrder`, `MedicationSchedule`, `MedicationAdministration` FK internación; deprecar uso de `horario` string.  
2. Migraciones; copiar `MedicacionInternacion` → órdenes (script).  
3. APIs: órdenes (médico); administraciones (enfermería).  
4. UI: médico indica; enf marca MAR (hora real, estado).  
5. Permisos: write split.  
6. Tests 403 cruzados.  
7. Una indicación no se “cumple” solo con columnas horarias; cada toma es fila.  
8. Rollback: mantener tablas viejas hasta cutover.

### Fase 3 — Controles como observaciones

1. `ObservacionClinica` (tipo, valor, unidad, performed_at, internacion, autor) o reusar `SignosVitales` **con internacion_id**.  
2. Migrar `ControlEnfermeria` a observaciones.  
3. List/filter by tipo y rango fechas.  
4. UI: carga puntual + gráfico simple (no calcar papel).  
5. Write enfermería; pauta insulina = orden médica (fase 2).  
6. Tests series temporales.  
7. T, FC, TAS, TAD, FR, glucemia, catarsis con timestamp.  
8. Rollback: tabla controles se conserva read-only.

### Fase 4 — Balance UTI real

1. `BalanceHidricoDia` + `MovimientoHidrico`.  
2. Cálculo de totales hora/turno/día en servicio (no columnas denormalizadas).  
3. API nested.  
4. UI por turno 06–14 / 14–22 / 22–06.  
5. Solo enfermería escribe.  
6. Tests de suma neta.  
7. A–G y H–J configurables por día.  
8. Rollback: `BalanceHidrico` actual queda hasta vaciar.

### Fase 5 — Notas: evolución, kine, enfermería (inmutabilidad)

1. Estado `borrador|firmado` en evoluciones, kine, notas; `fecha_clinica`.  
2. Sin DELETE de firmados; adenda.  
3. Endpoints PATCH limitado.  
4. UI deshabilita edición firmada.  
5. Roles actuales.  
6. Tests.  
7. Cumple regla “no sobrescribir notas firmadas”.  
8. Rollback: flag estado default borrador.

### Fase 6 — Laboratorio en internación (sin tabla ancha)

1. FK opcional `SolicitudExamen.internacion`; vista tendencia analitos del catálogo hoja 10.  
2. Migración laboratorio (no romper pedidos actuales).  
3. Endpoint contexto-revista ya lista labs; agregar pivot read-only.  
4. Revista: grilla fechas × analitos **desde resultados LIMS**.  
5. Pedido: médico (como ahora); carga resultado: LIMS.  
6. Tests origen internación.  
7. Grupo/factor en paciente.  
8. Rollback: FK null.

---

## Criterios globales de aceptación (cuando se implemente)

1. Ingreso/anamnesis  
2. Antecedentes  
3. Examen inicial  
4. Evolución médica  
5. Kinesiología  
6. Indicaciones médicas  
7. Controles de enfermería  
8. Cumplimiento/administración  
9. Balance UTI  
10. Comentarios de enfermería  
11. Laboratorio (catálogo + resultados, no columnas fijas)

Roles: kine solo hoja 04; enf 06, 07, 08, 09; médico 01, 02, 03, 05 y pedidos lab; todos leen.

---

## Decisiones (no negociar en silencio)

- **No** copiar grillas de papel en HTML.  
- **No** crear `hemoglobina`, `urea`, … en internación.  
- **No** mezclar `historias_clinicas.Internacion` con el censo de camas.  
- **No** tocar `.env` / Postgres nativo.  
- Esperar **aprobación de fases** (sobre todo 2, 3 y 4) antes de migraciones de modelo.
