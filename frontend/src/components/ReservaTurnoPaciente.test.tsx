import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import ReservaTurnoPaciente from './ReservaTurnoPaciente';
import { getDiasDisponibles, getSlotsMedico, reservarHorario } from '../services/agendaMedica';

jest.mock('../services/agendaMedica', () => ({
  getSlotsMedico: jest.fn(),
  getDiasDisponibles: jest.fn(),
  reservarHorario: jest.fn(),
}));

jest.mock('./common/AsyncAutocomplete', () => ({
  __esModule: true,
  default: ({
    label,
    onChange,
    disabled,
  }: {
    label: string;
    onChange: (v: unknown) => void;
    disabled?: boolean;
  }) => (
    <button
      type="button"
      disabled={disabled}
      aria-label={label}
      onClick={() =>
        onChange({ id: 3, nombre: 'Ana', apellido: 'Prueba', duracion_slot_min: 15 })
      }
    >
      Buscar médico
    </button>
  ),
}));

jest.mock('../utils/calendarLocalizer', () => ({ localizer: {} }));

jest.mock('react-big-calendar', () => ({
  Calendar: (props: {
    events: Array<{ fecha: string; title: string; start: Date }>;
    onSelectEvent: (e: { fecha: string; start: Date }) => void;
    onSelectSlot: (s: { start: Date }) => void;
  }) => (
    <div data-testid="reserva-calendario-mock">
      {props.events.map((e) => (
        <button
          key={e.fecha}
          type="button"
          onClick={() => props.onSelectEvent(e)}
        >
          Día {e.fecha}
        </button>
      ))}
      <button
        type="button"
        onClick={() => props.onSelectSlot({ start: new Date(`${props.events[0]?.fecha || '2035-01-15'}T12:00:00`) })}
      >
        Slot vacío
      </button>
    </div>
  ),
}));

function pad(n: number) {
  return String(n).padStart(2, '0');
}

function fechaLocal(d: Date) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const dia = (() => {
  const d = new Date();
  d.setHours(12, 0, 0, 0);
  return d;
})();
const fechaStr = fechaLocal(dia);
const slotInicio = new Date(dia.getFullYear(), dia.getMonth(), dia.getDate(), 9, 0, 0);
const slotFin = new Date(dia.getFullYear(), dia.getMonth(), dia.getDate(), 9, 15, 0);
const slot = {
  horario_id: 7,
  inicio: slotInicio.toISOString(),
  fin: slotFin.toISOString(),
  duracion_min: 15,
  tipo: 'CONSULTA',
  recurso_id: 3,
  recurso_nombre: 'Consultorio 1',
};
const horaLabel = slotInicio.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });

beforeEach(() => {
  jest.clearAllMocks();
  (getDiasDisponibles as jest.Mock).mockResolvedValue([
    { fecha: fechaStr, cantidad_slots: 4 },
  ]);
  (getSlotsMedico as jest.Mock).mockResolvedValue([slot]);
  (reservarHorario as jest.Mock).mockResolvedValue({ id: 1 });
});

async function elegirMedicoYDia() {
  fireEvent.click(screen.getByRole('button', { name: 'Buscar médico' }));
  await waitFor(() => expect(getDiasDisponibles).toHaveBeenCalled());
  fireEvent.click(await screen.findByRole('button', { name: `Día ${fechaStr}` }));
  await waitFor(() => expect(getSlotsMedico).toHaveBeenCalled());
  fireEvent.click(await screen.findByRole('button', { name: horaLabel }));
}

it('busca médico, elige día en calendario y reserva mostrando consultorio', async () => {
  const onReserved = jest.fn();
  render(<ReservaTurnoPaciente onReserved={onReserved} />);
  await elegirMedicoYDia();

  expect(screen.getByLabelText('Buscar médico')).toBeInTheDocument();
  expect(screen.queryByLabelText(/prioridad/i)).not.toBeInTheDocument();

  const dialog = screen.getByRole('dialog');
  expect(within(dialog).getByText(/15 minutos/)).toBeInTheDocument();
  expect(within(dialog).getByText(/Consultorio 1/)).toBeInTheDocument();
  expect(reservarHorario).not.toHaveBeenCalled();

  fireEvent.click(within(dialog).getByRole('button', { name: 'Confirmar turno' }));
  await waitFor(() => expect(reservarHorario).toHaveBeenCalledWith(slot, ''));
  await waitFor(() => expect(onReserved).toHaveBeenCalledTimes(1));
  expect(await screen.findByText('Tu turno quedó reservado.')).toBeInTheDocument();
});

it('muestra el conflicto y vuelve a consultar disponibilidad', async () => {
  (reservarHorario as jest.Mock).mockRejectedValue({
    response: { status: 400, data: { detail: 'El horario ya está ocupado.' } },
  });
  const onReserved = jest.fn();
  render(<ReservaTurnoPaciente onReserved={onReserved} />);
  await elegirMedicoYDia();
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar turno' }));
  expect(await screen.findByText('El horario ya está ocupado.')).toBeInTheDocument();
  await waitFor(() => expect(getDiasDisponibles).toHaveBeenCalledTimes(2));
  expect(onReserved).not.toHaveBeenCalled();
});

it('carga el calendario del mes al elegir médico', async () => {
  render(<ReservaTurnoPaciente onReserved={jest.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Buscar médico' }));
  await waitFor(() => expect(getDiasDisponibles).toHaveBeenCalled());
  expect(screen.getByTestId('reserva-calendario-mock')).toBeInTheDocument();
  const [medicoId, desde, hasta, tipo] = (getDiasDisponibles as jest.Mock).mock.calls[0];
  expect(medicoId).toBe(3);
  expect(tipo).toBe('CONSULTA');
  expect(desde <= fechaStr).toBe(true);
  expect(hasta >= fechaStr).toBe(true);
});
