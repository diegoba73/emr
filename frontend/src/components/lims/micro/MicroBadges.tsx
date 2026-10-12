import React from 'react';
import { Chip } from '@mui/material';
import type {
  EstadoAntibiograma,
  EstadoAisladoMicrobiologico,
  EstadoEstudioMicrobiologia,
  EstadoInformeMicrobiologia,
  InterpretacionAntibiotico,
} from '../../../types/lims';
import {
  estadoEstudioMicroColor,
  labelEstadoEstudioMicro,
} from '../../../utils/limsEstadosMicro';

type ChipSize = 'small' | 'medium';

export const EstudioMicrobiologiaEstadoBadge: React.FC<{
  estado: EstadoEstudioMicrobiologia | string;
  size?: ChipSize;
}> = ({ estado, size = 'small' }) => (
  <Chip
    size={size}
    label={labelEstadoEstudioMicro(estado)}
    color={estadoEstudioMicroColor(estado)}
  />
);

export const AisladoEstadoBadge: React.FC<{
  estado: EstadoAisladoMicrobiologico | string;
  size?: ChipSize;
}> = ({ estado, size = 'small' }) => (
  <Chip
    size={size}
    label={estado}
    color={estado === 'DESCARTADO' ? 'default' : estado === 'IDENTIFICADO' ? 'success' : 'warning'}
    variant="outlined"
  />
);

export const AntibiogramaEstadoBadge: React.FC<{
  estado: EstadoAntibiograma | string;
  size?: ChipSize;
}> = ({ estado, size = 'small' }) => (
  <Chip
    size={size}
    label={estado}
    color={estado === 'COMPLETO' ? 'success' : estado === 'CANCELADO' ? 'error' : 'primary'}
    variant="outlined"
  />
);

export const InformeMicrobiologiaEstadoBadge: React.FC<{
  estado: EstadoInformeMicrobiologia | string;
  tipo?: string;
  size?: ChipSize;
}> = ({ estado, tipo, size = 'small' }) => (
  <Chip
    size={size}
    label={tipo ? `${tipo} · ${estado}` : estado}
    color={
      estado === 'VALIDADO' ? 'success' : estado === 'ANULADO' ? 'default' : estado === 'EMITIDO' ? 'info' : 'warning'
    }
    variant="outlined"
  />
);

const INTERP_LABEL: Record<string, string> = {
  S: 'Sensible',
  I: 'Intermedio',
  R: 'Resistente',
  SDD: 'SDD',
  NO_APLICA: 'N/A',
};

export const InterpretacionAntibioticoBadge: React.FC<{
  interpretacion: InterpretacionAntibiotico | string;
  size?: ChipSize;
}> = ({ interpretacion, size = 'small' }) => {
  const color =
    interpretacion === 'R' ? 'error' : interpretacion === 'S' ? 'success' : interpretacion === 'I' ? 'warning' : 'default';
  return (
    <Chip
      size={size}
      label={INTERP_LABEL[interpretacion] || interpretacion}
      color={color}
      variant="outlined"
    />
  );
};
