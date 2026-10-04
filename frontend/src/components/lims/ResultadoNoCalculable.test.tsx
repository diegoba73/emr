import React from 'react';
import { render, screen } from '@testing-library/react';
import ResultadosOrdenLista from './ResultadosOrdenLista';
import { RESULTADO_NO_CALCULABLE } from '../../utils/calculosDerivados';
import type { ResultadoExamenLims } from '../../types/lims';

const resultadoNoCalculable = {
  id: 1,
  tipo_examen: 1,
  tipo_examen_codigo: 'LDL',
  tipo_examen_nombre: 'LDL colesterol',
  valor_obtenido: RESULTADO_NO_CALCULABLE,
  valor_numerico: null,
  unidad: 'mg/dl',
  es_patologico: false,
  es_critico: false,
} as ResultadoExamenLims;

const resultadoVacio = {
  id: 2,
  tipo_examen: 2,
  tipo_examen_codigo: 'CLEAR_CREA',
  tipo_examen_nombre: 'Clearance de creatinina',
  valor_obtenido: '',
  valor_numerico: null,
  unidad: 'mL/min',
  es_patologico: false,
  es_critico: false,
} as ResultadoExamenLims;

it('en laboratorio muestra el aviso sin número, unidad ni clasificación en rango', () => {
  render(<ResultadosOrdenLista resultados={[resultadoNoCalculable]} modo="laboratorio" />);
  expect(screen.getByText(RESULTADO_NO_CALCULABLE)).toBeInTheDocument();
  expect(screen.getByText('No calculable')).toBeInTheDocument();
  expect(screen.queryByText('En rango')).not.toBeInTheDocument();
  expect(screen.queryByText('mg/dl')).not.toBeInTheDocument();
});

it('en clínica, orden no finalizada: no calculable / vacío → En proceso (sin texto técnico)', () => {
  render(
    <ResultadosOrdenLista
      resultados={[resultadoNoCalculable, resultadoVacio]}
      modo="clinico"
      estadoOrden="INFORMADO_PARCIAL"
    />
  );
  expect(screen.queryByText(RESULTADO_NO_CALCULABLE)).not.toBeInTheDocument();
  expect(screen.queryByText('No calculable')).not.toBeInTheDocument();
  expect(screen.getAllByText('En proceso')).toHaveLength(2);
});

it('en clínica, orden FINALIZADO: conserva No calculable', () => {
  render(
    <ResultadosOrdenLista
      resultados={[resultadoNoCalculable]}
      modo="clinico"
      estadoOrden="FINALIZADO"
    />
  );
  expect(screen.getByText(RESULTADO_NO_CALCULABLE)).toBeInTheDocument();
  expect(screen.getByText('No calculable')).toBeInTheDocument();
  expect(screen.queryByText('En proceso')).not.toBeInTheDocument();
});
