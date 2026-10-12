import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

const mockGetZpl = jest.fn();
const mockPrepare = jest.fn();
const mockTalon = jest.fn();
const mockImprimirLocal = jest.fn();

jest.mock('../../../services/limsMicroApi', () => ({
  getEstudioMicroEtiquetaZpl: (...args: any[]) => mockGetZpl(...args),
  postEstudioMicroImprimirEtiqueta: (...args: any[]) => mockPrepare(...args),
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
    mockPrepare.mockResolvedValue({
      estudio_id: 7,
      profile: 'p',
      resultado: 'prepared',
      zpl: '^XA^XZ',
    });
    mockTalon.mockResolvedValue(undefined);
    mockImprimirLocal.mockResolvedValue(undefined);
  });

  it('al abrir solo preview: no marca recepción', async () => {
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
      expect(screen.getByRole('button', { name: 'Imprimir etiqueta' })).toBeEnabled();
    });
    expect(mockPrepare).not.toHaveBeenCalled();
    expect(onEtiquetasOk).not.toHaveBeenCalled();
  });

  it('imprimir: marca etiquetas, imprime y notifica (pasa a esperando recepción)', async () => {
    const onEtiquetasOk = jest.fn().mockResolvedValue(undefined);
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
      expect(screen.getByRole('button', { name: 'Imprimir etiqueta' })).toBeEnabled();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Imprimir etiqueta' }));
    await waitFor(() => {
      expect(mockPrepare).toHaveBeenCalledWith(7);
      expect(mockImprimirLocal).toHaveBeenCalledWith(7);
      expect(onEtiquetasOk).toHaveBeenCalled();
    });
  });

  it('si falla el USB igual notifica tras marcar etiquetas', async () => {
    mockImprimirLocal.mockRejectedValue(new Error('sin agente'));
    const onEtiquetasOk = jest.fn().mockResolvedValue(undefined);
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
      expect(screen.getByRole('button', { name: 'Imprimir etiqueta' })).toBeEnabled();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Imprimir etiqueta' }));
    await waitFor(() => {
      expect(mockPrepare).toHaveBeenCalled();
      expect(onEtiquetasOk).toHaveBeenCalled();
    });
  });
});
