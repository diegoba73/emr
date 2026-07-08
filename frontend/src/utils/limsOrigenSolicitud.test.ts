import {
  esOrigenAmbulatorioExterno,
  formatOrigenProcedenciaCell,
  labelOrigenSolicitudLims,
} from './limsOrigenSolicitud';

describe('limsOrigenSolicitud', () => {
  it('formatOrigenProcedenciaCell muestra detalle cuando agrega contexto', () => {
    const cell = formatOrigenProcedenciaCell({
      origen_solicitud: 'AMBULATORIO_CEHTA',
      procedencia_display: 'Consultorio Ambulatorio — Consultorio CEHTA 1 — CEHTA',
    });
    expect(cell.titulo).toBe('Ambulatorio — CEHTA');
    expect(cell.detalle).toContain('Consultorio CEHTA 1');
  });

  it('formatOrigenProcedenciaCell omite detalle si repite el título', () => {
    const cell = formatOrigenProcedenciaCell({
      origen_solicitud: 'GUARDIA',
      procedencia_display: 'Guardia',
    });
    expect(cell.titulo).toBe('Guardia');
    expect(cell.detalle).toBeUndefined();
  });

  it('labelOrigenSolicitudLims usa display del backend si viene', () => {
    expect(labelOrigenSolicitudLims('AMBULATORIO_ICPL', 'Ambulatorio — ICPL')).toBe(
      'Ambulatorio — ICPL'
    );
  });

  it('esOrigenAmbulatorioExterno identifica CEHTA e ICPL', () => {
    expect(esOrigenAmbulatorioExterno('EXTERNO_CEHTA')).toBe(true);
    expect(esOrigenAmbulatorioExterno('EXTERNO_ICPL')).toBe(true);
    expect(esOrigenAmbulatorioExterno('AMBULATORIO_CEHTA')).toBe(false);
  });

  it('formatOrigenProcedenciaCell muestra receta externa', () => {
    const cell = formatOrigenProcedenciaCell({
      origen_solicitud: 'EXTERNO_CEHTA',
      procedencia_display: 'Receta externa — presentada en CEHTA · Dr. García',
    });
    expect(cell.titulo).toBe('Ambulatorio externo — CEHTA');
    expect(cell.detalle).toContain('Receta externa');
    expect(cell.detalle).toContain('Dr. García');
  });
});
