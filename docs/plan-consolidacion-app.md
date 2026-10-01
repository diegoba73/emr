# Plan estratégico de consolidación de SYNESIS EMR

Fecha: 24 de septiembre de 2026. Estado: propuesta para priorización; no acredita que los controles estén implementados ni autoriza cambios en producción.

## 1. Objetivo y alcance

Consolidar la aplicación para que el equipo pueda mantenerla, verificar sus cambios y operarla diariamente con evidencia de confiabilidad. Preparar su crecimiento sin reescribir el producto ni fragmentarlo prematuramente en servicios.

El alcance comprende frontend, API, PostgreSQL, archivos clínicos, permisos, auditoría, integraciones, pruebas, infraestructura y operación. Los cambios funcionales urgentes pueden continuar; deben pasar por los controles que se incorporen.

Resultados esperados:

1. Una persona distinta del desarrollador original puede levantar el sistema, diagnosticar un fallo y seguir el procedimiento de recuperación.
2. Cada versión publicada identifica su código, pasa controles reproducibles y tiene una estrategia de recuperación compatible con sus migraciones.
3. Los circuitos prioritarios tienen pruebas de éxito, rechazo de accesos, errores y concurrencia.
4. Cada módulo tiene responsabilidades y contratos claros, con complejidad y dependencias en reducción.
5. Las decisiones de capacidad se toman con mediciones y un escenario de crecimiento acordado.

## 2. Punto de partida comprobado

| Evidencia del repositorio | Implicación para el plan |
| --- | --- |
| `.github/workflows/smoke.yml` ejecuta un conjunto acotado de pruebas de backend con SQLite; frontend ejecuta Jest y build. | Ampliar cobertura por riesgo y agregar integración con PostgreSQL antes de confiar en la equivalencia con producción. |
| CI de frontend configura Node 18 y el Dockerfile del demo usa Node 20. | Elegir y verificar una versión soportada, y alinear desarrollo, CI e imágenes; revisar también Python y PostgreSQL. |
| `deploy/backup/` contiene plantillas de respaldos de base y archivos y un procedimiento de restauración. | Verificar automatización real, copias externas, alertas y restauración consistente. La documentación sola no acredita recuperabilidad. |
| `deploy/observability/` contiene controles operativos de ejemplo. | Convertir los controles necesarios en monitoreo continuo, con responsables y alertas probadas. |
| Hay permisos en `utils/permissions.ts`, `utils/limsAccess.ts` y módulos específicos. | Relevar una matriz común y verificar su cumplimiento en backend; no basta con ocultar acciones en pantalla. |
| Componentes como `OrdenLimsDetalle`, inventario y control de calidad concentran muchas responsabilidades. | Refactorizar por secciones y casos de uso, con pruebas previas de comportamiento. |
| La documentación del servidor describe configuraciones específicas fuera del repositorio y una rama con cambios propios. | Relevar diferencias, preservar cambios necesarios y converger hacia artefactos reproducibles sin secretos en Git. |
| El demo tiene una base separada; sus recorridos y marca se actualizaron recientemente. | Mantener aislamiento y usarlo para demostración. Crear staging independiente para validar versiones. |

No se verificaron en esta revisión la ejecución real de backups productivos, la restauración completa, métricas de disponibilidad, la seguridad integral ni la capacidad bajo carga. Son asuntos por demostrar, no defectos afirmados.

## 3. Organización y capacidad

Horizonte orientativo: 12 semanas para una primera consolidación, con dos desarrolladores, apoyo operativo y participación regular de referentes funcionales. Estimación a recalibrar al cerrar la primera etapa. Con un único desarrollador y atención simultánea de soporte, prever aproximadamente 16–24 semanas o reducir el alcance sin quitar controles críticos.

| Responsabilidad | Compromiso necesario |
| --- | --- |
| Responsable del producto — inicialmente Diego | Priorizar, aprobar circuitos, definir criticidad y aceptar entregables. |
| Responsable técnico | Arquitectura, revisiones, CI, calidad y coordinación de cambios. |
| Desarrollo | Implementación y pruebas; revisión cruzada cuando haya capacidad. |
| Operación | Entornos, acceso, backups, monitoreo, despliegue y recuperación. |
| Verificación funcional | Casos reproducibles y pruebas de aceptación. Puede compartir rol con otra persona, pero debe tener tiempo asignado. |
| Referentes médico, enfermería y laboratorio | Validar estados, responsabilidades y resultados esperados; no se reemplaza esta revisión con pruebas de código. |

Una misma persona puede cubrir varios roles. Para operaciones críticas debe existir una segunda revisión cuando sea posible y un suplente capaz de seguir los procedimientos.

Reserva inicial de capacidad propuesta: 60% consolidación, 25% correcciones y soporte, 15% funcionalidad prioritaria. Limitar el trabajo simultáneo a dos iniciativas de consolidación. Un incidente grave desplaza el trabajo planificado.

## 4. Etapas, entregables y condiciones de avance

### Etapa 1 — Conocer y proteger la operación (semanas 1–2)

**Objetivo:** establecer qué existe, qué puede fallar y cómo recuperar el servicio.

Trabajo:

- Inventariar entornos, componentes, versiones, volúmenes, integraciones, responsables y accesos. Separar demo, desarrollo, staging y producción.
- Registrar la revisión Git y la configuración no secreta de cada entorno; relevar diferencias de la rama del servidor.
- Identificar los diez circuitos más críticos y clasificar incidentes y riesgos por impacto y probabilidad.
- Revisar respaldos de PostgreSQL y archivos, consistencia entre ambos, permisos, cifrado, retención y copia fuera del servidor.
- Ejecutar una restauración en entorno aislado: base, adjuntos, configuración necesaria y versión compatible de la aplicación. Verificar archivos referenciados y estados de operaciones, además de conteos.
- Relevar usuarios y credenciales demo, sesiones, privilegios, exposición de archivos y configuración de transporte en el entorno productivo. Priorizar cualquier acceso indebido confirmado.
- Establecer mediciones iniciales de errores, tiempos de respuesta, incidentes y uso de recursos.

Entregables: mapa del sistema, inventario de entornos, registro de riesgos priorizado, matriz inicial de criticidad, procedimiento de contingencia e informe de restauración sin datos clínicos en Git.

Condición de avance: restauración demostrada y medida; riesgos críticos con contención o resolución; responsables y accesos operativos identificados. Si no se puede restaurar, esa brecha conserva prioridad sobre mejoras estructurales.

### Etapa 2 — Publicar versiones reproducibles (semanas 3–4)

**Objetivo:** evitar diferencias desconocidas entre lo probado y lo publicado.

Trabajo:

- Crear staging con PostgreSQL y topología representativa; usar datos sintéticos o preparados con un procedimiento aprobado.
- Alinear versiones de ejecución y dependencias; fijar imágenes y artefactos por identificador inmutable y establecer su actualización controlada.
- Extender CI con pruebas de integración PostgreSQL, comprobación de migraciones, chequeo de tipos y build. Mantener controles rápidos por cambio y una suite más amplia periódica.
- Incorporar revisión de cambios, controles obligatorios de CI y validación de permisos de publicación en GitHub.
- Compilar una vez por versión y promover el mismo artefacto validado en staging. Mostrar identificador de versión y entorno en un lugar consultable de la aplicación.
- Reemplazar cambios manuales del servidor por configuración reproducible; mantener secretos en un mecanismo operativo restringido.
- Separar despliegue normal, migraciones y carga de datos de ejemplo. Los seeds demo deben rechazar entornos no autorizados.
- Definir recuperación por cambio: reversión de imagen cuando sea compatible; para migraciones, evaluar compatibilidad, corrección hacia adelante o restauración con impacto explícito sobre datos recientes.

Entregables: pipeline, staging, procedimiento de publicación, inventario de secretos sin valores, registro de versiones y procedimiento de recuperación por tipo de cambio.

Condición de avance: dos publicaciones consecutivas verificadas en staging y un ejercicio de reversión compatible. La versión servida debe coincidir con el artefacto aprobado, incluidos frontend y backend.

### Etapa 3 — Verificar datos, permisos y circuitos completos (semanas 5–7)

**Objetivo:** proteger comportamientos que atraviesan varios módulos.

Trabajo:

- Completar matriz de rol × acción × recurso × estado × ámbito de datos, y convertir sus casos críticos en pruebas del backend.
- Revisar acceso directo por identificador: pacientes, órdenes, adjuntos e informes, tanto en lectura como escritura.
- Documentar estados y transiciones de atención, internación, solicitud, muestra, resultado e informe. Definir quién puede cambiar cada estado y qué invariantes conserva.
- Agregar pruebas de concurrencia e idempotencia con PostgreSQL: doble reserva incompatible, ocupación simultánea de cama, doble recepción, reintentos y validación concurrente.
- Verificar exactitud de cálculos, redondeos, unidades, fechas y zona horaria con casos aprobados por referentes del dominio, especialmente en laboratorio.
- Diseñar contratos de API y errores estables; evitar mensajes de éxito antes de confirmar persistencia y pérdidas de edición no advertidas.
- Verificar que auditoría registre actor, recurso, acción y resultado según el caso. Proteger acceso y retención de auditoría; separar estos registros de logs operativos sin datos clínicos innecesarios.
- Probar fallos de API, sesiones vencidas, interrupciones de red y reintentos de integraciones. Evitar duplicados y fallos silenciosos.

Circuitos iniciales de aceptación:

| Circuito | Comprobaciones prioritarias |
| --- | --- |
| Identificación y ficha | Paciente correcto; acceso por rol y ámbito; actualización y trazabilidad. |
| Agenda y atención | Reserva y cambio de estado; ausencia de duplicados incompatibles; vínculo correcto con la atención. |
| Guardia e internación | Derivación y pedidos relacionados; ocupación exclusiva; alta restringida por rol. |
| Enfermería | Escritura de formularios propios, identificación de autor y fecha; límites frente a funciones médicas. |
| Laboratorio | Pedido → muestra → recepción → carga → validación → informe; coherencia de valores, estado y autor. |
| Portal y archivos | Solo recursos autorizados; publicación de informes según estado; descarga autenticada y rechazo de acceso ajeno. |
| Integraciones | Repetición, mensajes incompletos, desconexión y reconciliación, según interfaces efectivamente instaladas. |

Entregables: matriz de permisos y estados, casos de aceptación, suite de regresión por circuito y registro de defectos corregidos.

Condición de avance: circuitos críticos aprobados por referente y pruebas automatizadas; ningún acceso indebido o defecto de integridad crítico conocido pendiente de resolución para el alcance a liberar.

### Etapa 4 — Reducir complejidad y medir capacidad (semanas 8–10)

**Objetivo:** facilitar cambios sin degradar comportamiento.

Trabajo:

- Priorizar componentes según complejidad, frecuencia de cambios e incidentes; empezar por dos o tres, no por todo el repositorio.
- Separar presentación, formularios, consulta de datos y casos de uso; centralizar reglas compartidas y eliminar duplicaciones cuando exista evidencia de equivalencia.
- Mantener un monolito modular: definir límites entre pacientes, atención, internación, laboratorio, documentos, usuarios y auditoría. Documentar dependencias y decisiones relevantes.
- Establecer contratos de API y de errores; migrar gradualmente validaciones y acceso a datos hacia convenciones comunes.
- Medir consultas lentas, N+1, paginación, tamaño de respuestas, índices y límites de memoria/conexiones.
- Probar carga representativa y un escenario de crecimiento de dos veces el pico medido, incluyendo escritura concurrente y documentos. Separar operaciones interactivas de procesos largos.
- Evaluar colas, cachés o réplicas solo cuando la medición justifique su complejidad. Para cachés, definir permisos, invalidación y coherencia antes de incorporarlas.

Entregables: módulos prioritarios refactorizados, decisiones arquitectónicas breves, perfil de rendimiento, presupuesto de capacidad y pruebas comparativas.

Condición de avance: comportamiento preservado en los módulos intervenidos y mejora medida en el cuello de botella priorizado, sin pérdida de integridad bajo la carga acordada.

### Etapa 5 — Institucionalizar la operación (semanas 11–12)

**Objetivo:** sostener los controles cuando cambien el equipo o la carga.

Trabajo:

- Monitorear desde fuera del servidor disponibilidad, latencia, errores, disco, backups, certificados, conexiones y trabajos pendientes cuando existan.
- Diferenciar servicio vivo de servicio listo; la comprobación HTTP básica no reemplaza una prueba funcional sintética sin datos reales.
- Configurar avisos con destinatario, plazo de atención y procedimiento. Probar la entrega y escalamiento de alertas.
- Definir severidades, comunicación de incidentes, procedimiento de contingencia y reconciliación de registros si se trabaja temporalmente fuera del sistema.
- Ensayar restauración y publicación con una segunda persona, midiendo duración y dependencias del operador original.
- Documentar incorporación de desarrolladores y usuarios, mapa de módulos, decisiones y operación frecuente.
- Revisar riesgos pendientes, objetivos alcanzados y capacidad para el siguiente trimestre.

Entregables: tablero operativo, alertas probadas, procedimientos de incidentes, manual de incorporación e informe de cierre.

Condición de avance: segunda persona completa el ejercicio operativo; responsables aceptan el riesgo residual; existe un ciclo de revisión y mantenimiento asignado.

## 5. Objetivos y métricas

Los siguientes valores son metas iniciales propuestas. Durante las primeras dos semanas se deben acordar según horario asistencial, presupuesto, infraestructura y criticidad. No representan garantías actuales ni deben relajarse sin registrar el motivo.

| Indicador | Meta propuesta | Evidencia |
| --- | --- | --- |
| Disponibilidad de circuitos críticos | 99,9% mensual durante la ventana operativa acordada | Monitoreo externo y fallos funcionales; informar también mantenimiento planificado. |
| Pérdida de datos recuperables — RPO | Hasta 15 minutos para registros críticos | Estrategia de recuperación de PostgreSQL, archivos y pruebas; un backup diario no satisface esta meta. |
| Tiempo de recuperación — RTO | Hasta 2 horas para servicio esencial | Simulacro desde incidente hasta operación verificada, incluyendo adjuntos y dependencias. |
| Detección de caída | Hasta 5 minutos | Alerta disparada, entregada y registrada durante ejercicio. |
| Respuesta interactiva | p95 inferior a 2 segundos en circuitos seleccionados, a la carga acordada | Medición de extremo a extremo; presupuestos separados para descargas y procesos largos. |
| Versiones identificables | 100% de publicaciones con revisión y artefacto registrados | Registro de despliegues y versión consultable. |
| Circuitos críticos verificables | 100% del conjunto priorizado con éxito, rechazo y errores relevantes | Matriz vinculada a pruebas y aceptación funcional; no equivale a cobertura total de código. |
| Backups | 100% de ejecuciones programadas con resultado observado; alerta ante fallo o falta | Registro operativo y restauraciones periódicas. |
| Cambios fallidos e incidentes recurrentes | Línea base en etapa 1; tendencia descendente por trimestre | Despliegues con rollback/corrección y revisión de incidentes. |

Si los objetivos de RPO/RTO exigen más infraestructura o guardia de la disponible, presentar alternativas con costo, riesgo y responsable de aceptación. No afirmar cumplimiento antes de medirlo.

## 6. Backlog inicial para convertir en tareas

Cada fila se debe dividir en cambios revisables; ninguna debería convertirse en una única PR de varias semanas.

| ID | Prioridad | Entregable | Responsable principal | Dependencia | Aceptación |
| --- | --- | --- | --- | --- | --- |
| C01 | P0 | Inventario y diferencias entre entornos | Técnico + operación | Ninguna | Entornos, versiones, configuración y responsables documentados sin secretos. |
| C02 | P0 | Respaldo completo y restauración ensayada | Operación | C01 | Base y adjuntos recuperados y tiempos registrados. |
| C03 | P0 | Revisión de accesos de mayor impacto | Backend + referente | C01 | Casos de acceso ajeno rechazados; hallazgos críticos contenidos. |
| C04 | P0 | Alertas de caída, disco y backups | Operación | C01 | Fallos simulados producen alertas recibidas. |
| C05 | P1 | Staging reproducible | Técnico | C01 | Instalación repetible con datos adecuados. |
| C06 | P1 | CI con PostgreSQL y migraciones | Desarrollo | C05 | Pull requests verifican operaciones representativas contra PostgreSQL. |
| C07 | P1 | Artefactos y publicación verificable | Técnico + operación | C05, C06 | Misma imagen promovida y versión visible; reversión ensayada. |
| C08 | P1 | Matriz de permisos y estados | Backend + referentes | C03 | Casos críticos acordados y trazables a pruebas. |
| C09 | P1 | Regresión de circuitos completos | Verificación + desarrollo | C08 | Circuitos priorizados pasan en staging. |
| C10 | P1 | Concurrencia e idempotencia | Backend | C06, C08 | Reintentos y escrituras simultáneas conservan invariantes. |
| C11 | P1 | Auditoría y fallos de integraciones | Backend + operación | C08 | Trazabilidad y reconciliación verificadas sin exposición en logs. |
| C12 | P2 | Modularización de componentes prioritarios | Frontend + backend | C09 | Cambios pequeños, contratos claros y regresión aprobada. |
| C13 | P2 | Capacidad y consultas | Backend + operación | C05, C09 | Informe de carga con límites y mejora prioritaria demostrada. |
| C14 | P1 | Procedimientos, suplencia y contingencia | Operación + producto | C02, C04, C07 | Segunda persona completa el ejercicio sin ayuda del autor. |
| C15 | P2 | Cierre y estrategia siguiente trimestre | Producto + técnico | Etapas previas | Riesgo residual y prioridades aceptados con evidencia. |

P0: recuperar, proteger o detectar fallos graves. P1: controlar operación y cambios. P2: mejorar mantenibilidad y crecimiento. La prioridad puede aumentar ante un hallazgo concreto.

## 7. Reglas de trabajo y aceptación de cambios

- Toda tarea tiene problema, impacto, alcance, criterio de aceptación y responsable. Los defectos incluyen reproducción y resultado esperado.
- Las PR son pequeñas y describen comportamiento y validación. Los cambios en permisos, cálculos o estados requieren pruebas de regresión pertinentes.
- Ninguna publicación clínica incorpora seeds demo ni presupone que revertir una imagen revierte la base.
- La aceptación incluye permisos del backend, fallos de red cuando apliquen, observabilidad necesaria y estrategia de migración/recuperación.
- Los registros de operación y evidencias no incluyen datos clínicos ni secretos en Git, tickets públicos o logs generales.
- Las dependencias y vulnerabilidades se revisan con periodicidad y prioridad por exposición; los cambios se validan en staging antes de producción.
- No se inicia una refactorización transversal sin un problema concreto, pruebas de comportamiento y una forma de medir su beneficio.

Cadencia: reunión semanal breve de riesgos, avances y bloqueos; revisión quincenal de entregables con referentes; revisión mensual de incidentes y restauración en entorno aislado. Ajustar frecuencia tras medir costos y criticidad.

## 8. Crecimiento posterior: meses 4–6

1. Mejorar el cuello de botella demostrado por medición y actualizar el modelo de capacidad ante nuevos usuarios o integraciones.
2. Incorporar nuevas sedes solo después de definir aislamiento de datos, ámbitos de permisos, configuración y reportes por sede. Para clientes distintos, evaluar explícitamente la estrategia de tenencia antes de compartir base.
3. Formalizar contratos y reconciliación de integraciones; prever observación de errores y reintentos antes de ampliar automatismos.
4. Evaluar mayor disponibilidad según las metas acordadas: redundancia, recuperación de base y almacenamiento, y dependencia de conectividad. Contemplar también cómo operar cuando falla una dependencia externa.
5. Revisar modularización y experiencia por rol; extraer servicios únicamente si hay un límite de responsabilidad y una necesidad operativa comprobables.
6. Mantener ejercicios de restauración, revisión de accesos, actualización de dependencias y medición de incidentes como trabajo recurrente con capacidad asignada.

## 9. Primeros diez días hábiles

- Días 1–2: asignar responsables, inventariar entornos y acordar circuitos críticos y horarios de operación.
- Días 3–4: verificar respaldos, preparar entorno aislado y relevar accesos de mayor impacto.
- Días 5–6: ejecutar restauración completa y medir RPO/RTO alcanzables; registrar brechas.
- Días 7–8: acordar matriz inicial de permisos, medir comportamiento base y probar alertas prioritarias.
- Días 9–10: priorizar hallazgos, estimar las tareas siguientes y confirmar recursos, metas y calendario.

Primer hito: poder explicar y demostrar cómo recuperar la aplicación, quién puede operar sobre qué datos y cómo detectar un fallo relevante. Este hito habilita el resto del plan, sin postergar correcciones urgentes.

## Referencias internas revisadas

- `.github/workflows/smoke.yml`
- `deploy/backup/README.md`
- `deploy/backup/RESTORE_DRILL_STAGING.md`
- `deploy/observability/README.md`
- `docs/despliegue-20260924.md`
- `docs/demo-stack.md`
- `frontend/src/utils/permissions.ts`
- `frontend/src/utils/limsAccess.ts`
