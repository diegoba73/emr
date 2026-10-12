import { estadoEstudioMicroColor, labelEstadoEstudioMicro } from './limsEstadosMicro';
import { estadoOrdenColor } from './limsEstadosOrden';

describe('limsEstadosMicro — colores alineados con clínico', () => {
  it('Pendiente es warning (amarillo), igual que lab clínico', () => {
    expect(estadoEstudioMicroColor('PENDIENTE')).toBe('warning');
    expect(estadoOrdenColor('PENDIENTE')).toBe('warning');
    expect(labelEstadoEstudioMicro('PENDIENTE')).toBe('Pendiente');
  });

  it('Listo para validar es warning; validado/informado success; cancelado error', () => {
    expect(estadoEstudioMicroColor('LISTO_PARA_VALIDAR')).toBe('warning');
    expect(estadoEstudioMicroColor('VALIDADO')).toBe('success');
    expect(estadoEstudioMicroColor('INFORMADO')).toBe('success');
    expect(estadoEstudioMicroColor('CANCELADO')).toBe('error');
  });

  it('estados en curso usan primary', () => {
    expect(estadoEstudioMicroColor('RECIBIDO')).toBe('primary');
    expect(estadoEstudioMicroColor('SEMBRADO')).toBe('primary');
    expect(estadoEstudioMicroColor('ANTIBIOGRAMA')).toBe('primary');
  });
});
