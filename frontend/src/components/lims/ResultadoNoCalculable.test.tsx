import React from 'react';
import { render, screen } from '@testing-library/react';
import ResultadosOrdenLista from './ResultadosOrdenLista';
import { RESULTADO_NO_CALCULABLE } from '../../utils/calculosDerivados';
import type { ResultadoExamenLims } from '../../types/lims';

it('muestra el aviso sin número, unidad ni clasificación en rango', () => {
  const resultado = {
    id: 1, tipo_examen: 1, tipo_examen_codigo: 'LDL', tipo_examen_nombre: 'LDL colesterol',
    valor_obtenido: RESULTADO_NO_CALCULABLE, valor_numerico: null,
    unidad: 'mg/dl', es_patologico: false, es_critico: false,
  } as ResultadoExamenLims;
  render(<ResultadosOrdenLista resultados={[resultado]} modo="clinico" />);
  expect(screen.getByText(RESULTADO_NO_CALCULABLE)).toBeInTheDocument();
  expect(screen.getByText('No calculable')).toBeInTheDocument();
  expect(screen.queryByText('En rango')).not.toBeInTheDocument();
  expect(screen.queryByText('mg/dl')).not.toBeInTheDocument();
});
