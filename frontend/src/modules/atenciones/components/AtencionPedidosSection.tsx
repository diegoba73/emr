import React from 'react';
import { Alert, Box, Button, CircularProgress, Typography } from '@mui/material';
import ConsultaPedidosPanel from './ConsultaPedidosPanel';
import { useConsultaHcForAtencion } from '../hooks/useConsultaHcForAtencion';

interface AtencionPedidosSectionProps {
  atencionId: number;
  canEdit: boolean;
  variant?: 'compact' | 'full';
}

/**
 * Pedidos lab/estudios — misma UX que consulta ambulatoria.
 */
const AtencionPedidosSection: React.FC<AtencionPedidosSectionProps> = ({
  atencionId,
  canEdit,
  variant = 'compact',
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
    <ConsultaPedidosPanel
      consultaHcId={consultaHcId}
      canEdit={canEdit}
      variant={variant}
      key={`pedidos-${consultaHcId}-${variant}`}
    />
  );
};

export default AtencionPedidosSection;
