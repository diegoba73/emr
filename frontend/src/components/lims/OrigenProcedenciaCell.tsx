import React from 'react';
import { Typography } from '@mui/material';
import type { SolicitudExamenLims } from '../../types/lims';
import { formatOrigenProcedenciaCell } from '../../utils/limsOrigenSolicitud';

export interface OrigenProcedenciaCellProps {
  row: Pick<
    SolicitudExamenLims,
    'origen_solicitud' | 'origen_solicitud_display' | 'procedencia_display'
  >;
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
