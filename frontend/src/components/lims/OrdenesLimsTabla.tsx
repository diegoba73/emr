import React from 'react';
import {
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import type { SolicitudExamenLims } from '../../types/lims';
import { estadoOrdenColor, labelEstadoOrdenLims } from '../../utils/limsEstadosOrden';
import OrigenProcedenciaCellView from './OrigenProcedenciaCell';

export interface OrdenesLimsTablaProps {
  rows: SolicitudExamenLims[];
  emptyMessage: string;
  onVer: (id: number) => void;
  columnaFecha?: 'solicitud' | 'toma';
  accionLabel?: string;
}

const OrdenesLimsTabla: React.FC<OrdenesLimsTablaProps> = ({
  rows,
  emptyMessage,
  onVer,
  columnaFecha = 'solicitud',
  accionLabel = 'Ver',
}) => (
  <TableContainer>
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Número</TableCell>
          <TableCell>Paciente</TableCell>
          <TableCell>Médico</TableCell>
          <TableCell sx={{ minWidth: 200 }}>Origen</TableCell>
          <TableCell>Estado</TableCell>
          <TableCell>{columnaFecha === 'toma' ? 'Muestra tomada' : 'Fecha pedido'}</TableCell>
          <TableCell align="right">Acción</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.length === 0 ? (
          <TableRow>
            <TableCell colSpan={7}>
              <Typography color="text.secondary">{emptyMessage}</Typography>
            </TableCell>
          </TableRow>
        ) : (
          rows.map((r) => {
            const fechaMostrar =
              columnaFecha === 'toma'
                ? r.fecha_toma_muestra || null
                : r.fecha_solicitud || null;
            return (
              <TableRow key={r.id} hover>
                <TableCell>{r.numero || r.id}</TableCell>
                <TableCell>
                  {r.paciente_nombre || r.paciente}
                  {r.paciente_dni ? (
                    <Typography variant="caption" display="block" color="text.secondary">
                      DNI {r.paciente_dni}
                    </Typography>
                  ) : null}
                </TableCell>
                <TableCell>{r.medico_display || r.medico_interno_nombre || '—'}</TableCell>
                <TableCell>
                  <OrigenProcedenciaCellView row={r} />
                </TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={labelEstadoOrdenLims(r.estado)}
                    color={estadoOrdenColor(r.estado)}
                  />
                </TableCell>
                <TableCell>{fechaMostrar ? new Date(fechaMostrar).toLocaleString() : '—'}</TableCell>
                <TableCell align="right">
                  <Button size="small" variant="contained" onClick={() => onVer(r.id)}>
                    {accionLabel}
                  </Button>
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
