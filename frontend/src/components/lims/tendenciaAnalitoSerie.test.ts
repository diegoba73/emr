import {
  armarSerieTendencia,
  parseValorNumerico,
  puntosNumericos,
} from './tendenciaAnalitoSerie';

describe('parseValorNumerico', () => {
  it('parsea número, string y coma decimal', () => {
    expect(parseValorNumerico(12.5)).toBe(12.5);
    expect(parseValorNumerico('3.2')).toBe(3.2);
    expect(parseValorNumerico('1,5')).toBe(1.5);
  });

  it('devuelve null si no es numérico', () => {
    expect(parseValorNumerico(null)).toBeNull();
    expect(parseValorNumerico('')).toBeNull();
    expect(parseValorNumerico('Positivo')).toBeNull();
  });

  it('usa el límite cuando hay operador', () => {
    expect(parseValorNumerico('<0.1')).toBe(0.1);
    expect(parseValorNumerico('>20')).toBe(20);
  });
});

describe('armarSerieTendencia', () => {
  const previos = [
    {
      valor: '30',
      valor_numerico: '30',
      unidad: 'ng/L',
      fecha: '2026-03-10T10:00:00Z',
      solicitud_id: 3,
      solicitud_numero: 'LAB-3',
    },
    {
      valor: '10',
      valor_numerico: '10',
      unidad: 'ng/L',
      fecha: '2026-01-01T10:00:00Z',
      solicitud_id: 1,
      solicitud_numero: 'LAB-1',
    },
  ];

  it('ordena cronológicamente e incluye el actual al final si es más reciente', () => {
    const serie = armarSerieTendencia({
      previos,
      actual: {
        valor: '50',
        valor_numerico: 50,
        unidad: 'ng/L',
        fecha: '2026-04-01T12:00:00Z',
        solicitudId: 9,
        solicitudNumero: 'LAB-9',
      },
    });
    expect(serie.map((p) => p.valor)).toEqual(['10', '30', '50']);
    expect(serie[2].esActual).toBe(true);
  });

  it('omite actual vacío', () => {
    const serie = armarSerieTendencia({ previos, actual: { valor: '  ' } });
    expect(serie).toHaveLength(2);
    expect(serie.every((p) => !p.esActual)).toBe(true);
  });
});

describe('puntosNumericos', () => {
  it('filtra solo puntos con valor numérico', () => {
    const serie = armarSerieTendencia({
      previos: [
        {
          valor: 'Positivo',
          valor_numerico: null,
          fecha: '2026-01-01T00:00:00Z',
          solicitud_id: 1,
          solicitud_numero: 'A',
        },
        {
          valor: '2.1',
          valor_numerico: '2.1',
          fecha: '2026-02-01T00:00:00Z',
          solicitud_id: 2,
          solicitud_numero: 'B',
        },
      ],
    });
    expect(puntosNumericos(serie)).toHaveLength(1);
    expect(puntosNumericos(serie)[0].valor).toBe('2.1');
  });
});
