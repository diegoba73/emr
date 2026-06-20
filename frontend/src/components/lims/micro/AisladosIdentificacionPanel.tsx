import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import type { AisladoMicrobiologico, IdentificacionMicroorganismo, LecturaCultivo, Microorganismo } from '../../../types/lims';
import {
  createAisladoMicrobiologico,
  createIdentificacionMicroorganismo,
  descartarAisladoMicrobiologico,
  formatDrfError,
} from '../../../services/limsApi';
import { AisladoEstadoBadge } from './MicroBadges';
import { MotivoDialog, useMotivoDialog } from './MotivoDialog';

export interface AisladosIdentificacionPanelProps {
  estudioId: number;
  lecturas: LecturaCultivo[];
  aislados: AisladoMicrobiologico[];
  identificaciones: IdentificacionMicroorganismo[];
  microorganismos: Microorganismo[];
  canOperate: boolean;
  onRefresh: () => void;
}

const AisladosIdentificacionPanel: React.FC<AisladosIdentificacionPanelProps> = ({
  estudioId,
  lecturas,
  aislados,
  identificaciones,
  microorganismos,
  canOperate,
  onRefresh,
}) => {
  const [lecturaId, setLecturaId] = useState<number | ''>('');
  const [microId, setMicroId] = useState<number | ''>('');
  const [aisladoIdIdent, setAisladoIdIdent] = useState<number | ''>('');
  const [microIdIdent, setMicroIdIdent] = useState<number | ''>('');
  const { openMotivoDialog, dialogProps } = useMotivoDialog();

  const crearAislado = async () => {
    if (lecturaId === '') {
      toast.error('Seleccione lectura de origen');
      return;
    }
    try {
      await createAisladoMicrobiologico({
        estudio_id: estudioId,
        lectura_id: Number(lecturaId),
        microorganismo_id: microId === '' ? null : Number(microId),
        requiere_antibiograma: true,
      });
      toast.success('Aislado creado');
      onRefresh();
    } catch (e) {
      toast.error(formatDrfError(e));
    }
  };

  const identificar = async () => {
    if (aisladoIdIdent === '' || microIdIdent === '') {
      toast.error('Aislado y microorganismo requeridos');
      return;
    }
    const a = aislados.find((x) => x.id === Number(aisladoIdIdent));
    if (a?.estado === 'DESCARTADO') {
      toast.error('No se puede identificar un aislado descartado');
      return;
    }
    try {
      await createIdentificacionMicroorganismo({
        aislado_id: Number(aisladoIdIdent),
        microorganismo_id: Number(microIdIdent),
      });
      toast.success('Identificación registrada');
      onRefresh();
    } catch (e) {
      toast.error(formatDrfError(e));
    }
  };

  const descartar = (id: number) => {
    openMotivoDialog({
      title: 'Descartar aislado',
      label: 'Motivo de descarte (obligatorio)',
      confirmLabel: 'Descartar',
      onConfirm: async (motivo) => {
        try {
          await descartarAisladoMicrobiologico(id, motivo);
          toast.success('Aislado descartado');
          onRefresh();
        } catch (e) {
          const msg = formatDrfError(e);
          toast.error(msg);
          throw new Error(msg);
        }
      },
    });
  };

  return (
    <Box>
      <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Lectura</TableCell>
              <TableCell>Estado</TableCell>
              <TableCell>Significancia</TableCell>
              <TableCell>AB</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {aislados.map((a) => (
              <TableRow key={a.id}>
                <TableCell>{a.id}</TableCell>
                <TableCell>{a.lectura_origen}</TableCell>
                <TableCell>
                  <AisladoEstadoBadge estado={a.estado} />
                </TableCell>
                <TableCell>{a.significancia}</TableCell>
                <TableCell>{a.requiere_antibiograma ? 'Sí' : 'No'}</TableCell>
                <TableCell>
                  {canOperate && a.estado !== 'DESCARTADO' && (
                    <Button size="small" color="error" onClick={() => descartar(a.id)}>
                      Descartar
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        Identificaciones
      </Typography>
      <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Aislado</TableCell>
              <TableCell>Microorganismo</TableCell>
              <TableCell>Método</TableCell>
              <TableCell>Fecha</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {identificaciones.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4}>
                  <Typography color="text.secondary">Sin identificaciones.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              identificaciones.map((i) => (
                <TableRow key={i.id}>
                  <TableCell>{i.aislado}</TableCell>
                  <TableCell>
                    {microorganismos.find((m) => m.id === i.microorganismo)?.nombre || i.microorganismo}
                  </TableCell>
                  <TableCell>{i.metodo || '—'}</TableCell>
                  <TableCell>{i.fecha ? new Date(i.fecha).toLocaleString() : '—'}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {canOperate && (
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Nuevo aislado
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel>Lectura</InputLabel>
              <Select label="Lectura" value={lecturaId === '' ? '' : String(lecturaId)} onChange={(e) => setLecturaId(e.target.value === '' ? '' : Number(e.target.value))}>
                <MenuItem value="">—</MenuItem>
                {lecturas.map((l) => (
                  <MenuItem key={l.id} value={l.id}>
                    #{l.id}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel>Micro (opc.)</InputLabel>
              <Select label="Micro (opc.)" value={microId === '' ? '' : String(microId)} onChange={(e) => setMicroId(e.target.value === '' ? '' : Number(e.target.value))}>
                <MenuItem value="">—</MenuItem>
                {microorganismos.filter((m) => m.activo !== false).map((m) => (
                  <MenuItem key={m.id} value={m.id}>
                    {m.codigo}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button variant="contained" onClick={crearAislado}>
              Crear aislado
            </Button>
          </Box>
        </Paper>
      )}

      {canOperate && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Nueva identificación
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel>Aislado</InputLabel>
              <Select
                label="Aislado"
                value={aisladoIdIdent === '' ? '' : String(aisladoIdIdent)}
                onChange={(e) => setAisladoIdIdent(e.target.value === '' ? '' : Number(e.target.value))}
              >
                <MenuItem value="">—</MenuItem>
                {aislados.filter((a) => a.estado !== 'DESCARTADO').map((a) => (
                  <MenuItem key={a.id} value={a.id}>
                    #{a.id} ({a.estado})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>Microorganismo</InputLabel>
              <Select
                label="Microorganismo"
                value={microIdIdent === '' ? '' : String(microIdIdent)}
                onChange={(e) => setMicroIdIdent(e.target.value === '' ? '' : Number(e.target.value))}
              >
                <MenuItem value="">—</MenuItem>
                {microorganismos.filter((m) => m.activo !== false).map((m) => (
                  <MenuItem key={m.id} value={m.id}>
                    {m.codigo} — {m.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button variant="contained" onClick={identificar}>
              Identificar
            </Button>
          </Box>
        </Paper>
      )}
      <MotivoDialog {...dialogProps} />
    </Box>
  );
};

export default AisladosIdentificacionPanel;
