import React from 'react';
import { Chip } from '@mui/material';
import type { ResultadoExamenLims } from '../../types/lims';

export interface ResultadoEstadoBadgeProps {
  resultado: Pick<ResultadoExamenLims, 'valor_obtenido' | 'es_patologico' | 'es_critico'>;
  size?: 'small' | 'medium';
}

const ResultadoEstadoBadge: React.FC<ResultadoEstadoBadgeProps> = ({ resultado, size = 'small' }) => {
  const valor = (resultado.valor_obtenido ?? '').trim();
  if (!valor) {
    return <Chip size={size} label="Pendiente" color="default" variant="outlined" />;
  }
  if (resultado.es_critico) {
    return <Chip size={size} label="Crítico" color="error" />;
  }
  if (resultado.es_patologico) {
    return <Chip size={size} label="Patológico" color="warning" />;
  }
  return <Chip size={size} label="Normal" color="success" variant="outlined" />;
};

export default ResultadoEstadoBadge;
