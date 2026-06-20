import React from 'react';
import { Typography } from '@mui/material';
import type { ResultadoExamenLims } from '../../types/lims';

export interface ResultadoRangoInfoProps {
  resultado: Pick<
    ResultadoExamenLims,
    | 'rango_referencia_snapshot'
    | 'rango_min_snapshot'
    | 'rango_max_snapshot'
    | 'unidad'
    | 'tipo_examen_rango_referencia'
  >;
  variant?: 'body2' | 'caption';
}

function formatNum(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '';
  return String(v);
}

const ResultadoRangoInfo: React.FC<ResultadoRangoInfoProps> = ({ resultado, variant = 'caption' }) => {
  const snap = (resultado.rango_referencia_snapshot ?? '').trim();
  if (snap) {
    return (
      <Typography variant={variant} color="text.secondary" component="span">
        Ref: {snap}
      </Typography>
    );
  }

  const min = formatNum(resultado.rango_min_snapshot);
  const max = formatNum(resultado.rango_max_snapshot);
  if (min && max) {
    const u = (resultado.unidad ?? '').trim();
    return (
      <Typography variant={variant} color="text.secondary" component="span">
        Ref: {min} – {max}
        {u ? ` ${u}` : ''}
      </Typography>
    );
  }

  const catalog = (resultado.tipo_examen_rango_referencia ?? '').trim();
  if (catalog) {
    return (
      <Typography variant={variant} color="text.secondary" component="span">
        Catálogo: {catalog}
      </Typography>
    );
  }

  return (
    <Typography variant={variant} color="text.secondary" component="span">
      Sin rango estructurado
    </Typography>
  );
};

export default ResultadoRangoInfo;
