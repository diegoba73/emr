import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MotivoDialog, useMotivoDialog } from './MotivoDialog';

function TestHarness({
  onConfirm,
  required = true,
}: {
  onConfirm: (motivo: string) => Promise<void>;
  required?: boolean;
}) {
  const { openMotivoDialog, dialogProps } = useMotivoDialog();
  return (
    <>
      <button
        type="button"
        onClick={() =>
          openMotivoDialog({
            title: 'Cancelar acción',
            label: 'Motivo de cancelación',
            required,
            onConfirm,
          })
        }
      >
        Abrir
      </button>
      <MotivoDialog {...dialogProps} />
    </>
  );
}

describe('MotivoDialog', () => {
  it('abre el modal y no llama API al cancelar', async () => {
    const onConfirm = jest.fn().mockResolvedValue(undefined);
    render(<TestHarness onConfirm={onConfirm} />);

    fireEvent.click(screen.getByRole('button', { name: 'Abrir' }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('deshabilita confirmar con motivo vacío si es obligatorio', () => {
    const onConfirm = jest.fn();
    render(<TestHarness onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole('button', { name: 'Abrir' }));

    const confirmar = screen.getByRole('button', { name: 'Confirmar' });
    expect(confirmar).toBeDisabled();
    fireEvent.click(confirmar);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('confirma con motivo trim y llama onConfirm', async () => {
    const onConfirm = jest.fn().mockResolvedValue(undefined);
    render(<TestHarness onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole('button', { name: 'Abrir' }));

    const dialog = screen.getByRole('dialog');
    fireEvent.change(within(dialog).getByRole('textbox'), {
      target: { value: '  Contaminación  ' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }));

    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledWith('Contaminación');
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('usa initialMotivo al abrir', () => {
    function InitialHarness() {
      const { openMotivoDialog, dialogProps } = useMotivoDialog();
      return (
        <>
          <button
            type="button"
            onClick={() =>
              openMotivoDialog({
                title: 'Acción',
                label: 'Motivo',
                initialMotivo: 'No asistió',
                onConfirm: async () => undefined,
              })
            }
          >
            Abrir
          </button>
          <MotivoDialog {...dialogProps} />
        </>
      );
    }
    render(<InitialHarness />);
    fireEvent.click(screen.getByRole('button', { name: 'Abrir' }));
    expect(within(screen.getByRole('dialog')).getByRole('textbox')).toHaveValue('No asistió');
  });

  it('muestra error y mantiene el modal si onConfirm falla', async () => {
    const onConfirm = jest.fn().mockRejectedValue(new Error('Error API'));
    render(<TestHarness onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole('button', { name: 'Abrir' }));
    const dialog = screen.getByRole('dialog');
    fireEvent.change(within(dialog).getByRole('textbox'), {
      target: { value: 'Motivo válido' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }));

    await waitFor(() => {
      expect(screen.getByText('Error API')).toBeInTheDocument();
    });
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
