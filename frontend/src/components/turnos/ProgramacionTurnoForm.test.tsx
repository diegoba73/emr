import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import ProgramacionTurnoForm from './ProgramacionTurnoForm';

jest.mock('../../contexts/DataContext', () => ({
  useData: () => ({
    currentUser: { id: 1, rol: 'SECRETARIA', is_staff: true },
    medicos: [{ id: 1, nombre: 'Juan', apellido: 'Perez' }],
    pacientes: [],
    loadMedicos: jest.fn(),
    loadPacientes: jest.fn(),
    refreshTurnos: jest.fn(),
  }),
}));

jest.mock('../common/AsyncAutocomplete', () => ({
  __esModule: true,
  default: ({ label }: { label?: string }) => <div data-testid="async-ac">{label}</div>,
}));

jest.mock('../../services/estudiosComplementariosApi', () => ({
  listTiposEstudioComplementario: jest.fn(() => Promise.resolve([])),
  createEstudioComplementario: jest.fn(),
  asignarTurnoEstudio: jest.fn(),
  agendarTurnoEstudioDesdeAgenda: jest.fn(),
}));

jest.mock('../../services/apiService', () => ({
  getCirugiaEspecialidades: jest.fn(() => Promise.resolve([])),
  getCirugiaProcedimientos: jest.fn(() => Promise.resolve([])),
  getCirugiaAbordajes: jest.fn(() => Promise.resolve([])),
}));

jest.mock('../../utils/recursosEstudio', () => ({
  listRecursosProcCirugiaAgenda: jest.fn(() => Promise.resolve([])),
}));

jest.mock('../../services/agendaMedica', () => ({
  getDiasDisponibles: jest.fn(() => Promise.resolve([])),
  getSlotsMedico: jest.fn(() => Promise.resolve([])),
}));

describe('ProgramacionTurnoForm', () => {
  it('muestra orden paciente → profesional → tipo de actividad', async () => {
    render(<ProgramacionTurnoForm onCancel={jest.fn()} />);
    await waitFor(() => {
      expect(screen.getByText('Consulta médica')).toBeInTheDocument();
    });
    expect(screen.getByTestId('async-ac')).toHaveTextContent(/Paciente/i);
    expect(screen.getAllByText(/Profesional \/ médico/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Tipo de actividad').length).toBeGreaterThan(0);
  });
});
