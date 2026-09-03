import React from 'react';
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
import type { EstadoSolicitudLims, SolicitudExamenLims } from '../../types/lims';
import { estadoOrdenColor, labelEstadoOrdenLims, ordenPuedeAgregarExamenes } from '../../utils/limsEstadosOrden';
import type { PendientePedidoRow } from '../../utils/limsPendientesUnificados';
import OrigenProcedenciaCellView from './OrigenProcedenciaCell';

export interface OrdenesLimsTablaProps {
  rows: PendientePedidoRow[];
  emptyMessage: string;
  onVer: (row: PendientePedidoRow) => void;
  /** Si se define, el botón principal invoca esto con la fila (p. ej. imprimir etiquetas). */
  onAccion?: (row: PendientePedidoRow) => void;
  /** Agregar exámenes a la orden Lab (solo LAB_CLINICO). */
  onAgregarExamenes?: (orden: SolicitudExamenLims) => void;
  columnaFecha?: 'solicitud' | 'toma';
  accionLabel?: string;
}

const OrdenesLimsTabla: React.FC<OrdenesLimsTablaProps> = ({
  rows,
  emptyMessage,
  onVer,
  onAccion,
  onAgregarExamenes,
  columnaFecha = 'solicitud',
  accionLabel = 'Ver',
}) => (
  <TableContainer>
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Tipo</TableCell>
          <TableCell>Número</TableCell>
          <TableCell>Paciente</TableCell>
          <TableCell>Médico</TableCell>
          <TableCell sx={{ minWidth: 180 }}>Origen</TableCell>
          <TableCell>Estado</TableCell>
          <TableCell>IQC</TableCell>
          <TableCell>{columnaFecha === 'toma' ? 'Muestra tomada' : 'Fecha pedido'}</TableCell>
          <TableCell align="right">Acción</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.length === 0 ? (
          <TableRow>
            <TableCell colSpan={9}>
              <Typography color="text.secondary">{emptyMessage}</Typography>
            </TableCell>
          </TableRow>
        ) : (
          rows.map((r) => {
            const fechaMostrar =
              columnaFecha === 'toma'
                ? r.fecha_toma_muestra || null
                : r.fecha_solicitud || null;
            const puedeAgregar =
              r.tipo === 'LAB_CLINICO' &&
              Boolean(onAgregarExamenes) &&
              Boolean(r.labOrden) &&
              ordenPuedeAgregarExamenes(r.labOrden!);
            return (
              <TableRow key={r.key} hover>
                <TableCell>
                  <Chip
                    size="small"
                    label={r.tipo === 'MICROBIOLOGIA' ? 'Microbiología' : 'Lab. Clínico'}
                    color={r.tipo === 'MICROBIOLOGIA' ? 'secondary' : 'primary'}
                    variant="outlined"
                  />
                  {r.tipo === 'MICROBIOLOGIA' && r.cultivo_nombre ? (
                    <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>
                      {r.cultivo_nombre}
                      {r.muestra_nombre ? ` · ${r.muestra_nombre}` : ''}
                    </Typography>
                  ) : null}
                </TableCell>
                <TableCell>{r.numero || r.id}</TableCell>
                <TableCell>
                  {r.paciente_nombre}
                  {r.paciente_dni ? (
                    <Typography variant="caption" display="block" color="text.secondary">
                      DNI {r.paciente_dni}
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
                  <Chip
                    size="small"
                    label={labelEstadoOrdenLims(r.estado)}
                    color={estadoOrdenColor(r.estado as EstadoSolicitudLims)}
                  />
                  {r.esperando_recepcion && (
                    <Chip
                      size="small"
                      label="Esperando recepción"
                      color="info"
                      variant="outlined"
                      sx={{ ml: 0.5, mt: 0.5 }}
                    />
                  )}
                  {r.pedido_adicional && (
                    <Chip
                      size="small"
                      label="Pedido adicional"
                      color="secondary"
                      variant="outlined"
                      sx={{ ml: 0.5, mt: 0.5 }}
                    />
                  )}
                  {r.tubos_pendientes_extraccion && r.tubos_pendientes_extraccion.length > 0 && (
                    <Typography variant="caption" display="block" color="warning.main">
                      Faltan {r.tubos_pendientes_extraccion.length} tubo(s)
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  {r.tipo !== 'LAB_CLINICO' || !r.iqcStatus || r.iqcStatus === 'na' ? (
                    <Typography variant="caption" color="text.secondary">
                      —
                    </Typography>
                  ) : r.iqcStatus === 'ok' ? (
                    <Chip size="small" label="IQC OK" color="success" variant="outlined" />
                  ) : (
                    <Chip size="small" label="Falta IQC" color="warning" variant="outlined" />
                  )}
                </TableCell>
                <TableCell>{fechaMostrar ? new Date(fechaMostrar).toLocaleString() : '—'}</TableCell>
                <TableCell align="right">
                  <Stack direction="row" spacing={0.5} justifyContent="flex-end" flexWrap="wrap" useFlexGap>
                    {puedeAgregar && r.labOrden && (
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => onAgregarExamenes?.(r.labOrden!)}
                      >
                        Agregar exámenes
                      </Button>
                    )}
                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => (onAccion ? onAccion(r) : onVer(r))}
                    >
                      {accionLabel}
                    </Button>
                    {onAccion && (
                      <Button size="small" variant="text" onClick={() => onVer(r)}>
                        Ver
                      </Button>
                    )}
                  </Stack>
                </TableCell>
              </TableRow>
            );
          })
        )}
      </TableBody>
    </Table>
  </TableContainer>
);

export default OrdenesLimsTabla;
