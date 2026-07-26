import React from 'react';
import { Typography } from '@mui/material';
import type { OrigenSolicitudLims } from '../../types/lims';
import { formatOrigenProcedenciaCell } from '../../utils/limsOrigenSolicitud';

export interface OrigenProcedenciaCellProps {
  row: {
    origen_solicitud?: OrigenSolicitudLims | string | null;
    origen_solicitud_display?: string | null;
    procedencia_display?: string | null;
  };
}

const OrigenProcedenciaCellView: React.FC<OrigenProcedenciaCellProps> = ({ row }) => {
  const { titulo, detalle } = formatOrigenProcedenciaCell(row);
  return (
    <>
      <Typography variant="body2" fontWeight={500}>
        {titulo}
      </Typography>
      {detalle ? (
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.25 }}>
          {detalle}
        </Typography>
      ) : null}
    </>
  );
};

export default OrigenProcedenciaCellView;
