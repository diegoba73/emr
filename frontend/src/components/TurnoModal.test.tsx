import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TurnoModal from './TurnoModal';
import { CLINICAL_ACTION_ERRORS } from '../utils/apiError';

const mockCancelarTurno = jest.fn();
const mockMarcarNoAsistioTurno = jest.fn();
const mockGetTurno = jest.fn();
const mockReprogramarTurno = jest.fn();
const mockUpdateTurno = jest.fn();

jest.mock('../services/api', () => ({
  apiService: {
    getTurno: (...args: unknown[]) => mockGetTurno(...args),
    cancelarTurno: (...args: unknown[]) => mockCancelarTurno(...args),
    marcarNoAsistioTurno: (...args: unknown[]) => mockMarcarNoAsistioTurno(...args),
    reprogramarTurno: (...args: unknown[]) => mockReprogramarTurno(...args),
    updateTurno: (...args: unknown[]) => mockUpdateTurno(...args),
    createTurno: jest.fn(),
    confirmarTurno: jest.fn(),
    marcarRealizadoTurno: jest.fn(),
    iniciarAtencionTurno: jest.fn(),
    createAtencion: jest.fn(),
    getAtenciones: jest.fn().mockResolvedValue([]),
  },
}));

jest.mock('../contexts/DataContext', () => ({
  useData: () => ({
    recursos: [{ id: 1, nombre: 'Consultorio 1', tipo_recurso: 'CONSULTORIO', activo: true }],
    currentUser: { id: 1, rol: 'ADMIN', is_staff: true, is_superuser: true },
    refreshAll: jest.fn().mockResolvedValue(undefined),
    refreshTurnos: jest.fn().mockResolvedValue(undefined),
  }),
}));

jest.mock('./common/AsyncAutocomplete', () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock('../modules/atenciones/components/AtencionDetailDrawer', () => ({
  __esModule: true,
  default: () => null,
}));

const baseTurno = {
  id: 42,
  estado: 'CONFIRMADO',
  medico_id: 1,
  recurso_id: 1,
  paciente_id: 10,
  fecha_hora_inicio: '2026-06-20T10:00:00',
  fecha_hora_fin: '2026-06-20T11:00:00',
  medico: { id: 1, nombre: 'Juan', apellido: 'Perez' },
  recurso: { id: 1, nombre: 'Consultorio 1', tipo_recurso: 'CONSULTORIO' },
  paciente: { id: 10, nombre: 'Ana', apellido: 'Lopez' },
};

function getMotivoDialog(title: string): HTMLElement {
  const heading = screen.getByRole('heading', { name: title });
  const dialog = heading.closest('[role="dialog"]');
  if (!dialog) {
    throw new Error(`Motivo dialog "${title}" not found`);
  }
  return dialog as HTMLElement;
}

function renderTurnoModal(props: Partial<React.ComponentProps<typeof TurnoModal>> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <TurnoModal
        open
        onClose={jest.fn()}
        editingTurno={baseTurno}
        onSuccess={jest.fn()}
        {...props}
      />
    </QueryClientProvider>
  );
}

async function waitForTurnoFormReady() {
  await waitFor(() => {
    expect(screen.getByRole('button', { name: 'Actualizar Turno' })).toBeInTheDocument();
    expect(screen.getByDisplayValue('10:00')).toBeInTheDocument();
  });
}

async function submitReprogramacionForm() {
  await waitForTurnoFormReady();
  fireEvent.change(screen.getByDisplayValue('10:00'), { target: { value: '11:00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Actualizar Turno' }));
  await waitFor(() => {
    expect(screen.getByRole('heading', { name: 'Reprogramar turno' })).toBeInTheDocument();
  });
}

describe('TurnoModal motivo dialog', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetTurno.mockResolvedValue(baseTurno);
    mockCancelarTurno.mockResolvedValue({
      turno: { ...baseTurno, estado: 'CANCELADO' },
      message: 'Turno cancelado',
    });
    mockMarcarNoAsistioTurno.mockResolvedValue({ turno: baseTurno, message: 'OK' });
    window.alert = jest.fn();
  });

  it('abre modal al cancelar turno y no llama API si se cancela', async () => {
    renderTurnoModal();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Cancelar turno' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }));
    const dialog = getMotivoDialog('Cancelar turno');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }));

    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Cancelar turno' })).not.toBeInTheDocument();
    });
    expect(mockCancelarTurno).not.toHaveBeenCalled();
  });

  it('confirma cancelación con motivo trim y llama API', async () => {
    const onSuccess = jest.fn();
    renderTurnoModal({ onSuccess });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Cancelar turno' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }));
    const dialog = getMotivoDialog('Cancelar turno');
    fireEvent.change(within(dialog).getByRole('textbox'), {
      target: { value: '  Paciente avisó  ' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar turno' }));

    await waitFor(() => {
      expect(mockCancelarTurno).toHaveBeenCalledWith(42, 'Paciente avisó');
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it('deshabilita confirmar con motivo vacío en cancelación', async () => {
    renderTurnoModal();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Cancelar turno' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }));
    const dialog = getMotivoDialog('Cancelar turno');
    const confirmar = within(dialog).getByRole('button', { name: 'Cancelar turno' });
    expect(confirmar).toBeDisabled();
    fireEvent.click(confirmar);
    expect(mockCancelarTurno).not.toHaveBeenCalled();
  });

  it('muestra error seguro de API al cancelar sin cerrar el modal', async () => {
    mockCancelarTurno.mockRejectedValue(new Error('Error de red'));
    renderTurnoModal();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Cancelar turno' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }));
    const dialog = getMotivoDialog('Cancelar turno');
    fireEvent.change(within(dialog).getByRole('textbox'), {
      target: { value: 'Motivo válido' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar turno' }));

    await waitFor(() => {
      expect(within(dialog).getByText(CLINICAL_ACTION_ERRORS.turnoCancelar)).toBeInTheDocument();
    });
    expect(screen.getByRole('heading', { name: 'Cancelar turno' })).toBeInTheDocument();
  });

  it('impide doble envío mientras la API está en curso', async () => {
    let resolveCancel!: (value: unknown) => void;
    mockCancelarTurno.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCancel = resolve;
        })
    );
    renderTurnoModal();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Cancelar turno' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }));
    const dialog = getMotivoDialog('Cancelar turno');
    fireEvent.change(within(dialog).getByRole('textbox'), {
      target: { value: 'Motivo' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar turno' }));

    await waitFor(() => {
      expect(within(dialog).getByRole('button', { name: 'Cancelar turno' })).toBeDisabled();
    });

    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar turno' }));
    expect(mockCancelarTurno).toHaveBeenCalledTimes(1);

    resolveCancel({ turno: baseTurno, message: 'OK' });
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Cancelar turno' })).not.toBeInTheDocument();
    });
  });

  it('no muestra cancelar turno si el turno está REALIZADO', async () => {
    renderTurnoModal({
      editingTurno: { ...baseTurno, estado: 'REALIZADO' },
    });
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Cancelar turno' })).not.toBeInTheDocument();
    });
  });

  it('abre modal no asistió con valor inicial y llama API', async () => {
    renderTurnoModal();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'No asistió' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'No asistió' }));
    const dialog = getMotivoDialog('Registrar no asistencia');
    expect(within(dialog).getByRole('textbox')).toHaveValue('No asistió');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Confirmar' }));

    await waitFor(() => {
      expect(mockMarcarNoAsistioTurno).toHaveBeenCalledWith(42, 'No asistió');
    });
  });
});

describe('TurnoModal reprogramación', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetTurno.mockResolvedValue(baseTurno);
    mockReprogramarTurno.mockResolvedValue({
      turno: { ...baseTurno, fecha_hora_inicio: '2026-06-20T11:00:00' },
    });
    mockUpdateTurno.mockResolvedValue(baseTurno);
    window.alert = jest.fn();
  });

  it('al reprogramar un turno, abre MotivoDialog, exige motivo y llama reprogramarTurno con payload preservado', async () => {
    const onClose = jest.fn();
    const onSuccess = jest.fn();
    renderTurnoModal({ onClose, onSuccess });

    await submitReprogramacionForm();
    const dialog = getMotivoDialog('Reprogramar turno');
    expect(within(dialog).getByText('Motivo de reprogramación (obligatorio)')).toBeInTheDocument();

    const confirmar = within(dialog).getByRole('button', { name: 'Reprogramar' });
    expect(confirmar).toBeDisabled();

    fireEvent.change(within(dialog).getByRole('textbox'), {
      target: { value: '  Cambio de horario solicitado  ' },
    });
    expect(confirmar).not.toBeDisabled();
    fireEvent.click(confirmar);

    await waitFor(() => {
      expect(mockReprogramarTurno).toHaveBeenCalledTimes(1);
      expect(mockReprogramarTurno).toHaveBeenCalledWith(42, {
        fecha_hora_inicio: '2026-06-20T11:00:00',
        fecha_hora_fin: '2026-06-20T12:00:00',
        motivo: 'Cambio de horario solicitado',
        medico_id: 1,
        recurso_id: 1,
      });
      expect(mockUpdateTurno).toHaveBeenCalledWith(42, {
        motivo_reserva: '',
        paciente_id: 10,
      });
      expect(onSuccess).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
      expect(screen.queryByRole('heading', { name: 'Reprogramar turno' })).not.toBeInTheDocument();
    });
  });

  it('reprogramación no llama API si se cancela el modal de motivo', async () => {
    renderTurnoModal();
    await submitReprogramacionForm();

    const dialog = getMotivoDialog('Reprogramar turno');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }));

    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Reprogramar turno' })).not.toBeInTheDocument();
    });
    expect(mockReprogramarTurno).not.toHaveBeenCalled();
    expect(mockUpdateTurno).not.toHaveBeenCalled();
  });
});
