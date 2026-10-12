import React, { useState } from 'react';
import {
  Button,
  Chip,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import type { EstadoSolicitudLims } from '../../types/lims';
import { estadoOrdenColor, labelEstadoOrdenLims } from '../../utils/limsEstadosOrden';
import {
  estadoEstudioMicroColor,
  labelEstadoEstudioMicro,
} from '../../utils/limsEstadosMicro';
import { limsActionBtnSoftSx, limsActionBtnSx } from '../../utils/limsActionButtonSx';
import type { PendientePedidoRow } from '../../utils/limsPendientesUnificados';
import OrigenProcedenciaCellView from './OrigenProcedenciaCell';
import EstadoObraSocialDialog from './EstadoObraSocialDialog';
import { colorEstadoObraSocial, labelEstadoObraSocial } from '../../utils/limsObraSocial';
import { patchEstadoObraSocialSolicitud } from '../../services/limsApi';
import { patchEstadoObraSocialEstudio } from '../../services/limsMicroApi';

export interface OrdenesLimsTablaProps {
  rows: PendientePedidoRow[];
  emptyMessage: string;
  onVer: (row: PendientePedidoRow) => void;
  /** Si se define, el botón principal invoca esto con la fila (p. ej. imprimir etiquetas). */
  onAccion?: (row: PendientePedidoRow) => void;
  accionLabel?: string;
  /** Botón «Obra social» junto a imprimir / ver. */
  puedeObraSocial?: boolean;
  /** Tras guardar el estado de cobertura (para refrescar el listado). */
  onObraSocialSaved?: () => void;
  /** Oculta columnas técnicas (IQC, tubos, recepción) para secretaría. */
  modoEntrega?: boolean;
  /**
   * Prefijo visual 1, 2, 3… según el orden del listado del día
   * (antes del número de pedido; no agrega columna).
   */
  mostrarIndiceDia?: boolean;
}

const OrdenesLimsTabla: React.FC<OrdenesLimsTablaProps> = ({
  rows,
  emptyMessage,
  onVer,
  onAccion,
  accionLabel = 'Ver',
  puedeObraSocial = false,
  onObraSocialSaved,
  modoEntrega = false,
  mostrarIndiceDia = false,
}) => {
  const [obraSocialRow, setObraSocialRow] = useState<PendientePedidoRow | null>(null);

  const handleGuardarObraSocial = async (estado: string) => {
    if (!obraSocialRow) return;
    if (obraSocialRow.tipo === 'MICROBIOLOGIA') {
      await patchEstadoObraSocialEstudio(obraSocialRow.id, estado);
    } else {
      await patchEstadoObraSocialSolicitud(obraSocialRow.id, estado);
    }
    onObraSocialSaved?.();
  };

  return (
  <>
  <TableContainer>
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Número</TableCell>
          <TableCell>Paciente</TableCell>
          <TableCell>Médico</TableCell>
          <TableCell sx={{ minWidth: 180 }}>Origen</TableCell>
          <TableCell>Estado</TableCell>
          <TableCell align="right">Acción</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.length === 0 ? (
          <TableRow>
            <TableCell colSpan={6}>
              <Typography color="text.secondary">{emptyMessage}</Typography>
            </TableCell>
          </TableRow>
        ) : (
          rows.map((r, idx) => (
              <TableRow key={r.key} hover>
                <TableCell>
                  <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap" useFlexGap>
                    {mostrarIndiceDia ? (
                      <Typography
                        component="span"
                        variant="body2"
                        color="text.secondary"
                        sx={{ fontVariantNumeric: 'tabular-nums', minWidth: '1.5ch' }}
                      >
                        {idx + 1}
                      </Typography>
                    ) : null}
                    <Typography component="span" variant="body2" fontWeight={600}>
                      {r.numero || r.id}
                    </Typography>
                    <Chip
                      size="small"
                      label={r.tipo === 'MICROBIOLOGIA' ? 'Microbiología' : 'Lab. Clínico'}
                      color={r.tipo === 'MICROBIOLOGIA' ? 'secondary' : 'primary'}
                      variant="outlined"
                    />
                  </Stack>
                  {r.tipo === 'MICROBIOLOGIA' && r.cultivo_nombre ? (
                    <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>
                      {r.cultivo_nombre}
                      {r.muestra_nombre ? ` · ${r.muestra_nombre}` : ''}
                    </Typography>
                  ) : null}
                  {r.tipo === 'LAB_CLINICO' && (r.tipos_muestra_display || r.muestra_nombre) ? (
                    <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>
                      {r.tipos_muestra_display || r.muestra_nombre}
                    </Typography>
                  ) : null}
                </TableCell>
                <TableCell>
                  {r.paciente_nombre}
                  {r.paciente_dni ? (
                    <Typography variant="caption" display="block" color="text.secondary">
                      DNI {r.paciente_dni}
                    </Typography>
                  ) : null}
                  {r.fecha_toma_muestra ? (
                    <Typography variant="caption" display="block" color="primary.main" sx={{ mt: 0.25 }}>
                      Extracción{' '}
                      {new Date(r.fecha_toma_muestra).toLocaleString('es-AR', {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </Typography>
                  ) : null}
                </TableCell>
                <TableCell>{r.medico_display || '—'}</TableCell>
                <TableCell>
                  <OrigenProcedenciaCellView
                    row={{
                      origen_solicitud: r.origen_solicitud,
                      origen_solicitud_display: r.origen_solicitud_display,
                      procedencia_display: r.procedencia_display,
                    }}
                  />
                </TableCell>
                <TableCell>
                  <Stack spacing={0.5} alignItems="flex-start">
                    <Chip
                      size="small"
                      label={
                        r.tipo === 'MICROBIOLOGIA'
                          ? labelEstadoEstudioMicro(r.estado)
                          : labelEstadoOrdenLims(r.estado)
                      }
                      color={
                        r.tipo === 'MICROBIOLOGIA'
                          ? estadoEstudioMicroColor(r.estado)
                          : estadoOrdenColor(r.estado as EstadoSolicitudLims)
                      }
                    />
                    {r.estado_obra_social ? (
                      <Chip
                        size="small"
                        label={labelEstadoObraSocial(r.estado_obra_social)}
                        color={colorEstadoObraSocial(r.estado_obra_social)}
                        variant="outlined"
                      />
                    ) : null}
                    {r.esperando_recepcion && !modoEntrega && (
                      <Chip
                        size="small"
                        label="Esperando recepción"
                        color="info"
                        variant="outlined"
                      />
                    )}
                    {r.pedido_adicional && !modoEntrega && (
                      <Chip
                        size="small"
                        label="Pedido adicional"
                        color="secondary"
                        variant="outlined"
                      />
                    )}
                    {!modoEntrega &&
                      r.tubos_pendientes_extraccion &&
                      r.tubos_pendientes_extraccion.length > 0 && (
                        <Typography variant="caption" color="warning.main">
                          Faltan {r.tubos_pendientes_extraccion.length} tubo(s)
                        </Typography>
                      )}
                    {/* IQC: sin columna; solo aviso cuando hay que actuar o no hay config. */}
                    {!modoEntrega &&
                      r.tipo === 'LAB_CLINICO' &&
                      r.iqcStatus === 'falta' && (
                        <Chip
                          size="small"
                          label="Falta IQC"
                          color="warning"
                          variant="outlined"
                        />
                      )}
                    {!modoEntrega &&
                      r.tipo === 'LAB_CLINICO' &&
                      r.iqcStatus === 'sin_config' && (
                        <Chip
                          size="small"
                          label="Sin IQC"
                          color="default"
                          variant="outlined"
                        />
                      )}
                  </Stack>
                </TableCell>
                <TableCell align="right" sx={{ verticalAlign: 'middle' }}>
                  <Stack direction="column" spacing={0.75} alignItems="stretch" sx={{ minWidth: 132 }}>
                    <Button
                      size="small"
                      variant="contained"
                      color="primary"
                      disableElevation
                      sx={limsActionBtnSx}
                      onClick={() => (onAccion ? onAccion(r) : onVer(r))}
                    >
                      {accionLabel}
                    </Button>
                    {onAccion && (
                      <Button
                        size="small"
                        variant="outlined"
                        color="primary"
                        sx={limsActionBtnSoftSx}
                        onClick={() => onVer(r)}
                      >
                        Ver
                      </Button>
                    )}
                    {puedeObraSocial && (
                      <Button
                        size="small"
                        variant="outlined"
                        color="primary"
                        sx={limsActionBtnSx}
                        onClick={() => setObraSocialRow(r)}
                      >
                        Obra social
                      </Button>
                    )}
                  </Stack>
                </TableCell>
              </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  </TableContainer>
  <EstadoObraSocialDialog
    open={!!obraSocialRow}
    numero={obraSocialRow?.numero}
    value={obraSocialRow?.estado_obra_social}
    onClose={() => setObraSocialRow(null)}
    onSave={handleGuardarObraSocial}
  />
  </>
  );
};

export default OrdenesLimsTabla;
