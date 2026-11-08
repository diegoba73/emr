import {
  EXAMENES_GUARDIA_PERMITIDOS,
  PANELES_GUARDIA_PERMITIDOS,
  esOrigenCatalogoGuardia,
  examenPermitidoEnGuardia,
  filtrarExamenesGuardia,
  filtrarPanelesGuardia,
  panelPermitidoEnGuardia,
} from './limsCatalogoGuardia';

describe('limsCatalogoGuardia', () => {
  it('detecta origen GUARDIA', () => {
    expect(esOrigenCatalogoGuardia('GUARDIA')).toBe(true);
    expect(esOrigenCatalogoGuardia('guardia')).toBe(true);
    expect(esOrigenCatalogoGuardia('AMBULATORIO_ICPL')).toBe(false);
  });

  it('permite paneles y exámenes canónicos', () => {
    Array.from(PANELES_GUARDIA_PERMITIDOS).forEach((c) => {
      expect(panelPermitidoEnGuardia(c)).toBe(true);
    });
    Array.from(EXAMENES_GUARDIA_PERMITIDOS).forEach((c) => {
      expect(examenPermitidoEnGuardia(c)).toBe(true);
    });
  });

  it('acepta urea y rechaza AU / perfil lipídico', () => {
    expect(examenPermitidoEnGuardia('UREA')).toBe(true);
    expect(examenPermitidoEnGuardia('AU')).toBe(false);
    expect(panelPermitidoEnGuardia('PAN_LIP')).toBe(false);
  });

  it('acepta examen con panel_equivalente permitido', () => {
    expect(
      examenPermitidoEnGuardia('HEMO_PROD', { panelEquivalente: 'PAN_HEMO' })
    ).toBe(true);
  });

  it('filtra listas', () => {
    expect(
      filtrarPanelesGuardia([
        { codigo: 'PAN_HEMO' },
        { codigo: 'PAN_LIP' },
      ]).map((p) => p.codigo)
    ).toEqual(['PAN_HEMO']);
    expect(
      filtrarExamenesGuardia([
        { codigo: 'GLU' },
        { codigo: 'UREA' },
        { codigo: 'AU' },
        { codigo: 'X', panel_equivalente: 'PAN_IONO' },
      ]).map((e) => e.codigo)
    ).toEqual(['GLU', 'UREA', 'X']);
  });
});
