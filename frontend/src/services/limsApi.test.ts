import { apiClient } from './apiClient';
import { listTiposExamenLims } from './limsApi';

jest.mock('./apiClient', () => ({
  apiClient: { defaults: { baseURL: '/api' }, get: jest.fn() },
}));

describe('paginación del catálogo detrás del proxy', () => {
  beforeEach(() => jest.clearAllMocks());

  it.each(['/api', 'https://emr.example/api'])(
    'carga la segunda página sin usar el origen HTTP de next con base %s',
    async (baseURL) => {
      apiClient.defaults.baseURL = baseURL;
      const get = apiClient.get as jest.Mock;
      get.mockResolvedValueOnce({ data: {
        results: [{ id: 1, codigo: 'CREATI' }],
        next: 'http://emr.example/api/lab/examenes/?activo=true&page=2&page_size=2000',
      } });
      get.mockResolvedValueOnce({ data: {
        results: [{ id: 69, codigo: 'AU' }], next: null,
      } });

      const rows = await listTiposExamenLims({ activo: true });

      expect(get).toHaveBeenNthCalledWith(
        2, '/lab/examenes/?activo=true&page=2&page_size=2000'
      );
      expect(rows.map((row) => row.codigo)).toEqual(['CREATI', 'AU']);
    }
  );
});
