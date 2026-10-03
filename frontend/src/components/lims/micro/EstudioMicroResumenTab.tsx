import React from 'react';
import { Box, Button, Chip, Paper, Typography } from '@mui/material';
import type { EstudioMicrobiologia } from '../../../types/lims';
import { EstudioMicrobiologiaEstadoBadge } from './MicroBadges';
import { colorEstadoObraSocial, labelEstadoObraSocial } from '../../../utils/limsObraSocial';

export interface EstudioMicroResumenTabProps {
  estudio: EstudioMicrobiologia;
  canOperateTecnico: boolean;
  canMarcarInformado: boolean;
  canEditarObraSocial?: boolean;
  /** Impresión / reimpresión ZPL (post-recepción incluido; mismo diálogo que pendientes). */
  onReimprimirEtiquetas?: () => void;
  /** Talón A4 — no muta estado ni etiquetas_impresas_at. */
  onImprimirTalon?: () => void;
  downloadingTalon?: boolean;
  onIniciar: () => void;
  onCancelar: () => void;
  onMarcarInformado: () => void;
  onObraSocial?: () => void;
}

const EstudioMicroResumenTab: React.FC<EstudioMicroResumenTabProps> = ({
  estudio,
  canOperateTecnico,
  canMarcarInformado,
  canEditarObraSocial = false,
  onReimprimirEtiquetas,
  onImprimirTalon,
  downloadingTalon,
  onIniciar,
  onCancelar,
  onMarcarInformado,
  onObraSocial,
}) => {
  const e = estudio.estado;
  const tieneEtiqueta = Boolean(estudio.etiquetas_impresas_at || estudio.codigo_barra);
  const puedeImprimirEtiqueta =
    Boolean(onReimprimirEtiquetas) && e !== 'CANCELADO';
  const puedeImprimirTalon = Boolean(onImprimirTalon) && e !== 'CANCELADO';
  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Estudio {estudio.numero || estudio.id}</Typography>
        <EstudioMicrobiologiaEstadoBadge estado={e} />
        {estudio.estado_obra_social ? (
          <Chip
            size="small"
            label={`Obra social: ${labelEstadoObraSocial(estudio.estado_obra_social)}`}
            color={colorEstadoObraSocial(estudio.estado_obra_social)}
            variant="outlined"
          />
        ) : null}
      </Box>
      <Typography>
        <strong>Paciente:</strong> {estudio.paciente_nombre || `#${estudio.paciente}`}
      </Typography>
      <Typography sx={{ mt: 1 }}>
        <strong>Médico:</strong> {estudio.medico_display || '—'}
      </Typography>
      <Typography sx={{ mt: 1 }}>
        <strong>Tipo de cultivo:</strong>{' '}
        {estudio.tipo_cultivo_nombre || estudio.tipo_estudio}
      </Typography>
      <Typography sx={{ mt: 1 }}>
        <strong>Tipo de muestra:</strong>{' '}
        {estudio.tipo_muestra_micro_nombre || estudio.muestra_tipo_nombre || '—'}
      </Typography>
      {estudio.codigo_barra ? (
        <Typography sx={{ mt: 1 }} fontFamily="monospace">
          <strong>Código:</strong> {estudio.codigo_barra}
        </Typography>
      ) : null}
      {estudio.solicitud ? (
        <Typography sx={{ mt: 1 }} variant="body2" color="text.secondary">
          Orden LIMS (legado): {estudio.solicitud_numero || `#${estudio.solicitud}`}
        </Typography>
      ) : null}
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
      {(canOperateTecnico ||
        canMarcarInformado ||
        canEditarObraSocial ||
        puedeImprimirEtiqueta ||
        puedeImprimirTalon) && (
        <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {canEditarObraSocial && onObraSocial && (
            <Button variant="outlined" onClick={onObraSocial}>
              Obra social
            </Button>
          )}
          {puedeImprimirEtiqueta && (
            <Button variant="outlined" onClick={onReimprimirEtiquetas}>
              {tieneEtiqueta ? 'Reimprimir etiquetas' : 'Imprimir etiquetas'}
            </Button>
          )}
          {puedeImprimirTalon && (
            <Button
              variant="outlined"
              disabled={Boolean(downloadingTalon)}
              onClick={onImprimirTalon}
            >
              {downloadingTalon ? 'Abriendo impresión…' : 'Imprimir talón'}
            </Button>
          )}
          {canOperateTecnico && e === 'PENDIENTE' && (
            <Button variant="contained" onClick={onIniciar}>
              Confirmar recepción
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
      {(puedeImprimirEtiqueta || puedeImprimirTalon) && (
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1.5 }}>
          Podés reimprimir la etiqueta (USB) o el talón (hoja A4) aunque la muestra ya esté
          recibida; no cambia el estado del estudio.
        </Typography>
      )}
    </Paper>
  );
};

export default EstudioMicroResumenTab;
