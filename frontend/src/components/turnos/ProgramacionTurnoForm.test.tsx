import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import ProgramacionTurnoForm from './ProgramacionTurnoForm';
import { listTiposEstudioComplementario } from '../../services/estudiosComplementariosApi';
import { getCirugiaEspecialidades } from '../../services/apiService';
import { listRecursosProcCirugiaAgenda } from '../../utils/recursosEstudio';

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

jest.mock('./SlotPickerStaff', () => () => null);

jest.mock('../../services/estudiosComplementariosApi', () => ({
  __esModule: true,
  listTiposEstudioComplementario: jest.fn(),
  createEstudioComplementario: jest.fn(),
  asignarTurnoEstudio: jest.fn(),
  agendarTurnoEstudioDesdeAgenda: jest.fn(),
}));

jest.mock('../../services/apiService', () => ({
  __esModule: true,
  getCirugiaEspecialidades: jest.fn(),
  getCirugiaProcedimientos: jest.fn(),
  getCirugiaAbordajes: jest.fn(),
}));

jest.mock('../../utils/recursosEstudio', () => ({
  __esModule: true,
  listRecursosProcCirugiaAgenda: jest.fn(),
}));

jest.mock('../../services/agendaMedica', () => ({
  __esModule: true,
  getDiasDisponibles: jest.fn(() => Promise.resolve([])),
  getSlotsMedico: jest.fn(() => Promise.resolve([])),
}));

jest.mock('../../services/api', () => ({
  apiService: {
    createTurno: jest.fn(),
  },
}));

describe('ProgramacionTurnoForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (listTiposEstudioComplementario as jest.Mock).mockResolvedValue([]);
    (listRecursosProcCirugiaAgenda as jest.Mock).mockResolvedValue([]);
    (getCirugiaEspecialidades as jest.Mock).mockResolvedValue([]);
  });

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
