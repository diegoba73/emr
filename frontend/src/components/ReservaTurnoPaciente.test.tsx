import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import ReservaTurnoPaciente from './ReservaTurnoPaciente';
import { getMedicos } from '../services/apiService';
import { getSlotsMedico, reservarHorario } from '../services/agendaMedica';
jest.mock('../services/apiService', () => ({ getMedicos: jest.fn() }));
jest.mock('../services/agendaMedica', () => ({ getSlotsMedico: jest.fn(), reservarHorario: jest.fn() }));
jest.mock('../utils/calendarLocalizer', () => ({ localizer: {} }));
jest.mock('react-big-calendar', () => ({ Calendar: (props: any) => <div>
  <span>{props.step} minutos · {props.timeslots} divisiones</span>
  {props.events.map((e: any) => <button key={e.slot.inicio} onClick={() => props.onSelectEvent(e)}>Reservar {e.slot.inicio}</button>)}
</div> }));
const slot = { horario_id: 7, inicio: '2035-01-02T09:00:00-03:00', fin: '2035-01-02T09:20:00-03:00', duracion_min: 20, tipo: 'CONSULTA' };
beforeEach(() => {
  jest.clearAllMocks();
  (getMedicos as jest.Mock).mockResolvedValue([{ id: 3, nombre: 'Ana', apellido: 'Prueba' }]);
  (getSlotsMedico as jest.Mock).mockResolvedValue([slot]);
  (reservarHorario as jest.Mock).mockResolvedValue({ id: 1 });
});
async function selectDoctor() {
  await waitFor(() => expect(getMedicos).toHaveBeenCalled());
  fireEvent.mouseDown(screen.getByLabelText('Médico'));
  fireEvent.click(await screen.findByRole('option', { name: 'Prueba, Ana' }));
  fireEvent.click(await screen.findByRole('button', { name: /Reservar 2035/ }));
}
it('reserva el horario confirmado sin pedir consultorio ni prioridad', async () => {
  const onReserved = jest.fn();
  render(<ReservaTurnoPaciente onReserved={onReserved} />);
  await selectDoctor();
  expect(screen.queryByLabelText(/consultorio/i)).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/prioridad/i)).not.toBeInTheDocument();
  expect(screen.getByText('20 minutos · 3 divisiones')).toBeInTheDocument();
  expect(reservarHorario).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar turno' }));
  await waitFor(() => expect(reservarHorario).toHaveBeenCalledWith(slot, ''));
  await waitFor(() => expect(onReserved).toHaveBeenCalledTimes(1));
  expect(await screen.findByText('Tu turno quedó reservado.')).toBeInTheDocument();
});
it('muestra el conflicto y vuelve a consultar disponibilidad', async () => {
  (reservarHorario as jest.Mock).mockRejectedValue({ response: { status: 400, data: { detail: 'El horario ya está ocupado.' } } });
  const onReserved = jest.fn();
  render(<ReservaTurnoPaciente onReserved={onReserved} />);
  await selectDoctor();
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar turno' }));
  expect(await screen.findByText('El horario ya está ocupado.')).toBeInTheDocument();
  await waitFor(() => expect(getSlotsMedico).toHaveBeenCalledTimes(2));
  expect(onReserved).not.toHaveBeenCalled();
});
