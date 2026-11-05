import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import PatientDashboard, { mapTimelineEvent } from './PatientDashboard';
import type { PacienteTimelineEvent, User } from '../../types';
import { useData } from '../../contexts/DataContext';
import { listSolicitudesExamen } from '../../services/limsApi';
import { listEstudiosMicrobiologia } from '../../services/limsMicroApi';
import { apiService } from '../../services/api';
import { getInternaciones } from '../../services/apiService';

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));
jest.mock('../../contexts/DataContext', () => ({ useData: jest.fn() }));
jest.mock('../../services/limsApi', () => ({ listSolicitudesExamen: jest.fn() }));
jest.mock('../../services/limsMicroApi', () => ({
  listEstudiosMicrobiologia: jest.fn(),
}));
jest.mock('../../services/api', () => ({
  apiService: {
    getAtenciones: jest.fn(),
    getPacienteTimeline: jest.fn(),
  },
}));
jest.mock('../../services/apiService', () => ({ getInternaciones: jest.fn() }));
jest.mock('../PatientIntegratedView', () => () => null);
jest.mock('../PacienteFormDialog', () => () => null);
jest.mock('./ProblemasClinicosPanel', () => () => null);

beforeEach(() => {
  jest.clearAllMocks();
  (getInternaciones as jest.Mock).mockResolvedValue([]);
  (apiService.getAtenciones as jest.Mock).mockResolvedValue({ results: [] });
  (apiService.getPacienteTimeline as jest.Mock).mockResolvedValue([]);
  (listSolicitudesExamen as jest.Mock).mockResolvedValue([]);
  (listEstudiosMicrobiologia as jest.Mock).mockResolvedValue([]);
});

it.each(['LABORATORIO', 'BIOQUIMICO'])(
  'abre el histórico importado desde la ficha como %s',
  async (rol) => {
    const user = { id: 1, rol, is_staff: false, is_superuser: false } as User;
    (useData as jest.Mock).mockReturnValue({
      currentUser: user,
      pacientes: [{ id: 12, nombre: 'Prueba', apellido: 'Historial' }],
      loading: { pacientes: false },
      archivosMedicos: [],
      loadPacientes: jest.fn(),
      loadArchivosMedicos: jest.fn(),
    });
    (listSolicitudesExamen as jest.Mock).mockResolvedValue([
      { id: 42, numero: 'LW-2022-00001', estado: 'FINALIZADO' },
    ]);
    render(
      <MemoryRouter initialEntries={['/paciente/12']}>
        <Routes>
          <Route path="/paciente/:id" element={<PatientDashboard />} />
        </Routes>
      </MemoryRouter>
    );
    fireEvent.click(await screen.findByText('LW-2022-00001 · Finalizado'));
    expect(mockNavigate).toHaveBeenCalledWith(
      '/laboratorio/ordenes/42',
      expect.anything()
    );

    const event = mapTimelineEvent(
      {
        id: 'lab42',
        type: 'laboratorio',
        title: 'Importado',
        date: '2022-06-30',
        navigate_to: '/solicitudes/42',
      } as PacienteTimelineEvent,
      mockNavigate,
      12,
      user
    );
    event?.onClick?.();
    expect(mockNavigate).toHaveBeenLastCalledWith(
      '/laboratorio/ordenes/42',
      expect.anything()
    );
  }
);
