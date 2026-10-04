import React from 'react';
import { Chip } from '@mui/material';
import type { ResultadoExamenLims } from '../../types/lims';
import { esResultadoNoCalculable } from '../../utils/calculosDerivados';

export interface ResultadoEstadoBadgeProps {
  resultado: Pick<ResultadoExamenLims, 'valor_obtenido' | 'es_patologico' | 'es_critico'>;
  size?: 'small' | 'medium';
  /**
   * En vista clínica, mientras la orden no esté FINALIZADO, vacío o
   * «No calculable…» se muestran como «En proceso» (aún faltan datos).
   */
  modo?: 'laboratorio' | 'clinico';
  ordenFinalizada?: boolean;
}

const ResultadoEstadoBadge: React.FC<ResultadoEstadoBadgeProps> = ({
  resultado,
  size = 'small',
  modo = 'laboratorio',
  ordenFinalizada = false,
}) => {
  const valor = (resultado.valor_obtenido ?? '').trim();
  const pendienteClinico =
    modo === 'clinico' && !ordenFinalizada && (!valor || esResultadoNoCalculable(valor));
  if (pendienteClinico) {
    return <Chip size={size} label="En proceso" color="info" variant="outlined" />;
  }
  if (!valor) {
    return <Chip size={size} label="Pendiente" color="default" variant="outlined" />;
  }
  if (esResultadoNoCalculable(valor)) {
    return <Chip size={size} label="No calculable" color="default" variant="outlined" />;
  }
  if (resultado.es_critico) {
    return <Chip size={size} label="Crítico" color="error" />;
  }
  if (resultado.es_patologico) {
    return <Chip size={size} label="Fuera de rango" color="warning" />;
  }
  return <Chip size={size} label="En rango" color="success" variant="outlined" />;
};

export default ResultadoEstadoBadge;
