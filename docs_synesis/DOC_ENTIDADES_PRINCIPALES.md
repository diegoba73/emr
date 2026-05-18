# DOC_ENTIDADES_PRINCIPALES — Entidades del modelo conceptual (Fase C0)

**Versión:** C0 — 18 de mayo de 2026  
**Leyenda:** **[RECTOR]** principio | **[IMPLEMENTADO]** en código | **[OBJETIVO]** futuro | **[DEUDA]** gap conocido

**Fuentes operativas:** `DOC_MODELOS_DB.md`, `DOC_REGLAS_NEGOCIO.md`.

---

## Paciente

| Aspecto | Contenido |
|---------|-----------|
| **Representa** | Identidad demográfica y vínculo opcional a `User` (`pacientes.Paciente`). |
| **No representa** | El encuentro clínico, la orden de lab ni el informe. |
| **Relaciones** | `Turno`, `Atencion`, `HistoriaClinica` 1:1, `SolicitudExamen`, `Muestra`, estudios micro. |
| **Invariantes** | DNI único; no borrado físico con historia (**[RECTOR]**; delete no es flujo estándar). |
| **Estado actual** | **[IMPLEMENTADO]** sin máquina `activo/inactivo` en modelo. |
| **Deuda** | **[OBJETIVO]** fusión de duplicados; **[DEUDA]** validación anti-duplicado solo por DNI. |

---

## Atención / Episodio

| Aspecto | Contenido |
|---------|-----------|
| **Representa** | Encuentro asistencial operativo (`turnos.Atencion`), usualmente 1:1 con `Turno`. |
| **No representa** | La consulta longitudinal de HC (`historias_clinicas.Consulta`) ni la orden LIMS. |
| **Relaciones** | `Paciente`, `Medico`, hijos 1:1 (`ConsultaAmbulatoria`, registros procedimiento/quirúrgico), `emr.Documento`, `SignosVitales`. |
| **Invariantes** | Una atención por turno (OneToOne); paciente/médico coherentes con turno en creación vía servicio. |
| **Estado actual** | **[IMPLEMENTADO]** `estado_clinico`: `ABIERTA`, `FINALIZADA`, `EN_REVISION`. Creación HTTP: `AtencionService` `api_post_compat=True`. |
| **Deuda** | **[DEUDA]** Doble concepto “consulta” (HC vs ambulatoria). **[OBJETIVO]** mapa conceptual “pendiente/en curso/cerrada” alineado a estados reales. |

---

## Orden

| Aspecto | Contenido |
|---------|-----------|
| **Representa** | Pedido de estudios o trámite: **`SolicitudExamen`** (LIMS nativo) y/o **`solicitudes.Solicitud`** (EMR + LIMS externo). |
| **No representa** | El resultado ni la muestra ya procesada (aunque dispara su creación). |
| **Relaciones** | Paciente, médico interno/externo, M2M tipos/paneles; filas `ResultadoExamen` al crear orden LIMS. |
| **Invariantes** | Número de protocolo único LAB-…; estado de orden no editable por PATCH CRUD estándar. |
| **Estado actual** | **[IMPLEMENTADO]** `SolicitudExamen.estado`: ver `DOC_ESTADOS_TRANSICIONES.md`. |
| **Deuda** | **[DEUDA]** Dos sistemas de orden sin FK obligatoria entre sí. |

---

## Muestra

| Aspecto | Contenido |
|---------|-----------|
| **Representa** | Tubo/material trazable (`laboratorio.Muestra`) ligado a orden y paciente. |
| **No representa** | La orden completa ni el informe final. |
| **Relaciones** | `SolicitudExamen`, `Paciente`, `ResultadoExamen` (opcional), `EstudioMicrobiologico`, `EventoMuestra`. |
| **Invariantes** | Coherencia paciente orden-muestra en `clean`; rechazo impide validación de resultados vinculados. |
| **Estado actual** | **[IMPLEMENTADO]** máquina B1 en `muestra_estado.py`. |
| **Deuda** | **[DEUDA]** `tomar-muestra` en orden vs toma física `Muestra` (doble marcador). |

---

## Determinación / Examen

| Aspecto | Contenido |
|---------|-----------|
| **Representa** | Catálogo `TipoExamen` / ítems de `PanelExamen` (qué se solicita). |
| **No representa** | El valor medido (eso es `ResultadoExamen`). |
| **Relaciones** | `TipoMuestra` requerida; M2M en orden; 1 fila resultado por (orden, tipo). |
| **Invariantes** | `unique_together` (solicitud, tipo_examen). |
| **Estado actual** | **[IMPLEMENTADO]** catálogo + B4.1 campos estructurados en tipo/resultado. |
| **Deuda** | — |

---

## Resultado

| Aspecto | Contenido |
|---------|-----------|
| **Representa** | `ResultadoExamen` (valor, flags, validación, muestra opcional). |
| **No representa** | Informe narrativo micro (`InformeMicrobiologico` es capa aparte). |
| **Relaciones** | `SolicitudExamen`, `TipoExamen`, `Muestra` nullable, `validado_por`. |
| **Invariantes** | No validar orden con valores vacíos; no cargar en orden terminal. |
| **Estado actual** | **[IMPLEMENTADO]** validación vía acción `validar` (admin); sin estado “CORREGIDO” en modelo. |
| **Deuda** | **[OBJETIVO]** corrección versionada post-validación; **[DEUDA]** `bulk_update` en validar vs auditoría “before”. |

---

## Informe

| Aspecto | Contenido |
|---------|-----------|
| **Representa** | **[IMPLEMENTADO]** `InformeMicrobiologico` (PRELIMINAR/FINAL, estados B3.4). **[OBJETIVO]** informe PDF/HL7 general LIMS. |
| **No representa** | La fila de resultado individual de química/hematología. |
| **Relaciones** | `EstudioMicrobiologico`, validador, emisor. |
| **Invariantes** | Informe FINAL validado no se edita sin anulación (**[RECTOR]**; ver reglas micro en código). |
| **Estado actual** | **[IMPLEMENTADO]** B3.4. |
| **Deuda** | **[DEUDA]** `marcar-entregado` en orden ≠ informe PDF. |

---

## Auditoría

| Aspecto | Contenido |
|---------|-----------|
| **Representa** | `auditoria.AuditEvent` append-only + eventos de dominio (`EventoMuestra`, transiciones orden). |
| **No representa** | Log de aplicación Django genérico. |
| **Relaciones** | Actor `User`, entidad (tipo + id), before/after sanitizados. |
| **Invariantes** | No UPDATE/DELETE en `AuditEvent` vía ORM estándar. |
| **Estado actual** | **[IMPLEMENTADO]** `on_commit` en transacciones; sanitizer. |
| **Deuda** | **[DEUDA]** cobertura desigual entre views; blacklist recursión. |

---

## Usuario / Rol

| Aspecto | Contenido |
|---------|-----------|
| **Representa** | `usuarios.User` + perfiles (`Medico`, `Paciente`, …). |
| **No representa** | Permisos finos por objeto sin código explícito. |
| **Relaciones** | Rol en `ROL_CHOICES`; grupos Django nombrados. |
| **Invariantes** | Separación `laboratorio` (LIMS) vs clínico EMR (`IsEMRClinician`). |
| **Estado actual** | **[IMPLEMENTADO]** ver `reglas/usuarios-y-permisos.md`. |
| **Deuda** | **[DEUDA]** muchos `get_queryset` manuales vs clases de permiso. |

---

## IA (asistente, no autoridad)

| Aspecto | Contenido |
|---------|-----------|
| **Representa** | **[OBJETIVO]** asistencia a documentación clínica (campos preparados en HC). |
| **No representa** | Validación, firma, diagnóstico definitivo ni emisión de informe. |
| **Relaciones** | Futuras: sugerencias ligadas a entidad + actor aceptador. |
| **Invariantes** | Ver `reglas/ia.md`. |
| **Estado actual** | **[OBJETIVO]** sin servicio IA productivo en repo. |
| **Deuda** | Campos “para IA” en modelos HC sin pipeline. |
