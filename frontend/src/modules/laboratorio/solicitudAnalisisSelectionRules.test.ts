import {
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

  it('cubre INR y CL por sus paneles', () => {
    expect(EXAMENES_CUBIERTOS_POR_PANEL.INR).toBe('PAN_COAG');
    expect(EXAMENES_CUBIERTOS_POR_PANEL.CL).toBe('PAN_IONO');
  });
});

describe('solicitudAnalisisPapelLayout — ítems nuevos', () => {
  it('incluye CL bajo ionograma, INR bajo coagulograma y pruebas bajo LDH', () => {
    const codes = papelCodigosSet();
    for (const c of [
      'CL',
      'INR',
      'HBVAGS',
      'HCVG',
      'HIVAC',
      'HCGB',
      'SANOC',
      'ASTO',
      'GRUPO',
    ]) {
      expect(codes.has(c)).toBe(true);
    }
    const flat = SOLICITUD_ANALISIS_PAPEL_ROWS.flatMap((r) =>
      [r.left, r.right].filter(Boolean).map((i) => i!.codigo)
    );
    expect(flat.indexOf('CL')).toBeGreaterThan(flat.indexOf('PAN_IONO'));
    expect(flat.indexOf('INR')).toBeGreaterThan(flat.indexOf('PAN_COAG'));
    expect(flat.indexOf('HBVAGS')).toBeGreaterThan(flat.indexOf('LDH'));
  });
});
