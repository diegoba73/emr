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
    pacientes: [],
    loadPacientes: jest.fn().mockResolvedValue(undefined),
    loadRecursos: jest.fn().mockResolvedValue(undefined),
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

  it('muestra reprogramar para secretaría/admin y no muestra actualizar', async () => {
    renderTurnoModal();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Reprogramar turno' })).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: 'Actualizar turno' })).not.toBeInTheDocument();
  });

  it('reprograma con motivo y ofrece abrir WhatsApp si hay enlace', async () => {
    const onSuccess = jest.fn();
    mockReprogramarTurno.mockResolvedValue({
      turno: { ...baseTurno, fecha_hora_inicio: '2026-06-21T11:00:00' },
      message: 'Turno reprogramado',
      notificacion: {
        whatsapp_enviado: false,
        whatsapp_url: 'https://wa.me/5491112345678?text=hola',
        push_enviados: 0,
      },
    });
    window.confirm = jest.fn(() => true);
    window.open = jest.fn();
    renderTurnoModal({ onSuccess });
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Reprogramar turno' })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Reprogramar turno' }));
    const dialog = getMotivoDialog('Reprogramar turno');
    fireEvent.change(within(dialog).getByRole('textbox'), {
      target: { value: 'Paciente pidió otro día' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Reprogramar' }));
    await waitFor(() => {
      expect(mockReprogramarTurno).toHaveBeenCalled();
      expect(window.open).toHaveBeenCalledWith(
        'https://wa.me/5491112345678?text=hola',
        '_blank',
        'noopener,noreferrer'
      );
      expect(onSuccess).toHaveBeenCalled();
    });
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
