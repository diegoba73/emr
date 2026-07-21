import { cantidadTubosPorExamenes, totalEtiquetasDesdeTubos, unidadesParaCalculoTubos } from './limsTubosOrden';

describe('limsTubosOrden', () => {
  it('cantidadTubosPorExamenes usa ceil(n/10)', () => {
    expect(cantidadTubosPorExamenes(0)).toBe(0);
    expect(cantidadTubosPorExamenes(1)).toBe(1);
    expect(cantidadTubosPorExamenes(10)).toBe(1);
    expect(cantidadTubosPorExamenes(11)).toBe(2);
    expect(cantidadTubosPorExamenes(21)).toBe(3);
  });

  it('unidadesParaCalculoTubos: hemograma cuenta como 1', () => {
    const hemo = [
      'HEMATIES',
      'HTO',
      'HGB',
      'RDW',
      'LEU',
      'NEUT_CAY',
      'NEUT_SEG',
      'EOS',
      'BAS',
      'LINF',
      'MONO',
      'PLAQ',
    ];
    expect(unidadesParaCalculoTubos(hemo)).toBe(1);
    expect(unidadesParaCalculoTubos([...hemo, 'HBA1C'])).toBe(2);
    expect(unidadesParaCalculoTubos(['GLU', 'UREA'])).toBe(2);
  });

  it('totalEtiquetasDesdeTubos suma cantidades', () => {
    expect(
      totalEtiquetasDesdeTubos([
        {
          tipo_muestra_id: 1,
          tipo_contenedor_id: 1,
          tipo_contenedor_codigo: 'EDTA',
          tipo_contenedor_nombre: 'EDTA',
          examenes: ['a'],
          cantidad: 1,
          examenes_count: 1,
        },
        {
          tipo_muestra_id: 1,
          tipo_contenedor_id: 2,
          tipo_contenedor_codigo: 'SUERO',
          tipo_contenedor_nombre: 'Suero',
          examenes: Array(12).fill('x'),
          cantidad: 2,
          examenes_count: 12,
        },
      ])
    ).toBe(3);
  });
});
