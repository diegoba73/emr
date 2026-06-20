import React from 'react';
import { Chip } from '@mui/material';
import type { EstadoMuestraLims } from '../../types/lims';

const COLORS: Record<EstadoMuestraLims, 'default' | 'primary' | 'secondary' | 'success' | 'warning' | 'error'> = {
  PENDIENTE_TOMA: 'default',
  TOMADA: 'primary',
  RECIBIDA: 'primary',
  EN_PROCESO: 'warning',
  RECHAZADA: 'error',
  CONSERVADA: 'secondary',
  DESCARTADA: 'default',
  CANCELADA: 'error',
};

const LABELS: Record<EstadoMuestraLims, string> = {
  PENDIENTE_TOMA: 'Pendiente toma',
  TOMADA: 'Tomada',
  RECIBIDA: 'Recibida',
  EN_PROCESO: 'En proceso',
  RECHAZADA: 'Rechazada',
  CONSERVADA: 'Conservada',
  DESCARTADA: 'Descartada',
  CANCELADA: 'Cancelada',
};

export interface MuestraEstadoBadgeProps {
  estado: EstadoMuestraLims;
}

const MuestraEstadoBadge: React.FC<MuestraEstadoBadgeProps> = ({ estado }) => (
  <Chip
    size="small"
    label={LABELS[estado] || estado}
    color={COLORS[estado] || 'default'}
    variant={estado === 'PENDIENTE_TOMA' ? 'outlined' : 'filled'}
  />
);

export default MuestraEstadoBadge;
