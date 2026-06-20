import React from 'react';
import { Box, Button, Paper, Typography } from '@mui/material';
import type { EstudioMicrobiologia } from '../../../types/lims';
import { EstudioMicrobiologiaEstadoBadge } from './MicroBadges';

export interface EstudioMicroResumenTabProps {
  estudio: EstudioMicrobiologia;
  canOperateTecnico: boolean;
  canMarcarInformado: boolean;
  onIniciar: () => void;
  onCancelar: () => void;
  onMarcarInformado: () => void;
}

const EstudioMicroResumenTab: React.FC<EstudioMicroResumenTabProps> = ({
  estudio,
  canOperateTecnico,
  canMarcarInformado,
  onIniciar,
  onCancelar,
  onMarcarInformado,
}) => {
  const e = estudio.estado;
  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Estudio {estudio.numero || estudio.id}</Typography>
        <EstudioMicrobiologiaEstadoBadge estado={e} />
      </Box>
      <Typography>
        <strong>Solicitud:</strong> #{estudio.solicitud}
      </Typography>
      <Typography sx={{ mt: 1 }}>
        <strong>Muestra:</strong> #{estudio.muestra}
      </Typography>
      <Typography sx={{ mt: 1 }}>
        <strong>Paciente:</strong> #{estudio.paciente}
      </Typography>
      <Typography sx={{ mt: 1 }}>
        <strong>Tipo:</strong> {estudio.tipo_estudio}
      </Typography>
      <Typography sx={{ mt: 1 }}>
        <strong>Inicio:</strong> {estudio.fecha_inicio ? new Date(estudio.fecha_inicio).toLocaleString() : '—'}
      </Typography>
      {estudio.motivo_cancelacion ? (
        <Typography sx={{ mt: 1 }} color="error">
          <strong>Cancelación:</strong> {estudio.motivo_cancelacion}
        </Typography>
      ) : null}
      <Typography sx={{ mt: 2 }} variant="body2" color="text.secondary">
        {estudio.observaciones || 'Sin observaciones.'}
      </Typography>
      {(canOperateTecnico || canMarcarInformado) && (
        <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {canOperateTecnico && e === 'PENDIENTE' && (
            <Button variant="contained" onClick={onIniciar}>
              Iniciar estudio
            </Button>
          )}
          {canOperateTecnico && e !== 'CANCELADO' && e !== 'INFORMADO' && e !== 'VALIDADO' && (
            <Button color="error" variant="outlined" onClick={onCancelar}>
              Cancelar estudio
            </Button>
          )}
          {canMarcarInformado && (
            <Button variant="contained" color="success" onClick={onMarcarInformado}>
              Marcar informado
            </Button>
          )}
        </Box>
      )}
    </Paper>
  );
};

export default EstudioMicroResumenTab;
