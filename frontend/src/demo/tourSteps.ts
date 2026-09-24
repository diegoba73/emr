import type { DriveStep } from 'driver.js';
import type { DemoTourRole } from './demoStorage';

export type DemoTourStep = DriveStep & {
  route?: string;
  resolveRoute?: () => Promise<string | null>;
  /** Only UI navigation: never submit a form or change clinical data. */
  prepare?: () => void;
};

export const MKTG_LIMS_VIVO = 'LAB-MKTG-00001';
export const MKTG_LIMS_FINAL = 'LAB-MKTG-00002';
export const MKTG_PORTAL_PACIENTE_DNI = 'QA-DEMO-00001';

function step(route: string, anchor: string, title: string, description: string): DemoTourStep {
  return { route, element: `[data-demo="${anchor}"]`, popover: {
    title, description, side: 'bottom', align: 'start',
  } };
}

function welcome(route: string, anchor: string, title: string, content: string): DemoTourStep {
  return step(route, anchor, title, `<p>${content}</p><p>Avanzá con <b>Siguiente</b> y volvé con <b>Anterior</b>. Podés cerrar la guía para explorar y reiniciarla desde el botón flotante. Los ejemplos dependen de los datos demo cargados.</p>`);
}

function finish(route: string, anchor: string): DemoTourStep {
  return step(route, anchor, 'Seguí explorando', '<p>Terminaste el recorrido. Cerrá la guía con <b>Listo</b> para probar las opciones que acabamos de ver.</p><p><b>Reiniciar tour</b> vuelve al comienzo. <b>Cambiar rol</b> permite recorrer la aplicación desde otra perspectiva.</p>');
}

function patientStep(anchor: string, title: string, description: string): DemoTourStep {
  return { ...step('/pacientes', anchor, title, description), resolveRoute: async () => {
    const { resolveDemoPatientId } = await import('./demoResolve');
    const id = await resolveDemoPatientId();
    return id ? `/paciente/${id}` : null;
  } };
}

function orderStep(numero: string, title: string, description: string, tab = 0): DemoTourStep {
  return { ...step('/laboratorio/ordenes', 'lims-content', title, description), element: `[data-demo-order="${numero}"] [data-demo="lims-content"]`, resolveRoute: async () => {
    const { resolveDemoLimsOrdenId } = await import('./demoResolve');
    const id = await resolveDemoLimsOrdenId(numero);
    return id ? `/laboratorio/ordenes/${id}` : null;
  }, prepare: () => { document.querySelector<HTMLButtonElement>(`[data-demo="lims-tab-${tab}"]`)?.click(); } };
}

const patients = () => step('/pacientes', 'page-pacientes', 'Encontrar la ficha correcta', '<p>El listado reúne identificación, DNI, fecha de nacimiento, contacto y obra social. Usá la búsqueda para localizar al paciente y la acción <b>Ficha del paciente</b> para abrir su vista 360.</p><p>El recorrido intentará abrir el paciente ficticio asociado al portal demo.</p>');
const clinicalSummary = () => patientStep('page-paciente-360', 'Historia clínica 360: contexto del paciente', '<p>La cabecera reúne identidad, edad, alergias registradas y situación de internación cuando corresponde. Debajo se conectan la historia del paciente, sus atenciones, archivos y análisis.</p><p>Esta vista permite recuperar el contexto antes de abrir un episodio concreto.</p>');
const timeline = () => patientStep('patient-timeline', 'Línea de tiempo clínica', '<p>Revisá la secuencia de eventos clínicos y sus fechas para entender la evolución del paciente. Las atenciones vinculadas son el eje de la historia.</p><p>Los paneles laterales permiten abrir atenciones recientes y consultar los últimos signos vitales registrados.</p>');
const detailedRecord = () => patientStep('patient-detail', 'Ficha detallada: información, atenciones y análisis', '<p>Las pestañas <b>Información Personal</b>, <b>Atenciones</b> y <b>Análisis de Laboratorio</b> organizan la información completa del paciente.</p><p>La primera reúne datos personales y de cobertura; las otras permiten revisar episodios y pedidos relacionados sin buscar de nuevo al paciente. Cerrá la guía para recorrerlas.</p>');
const attentionFilters = () => step('/atenciones', 'atenciones-filters', 'Acotar la búsqueda de atenciones', '<p>Combiná contexto, tipo de intervención, estado clínico y médico responsable. La búsqueda rápida admite paciente, médico o notas, y las fechas <b>Desde</b> y <b>Hasta</b> delimitan el período.</p><p>Usá <b>Aplicar filtros</b> para actualizar el listado con esos criterios y <b>Limpiar</b> para quitarlos.</p>');
const beds = () => step('/internacion', 'page-internacion', 'Internación: ubicación y ocupación', '<p>El tablero separa las camas de <b>Unidad Coronaria (UCO)</b> y <b>Cuidados Especiales (UCE)</b>. Cada tarjeta permite identificar el estado de la cama y el paciente cuando está ocupada.</p><p>Al explorar, abrí una cama ocupada para consultar su episodio. El botón de actualización vuelve a cargar el tablero.</p>');
const bedDetails = () => step('/internacion', 'internacion-uco', 'Qué encontrás al abrir una cama', '<p>El detalle de una cama ocupada ofrece <b>Datos del paciente</b>, <b>Formularios HC</b> y <b>Revista de sala</b>. Allí se reúne la información del episodio y sus registros clínicos.</p><p>Cerrá la guía para abrir una cama y revisar esas pestañas. Las acciones de edición dependen del rol.</p>');
const requests = () => step('/solicitudes', 'page-solicitudes', 'Laboratorio desde el equipo asistencial', '<p>Esta bandeja permite consultar pedidos de laboratorio clínico y microbiología. Combiná búsqueda, tipo y estado para ubicar una solicitud; los contadores resumen lo que muestra el listado.</p><p>Abrí el pedido para consultar su detalle. La descarga del informe clínico requiere una orden finalizada.</p>');

export function getTourSteps(role: DemoTourRole): DemoTourStep[] {
  switch (role) {
    case 'medico': return [
      welcome('/turnos', 'page-turnos', 'Recorrido médico: de la agenda al seguimiento', 'Vamos a recorrer agenda, ficha del paciente, atenciones, guardia, internación, laboratorio y estudios complementarios.'),
      step('/turnos', 'turnos-filters', 'Filtrar la agenda', '<p>Buscá por paciente y combiná médico, recurso o sala y estado del turno. Podés distinguir consultas de estudios para concentrarte en el tipo de actividad que necesitás.</p><p>Si no encontrás una reserva, revisá los filtros y el período elegido antes de crear otra.</p>'),
      step('/turnos', 'page-turnos', 'Reservas y atención del día', '<p>La agenda diferencia turnos reservados, confirmados, realizados y cancelados. Abrí un turno para revisar su información y las acciones disponibles.</p><p><b>Nuevo turno</b> abre el formulario de reserva cuando tu usuario tiene permiso. El tour solo presenta las opciones: no crea reservas.</p>'),
      patients(), clinicalSummary(), timeline(), detailedRecord(),
      step('/atenciones', 'page-atenciones', 'Atenciones: trabajar sobre un episodio', '<p>Esta sección reúne las atenciones clínicas. Abrí un registro para revisar su detalle y continuar el trabajo según el estado y los permisos de tu usuario.</p><p>La atención conecta el registro clínico con el seguimiento del paciente; la ficha 360 permite volver a encontrarla en su contexto.</p>'),
      attentionFilters(),
      step('/guardia', 'page-guardia', 'Guardia: seguimiento de atenciones abiertas', '<p>El tablero muestra las atenciones de guardia y marca pedidos pendientes de laboratorio y estudios. Las acciones permiten consultar el detalle, continuar la atención, cerrarla o derivar a internación cuando corresponde.</p><p>La derivación no exige cerrar primero la atención: los pedidos pendientes siguen identificados en la lista.</p>'),
      beds(), bedDetails(), requests(),
      step('/estudios-complementarios', 'page-estudios', 'Estudios complementarios', '<p>Filtrá por paciente, estado y modalidad para seguir los estudios solicitados. El listado muestra tipo de estudio, turno vinculado, fechas de solicitud y realización y centro realizador.</p><p>Abrí un estudio para revisar su detalle y las acciones habilitadas en su etapa del proceso.</p>'),
      finish('/estudios-complementarios', 'page-estudios'),
    ];
    case 'laboratorio': return [
      welcome('/laboratorio/pendientes', 'page-lims-pendientes', 'Laboratorio: del pedido al informe', 'Seguiremos pendientes, etiquetas, recepción, órdenes, muestras, carga de resultados e informes. Este usuario opera como laboratorio; la validación está reservada al bioquímico o administrador.'),
      step('/laboratorio/pendientes', 'page-lims-pendientes', 'Pendientes y preparación de etiquetas', '<p><b>Sin etiquetas</b> reúne los pedidos que necesitan identificación. Luego de imprimir pasan a <b>Esperando recepción</b>, donde permanecen hasta que el laboratorio recibe las muestras.</p><p>La búsqueda admite número, paciente, DNI o cultivo. También se pueden reimprimir etiquetas cuando sea necesario.</p>'),
      step('/laboratorio/muestras/recepcion', 'page-lims-recepcion', 'Recepción por código de barras', '<p>Indicá la ubicación de recepción y escaneá el código de la etiqueta. La pantalla reconoce tubos de laboratorio clínico y etiquetas de microbiología.</p><p>El escaneo registra la recepción: para observar el funcionamiento sin cambiar el estado de las muestras, seguí con la guía sin escanear.</p>'),
      step('/laboratorio/muestras/recepcion', 'page-lims-recepcion', 'Comprobar si llegó todo el pedido', '<p>La tabla de recepciones muestra código, tipo, paciente, orden y estado. La columna <b>Completa</b> ayuda a distinguir una recepción completa de otra con tubos pendientes.</p><p>Los avisos enumeran las muestras que todavía faltan para la última orden recibida.</p>'),
      step('/laboratorio/ordenes', 'page-lims-ordenes', 'Órdenes recibidas y en proceso', `<p>Esta bandeja continúa el trabajo después de la recepción. Buscá el número <b>${MKTG_LIMS_VIVO}</b> para identificar la orden de ejemplo en proceso.</p><p>El tour intentará abrirla automáticamente. Si el ejemplo no está cargado, te lo indicará para que puedas continuar.</p>`),
      orderStep(MKTG_LIMS_VIVO, 'Resumen de la orden', '<p>El resumen permite revisar el pedido antes de cargar resultados. En la cabecera se muestran estado, avance de resultados y datos administrativos de la orden.</p><p>Las acciones disponibles cambian según su estado. Revisá también las pestañas <b>Muestras</b> y <b>Resultados</b>, que abriremos a continuación.</p>'),
      orderStep(MKTG_LIMS_VIVO, 'Muestras vinculadas a la orden', '<p>Esta pestaña reúne las muestras de la solicitud para consultar su identificación y situación dentro del proceso.</p><p>La relación entre orden y muestra permite seguir cada tubo desde la toma y recepción hasta el trabajo analítico. Las acciones habilitadas dependen del estado de la orden.</p>', 1),
      orderStep(MKTG_LIMS_VIVO, 'Carga y revisión de resultados', '<p>En <b>Resultados</b> se cargan los valores de los exámenes. La edición se habilita para órdenes en proceso o informadas parcialmente que aún no están finalizadas.</p><p>Revisá el avance de la carga y las observaciones antes de guardar. Guardar valores y validar el informe son etapas diferentes.</p>', 2),
      orderStep(MKTG_LIMS_VIVO, 'Quién valida y libera el informe', '<p>El usuario de laboratorio puede operar y cargar resultados. La <b>validación y liberación</b> corresponde al bioquímico o administrador.</p><p>Cuando el pedido está listo, la pantalla puede mostrar que queda pendiente del bioquímico. El tour no modifica ni valida la orden de ejemplo.</p>', 2),
      orderStep(MKTG_LIMS_FINAL, 'Orden finalizada e informe disponible', `<p>Ahora intentamos abrir <b>${MKTG_LIMS_FINAL}</b>, el ejemplo preparado como finalizado. En ese estado se habilitan la descarga del PDF y el envío del informe según los permisos.</p><p>Es también el estado que permite mostrar el resultado en el portal del paciente. Podés explorar esas acciones al terminar el tour.</p>`),
      step('/laboratorio/muestras/consulta', 'page-muestras', 'Consulta y trazabilidad de muestras', '<p>Ingresá el código de barras de una muestra para consultar el paciente, pedido y estado relacionados. Esta pantalla permite buscar tanto laboratorio clínico como microbiología.</p><p>El historial detalla fecha, acción, estado y observaciones de los eventos registrados, para reconstruir el recorrido de la muestra.</p>'),
      step('/laboratorio/inventario', 'page-lims-inventario', 'Inventario y abastecimiento', '<p>Las pestañas organizan <b>Reactivos</b>, <b>Insumos</b>, <b>Lotes</b>, <b>Consumo por ensayo</b>, <b>Movimientos</b> y <b>Pedidos / alertas</b>.</p><p>Permiten relacionar las existencias con el consumo del laboratorio y revisar los movimientos y necesidades de reposición. Explorá cada pestaña al cerrar la guía.</p>'),
      finish('/laboratorio/inventario', 'page-lims-inventario'),
    ];
    case 'enfermeria': return [
      welcome('/internacion', 'page-internacion', 'Enfermería: contexto y continuidad del cuidado', 'Recorreremos el tablero de internación, las opciones del episodio, la ficha del paciente, las atenciones y la consulta de laboratorio.'),
      beds(), bedDetails(),
      step('/internacion', 'internacion-uce', 'Formularios y registros de enfermería', '<p>Dentro de una cama ocupada, <b>Formularios HC</b> permite acceder a los registros del episodio. Enfermería tiene permiso para escribir sus formularios de controles, balance y notas; los registros médicos tienen permisos propios.</p><p>Revisá también <b>Revista de sala</b> para consultar el seguimiento del episodio. Cerrá la guía para explorar estas opciones.</p>'),
      step('/internacion', 'page-internacion', 'Ingreso, infraestructura y alta', '<p>El rol de enfermería puede ingresar pacientes a internación y administrar la infraestructura. Una cama disponible ofrece el ingreso; una ocupada abre el episodio existente.</p><p>El alta médica requiere otro permiso y no está habilitada para este rol. Las acciones del tablero se ajustan a esas responsabilidades.</p>'),
      patients(), clinicalSummary(), timeline(), detailedRecord(),
      step('/atenciones', 'page-atenciones', 'Consultar atenciones del paciente', '<p>Podés acceder al listado y al detalle de las atenciones para recuperar información del episodio asistencial.</p><p>El acceso de enfermería a esta sección no habilita las mismas operaciones que el médico: usá los formularios propios de enfermería para los registros que te corresponden.</p>'),
      attentionFilters(), requests(), finish('/solicitudes', 'page-solicitudes'),
    ];
    case 'paciente': return [
      welcome('/portal', 'page-portal', 'Tu portal: información para seguir tu atención', 'Desde esta cuenta podés consultar turnos, resultados de laboratorio, documentos e historia del paciente asociado.'),
      step('/portal', 'page-portal', 'Accesos y resumen personal', '<p>Las tarjetas abren <b>Mis turnos</b>, <b>Resultados de laboratorio</b>, <b>Documentos</b> y <b>Mi historia</b>.</p><p>Los contadores disponibles resumen próximos turnos, resultados listos y documentos. Si una sección está vacía, puede no haber ejemplos cargados para esta cuenta.</p>'),
      step('/portal/turnos', 'page-portal-turnos', 'Próximos turnos', '<p>La sección <b>Próximos</b> ordena las reservas futuras por fecha. Cada entrada muestra día y hora, el motivo o recurso y una etiqueta con su estado.</p><p>Esta pantalla permite consultar los turnos asociados a la cuenta; no ofrece aquí un formulario de reserva o cancelación.</p>'),
      step('/portal/turnos', 'page-portal-turnos', 'Historial de turnos', '<p>Debajo de los próximos turnos aparecen hasta veinte reservas pasadas, desde la más reciente. El estado ayuda a distinguir cómo quedó registrada cada una.</p><p>Los ejemplos cambian de sección con el paso del tiempo: una reserva demo antigua aparecerá en el historial.</p>'),
      step('/portal/resultados', 'page-portal-resultados', 'Resultados liberados', `<p>Acá se muestran las órdenes finalizadas del paciente. El ejemplo previsto es <b>${MKTG_LIMS_FINAL}</b>, si está cargado en este entorno.</p><p>Los pedidos todavía en proceso no aparecen como resultados listos en esta pantalla.</p>`),
      step('/portal/resultados', 'page-portal-resultados', 'Descargar el informe PDF', '<p>Cada resultado muestra número de orden, fecha y estado. El botón <b>PDF</b> permite descargar el informe correspondiente.</p><p>Al terminar el recorrido podés cerrar la guía y usar ese botón para consultar el documento.</p>'),
      step('/portal/documentos', 'page-portal-documentos', 'Mis documentos', '<p>Esta sección lista los <b>Archivos médicos</b> asociados al paciente, mostrando título y tipo.</p><p>También reúne los <b>Estudios complementarios entregados</b>, con identificación del estudio, fecha y estado. Aquí se presenta el listado de documentos disponibles.</p>'),
      step('/portal/historia', 'page-portal-historia', 'Mi historia en orden cronológico', '<p>La línea de tiempo reúne los eventos clínicos disponibles para esta cuenta. Revisá fechas y descripciones para seguir la secuencia de la atención.</p><p>Podés complementar esa lectura con los informes de laboratorio y el listado de documentos de las otras secciones.</p>'),
      finish('/portal/historia', 'page-portal-historia'),
    ];
    default: return [];
  }
}
