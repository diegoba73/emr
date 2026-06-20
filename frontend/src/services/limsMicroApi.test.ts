import {
  listAisladosMicrobiologicos,
  listAntibiogramas,
  listIdentificacionesMicroorganismo,
  listInformesMicrobiologia,
  listLecturasCultivo,
  listResultadosAntibiotico,
  listSiembrasMicrobiologia,
} from './limsMicroApi';

jest.mock('./limsApi', () => ({
  getPaginatedAll: jest.fn(() => Promise.resolve([])),
}));

import { getPaginatedAll } from './limsApi';

describe('limsMicroApi estudio_id filter', () => {
  beforeEach(() => {
    (getPaginatedAll as jest.Mock).mockClear();
  });

  const cases: Array<{
    name: string;
    fn: (params?: { estudio_id?: number }) => Promise<unknown>;
    path: string;
    pageSize: number;
  }> = [
    {
      name: 'listSiembrasMicrobiologia',
      fn: listSiembrasMicrobiologia,
      path: '/lab/microbiologia/siembras/',
      pageSize: 500,
    },
    {
      name: 'listLecturasCultivo',
      fn: listLecturasCultivo,
      path: '/lab/microbiologia/lecturas/',
      pageSize: 500,
    },
    {
      name: 'listAisladosMicrobiologicos',
      fn: listAisladosMicrobiologicos,
      path: '/lab/microbiologia/aislados/',
      pageSize: 500,
    },
    {
      name: 'listIdentificacionesMicroorganismo',
      fn: listIdentificacionesMicroorganismo,
      path: '/lab/microbiologia/identificaciones/',
      pageSize: 500,
    },
    {
      name: 'listAntibiogramas',
      fn: listAntibiogramas,
      path: '/lab/microbiologia/antibiogramas/',
      pageSize: 500,
    },
    {
      name: 'listResultadosAntibiotico',
      fn: listResultadosAntibiotico,
      path: '/lab/microbiologia/resultados-antibiotico/',
      pageSize: 1000,
    },
    {
      name: 'listInformesMicrobiologia',
      fn: listInformesMicrobiologia,
      path: '/lab/microbiologia/informes/',
      pageSize: 500,
    },
  ];

  it.each(cases)('$name sends estudio_id when provided', async ({ fn, path, pageSize }) => {
    await fn({ estudio_id: 42 });
    expect(getPaginatedAll).toHaveBeenCalledWith(path, {
      page_size: pageSize,
      estudio_id: 42,
    });
  });

  it.each(cases)('$name without estudio_id keeps prior behavior', async ({ fn, path, pageSize }) => {
    await fn();
    expect(getPaginatedAll).toHaveBeenCalledWith(path, {
      page_size: pageSize,
    });
  });
});
