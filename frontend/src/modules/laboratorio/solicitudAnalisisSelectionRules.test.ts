import {
  CA_ION_INCLUYE_CODIGOS,
  CARTUCHO_CARDIACO_CODIGOS,
  EAB_INCLUYE_CODIGOS,
  EXAMENES_CUBIERTOS_POR_PANEL,
  esCodigoCartuchoCardiaco,
  esPanelEab,
} from './solicitudAnalisisSelectionRules';
import { papelCodigosSet, SOLICITUD_ANALISIS_PAPEL_ROWS } from './solicitudAnalisisPapelLayout';

describe('solicitudAnalisisSelectionRules', () => {
  it('agrupa cartucho cardíaco', () => {
    expect(CARTUCHO_CARDIACO_CODIGOS).toEqual(['TROP_I', 'CPK_MB', 'MIOG']);
    expect(esCodigoCartuchoCardiaco('TROP_I')).toBe(true);
    expect(esCodigoCartuchoCardiaco('GLU')).toBe(false);
  });

  it('incluye prácticas al pedir EAB', () => {
    expect(esPanelEab('PAN_EAB_ART')).toBe(true);
    expect(EAB_INCLUYE_CODIGOS.paneles).toContain('PAN_IONO');
    expect(EAB_INCLUYE_CODIGOS.examenes).toEqual(expect.arrayContaining(['LACT', 'CA_ION']));
  });

  it('CA_ION suelto incluye CA y PROT_T para Zeisler', () => {
    expect(CA_ION_INCLUYE_CODIGOS).toEqual(['CA', 'PROT_T']);
  });

  it('cubre INR y CL por sus paneles', () => {
    expect(EXAMENES_CUBIERTOS_POR_PANEL.INR).toBe('PAN_COAG');
    expect(EXAMENES_CUBIERTOS_POR_PANEL.CL).toBe('PAN_IONO');
  });
});

describe('solicitudAnalisisPapelLayout — ítems nuevos', () => {
  it('incluye CL bajo ionograma, INR bajo coagulograma y serologías en columna derecha', () => {
    const codes = papelCodigosSet();
    for (const c of [
      'CL',
      'INR',
      'HBVAGS',
      'HCVG',
      'HIVAC',
      'VDRL',
      'GRUPO',
      'PAN_ORI',
    ]) {
      expect(codes.has(c)).toBe(true);
    }
    const left = SOLICITUD_ANALISIS_PAPEL_ROWS.map((r) => r.left?.codigo).filter(
      Boolean
    ) as string[];
    const right = SOLICITUD_ANALISIS_PAPEL_ROWS.map((r) => r.right?.codigo).filter(
      Boolean
    ) as string[];
    expect(left.indexOf('CL')).toBeGreaterThan(left.indexOf('PAN_IONO'));
    expect(left.indexOf('INR')).toBeGreaterThan(left.indexOf('PAN_COAG'));
    expect(left[left.length - 1]).toBe('LDH');
    expect(right.slice(0, 5)).toEqual(['CPK', 'CPK_MB', 'MIOG', 'TROP_I', 'TROP_US']);
    expect(right.indexOf('VDRL')).toBeLessThan(right.indexOf('HBVAGS'));
    expect(right.indexOf('HBVAGS')).toBeLessThan(right.indexOf('HCVG'));
    expect(right.indexOf('HCVG')).toBeLessThan(right.indexOf('HIVAC'));
    expect(right[right.length - 1]).toBe('LACT');
    expect(codes.has('HCGB')).toBe(false);
    expect(codes.has('SANOC')).toBe(false);
    expect(codes.has('ASTO')).toBe(false);
    expect(codes.has('PAN_ENA')).toBe(false);
  });
});
