import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import PacienteFormDialog from './PacienteFormDialog';
import { createPaciente, updatePaciente } from '../services/apiService';
import { pacientesService } from '../services/pacientes';
import type { Paciente } from '../types';

jest.mock('../services/apiService', () => ({ createPaciente: jest.fn(), updatePaciente: jest.fn() }));
jest.mock('../services/pacientes', () => ({ pacientesService: { getById: jest.fn() } }));
const patient = { id: 8, nombre: 'ANA', apellido: 'TEST', dni: '123', fecha_nacimiento: '1990-01-01' } as Paciente;
beforeEach(() => { jest.resetAllMocks(); });
it('explica la fecha obligatoria antes de intentar crear', () => {
  render(<PacienteFormDialog open mode="create" onSaved={jest.fn()} onClose={jest.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Crear Paciente' }));
  expect(screen.getByRole('alert')).toHaveTextContent('fecha de nacimiento');
  expect(createPaciente).not.toHaveBeenCalled();
});
it('carga la ficha completa y permite corregir DNI y conservar los campos omitidos en el listado', async () => {
  (pacientesService.getById as jest.Mock).mockResolvedValue({ ...patient, observaciones: 'Conservar', antecedentes_personales: 'Antecedente', estado_civil: 'Casada', familiar_nombre: 'Contacto', sexo: 'O' });
  (updatePaciente as jest.Mock).mockResolvedValue(patient);
  render(<PacienteFormDialog open mode="edit" paciente={patient} onSaved={jest.fn()} onClose={jest.fn()} />);
  const dni = await screen.findByDisplayValue('123');
  expect(dni).toBeEnabled();
  fireEvent.change(dni, { target: { value: '456' } });
  fireEvent.click(screen.getByRole('button', { name: 'Guardar Cambios' }));
  await waitFor(() => expect(updatePaciente).toHaveBeenCalledWith(8, expect.objectContaining({ dni: '456', observaciones: 'Conservar', antecedentes_personales: 'Antecedente', estado_civil: 'Casada', familiar_nombre: 'Contacto', sexo: 'O' })));
});
it('no permite guardar una edición si falla la lectura de la ficha completa', async () => {
  (pacientesService.getById as jest.Mock).mockRejectedValue(new Error('Ficha no disponible'));
  render(<PacienteFormDialog open mode="edit" paciente={patient} onSaved={jest.fn()} onClose={jest.fn()} />);
  await screen.findByRole('alert');
  expect(screen.getByRole('button', { name: 'Guardar Cambios' })).toBeDisabled();
  expect(updatePaciente).not.toHaveBeenCalled();
});
