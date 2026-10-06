import {
  formatPctElp,
  porcentajeFraccionElp,
  esCodigoElpFraccion,
} from './proteinograma';

describe('proteinograma', () => {
  it('calcula % como en el informe de ejemplo', () => {
    expect(porcentajeFraccionElp(3.71, 6.2)).toBe(59.8);
    expect(formatPctElp(59.8)).toBe('59,8 %');
  });

  it('detecta códigos de fracción ELP', () => {
    expect(esCodigoElpFraccion('ELP_ALB')).toBe(true);
    expect(esCodigoElpFraccion('PROT_T')).toBe(false);
  });

  it('sin PROT_T no calcula', () => {
    expect(porcentajeFraccionElp(3.71, null)).toBeNull();
  });
});
