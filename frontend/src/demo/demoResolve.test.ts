import { resolveDemoLimsOrdenId, resolveDemoPatientId } from './demoResolve';
import { listSolicitudesExamen } from '../services/limsApi';
import { pacientesService } from '../services/pacientes';

jest.mock('../services/limsApi', () => ({ listSolicitudesExamen: jest.fn() }));
jest.mock('../services/pacientes', () => ({ pacientesService: { search: jest.fn() } }));

beforeEach(() => jest.resetAllMocks());

it('no abre una orden distinta cuando la búsqueda devuelve coincidencias parciales', async () => {
  (listSolicitudesExamen as jest.Mock).mockResolvedValue([{ id: 9, numero: 'OTRA-ORDEN', paciente: 3 }]);
  expect(await resolveDemoLimsOrdenId()).toBeNull();
});

it('no elige el primer paciente si no coincide con el ejemplo', async () => {
  (listSolicitudesExamen as jest.Mock).mockResolvedValue([{ id: 9, numero: 'OTRA-ORDEN', paciente: 3 }]);
  (pacientesService.search as jest.Mock).mockResolvedValue([{ id: 7, dni: 'OTRO-DNI' }]);
  expect(await resolveDemoPatientId()).toBeNull();
});

it('puede localizar por DNI el paciente demo cuando no accede a las órdenes', async () => {
  (listSolicitudesExamen as jest.Mock).mockRejectedValue(new Error('Sin acceso'));
  (pacientesService.search as jest.Mock).mockResolvedValue([{ id: 7, dni: 'QA-DEMO-00001' }]);
  expect(await resolveDemoPatientId()).toBe(7);
});
