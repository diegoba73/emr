import React from 'react';
import { Box, Chip, Divider, Paper, Typography } from '@mui/material';
import type { SolicitudExamenLims } from '../../types/lims';
import { labelEstadoOrdenLims } from '../../utils/limsEstadosOrden';
import { formatOrigenProcedenciaCell } from '../../utils/limsOrigenSolicitud';

export interface OrdenLimsResumenPanelProps {
  orden: SolicitudExamenLims;
}

const OrdenLimsResumenPanel: React.FC<OrdenLimsResumenPanelProps> = ({ orden }) => {
  const paneles = orden.paneles_nombres ?? [];
  const examenesSueltos = orden.tipos_examen_nombres ?? [];

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Datos de la orden
      </Typography>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
          gap: 2,
        }}
      >
        <Box>
          <Typography variant="overline" color="text.secondary" display="block">
            Paciente
          </Typography>
          <Typography fontWeight={600}>
            {orden.paciente_nombre || `ID ${orden.paciente}`}
          </Typography>
          {orden.paciente_dni && (
            <Typography variant="body2" color="text.secondary">
              DNI {orden.paciente_dni}
            </Typography>
          )}
          {(orden.paciente_email || orden.paciente_telefono) && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {[orden.paciente_email, orden.paciente_telefono].filter(Boolean).join(' · ')}
            </Typography>
          )}
        </Box>

        <Box>
          <Typography variant="overline" color="text.secondary" display="block">
            Médico solicitante
          </Typography>
          <Typography fontWeight={600}>
            {orden.medico_display || orden.medico_interno_nombre || orden.medico_externo_nombre || '—'}
          </Typography>
        </Box>

        <Box>
          <Typography variant="overline" color="text.secondary" display="block">
            Origen clínico
          </Typography>
          {(() => {
            const { titulo, detalle } = formatOrigenProcedenciaCell(orden);
            return (
              <>
                <Typography fontWeight={600}>{titulo}</Typography>
                {detalle ? (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {detalle}
                  </Typography>
                ) : null}
              </>
            );
          })()}
          {orden.procedencia_tipo === 'RECURSO' && orden.procedencia_display && (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
              Consultorio o recurso donde se generó la solicitud.
            </Typography>
          )}
          {orden.procedencia_tipo === 'INTERNACION' && orden.procedencia_display && (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
              Sector y cama al momento del pedido.
            </Typography>
          )}
        </Box>

        <Box>
          <Typography variant="overline" color="text.secondary" display="block">
            Estado
          </Typography>
          <Chip size="small" label={labelEstadoOrdenLims(orden.estado)} />
          {orden.fecha_solicitud && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Solicitud: {new Date(orden.fecha_solicitud).toLocaleString('es-AR')}
            </Typography>
          )}
        </Box>
      </Box>

      <Divider sx={{ my: 2 }} />

      <Typography variant="subtitle2" gutterBottom>
        Estudios solicitados
      </Typography>
      {paneles.length > 0 && (
        <Box sx={{ mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Paneles
          </Typography>
          <Typography variant="body2">{paneles.join(' · ')}</Typography>
        </Box>
      )}
      {examenesSueltos.length > 0 && (
        <Box sx={{ mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Exámenes sueltos
          </Typography>
          <Typography variant="body2">{examenesSueltos.join(' · ')}</Typography>
        </Box>
      )}
      {paneles.length === 0 && examenesSueltos.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          Sin estudios registrados en la orden.
        </Typography>
      )}

      {orden.observaciones && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" gutterBottom>
            Observaciones
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {orden.observaciones}
          </Typography>
        </>
      )}
    </Paper>
  );
};

export default OrdenLimsResumenPanel;
