# Ticket D — Cirugía básica (cerrado para revisión de alcance; no implementar)

**Estado:** **implementado** (ver `CIERRE_ETAPA_D.md`) — sin merge ni producción  
**Depende de:** Etapa A–C (`CIERRE_ETAPA_C.md`)  
**SoT:** este ticket prevalece sobre `DOC_DISENO_ESTUDIOS_PROCEDIMIENTOS.md` §Etapa D / §1.7 donde difieran  
**Restricciones duras:** LIMS **absolutamente intocable** (directa e indirectamente). Sin merge ni producción. Conservar estudios, procedimientos (C) y reprogramar/cancelar (B). Multisesión **sigue off**.

**Fuera de D:** quirófano integral (F), checklist OR avanzado, multisesión (E), cambios a factory global de consultorio salvo rama aislada del módulo.

---

## 0. Objetivo

Circuito controlado de **cirugía** (`tipo_actividad=CIRUGIA`, snapshot `QUIRURGICO`):

1. Alta + programación en quirófano / hemodinamia (compatibilidad explícita de catálogo).  
2. Realización **siempre** con `Atencion` + `RegistroQuirurgico` (con o sin turno; **sin** turno ficticio).  
3. Equipo: profesional responsable + **anestesista real** obligatorios en el acto (sin «No aplica», sin ficticios).  
4. **Protocolo quirúrgico** = única fuente editable versionada (PDF + rectificación); puede quedar **pendiente** tras realizar; **bloqueante** para cierre solo si completo y **validado**.  
5. Separar **validación clínica** del protocolo vs **cierre administrativo**.  
6. Permisos, auditoría (quién validó / quién cerró + fechas), idempotencia; UI + verificación en navegador.

---

## 1. Decisiones aceptadas

| # | Decisión |
| --- | --- |
| **D1** | Cirugía **realizada** siempre exige `Atencion` + `RegistroQuirurgico`, con o sin turno. No turno ficticio. |
| **D2** | Profesional responsable (`medico_principal`) **y** anestesista **real** obligatorios al registrar la realización. **No** «No aplica»; **no** profesionales ficticios; **no** flexibilizar nullabilidad de `anestesista` (sigue NOT NULL). |
| **D3** | Protocolo = canónico versionado + PDF + rectificación. **Una** fuente editable; sin duplicar textos (`InformeEstudioComplementario` como vehículo; proyección en `RegistroQuirurgico.protocolo_quirurgico`, no segundo editor). |
| **D4** | Secretaría: programar / reprogramar / cancelar **antes de realización** (acceso + motivo + auditoría B). **No** valida el protocolo. **Sí** puede **cerrar administrativamente** cuando el protocolo ya esté completo y validado. |
| **D5** | Hemodinamia: `PROCEDIMIENTO` o `CIRUGIA` por compatibilidad explícita de catálogo. El recurso **no** decide el hijo clínico. |
| **D6** | Mínimos del acto ≠ requisitos de cierre. Inventario §3. **Sin** cambiar nullabilidad de `anestesista`. Protocolo pendiente post-acto vía canónico versionado (sin textos de relleno). |
| **D7** | Confirmación administrativa de reserva ≠ verificación/validación clínica. **Único** bloqueante acordado para cierre: protocolo **completo y validado**. Sin otros bloqueantes clínicos universales (consentimiento, recuento, dx post, etc. **no** son gates de D). |
| **D8** | Pruebas: realización sin turno; documentación pendiente; validación; cierre; entrega; rectificación. |
| **D9** | Verificación en **navegador** (manual o automatizada). Código ≠ evidencia visual. |

### Decisiones clínicas cerradas (§7)

| Tema | Decisión |
| --- | --- |
| Anestesia | Anestesista real identificado al realizar. Sin «No aplica». Conservar obligatoriedad NOT NULL. |
| Protocolo post-acto | Puede quedar **pendiente** tras realización → bandeja `documentacion_pendiente`. Sin textos de relleno. |
| Gate de cierre | Protocolo **completo y validado** por profesional autorizado. Nada más como bloqueante universal en D. |
| Quién cierra | Profesional autorizado **o** secretaría (cierre administrativo), solo si el gate se cumple. |
| Validación vs cierre | Secretaría **no** valida ni elude requisitos. Backend comprueba el gate **dentro de la TX** de cierre. |
| Trazabilidad | Persistir y auditar **quién validó** y **quién cerró**, con **fechas**. |
| Vehículo canónico | Confirmado §4.2: informe versionado del módulo = único contenido editable del protocolo. |

---

## 2. Alcance funcional

### 2.1 Alta y catálogo

- Alta `CIRUGIA` solo con catálogo `clasificacion_quirurgica=QUIRURGICO`.  
- Rechazar `SIN_ASIGNAR` / `NO_QUIRURGICO`.  
- Conservar `ESTUDIO` y `PROCEDIMIENTO` (C). Multisesión off.

### 2.2 Programación (antes de realización)

- Asignar / reprogramar / anular (B: historial, guarda, `desde_modulo_estudios` solo kwarg interno).  
- Recursos: `QUIROFANO`; `SALA_HEMODINAMIA` si catálogo compatible.  
- Confirmación administrativa de reserva **no** valida protocolo ni habilita cierre.

### 2.3 Realización (acto)

| Condición | Comportamiento |
| --- | --- |
| Con turno | `Atencion` + `RegistroQuirurgico`; vínculo sesión→atención. |
| Sin turno | Igual, **sin** inventar turno. |
| Atencion incompatible | Bloqueo; sin parciales. |

Payload mínimo del acto:

- `profesional_id` (cirujano / `medico_principal`) real.  
- `anestesista_id` real (≠ placeholder; distinto del campo solo si la clínica lo carga así — debe ser `Medico` existente).  
- `diagnostico_preoperatorio` real (sin relleno).  
- Protocolo: **no** exigido aún (queda pendiente).

Actor (secretaria/admin/médico) puede marcar realizado; el responsable y el anestesista van identificados en datos clínicos.  
Idempotencia/concurrencia: no duplicar Atencion/Registro.  
Camino aislado del módulo: **no** factory global con placeholders.

### 2.4 Documentación → validación → cierre → entrega → rectificación

```
REALIZADO (+ Atencion/RQ)
    → documentacion_pendiente (sin protocolo completo/validado)
    → protocolo borrador → emitir → validar (solo clínico autorizado)
    → cierre administrativo (clínico o secretaría; gate en TX)
    → entrega (si el circuito lo define post-cierre)
    → rectificación (nueva versión; re-validar antes de nuevo cierre si aplica)
```

- Canónico versionado: única fuente editable (§4).  
- Cierre **rechaza** si falta protocolo completo/validado (backend, atómico).  
- No exigir consentimiento / recuento / dx post / etc. como bloqueantes de D.

### 2.5 UI

- Filtro `CIRUGIA`.  
- Circuito completo incl. sin turno y documentación pendiente.  
- Acciones de validar vs cerrar claramente separadas.  
- Sin multisesión.

### 2.6 Auditoría y trazabilidad

En TX, con rollback si falla auditoría:

| Evento | Metadata mínima |
| --- | --- |
| Marcar realizado | actor, profesional_id, anestesista_id, estudio/sesión/atencion |
| Emitir / validar / rectificar protocolo | actor, informe_id, versión, `validado_por` + `fecha_validacion` al validar |
| Cerrar | actor (`cerrado_por`), `fecha_cierre`, ref. a versión validada del protocolo, estado previo/nuevo |
| Entregar / reprogramar / anular | como B / estudios |

Debe poder responderse: **quién validó** el protocolo, **cuándo**, **quién cerró**, **cuándo**.

---

## 3. Inventario `RegistroQuirurgico`

Fuente: `turnos/models.py` — PK = `Atencion`.

| Campo | Modelo hoy | Rol en D |
| --- | --- | --- |
| `atencion` | PK | Identidad |
| `anestesista` | FK **NOT NULL** | **Acto:** `Medico` real; **sin** nullability change |
| `diagnostico_preoperatorio` | Text obligatorio | Acto: texto real |
| `protocolo_quirurgico` | Text obligatorio | **Proyección** del canónico versionado; no editor paralelo. Post-acto puede no haber versión aún → pendiente (sin relleno semántico; ver §4.3) |
| `procedimiento` | null/blank | Desde indicación |
| `diagnostico_postoperatorio` | null/blank | No bloqueante D |
| `hallazgos_operatorios` | null/blank | No bloqueante D |
| `complicaciones` | null/blank | No bloqueante D |
| `recuento_instrumental_ok` | bool default False | No bloqueante D |
| `equipo_quirurgico` | JSON blank | No bloqueante D |
| `consentimiento_informado` | File null | No bloqueante D; descarga PROD-4 intacta |
| `documentos_adjuntos` | M2M blank | No bloqueante D |

### 3.1 Consumidores (no romper)

`RegistroQuirurgicoSerializer` / ViewSet / `crear_registro_quirurgico`; tests PROD-4a/4b; factory `AtencionService` (placeholders — **no** usar en D); serializers turnos; `CirugiaForm` / drawer atenciones; `procedimiento_realizacion` (C); docs PROD-4.

**Nullabilidad:** **no** alterar `anestesista`. Cualquier ajuste técnico colateral de `protocolo_quirurgico` solo para soportar “pendiente sin relleno” (p. ej. proyección vacía vs canónico) debe ser aditivo, sin tocar LIMS, y sin reintroducir segundo editor.

---

## 4. Reglas documentales (protocolo canónico)

### 4.1 Fuente de verdad

- Única fuente editable: protocolo versionado (vehículo: `InformeEstudioComplementario` vinculado a indicación `CIRUGIA` + `RegistroQuirurgico`).  
- PDF = render de una versión.  
- Rectificación = nueva versión + motivo; no editar in-place la validada.

### 4.2 Un solo contenido editable (aceptado)

1. Informe versionado del módulo = vehículo de borrador / emitir / validar / PDF / rectificar.  
2. `RegistroQuirurgico.protocolo_quirurgico` = proyección de la versión vigente (sync al emitir/validar), **no** editable en paralelo.  
3. `CirugiaForm` / atenciones: alinear al canónico o excluir edición de protocolo en el flujo del módulo.

Si el vínculo resulta inviable sin impacto LIMS/compartido inaceptable → **parar** y proponer versiones aditivas en `estudios/` sin duplicar texto.

### 4.3 Acto vs cierre

**Acto (marcar realizado)** — obligatorios:

| Dato | |
| --- | --- |
| Paciente | vía indicación |
| Profesional responsable | `medico_principal` |
| Anestesista real | FK NOT NULL, `Medico` existente |
| Tipo intervención / atención | `CIRUGIA` + recurso coherente |
| Procedimiento catálogo | desde indicación |
| Diagnóstico preoperatorio | texto real |
| Protocolo | **no** obligatorio aún |

**Cierre (administrativo)** — único gate acordado:

| Requisito | |
| --- | --- |
| Protocolo canónico **completo** (contenido real, sin relleno) y **validado** por profesional autorizado | Sí — comprobado en backend **dentro de la TX** de cierre |
| Consentimiento / recuento / dx post / hallazgos / equipo | **No** bloqueantes en D |

Estados orientativos: tras realizar → `documentacion_pendiente` mientras no haya protocolo validado; tras validar → habilitado a cerrar; cierre registra `cerrado_por` + `fecha_cierre` (modelo/indicación/auditoría según diseño de implementación aditivo).

---

## 5. Matriz de permisos

| Acción | admin | medico autorizado | secretaria | enfermería |
| --- | --- | --- | --- | --- |
| Alta `CIRUGIA` | Sí | Según escritura clínica del módulo | No | No |
| Asignar / reprogramar / anular (pre-REALIZADO) | Sí | Si agenda del módulo | **Sí** (motivo + auditoría B) | No* |
| Marcar realizado (actor) | Sí | Sí | **Sí** (debe enviar profesional + anestesista reales) | No |
| Ser profesional responsable / anestesista | — | Sí (datos clínicos) | No | No |
| Crear/editar borrador e **emitir** protocolo | Sí | Realizador / autorizado | **No** | **No** |
| **Validar** protocolo | Sí | Autorizado (realizador/admin según reglas del módulo) | **No** | **No** |
| **Rectificar** protocolo | Sí | Autorizado | **No** | **No** |
| **Cerrar** (administrativo) | Sí | Sí | **Sí** — solo si protocolo ya completo y validado; backend enforce | No |
| Eludir gate de cierre / forzar sin validar | No | No | **No** | No |
| Entrega post-cierre (si aplica) | Sí | Sí | Sí (sin validar) | No |
| Multisesión | Off | Off | Off | Off |

\*Salvo regla previa existente fuera de D.

Resumen secretaría: agenda pre-acto + cierre administrativo **condicionado**; **nunca** validación clínica ni bypass.

---

## 6. Criterios de aceptación y pruebas (al implementar)

### 6.1 Automatizadas

- Alta `CIRUGIA` OK; rechazos catálogo/multi.  
- Programación quirófano; hemodinamia solo con compatibilidad de catálogo; hijo clínico por `tipo_actividad`.  
- Guarda B; flag interno no activable por API.  
- Realizar **con** turno → Atencion+RQ; anestesista real persistido.  
- Realizar **sin** turno → igual; sin turno ficticio.  
- Rechazar realización sin anestesista / con id inválido; **nunca** placeholder.  
- Realizar **sin** protocolo → estado/bandeja documentación pendiente; **sin** texto de relleno en canónico.  
- Idempotencia / concurrencia sin duplicar.  
- Atencion incompatible → sin parciales.  
- Secretaría: programar/reprogramar/anular OK.
- Secretaría: operador completo del módulo — emitir / validar / rectificar / cerrar / entregar OK (política operativa: delegación habitual).
- Secretaría: **cierre OK** si protocolo validado; **cierre 4xx** si pendiente o no validado (comprobado en TX).
- Médico/admin: validar; cierre OK.
- Persistencia/auditoría: `validado_por` + fecha; `cerrado_por` + fecha; rollback si falla audit.  
- Entrega post-cierre; rectificación → nueva versión; re-validar antes de cerrar de nuevo si el diseño lo exige.  
- Regresión A/B/C. A0 sin “arreglar”. Diff `laboratorio/` **vacío**.

### 6.2 Navegador (obligatorio para cierre de etapa D)

1. Con turno: alta → programar → realizar (anestesia real, sin protocolo) → documentar/validar → cierre (probar como secretaría tras validación) → entrega → rectificar.  
2. Sin turno: realizar → documentar → validar → cerrar → entregar.  

No usar referencias a código como “verificación visual”.

---

## 7. Decisiones clínicas — cerradas

No quedan preguntas abiertas de alcance D. Cualquier bloqueante clínico adicional (consentimiento, recuento, etc.) queda **fuera** hasta decisión explícita posterior.

---

## 8. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Factory placeholders | Camino D aislado |
| Hemodinamia | Hijo por actividad + catálogo |
| Doble editor protocolo | §4.2; alinear CirugiaForm |
| `protocolo_quirurgico` NOT NULL vs pendiente | Canónico versionado manda; proyección sin relleno semántico |
| Secretaría cierra sin validar | Gate en TX + tests 4xx |
| LIMS | Diff vacío; parar si obliga tocarlo |

---

## 9. Entregables futuros (no ahora)

Paquete exclusivo D, migraciones **aditivas** solo si hacen falta para trazabilidad cierre/validación o proyección (sin nullabilizar `anestesista`), UI, tests §6.1, evidencia navegador §6.2, `CIERRE_ETAPA_D.md`.

**No implementar D en este paso. Sin merge ni producción. LIMS intocable.**
