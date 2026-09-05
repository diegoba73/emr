import type { DriveStep } from 'driver.js';
import type { DemoTourRole } from './demoStorage';

export type DemoTourStep = DriveStep & {
  /** Ruta a la que navegar antes de mostrar el paso (opcional). */
  route?: string;
  /** Resuelve ruta dinámica (p. ej. /paciente/:id). */
  resolveRoute?: () => Promise<string | null>;
};

export const MKTG_LIMS_VIVO = 'LAB-MKTG-00001';
export const MKTG_LIMS_FINAL = 'LAB-MKTG-00002';
export const MKTG_PORTAL_PACIENTE_DNI = 'QA-DEMO-00001';

/**
 * Pasos del tour por rol. Selectores `data-demo` / `data-demo-nav`.
 */
export function getTourSteps(role: DemoTourRole): DemoTourStep[] {
  switch (role) {
    case 'medico':
      return [
        {
          element: '[data-demo="sidebar"]',
          route: '/turnos',
          popover: {
            title: 'Bienvenido a la demo Synesis',
            description:
              'Recorrido rápido: agenda, paciente 360, internación y laboratorio. Usá Siguiente para avanzar.',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo-nav="/turnos"]',
          route: '/turnos',
          popover: {
            title: 'Agenda / Turnos',
            description: 'Acá gestionás la agenda clínica. Hay turnos ficticios MKTG de hoy y próximos días.',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo="page-turnos"]',
          route: '/turnos',
          popover: {
            title: 'Calendario de turnos',
            description: 'Vista operativa de reservas, confirmaciones y atención del día.',
            side: 'bottom',
            align: 'start',
          },
        },
        {
          element: '[data-demo-nav="/pacientes"]',
          route: '/pacientes',
          popover: {
            title: 'Pacientes',
            description: 'Listado de fichas. Entramos a la vista 360 del paciente demo del portal.',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo="page-paciente-360"]',
          resolveRoute: async () => {
            const { resolveDemoPatientId } = await import('./demoResolve');
            const id = await resolveDemoPatientId();
            return id ? `/paciente/${id}` : '/pacientes';
          },
          popover: {
            title: 'Historia clínica 360',
            description:
              'Timeline de atenciones, signos vitales y laboratorio en un solo lugar. Datos 100% ficticios.',
            side: 'bottom',
            align: 'start',
          },
        },
        {
          element: '[data-demo-nav="/internacion"]',
          route: '/internacion',
          popover: {
            title: 'Internación',
            description: 'Tablero de camas UCO/UCE con internaciones MKTG de ejemplo.',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo="page-internacion"]',
          route: '/internacion',
          popover: {
            title: 'Panel de camas',
            description: 'Estado de ocupación y episodios activos para el equipo clínico.',
            side: 'bottom',
            align: 'start',
          },
        },
        {
          element: '[data-demo-nav="/solicitudes"]',
          route: '/solicitudes',
          popover: {
            title: 'Laboratorio clínico',
            description:
              'Los médicos consultan pedidos y resultados desde Solicitudes/Análisis. Las órdenes MKTG (LAB-MKTG-00001 / 00002) alimentan este flujo y el portal.',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo="page-solicitudes"]',
          route: '/solicitudes',
          popover: {
            title: 'Fin del tour médico',
            description:
              'Podés seguir explorando libremente. El botón «Reiniciar tour» vuelve a empezar este recorrido.',
            side: 'bottom',
            align: 'start',
          },
        },
      ];
    case 'laboratorio':
      return [
        {
          element: '[data-demo="sidebar"]',
          route: '/laboratorio/ordenes',
          popover: {
            title: 'Demo LIMS',
            description: 'Recorrido del laboratorio: órdenes, detalle y muestras.',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo-nav="/laboratorio/ordenes"]',
          route: '/laboratorio/ordenes',
          popover: {
            title: 'Órdenes LIMS',
            description: 'Bandeja de trabajo del laboratorio clínico.',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo="page-lims-ordenes"]',
          route: '/laboratorio/ordenes',
          popover: {
            title: 'Buscá la orden demo',
            description: `Filtrá por número ${MKTG_LIMS_VIVO} para abrir el pedido en proceso con muestra y resultados parciales.`,
            side: 'bottom',
            align: 'start',
          },
        },
        {
          element: '[data-demo="page-lims-detalle"]',
          resolveRoute: async () => {
            const { resolveDemoLimsOrdenId } = await import('./demoResolve');
            const id = await resolveDemoLimsOrdenId(MKTG_LIMS_VIVO);
            return id ? `/laboratorio/ordenes/${id}` : '/laboratorio/ordenes';
          },
          popover: {
            title: 'Detalle de orden',
            description: 'Acá se cargan y validan resultados. Esta orden MKTG está EN_PROCESO a propósito.',
            side: 'bottom',
            align: 'start',
          },
        },
        {
          element: '[data-demo-nav="/laboratorio/muestras/consulta"]',
          route: '/laboratorio/muestras/consulta',
          popover: {
            title: 'Consulta de muestras',
            description: 'Trazabilidad de tubos/códigos (p. ej. MUE-MKTG-00001).',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo="page-muestras"]',
          route: '/laboratorio/muestras/consulta',
          popover: {
            title: 'Fin del tour LIMS',
            description: 'Explorá Pendientes y Recepción para ver el flujo completo.',
            side: 'bottom',
            align: 'start',
          },
        },
      ];
    case 'enfermeria':
      return [
        {
          element: '[data-demo="sidebar"]',
          route: '/internacion',
          popover: {
            title: 'Demo internación',
            description: 'Vista pensada para el equipo de enfermería en planta.',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo-nav="/internacion"]',
          route: '/internacion',
          popover: {
            title: 'Menú Internación',
            description: 'Acceso al tablero de camas UCO y UCE.',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo="page-internacion"]',
          route: '/internacion',
          popover: {
            title: 'Tablero de camas',
            description:
              'Internaciones ficticias INT-MKTG-001… con diagnósticos de ejemplo. Hacé clic en una cama ocupada para ver el episodio.',
            side: 'bottom',
            align: 'start',
          },
        },
      ];
    case 'paciente':
      return [
        {
          element: '[data-demo="sidebar"]',
          route: '/portal',
          popover: {
            title: 'Portal del paciente',
            description: 'Lo que ve el paciente: turnos, resultados e historia.',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo-nav="/portal"]',
          route: '/portal',
          popover: {
            title: 'Mi portal',
            description: 'Resumen de acceso rápido a los servicios del paciente.',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo="page-portal"]',
          route: '/portal',
          popover: {
            title: 'Inicio del portal',
            description: 'Punto de entrada amigable, separado del escritorio clínico del staff.',
            side: 'bottom',
            align: 'start',
          },
        },
        {
          element: '[data-demo-nav="/portal/turnos"]',
          route: '/portal/turnos',
          popover: {
            title: 'Mis turnos',
            description: 'Turnos MKTG asociados a esta cuenta demo.',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo="page-portal-turnos"]',
          route: '/portal/turnos',
          popover: {
            title: 'Agenda del paciente',
            description: 'Consulta de próximos y pasados turnos.',
            side: 'bottom',
            align: 'start',
          },
        },
        {
          element: '[data-demo-nav="/portal/resultados"]',
          route: '/portal/resultados',
          popover: {
            title: 'Mis resultados',
            description: 'Órdenes FINALIZADAS (LAB-MKTG-00002) visibles para el paciente.',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo="page-portal-resultados"]',
          route: '/portal/resultados',
          popover: {
            title: 'Resultados de laboratorio',
            description: 'Informes listos para consulta desde el portal.',
            side: 'bottom',
            align: 'start',
          },
        },
        {
          element: '[data-demo-nav="/portal/historia"]',
          route: '/portal/historia',
          popover: {
            title: 'Mi historia',
            description: 'Línea de tiempo orientada al paciente.',
            side: 'right',
            align: 'start',
          },
        },
        {
          element: '[data-demo="page-portal-historia"]',
          route: '/portal/historia',
          popover: {
            title: 'Fin del tour paciente',
            description: 'Gracias por recorrer la demo. Podés volver a /demo para probar otro rol.',
            side: 'bottom',
            align: 'start',
          },
        },
      ];
    default:
      return [];
  }
}
