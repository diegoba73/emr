import {
  ESTADOS_ORDEN_LIMS,
  estadoOrdenColor,
  labelEstadoOrdenLims,
  ordenEsFinalizada,
  ordenListaParaValidar,
  ordenPuedeCargarResultados,
  ordenPuedeCorregirResultados,
  ordenPuedeDesvalidar,
  ordenPuedeEnviarInforme,
} from './limsEstadosOrden';

describe('limsEstadosOrden — LISTO_PARA_VALIDAR', () => {
  it('incluye el estado en el catálogo y label', () => {
    expect(ESTADOS_ORDEN_LIMS).toContain('LISTO_PARA_VALIDAR');
    expect(labelEstadoOrdenLims('LISTO_PARA_VALIDAR')).toBe('Listo para validar');
    expect(estadoOrdenColor('LISTO_PARA_VALIDAR')).toBe('warning');
    expect(labelEstadoOrdenLims('INFORMADO_PARCIAL')).toBe('Informe parcial');
  });

  it('ordenListaParaValidar solo mira el estado', () => {
    expect(ordenListaParaValidar('LISTO_PARA_VALIDAR')).toBe(true);
    expect(ordenListaParaValidar('LISTO_PARA_VALIDAR', false)).toBe(true);
    expect(ordenListaParaValidar('EN_PROCESO', true)).toBe(false);
    expect(ordenListaParaValidar('INFORMADO_PARCIAL', true)).toBe(false);
    expect(ordenListaParaValidar('FINALIZADO', true)).toBe(false);
  });

  it('permite carga/corrección hasta validar', () => {
    expect(ordenPuedeCargarResultados('EN_PROCESO')).toBe(true);
    expect(ordenPuedeCargarResultados('INFORMADO_PARCIAL')).toBe(true);
    expect(ordenPuedeCargarResultados('LISTO_PARA_VALIDAR')).toBe(true);
    expect(ordenPuedeCargarResultados('FINALIZADO')).toBe(false);
    expect(ordenPuedeCorregirResultados('LISTO_PARA_VALIDAR')).toBe(true);
  });

  it('permite desvalidar solo en FINALIZADO', () => {
    expect(ordenPuedeDesvalidar('FINALIZADO')).toBe(true);
    expect(ordenPuedeDesvalidar('LISTO_PARA_VALIDAR')).toBe(false);
    expect(ordenPuedeDesvalidar('EN_PROCESO')).toBe(false);
  });

  it('solo permite enviar informe validado (FINALIZADO)', () => {
    expect(ordenPuedeEnviarInforme('INFORMADO_PARCIAL')).toBe(false);
    expect(ordenPuedeEnviarInforme('LISTO_PARA_VALIDAR')).toBe(false);
    expect(ordenPuedeEnviarInforme('FINALIZADO')).toBe(true);
    expect(ordenPuedeEnviarInforme('EN_PROCESO')).toBe(false);
    expect(ordenEsFinalizada('LISTO_PARA_VALIDAR')).toBe(false);
  });
});
