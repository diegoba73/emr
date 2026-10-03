import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import EstudioMicroResumenTab from './EstudioMicroResumenTab';
import type { EstudioMicrobiologia } from '../../../types/lims';

const base: EstudioMicrobiologia = {
  id: 1,
  numero: 'LAB-2026-00001',
  paciente: 10,
  paciente_nombre: 'Perez, Ana',
  estado: 'RECIBIDO',
  tipo_estudio: 'UROCULTIVO',
  etiquetas_impresas_at: '2026-10-01T12:00:00Z',
  codigo_barra: 'LAB-2026-00001',
} as EstudioMicrobiologia;

describe('EstudioMicroResumenTab', () => {
  it('muestra reimprimir etiquetas y talón tras recepción', () => {
    const onEtq = jest.fn();
    const onTalon = jest.fn();
    render(
      <EstudioMicroResumenTab
        estudio={base}
        canOperateTecnico
        canMarcarInformado={false}
        onReimprimirEtiquetas={onEtq}
        onImprimirTalon={onTalon}
        onIniciar={jest.fn()}
        onCancelar={jest.fn()}
        onMarcarInformado={jest.fn()}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Reimprimir etiquetas' }));
    expect(onEtq).toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Imprimir talón' }));
    expect(onTalon).toHaveBeenCalled();
  });

  it('permite imprimir etiqueta la primera vez si ya está RECIBIDO sin barcode', () => {
    const onEtq = jest.fn();
    render(
      <EstudioMicroResumenTab
        estudio={{ ...base, etiquetas_impresas_at: null, codigo_barra: null }}
        canOperateTecnico
        canMarcarInformado={false}
        onReimprimirEtiquetas={onEtq}
        onImprimirTalon={jest.fn()}
        onIniciar={jest.fn()}
        onCancelar={jest.fn()}
        onMarcarInformado={jest.fn()}
      />
    );
    expect(screen.getByRole('button', { name: 'Imprimir etiquetas' })).toBeEnabled();
  });
});
