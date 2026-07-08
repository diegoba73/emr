import type { ResultadoExamenLims, SolicitudExamenLims } from '../types/lims';
import { ordenResultadosCompletos, resultadoTieneValor } from './limsOrdenResultados';

describe('limsOrdenResultados', () => {
  const baseOrden = (resultados: ResultadoExamenLims[]): SolicitudExamenLims => ({
    id: 1,
    numero: 'LAB-1',
    paciente: 1,
    medico_interno: 1,
    origen_solicitud: 'AMBULATORIO_CEHTA',
    estado: 'EN_PROCESO',
    fecha_solicitud: '2026-01-01',
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
    expect(resultadoTieneValor({ id: 1, solicitud: 1, tipo_examen: 1, valor_obtenido: '  ' })).toBe(false);
  });
});
