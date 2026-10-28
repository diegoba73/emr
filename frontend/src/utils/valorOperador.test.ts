import { numeroParaCalculo, parseValorConOperador } from './valorOperador';
import { parseValorNumerico as parseCarga } from './limsCargaMuestra';
import { buildCargarResultadoPayload, normalizeDraftRow } from './limsCargaMuestra';
import { parseValorNumerico as parseTendencia } from '../components/lims/tendenciaAnalitoSerie';

describe('valorOperador', () => {
  it('parsea <0.1 y >20', () => {
    expect(parseValorConOperador('<0.1')).toEqual({
      operador: '<',
      numero: 0.1,
      texto: '<0.1',
    });
    expect(numeroParaCalculo('> 20')).toBe(20);
    expect(numeroParaCalculo('≤0,5')).toBe(0.5);
  });

  it('no inventa número en texto libre', () => {
    expect(numeroParaCalculo('Positivo')).toBeNull();
    expect(numeroParaCalculo('')).toBeNull();
  });
});

describe('integración carga / tendencia', () => {
  it('buildCargarResultadoPayload manda valor_numerico = límite', () => {
    const item = buildCargarResultadoPayload(1, normalizeDraftRow({ valor: '<0.1' }));
    expect(item.valor).toBe('<0.1');
    expect(item.valor_numerico).toBe(0.1);
  });

  it('parseCarga y tendencia alineados', () => {
    expect(parseCarga('<0.1')).toBe(0.1);
    expect(parseTendencia('<0.1')).toBe(0.1);
    expect(parseTendencia('Positivo')).toBeNull();
    expect(parseCarga('Negativo')).toBe('Negativo');
  });
});
