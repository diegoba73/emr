import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

const mockGetZpl = jest.fn();
const mockTalon = jest.fn();
const mockImprimirLocal = jest.fn();

jest.mock('../../../services/limsMicroApi', () => ({
  getEstudioMicroEtiquetaZpl: (...args: any[]) => mockGetZpl(...args),
  printTalonEstudioMicro: (...args: any[]) => mockTalon(...args),
}));

jest.mock('../../../services/labelPrintAgent', () => ({
  LabelPrintAgentError: class LabelPrintAgentError extends Error {
    code: string;
    constructor(code: string, message: string) {
      super(message);
      this.code = code;
    }
  },
  imprimirEtiquetaEstudioMicroLocal: (...args: any[]) => mockImprimirLocal(...args),
}));

jest.mock('../EtiquetaMuestraZplDialog', () => ({
  printerErrorMessage: (e: unknown) => (e instanceof Error ? e.message : 'error'),
}));

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { success: jest.fn(), error: jest.fn() },
}));

import ImprimirPedidoMicroDialog from './ImprimirPedidoMicroDialog';

describe('ImprimirPedidoMicroDialog', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetZpl.mockResolvedValue({
      estudio_id: 7,
      profile: '3nstar_ldt114_203_40x23',
      width_mm: 40,
      height_mm: 23,
      lines: ['LAB-2026-00099', 'PEREZ J. | DNI 23123456', 'GUARDIA', '22/09 20:00 | UROCULTIVO'],
      zpl: '^XA^XZ',
      printable: true,
      validation_errors: [],
    });
    mockTalon.mockResolvedValue(undefined);
    mockImprimirLocal.mockResolvedValue(undefined);
  });

  it('talon no llama imprimir etiqueta ZPL', async () => {
    const onEtiquetasOk = jest.fn();
    render(
      <ImprimirPedidoMicroDialog
        open
        estudioId={7}
        estudioNumero="LAB-2026-00099"
        onClose={jest.fn()}
        onEtiquetasOk={onEtiquetasOk}
      />
    );
    await waitFor(() => {
      expect(mockGetZpl).toHaveBeenCalledWith(7);
      expect(screen.getByRole('button', { name: 'Imprimir talón' })).toBeEnabled();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Imprimir talón' }));
    await waitFor(() => {
      expect(mockTalon).toHaveBeenCalledWith(7);
    });
    expect(mockImprimirLocal).not.toHaveBeenCalled();
    expect(onEtiquetasOk).not.toHaveBeenCalled();
  });

  it('imprimir etiqueta usa agente local ZPL', async () => {
    const onEtiquetasOk = jest.fn();
    const onClose = jest.fn();
    render(
      <ImprimirPedidoMicroDialog
        open
        estudioId={7}
        estudioNumero="LAB-2026-00099"
        onClose={onClose}
        onEtiquetasOk={onEtiquetasOk}
      />
    );
    await waitFor(() => {
      expect(screen.getByText('LAB-2026-00099')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Imprimir etiqueta' }));
    await waitFor(() => {
      expect(mockImprimirLocal).toHaveBeenCalledWith(7);
    });
    expect(onEtiquetasOk).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});
