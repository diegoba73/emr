import React from 'react';
import { render, screen } from '@testing-library/react';
import BedCard from './BedCard';
import type { Cama } from '../../types';

it('una cama retirada ocupada sigue mostrando al paciente y la marca de retiro', () => {
  const cama = { id: 1, nombre: 'Cama 1', sector: 1, estado: 'OCUPADA', activo: false,
    aislada: false, internacion_actual: { nombre_paciente: 'Paciente de prueba',
      dias_internacion: 2, fecha_ingreso: '2026-01-01', diagnostico: 'Control' } } as Cama;
  render(<BedCard cama={cama} onClick={() => {}} />);
  expect(screen.getByText('Retirada de uso · sin nuevos ingresos')).toBeInTheDocument();
  expect(screen.getByText('Paciente de prueba')).toBeInTheDocument();
});
