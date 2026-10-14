import type { ResultadoExamenLims, SolicitudExamenLims } from '../types/lims';
import {
  ordenResultadosCompletos,
  resultadoTieneValor,
  valorTextoDesdeResultado,
} from './limsOrdenResultados';

describe('limsOrdenResultados', () => {
  const baseOrden = (resultados: ResultadoExamenLims[]): SolicitudExamenLims => ({
    id: 1,
    numero: 'LAB-1',
    paciente: 1,
    medico_interno: 1,
    origen_solicitud: 'AMBULATORIO_CEHTA',
    estado: 'EN_PROCESO',
    fecha_solicitud: '2026-01-01',
    fecha_programada_toma: '2026-01-01',
    resultados,
  });

  it('detecta resultados incompletos', () => {
    expect(
      ordenResultadosCompletos(
        baseOrden([
          { id: 1, solicitud: 1, tipo_examen: 1, valor_obtenido: '10' },
          { id: 2, solicitud: 1, tipo_examen: 2, valor_obtenido: '' },
        ])
      )
    ).toBe(false);
  });

  it('detecta resultados completos', () => {
    expect(
      ordenResultadosCompletos(
        baseOrden([
          { id: 1, solicitud: 1, tipo_examen: 1, valor_obtenido: '10' },
          { id: 2, solicitud: 1, tipo_examen: 2, valor_obtenido: 'Positivo' },
        ])
      )
    ).toBe(true);
  });

  it('ignora espacios en blanco', () => {
    expect(resultadoTieneValor({ valor_obtenido: '  ' })).toBe(false);
  });

  it('no trata solo valor_numerico como informado (cualitativos / símbolos mandan por texto)', () => {
    expect(resultadoTieneValor({ valor_obtenido: '', valor_numerico: 40 })).toBe(false);
    expect(resultadoTieneValor({ valor_obtenido: 'Positivo' })).toBe(true);
    expect(resultadoTieneValor({ valor_obtenido: '<0.5' })).toBe(true);
  });

  it('valorTextoDesdeResultado prioriza texto/símbolos y solo rellena número finito si no hay texto', () => {
    expect(
      valorTextoDesdeResultado({ valor_obtenido: 'Positivo', valor_numerico: 1 })
    ).toBe('Positivo');
    expect(valorTextoDesdeResultado({ valor_obtenido: '<0.5', valor_numerico: 0.5 })).toBe('<0.5');
    expect(valorTextoDesdeResultado({ valor_obtenido: '', valor_numerico: 40 })).toBe('40');
    expect(valorTextoDesdeResultado({ valor_obtenido: '  ', valor_numerico: null })).toBe('');
  });
});
