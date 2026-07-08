import {
  computeFormulaLeucocitariaProgress,
  convertSysmexEntry,
  formatFormulaProgressLabel,
  previewSysmexInforme,
  sysmexEntryFromStored,
} from './sysmexHemograma';

describe('sysmexHemograma', () => {
  it('convierte leucocitos ticket 93 → 9300 /mm³', () => {
    const c = convertSysmexEntry('LEU', '93');
    expect(c?.valorNumerico).toBe(9300);
    expect(c?.valorInforme).toBe('9300');
  });

  it('convierte hematíes ticket 237 → 2.370.000 en informe', () => {
    const c = convertSysmexEntry('HEMATIES', '237');
    expect(c?.valorNumerico).toBe(2.37);
    expect(c?.valorInforme).toBe('2.370.000');
  });

  it('convierte HGB ticket 73 → 7.3', () => {
    expect(previewSysmexInforme('HGB', '73')).toBe('7.3');
  });

  it('convierte RDW ticket 139 → 13.9', () => {
    expect(previewSysmexInforme('RDW', '139')).toBe('13.9');
  });

  it('convierte plaquetas ticket 158 → 158.000', () => {
    const c = convertSysmexEntry('PLAQ', '158');
    expect(c?.valorNumerico).toBe(158000);
    expect(c?.valorInforme).toBe('158000');
  });

  it('fórmula cayados 70 → 70 sin decimal', () => {
    expect(previewSysmexInforme('NEUT_CAY', '70')).toBe('70');
    expect(previewSysmexInforme('NEUT_SEG', '698')).toBe('698');
  });

  it('calcula faltante de fórmula leucocitaria hacia 100%', () => {
    const p = computeFormulaLeucocitariaProgress([
      { codigo: 'NEUT_CAY', valor_sysmex: '70' },
      { codigo: 'NEUT_SEG', valor_sysmex: '' },
      { codigo: 'LEU', valor_sysmex: '93' },
    ]);
    expect(p.sum).toBe(70);
    expect(p.remaining).toBe(30);
    expect(p.hasValues).toBe(true);
    expect(p.isComplete).toBe(false);
  });

  it('detecta fórmula completa y excedida', () => {
    const ok = computeFormulaLeucocitariaProgress([
      { codigo: 'NEUT_SEG', valor_sysmex: '60' },
      { codigo: 'LINF', valor_sysmex: '40' },
    ]);
    expect(ok.isComplete).toBe(true);
    expect(formatFormulaProgressLabel(ok)).toBe('100% completo');

    const over = computeFormulaLeucocitariaProgress([
      { codigo: 'NEUT_SEG', valor_sysmex: '70' },
      { codigo: 'LINF', valor_sysmex: '40' },
    ]);
    expect(over.isOver).toBe(true);
    expect(formatFormulaProgressLabel(over)).toBe('+10% de más');
  });

  it('reconstruye entero desde valor guardado', () => {
    expect(sysmexEntryFromStored('LEU', 9300)).toBe('93');
    expect(sysmexEntryFromStored('HEMATIES', 2.37)).toBe('237');
    expect(sysmexEntryFromStored('HGB', 7.3)).toBe('73');
  });
});
