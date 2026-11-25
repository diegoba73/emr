import { apiClient } from './apiClient';
import { listTiposExamenLims, sanitizeTipoExamenWriteBody } from './limsApi';

jest.mock('./apiClient', () => ({
  apiClient: { defaults: { baseURL: '/api' }, get: jest.fn() },
}));

describe('sanitizeTipoExamenWriteBody', () => {
  it('persiste vacíos en campos texto y rangos (no omite la clave)', () => {
    const out = sanitizeTipoExamenWriteBody({
      nombre: 'Glucosa',
      metodo: '',
      unidad_default: null as unknown as string,
      abreviatura: '',
      rango_referencia_texto: '',
      rango_min: '',
      rango_max: null,
      formato_informe_entrada: '',
    });
    expect(out.metodo).toBe('');
    expect(out.unidad_default).toBe('');
    expect(out.abreviatura).toBe('');
    expect(out.rango_referencia_texto).toBe('');
    expect(out.formato_informe_entrada).toBe('');
    expect(out.rango_min).toBeNull();
    expect(out.rango_max).toBeNull();
  });

  it('sigue omitiendo undefined (PATCH parcial)', () => {
    const out = sanitizeTipoExamenWriteBody({
      nombre: 'Glucosa',
      metodo: undefined,
    });
    expect(out).toEqual({ nombre: 'Glucosa' });
  });
});

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
        2,
        '/lab/examenes/?activo=true&page=2&page_size=2000',
        expect.anything()
      );
      expect(rows.map((row) => row.codigo)).toEqual(['CREATI', 'AU']);
    }
  );
});
