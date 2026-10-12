import {
  estadoEstudioMicroColor,
  labelEstadoEstudioMicro,
  labelEstadoMicroGeneral,
} from './limsEstadosMicro';
import { estadoOrdenColor, labelEstadoOrdenLims } from './limsEstadosOrden';

describe('limsEstadosMicro — alineado con órdenes clínicas', () => {
  it('estados compartidos: mismo texto y color que clínico', () => {
    expect(labelEstadoEstudioMicro('PENDIENTE')).toBe(labelEstadoOrdenLims('PENDIENTE'));
    expect(estadoEstudioMicroColor('PENDIENTE')).toBe(estadoOrdenColor('PENDIENTE'));

    expect(labelEstadoEstudioMicro('LISTO_PARA_VALIDAR')).toBe(
      labelEstadoOrdenLims('LISTO_PARA_VALIDAR')
    );
    expect(estadoEstudioMicroColor('LISTO_PARA_VALIDAR')).toBe(
      estadoOrdenColor('LISTO_PARA_VALIDAR')
    );

    expect(labelEstadoEstudioMicro('CANCELADO')).toBe(labelEstadoOrdenLims('CANCELADO'));
    expect(estadoEstudioMicroColor('CANCELADO')).toBe(estadoOrdenColor('CANCELADO'));
  });

  it('etapas técnicas se muestran como En proceso (mismo color que EN_PROCESO)', () => {
    for (const e of [
      'RECIBIDO',
      'SEMBRADO',
      'LECTURA_PRELIMINAR',
      'IDENTIFICACION',
      'ANTIBIOGRAMA',
    ] as const) {
      expect(labelEstadoEstudioMicro(e)).toBe('En proceso');
      expect(estadoEstudioMicroColor(e)).toBe(estadoOrdenColor('EN_PROCESO'));
    }
  });

  it('Validado e Informado se muestran como Finalizado', () => {
    expect(labelEstadoEstudioMicro('VALIDADO')).toBe('Finalizado');
    expect(labelEstadoEstudioMicro('INFORMADO')).toBe('Finalizado');
    expect(estadoEstudioMicroColor('VALIDADO')).toBe(estadoOrdenColor('FINALIZADO'));
    expect(estadoEstudioMicroColor('INFORMADO')).toBe(estadoOrdenColor('FINALIZADO'));
    expect(labelEstadoMicroGeneral('VALIDADO')).toBe('Finalizado');
    expect(labelEstadoMicroGeneral('INFORMADO')).toBe('Finalizado');
  });
});
