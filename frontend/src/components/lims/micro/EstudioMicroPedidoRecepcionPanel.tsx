import React from 'react';
import {
  Box,
  Button,
  Chip,
  Divider,
  Paper,
  Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import type { EstudioMicrobiologia } from '../../../types/lims';
import { EstudioMicrobiologiaEstadoBadge } from './MicroBadges';
import { labelOrigenSolicitudLims } from '../../../utils/limsOrigenSolicitud';
import { colorEstadoObraSocial, labelEstadoObraSocial } from '../../../utils/limsObraSocial';

export interface EstudioMicroPedidoRecepcionPanelProps {
  estudio: EstudioMicrobiologia;
  canOperate: boolean;
  reprinting?: boolean;
  confirmingRecepcion?: boolean;
  onReimprimirEtiquetas: () => void;
  onConfirmarRecepcion: () => void;
  onCancelar: () => void;
  onObraSocial?: () => void;
}

/**
 * Vista de pedido micro en PENDIENTE (pre-recepción), alineada a Orden LIMS pendiente:
 * datos del pedido, reimpresión de etiquetas y confirmación de recepción.
 * No expone siembras / iniciar estudio técnico.
 */
const EstudioMicroPedidoRecepcionPanel: React.FC<EstudioMicroPedidoRecepcionPanelProps> = ({
  estudio,
  canOperate,
  reprinting,
  confirmingRecepcion,
  onReimprimirEtiquetas,
  onConfirmarRecepcion,
  onCancelar,
  onObraSocial,
}) => {
  const tieneEtiqueta = Boolean(estudio.etiquetas_impresas_at || estudio.codigo_barra);

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', mb: 2 }}>
          <Typography variant="h5">Pedido {estudio.numero || estudio.id}</Typography>
          <EstudioMicrobiologiaEstadoBadge estado={estudio.estado} />
          {estudio.estado_obra_social ? (
            <Chip
              size="small"
              label={`Obra social: ${labelEstadoObraSocial(estudio.estado_obra_social)}`}
              color={colorEstadoObraSocial(estudio.estado_obra_social)}
              variant="outlined"
            />
          ) : null}
          <Chip size="small" label="Microbiología" color="secondary" variant="outlined" />
          {tieneEtiqueta ? (
            <Chip size="small" label="Esperando recepción" color="info" variant="outlined" />
          ) : (
            <Chip size="small" label="Sin etiquetas" color="warning" variant="outlined" />
          )}
        </Box>

        <Typography variant="subtitle2" gutterBottom>
          Acciones del pedido
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
          {canOperate && onObraSocial && (
            <Button variant="outlined" onClick={onObraSocial}>
              Obra social
            </Button>
          )}
          {canOperate && (
            <Button
              variant="outlined"
              disabled={reprinting || confirmingRecepcion}
              onClick={onReimprimirEtiquetas}
            >
              {reprinting
                ? 'Generando…'
                : tieneEtiqueta
                  ? 'Reimprimir etiquetas'
                  : 'Imprimir etiquetas'}
            </Button>
          )}
          {canOperate && tieneEtiqueta && (
            <Button
              variant="contained"
              disabled={confirmingRecepcion || reprinting}
              onClick={onConfirmarRecepcion}
            >
              {confirmingRecepcion ? 'Confirmando…' : 'Confirmar recepción de muestra'}
            </Button>
          )}
          {canOperate && (
            <Button color="error" variant="outlined" disabled={confirmingRecepcion} onClick={onCancelar}>
              Cancelar pedido
            </Button>
          )}
          <Button
            component={RouterLink}
            to="/laboratorio/muestras/recepcion"
            variant="text"
            size="small"
          >
            Ir a recepción (escaneo)
          </Button>
        </Box>
        <Typography variant="caption" color="text.secondary" display="block">
          {tieneEtiqueta ? (
            <>
              Etiquetas impresas
              {estudio.codigo_barra ? (
                <>
                  {' '}
                  (<strong>{estudio.codigo_barra}</strong>)
                </>
              ) : null}
              . El pedido queda en <strong>Esperando recepción</strong> hasta que la muestra llegue
              al laboratorio. Escaneá el código en{' '}
              <strong>Recepción de muestras</strong> o usá{' '}
              <strong>Confirmar recepción de muestra</strong> cuando la tengas físicamente. Después
              podrás sembrar e iniciar el trabajo técnico.
            </>
          ) : (
            <>
              Pendiente de etiquetas. Imprimí la etiqueta del cultivo antes de enviar la muestra.
            </>
          )}
        </Typography>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Datos del pedido
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
              {estudio.paciente_nombre || `ID ${estudio.paciente}`}
            </Typography>
            {estudio.paciente_dni && (
              <Typography variant="body2" color="text.secondary">
                DNI {estudio.paciente_dni}
              </Typography>
            )}
          </Box>
          <Box>
            <Typography variant="overline" color="text.secondary" display="block">
              Médico solicitante
            </Typography>
            <Typography fontWeight={600}>{estudio.medico_display || '—'}</Typography>
          </Box>
          <Box>
            <Typography variant="overline" color="text.secondary" display="block">
              Tipo de cultivo
            </Typography>
            <Typography fontWeight={600}>
              {estudio.tipo_cultivo_nombre || estudio.tipo_estudio}
            </Typography>
          </Box>
          <Box>
            <Typography variant="overline" color="text.secondary" display="block">
              Tipo de muestra
            </Typography>
            <Typography fontWeight={600}>
              {estudio.tipo_muestra_micro_nombre || estudio.muestra_tipo_nombre || '—'}
            </Typography>
          </Box>
          <Box>
            <Typography variant="overline" color="text.secondary" display="block">
              Origen
            </Typography>
            <Typography fontWeight={600}>
              {labelOrigenSolicitudLims(
                estudio.origen_solicitud,
                estudio.origen_solicitud_display
              )}
            </Typography>
          </Box>
          <Box>
            <Typography variant="overline" color="text.secondary" display="block">
              Código de barras
            </Typography>
            <Typography fontWeight={600} fontFamily="monospace">
              {estudio.codigo_barra || '—'}
            </Typography>
            {estudio.etiquetas_impresas_at && (
              <Typography variant="caption" color="text.secondary" display="block">
                Etiqueta: {new Date(estudio.etiquetas_impresas_at).toLocaleString()}
              </Typography>
            )}
          </Box>
        </Box>
        {estudio.observaciones ? (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="overline" color="text.secondary" display="block">
              Observaciones
            </Typography>
            <Typography variant="body2">{estudio.observaciones}</Typography>
          </>
        ) : null}
      </Paper>
    </Box>
  );
};

export default EstudioMicroPedidoRecepcionPanel;
