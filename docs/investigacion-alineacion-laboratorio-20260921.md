# Investigación de técnicas, informes y control de calidad

Fecha de consulta: 21/09/2026. Alcance: CM260 Wiener, Sysmex XP-300, VIDAS KUBE, EDAN i15, ERBA EC90 y Finecare FIA Meter Plus. El usuario confirmó que todos los reactivos del CM260 son Wiener. No se informaron todavía las referencias comerciales de cada kit ni los productos/lotes de control actuales.

**Estado: investigación y diagnóstico; no es una configuración clínica aprobada para importar.** Se consultaron código y catálogo de la base local; no se verificó la base de producción ni se modificaron resultados, referencias, controles o equipos. Las fuentes técnicas citadas son publicaciones de los fabricantes. Los folletos permiten identificar discrepancias, pero no sustituyen el inserto vigente de la referencia utilizada en Argentina.

## 1. Qué está desalineado en el sistema

La consulta local encontró 2.006 exámenes activos y 75 asociados a equipos: 71 a los seis equipos declarados y 4 a Coatron. Los 1.931 restantes no deben asignarse masivamente: incluyen entradas de catálogo/importaciones y requieren distinguir trabajo propio, derivaciones, cálculos y duplicados.

**Corte A (21/09/2026):** ver `docs/corte-a-matriz-laboratorio-20260921.md` — equipos B12/VITD/PROBNP, MXD≠MONO, QC sin defaults 100/5 en UI, IQC sin config visible, guardas de cálculos. Matriz 81 sigue borrador hasta Corte B.

| Hallazgo comprobado | Consecuencia y corrección propuesta |
|---|---|
| Los 82 targets de productos tienen exclusivamente media/DE 100/5 o 200/10. Los 27 materiales activos también usan esos dos pares. | Son los valores que genera `seed_qc_demo`, no valores establecidos para los kits actuales. Identificar los lotes de demostración y reemplazar su utilización operativa por lotes documentados, conservando el historial. |
| `QcHubPage.tsx` propone 100/5 al crear y reiniciar el formulario de material. | Quitar estos valores predeterminados; mostrar pendiente de configurar hasta registrar el dato real. |
| `TargetLoteControl` distingue lote, ensayo y nivel; `MaterialControl` guarda media/DE en el material y `LoteControl` no tiene targets propios. | Unificar la asignación por lote también para VIDAS y Finecare. Evitar que cambiar la media de un material altere la interpretación de otros lotes. |
| Los targets no almacenan unidad, método, referencia del kit ni documento/versiones. | Guardar estos datos y conservar una copia de los criterios utilizados en cada corrida. `PuntoQC` guarda valor, z y reglas, pero no una copia completa del target. |
| B12 y VITD no tienen equipo asociado; PROBNP tampoco. | Según la información del usuario: B12/VITD → VIDAS KUBE; PROBNP → Finecare, confirmando que el kit determina NT-proBNP. |
| Existen códigos parecidos importados: CPK_MB/CKMB y PROBNP/NTPROBNP. | Resolver equivalencias con trazabilidad; no fusionar por nombre ni sobrescribir estudios históricos. |
| El catálogo de referencia del código usa «Quimioluminiscencia» para tiroides/B12/VITD y «Inmunoturbidimetría» para varios inmunoensayos. | Identificar método por ensayo/plataforma: VIDAS ELFA, Finecare inmunofluorescencia. Confirmar el método actualmente persistido antes de migrar. |
| `TROP_US` local tiene límite 14 ng/L; `TROP_I` tiene 0,04 ng/mL. | Ambos requieren revisión contra sus ensayos concretos; no intercambiar troponina I ultrasensible VIDAS y troponina I del panel Finecare. |
| La semilla de integración Sysmex mapea MXD, MXD% y MXD# a MONO. | Retirar esa equivalencia al ajustar la integración: además de mezclar poblaciones, # y % son magnitudes diferentes. No afirmar que la semilla esté activa en el equipo sin revisar su configuración real. |
| El control operativo exige niveles N1/N2 y aceptación del día mediante reglas comunes. | Configurar niveles, frecuencia, cobertura por analito y eventos que invalidan la aceptación según cada técnica. La calibración y el control necesitan registros distintos. |

Evidencias de código: `laboratorio/models_qc.py`, `laboratorio/management/commands/seed_qc_demo.py:32`, `frontend/src/pages/laboratorio/qc/QcHubPage.tsx:320`, `laboratorio/equipos_lab.py`, `laboratorio/catalogo_referencias_clinicas.py`, `laboratorio/instrumentos_catalogo.py`, `laboratorio/qc_service.py`.

El gate actual puede considerar no aplicable un examen sin configuración QC. La aceptación rápida no exige valores numéricos. Tampoco invalida automáticamente el OK por vencimiento del lote, nueva calibración o cambio de reactivo. Son comportamientos del código actual, no instrucciones que se hayan encontrado en los fabricantes.

## 2. Evidencia por plataforma

### CM260 — Wiener

Wiener identifica al CM260 como plataforma de química e inmunoturbidimetría. Eso no define una única técnica para cada analito. Se necesitan el nombre comercial y REF: por ejemplo, la documentación distingue variantes de creatinina y de HDL. La aplicación específica del CM260 debe acompañar al inserto del reactivo. [CM260 oficial](https://www.wiener-lab.com/es-AR/product/456/).

Se localizaron insertos oficiales de [Colestat enzimático AA líquida](https://access.wiener-lab.com/VademecumDocumentos/Vademecum%20espanol/colestat_enzimatico_aa_liquida_sp.pdf) y [HDL colesterol monofase AA v.2](https://access.wiener-lab.com/VademecumDocumentos/Vademecum%20espanol/hdl_colesterol_monofase_aa_v2_sp.pdf). El segundo documenta método homogéneo, mg/dL, referencias por sexo, control en dos niveles y condiciones de calibración/estabilidad. Recomienda establecer referencias propias. Esto confirma que no corresponde copiar una descripción genérica para todo el perfil.

El [vademécum oficial que contiene Standatrol S-E](https://files.wiener-lab.com/Vademecum_completo_espanol.pdf) separa tablas por plataforma, técnica y nivel, incluida CM Series. La edición encontrada incluye un lote antiguo: sirve como evidencia de estructura, **no como fuente de targets actuales**. La tabla del lote comprado y la fila correspondiente al método realmente utilizado son imprescindibles.

La matriz adjunta enumera los 28 códigos actualmente asociados al CM260. Las variantes de reactivo, referencias y aplicaciones de todos ellos todavía no están verificadas individualmente; quedan señaladas como pendientes. Los cálculos LDL/VLDL/no-HDL/residual/índice CT-HDL y bilirrubina indirecta se distinguen de las determinaciones medidas.

### VIDAS KUBE — bioMérieux

El fabricante confirma que KUBE utiliza los reactivos de la familia VIDAS. Su documentación identifica ELFA; para B12, vitamina D y PSA también figura explícitamente en la documentación de producto. [KUBE](https://www.biomerieux.com/corp/en/our-offer/clinical-products/vidas-kube.html), [declaración técnica oficial](https://www.biomerieux.com/content/dam/biomerieux-com/03----our-offer/product-quality---safety/manufacturing/fr/france/38813-6.pdf).

Identificadores candidatos, **a cotejar con las cajas**:

| Examen local | Ensayo / REF publicada | Unidad/rango analítico publicado, cuando inequívoco |
|---|---|---|
| TROP_US | TNHS / 415386 | 1,5–40.000 pg/mL; también ng/L |
| VITD | 25 OH Vitamin D TOTAL / 30463 | 8,1–126 ng/mL |
| B12 | Vitamin B12 TOTAL / 424106 | 100–1.200 pg/mL |
| PSA | TPSA / 30428 | 0,07–100 ng/mL; confirmar PSA total |
| TSH | TSH / 30400 o TSH3 / 30441 | Son ensayos distintos; confirmar cuál |
| T3 | T3 / 30403 | 0,4–9 nmol/L |
| T4 | T4 / 30404 | 6–320 nmol/L |
| T4L | FT4N / 30459 | Verificar unidad en IFU: la tabla pública muestra una inconsistencia |
| FERRIT | Ferritin / 30411 | 1,5–1.200 ng/mL |

Fuente: [VIDAS Assays Practical Information, tabla y unidades](https://www.biomerieux.com/content/dam/biomerieux-com/03----our-offer/clinical/in-hospital--in-lab/products/vidas-range/documents/vidas-assays-practical-information.pdf). **Los rangos de esta tabla son analíticos, no intervalos normales.** La guía muestra secuencias distintas de calibración/control y diferentes frecuencias; no permite imponer una política idéntica a todos los ensayos ni interpretar esos días como vigencia universal del QC.

Para TNHS, una [tarjeta oficial del fabricante](https://www.biomerieux.com/content/dam/biomerieux-com/03----our-offer/clinical/in-hospital--in-lab/products/vidas-high-sensitive-troponin-i/documents/Pocket%20CARD%20VIDAS%20troponin.pdf) publica 19 ng/L como percentil 99 global. Difiere de los 14 ng/L locales. Es una discrepancia documentada para resolver con la IFU vigente/población aplicable, **no una autorización para reemplazar automáticamente 14 por 19 ni para adoptar el algoritmo clínico de esa tarjeta antigua**.

### Finecare FIA Meter Plus — Wondfo

La plataforma utiliza inmunocromatografía de fluorescencia. La página oficial diferencia reactivos individuales y panel cardíaco combinado. [Finecare Plus FS-113](https://en.wondfo.com/pt/index17.html), [menú y referencias publicadas por Wondfo](https://es.wondfo.com/pt/index278.html).

| Examen | Situación local | Dato publicado para contrastar; falta confirmar REF/IFU |
|---|---|---|
| HBA1C | %, referencia 4–6 | Publicación indica rango analítico 4–14,5%; separar límites diagnósticos de referencias |
| MICROALB | mg/L, límite 30 | MAU en orina; publicación indica referencia 0–20 mg/L |
| PROBNP | pg/mL, límite 125; sin equipo | Confirmar NT-proBNP; publicación presenta criterios por edad |
| DDIM | µg/mL, límite 0,5 | W211 informa 0,1–10 mg/L analítico; confirmar FEU/DDU y variante |
| TROP_I | ng/mL, límite 0,04 | Publicación indica referencia 0–0,3 ng/mL |
| CPK_MB | ng/mL | Confirmar masa CK-MB del panel, distinta de actividad en U/L |
| MIOG | ng/mL, límite 90 | Publicación indica referencia 0–58 ng/mL |

Las discrepancias de la columna final provienen de la [página oficial de la plataforma](https://es.wondfo.com/pt/index278.html). Esa página no identifica la revisión de cada kit: se usan como alertas de verificación, no como nuevos parámetros clínicos aprobados. Para D-dímero, la [ficha individual W211](https://en.wondfo.com/pt/d-dimer-rapid-quantitative-test.html) especifica sangre total/plasma; no ampliar automáticamente las matrices usando la tabla general.

El [folleto oficial de HbA1c](https://en.wondfo.com/vancheerfile/files/2023/3/20230310092528961.pdf) diferencia resultados DCCT en %, IFCC en mmol/mol y glucemia estimada. En el sistema deben mantenerse como magnitudes diferenciadas; una conversión de unidades no convierte una concentración de albúmina urinaria en cociente albúmina/creatinina ni en excreción diaria.

### Sysmex XP-300

Es un analizador con diferencial de tres partes: LYM, MXD y NEUT, con porcentajes y recuentos absolutos. El fabricante también distingue RDW-CV y RDW-SD y describe su control hematológico. [Ficha oficial XP-300](https://www.sysmex.com.au/product/xp-300/), [catálogo Sysmex que identifica «Mixed Population»](https://shop.sysmex.ch/sysmex-xp-300/ap807129).

Consecuencia para el diseño: agregar identidad propia a MXD y separar #/%. Eosinófilos, basófilos, monocitos y cayados de una fórmula manual no deben presentarse como si fueran una separación automática realizada por el XP-300. Identificar producto de control, niveles disponibles y hoja de asignación específica para XP-300; no cargar los valores de otro modelo Sysmex.

### EDAN i15

La documentación del fabricante distingue calibrador, control y simulador electrónico, y separa valores calculados, incluidos HCO3, BE y sO2 estimada. [EDAN i15 oficial](https://pt.edan.com/product/e/i15.html).

La configuración deberá distinguir cartucho utilizado, matriz arterial/venosa/capilar, unidad de presión y parámetros medidos frente a calculados. En el catálogo local hay 12 códigos, correspondientes a seis conceptos duplicados por origen arterial/venoso. Falta la REF del cartucho y la documentación de los controles actuales. No se reutilizó documentación del i15 VET.

### ERBA EC90

El fabricante documenta medición directa por ISE, Na/K/Cl/iCa, calibraciones de uno y dos puntos, funciones Levey–Jennings/Westgard y matrices diferentes. [Folleto oficial EC90](https://electrolyte-analyser-ec90.erbamannheim.com/getmedia/d744ee42-d908-4fef-b3cc-03cd33bbbde9/Erba_EC90_brochure_LIT-30-001_2022_1.pdf.aspx).

El informe debe distinguir calcio ionizado de calcio total. Falta confirmar cartucho con/sin iCa, matriz utilizada y producto/lote de control. Los límites de medición/reproducibilidad del folleto no son los valores de referencia del paciente ni los targets del control.

## 3. Diseño propuesto para corregir el sistema

Estas son propuestas de implementación basadas en los hallazgos, no requisitos textuales atribuidos a todos los fabricantes:

1. **Ficha versionada de técnica:** analito, plataforma, fabricante, nombre/REF de reactivo, método, muestra, unidad nativa y de informe, conversión, decimales, rango analítico, manejo de resultados fuera de rango, interferencias y documento fuente/revisión. Referencias clínicas estratificadas cuando corresponda, separadas de umbrales de decisión y alertas críticas.
2. **Control por lote y analito:** producto, lote, nivel real, equipo/método, matriz, unidad, valor asignado y límites del fabricante. Media/DE deben tener procedencia explícita. Si el inserto solo da mínimo/máximo, conservar ese intervalo; no inventar una DE dividiendo el rango por una constante.
3. **Medias propias:** separar asignaciones del fabricante de estadísticas obtenidas por el laboratorio, con fecha, cantidad de observaciones y aprobación. Una media de otro lote o una precisión publicada en un folleto no es la media/DE del lote en uso.
4. **Corrida multiparámetro:** un único ingreso de producto/lote/nivel que despliegue una fila por analito con su valor y unidad; no un único resultado para todo el instrumento. La cobertura aceptada debe corresponder a lo controlado.
5. **Política por técnica:** niveles requeridos configurables, frecuencia y eventos que exigen repetir QC —según IFU aplicable y procedimiento del laboratorio—. Separar calibración, controles líquidos, comprobaciones electrónicas y aceptación documentada externa. El motor Westgard no reemplaza estos requisitos.
6. **Trazabilidad:** registrar lote de reactivo, control y calibrador; vencimiento y estabilidad tras apertura/reconstitución; operador, acción correctiva y nueva corrida. Conservar en cada resultado/corrida la técnica y criterios vigentes en ese momento. Los cambios posteriores no deben reescribir informes validados ni reinterpretar silenciosamente su historia.
7. **Despliegue:** preparar una propuesta de catálogo por técnica para revisión del bioquímico, probarla con datos sintéticos y recién después activar cambios. Los datos de demostración y la ausencia de configuración deben mostrarse explícitamente, sin aparentar control analítico documentado.

## 4. Qué se puede investigar sin que el usuario suba todo

Se puede continuar obteniendo publicaciones oficiales, construir equivalencias, verificar métodos/unidades, separar mediciones y cálculos, detectar duplicados y preparar los cambios del modelo/UI. La matriz adjunta ya identifica el conjunto operativo local y qué falta verificar.

Para cerrar los datos específicos se necesitan: nombre comercial y REF de los reactivos; para CM, la variante de cada técnica y su aplicación; para VIDAS, especialmente TSH/TSH3, FT4 y PSA total/libre; para Finecare, REF del panel cardíaco, MAU, NT-proBNP y D-dímero; para i15/EC90, el cartucho; y por cada control, marca/producto, lote, niveles, vencimiento y hoja de valores asignados. Cuando la hoja oficial del lote esté disponible públicamente, puede buscarse por esos identificadores. Solo los documentos no accesibles públicamente o propios del lote deberán aportarse desde el laboratorio; no hacen falta contraseñas.

**Pendientes:** no están verificados todos los insertos individuales del CM ni los intervalos clínicos definitivos de todas las técnicas; faltan REF, revisiones aplicables y lotes reales. Ningún número de esta investigación fue activado en el sistema.
