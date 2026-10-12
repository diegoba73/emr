import React from 'react';
import { Alert, Box, Button, CircularProgress, Divider, Typography } from '@mui/material';
import ConsultaPedidosPanel from './ConsultaPedidosPanel';
import { useConsultaHcForAtencion } from '../hooks/useConsultaHcForAtencion';
import PacienteLabsAccesoPanel from '../../../components/lims/PacienteLabsAccesoPanel';

interface AtencionPedidosSectionProps {
  atencionId: number;
  canEdit: boolean;
  variant?: 'compact' | 'full';
  pacienteId?: number;
  showLab?: boolean;
  showEstudios?: boolean;
}

/**
 * Pedidos lab/estudios — misma UX que consulta ambulatoria.
 */
const AtencionPedidosSection: React.FC<AtencionPedidosSectionProps> = ({
  atencionId,
  canEdit,
  variant = 'compact',
  pacienteId,
  showLab = true,
  showEstudios = true,
}) => {
  const { consultaHcId, ensuring, error, retry } = useConsultaHcForAtencion(atencionId, canEdit);

  if (!canEdit && !consultaHcId) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ py: 1 }}>
        No hay pedidos clínicos registrados en esta atención.
      </Typography>
    );
  }

  if (!consultaHcId) {
    if (error) {
      return (
        <Alert
          severity="warning"
          sx={{ mt: variant === 'compact' ? 2 : 0 }}
          action={
            <Button color="inherit" size="small" onClick={retry}>
              Reintentar
            </Button>
          }
        >
          {error}
        </Alert>
      );
    }

    return (
      <Box
        sx={{
          mt: variant === 'compact' ? 2 : 0,
          p: 2,
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
        }}
      >
        <CircularProgress size={18} />
        <Typography variant="body2" color="text.secondary">
          {ensuring ? 'Preparando pedidos clínicos…' : 'Vinculando con historia clínica…'}
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <ConsultaPedidosPanel
        consultaHcId={consultaHcId}
        pacienteId={pacienteId}
        canEdit={canEdit}
        variant={variant}
        showLab={showLab}
        showEstudios={showEstudios}
        key={`pedidos-${consultaHcId}-${variant}-${showLab}-${showEstudios}`}
      />
      {pacienteId && variant === 'full' && (
        <Box sx={{ mt: 2 }}>
          <Divider sx={{ mb: 1.5 }} />
          <PacienteLabsAccesoPanel
            pacienteId={pacienteId}
            backPath="/turnos"
            backLabel="← Volver a turnos"
          />
        </Box>
      )}
    </Box>
  );
};

export default AtencionPedidosSection;
