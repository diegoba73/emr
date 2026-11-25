import React from 'react';
import { Chip, Stack, Typography } from '@mui/material';
import type { EstadoSolicitudLims } from '../../types/lims';
import {
  estadoOrdenColor,
  labelEstadoOrdenLims,
  ordenTieneExtraccionParcial,
  type OrdenExtraccionParcialInput,
} from '../../utils/limsEstadosOrden';

export type EstadoOrdenLimsChipProps = {
  orden: OrdenExtraccionParcialInput;
  size?: 'small' | 'medium';
};

/**
 * Chip de estado de orden LIMS.
 * Extracción parcial (EN_PROCESO + tubos PENDIENTE_TOMA): En proceso/Pendiente
 * con el color actual de cada tramo.
 */
const EstadoOrdenLimsChip: React.FC<EstadoOrdenLimsChipProps> = ({
  orden,
  size = 'small',
}) => {
  if (ordenTieneExtraccionParcial(orden)) {
    return (
      <Stack direction="row" spacing={0.5} alignItems="center" component="span">
        <Chip
          size={size}
          label={labelEstadoOrdenLims('EN_PROCESO')}
          color={estadoOrdenColor('EN_PROCESO')}
        />
        <Typography
          component="span"
          variant="caption"
          color="text.secondary"
          sx={{ lineHeight: 1, userSelect: 'none' }}
        >
          /
        </Typography>
        <Chip
          size={size}
          label={labelEstadoOrdenLims('PENDIENTE')}
          color={estadoOrdenColor('PENDIENTE')}
        />
      </Stack>
    );
  }

  const estado = orden.estado as EstadoSolicitudLims;
  return (
    <Chip
      size={size}
      label={labelEstadoOrdenLims(estado)}
      color={estadoOrdenColor(estado)}
    />
  );
};

export default EstadoOrdenLimsChip;
