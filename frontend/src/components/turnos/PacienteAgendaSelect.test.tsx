import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PacienteAgendaSelect, {
  looksLikeDniQuery,
  normalizeDniQuery,
} from './PacienteAgendaSelect';
import { api, createPaciente, getCandidatosDuplicadoPaciente } from '../../services/apiService';

jest.mock('../../services/apiService', () => ({
  api: { get: jest.fn() },
  createPaciente: jest.fn(),
  updatePaciente: jest.fn(),
  getCandidatosDuplicadoPaciente: jest.fn().mockResolvedValue({
    bloquea_alta: false,
    resultados: [],
  }),
}));

jest.mock('../ObraSocialSelect', () => {
  return function MockObraSocialSelect({
    value,
    onChange,
  }: {
    value: string;
    onChange: (v: string) => void;
  }) {
    return (
      <input
        aria-label="Obra Social"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  };
});

describe('looksLikeDniQuery / normalizeDniQuery', () => {
  it('reconoce DNI numérico con separadores', () => {
    expect(looksLikeDniQuery('30.111.222')).toBe(true);
    expect(looksLikeDniQuery('30111222')).toBe(true);
    expect(looksLikeDniQuery('Garcia')).toBe(false);
    expect(normalizeDniQuery('30.111.222')).toBe('30111222');
  });
});

async function typeCombobox(value: string) {
  const input = screen.getByRole('combobox');
  await userEvent.clear(input);
  await userEvent.type(input, value);
  // MUI debounce(0) aún encola microtask/timeout.
  await act(async () => {
    await Promise.resolve();
  });
}

describe('PacienteAgendaSelect', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (getCandidatosDuplicadoPaciente as jest.Mock).mockResolvedValue({
      bloquea_alta: false,
      resultados: [],
    });
    (api.get as jest.Mock).mockResolvedValue({ data: { results: [] } });
  });

  it('ofrece crear paciente cuando el DNI no existe', async () => {
    render(
      <PacienteAgendaSelect value={null} onChange={jest.fn()} debounceMs={0} />,
    );
    await typeCombobox('30999888');
    expect(
      await screen.findByText(/No existe un paciente con DNI 30999888/i),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Crear paciente' }));
    expect(await screen.findByText('Nuevo Paciente')).toBeInTheDocument();
    const dniFields = screen.getAllByDisplayValue('30999888');
    expect(dniFields.length).toBeGreaterThanOrEqual(1);
  });

  it('tras crear selecciona el paciente y permite seguir con el turno', async () => {
    const created = {
      id: 77,
      nombre: 'NUEVO',
      apellido: 'PAC',
      dni: '30999888',
      fecha_nacimiento: '1990-01-01',
      obra_social: 'PARTICULAR',
    };
    (createPaciente as jest.Mock).mockResolvedValue(created);
    const onChange = jest.fn();
    render(<PacienteAgendaSelect value={null} onChange={onChange} debounceMs={0} />);
    await typeCombobox('30999888');
    await userEvent.click(await screen.findByRole('button', { name: 'Crear paciente' }));
    expect(await screen.findByText('Nuevo Paciente')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Nombre \*/i), { target: { value: 'Nuevo' } });
    fireEvent.change(screen.getByLabelText(/Apellido \*/i), { target: { value: 'Pac' } });
    fireEvent.change(screen.getByLabelText(/Fecha de Nacimiento/i), {
      target: { value: '1990-01-01' },
    });
    fireEvent.change(screen.getByLabelText(/Obra Social/i), {
      target: { value: 'PARTICULAR' },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Crear Paciente' }));
    });

    await waitFor(() => {
      expect(createPaciente).toHaveBeenCalled();
      expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ id: 77, dni: '30999888' }));
    });
  });

  it('no ofrece alta si la búsqueda no parece DNI', async () => {
    render(<PacienteAgendaSelect value={null} onChange={jest.fn()} debounceMs={0} />);
    await typeCombobox('Garcia');
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(screen.queryByRole('button', { name: 'Crear paciente' })).not.toBeInTheDocument();
  });
});
