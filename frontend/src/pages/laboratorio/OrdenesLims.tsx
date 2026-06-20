import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  Chip,
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
  TextField,
  Typography,
  CircularProgress,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { EstadoSolicitudLims, SolicitudExamenLims } from '../../types/lims';
import { formatDrfError, listSolicitudesExamen } from '../../services/limsApi';
import { canAccessLimsModule } from '../../utils/limsAccess';

const ESTADOS: EstadoSolicitudLims[] = [
  'PENDIENTE',
  'TOMA_MUESTRA',
  'EN_PROCESO',
  'VALIDADO',
  'ENTREGADO',
  'CANCELADO',
];

const estadoColor = (e: EstadoSolicitudLims) => {
  switch (e) {
    case 'PENDIENTE':
      return 'default';
    case 'TOMA_MUESTRA':
      return 'primary';
    case 'EN_PROCESO':
      return 'primary';
    case 'VALIDADO':
      return 'success';
    case 'ENTREGADO':
      return 'success';
    case 'CANCELADO':
      return 'error';
    default:
      return 'default';
  }
};

const OrdenesLims: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [rows, setRows] = useState<SolicitudExamenLims[]>([]);
  const [loading, setLoading] = useState(true);
  const [estadoFiltro, setEstadoFiltro] = useState<string>('');
  const [numeroFiltro, setNumeroFiltro] = useState('');
  const [busqueda, setBusqueda] = useState('');

  const allowed = canAccessLimsModule(currentUser);

  const load = useCallback(async () => {
    if (!allowed) return;
    setLoading(true);
    try {
      const data = await listSolicitudesExamen({
        estado: estadoFiltro || undefined,
        numero: numeroFiltro.trim() || undefined,
      });
      setRows(data);
    } catch (e) {
      toast.error(formatDrfError(e));
    } finally {
      setLoading(false);
    }
  }, [allowed, estadoFiltro, numeroFiltro]);

  useEffect(() => {
    load();
  }, [load]);

  const filtradas = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => {
      const n = (r.numero || '').toLowerCase();
      const pn = (r.paciente_nombre || '').toLowerCase();
      const pd = (r.paciente_dni || '').toLowerCase();
      return n.includes(q) || pn.includes(q) || pd.includes(q);
    });
  }, [rows, busqueda]);

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>No tiene permisos para acceder al módulo de órdenes LIMS.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" gutterBottom>
        Órdenes LIMS
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Órdenes nativas de laboratorio (<strong>SolicitudExamen</strong>). No confundir con Solicitudes EMR (
        <code>/solicitudes</code>).
      </Typography>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
          <TextField
            size="small"
            label="Buscar (nº, paciente, DNI)"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            sx={{ minWidth: 220 }}
          />
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Estado (API)</InputLabel>
            <Select
              label="Estado (API)"
              value={estadoFiltro}
              onChange={(e) => setEstadoFiltro(e.target.value as string)}
            >
              <MenuItem value="">Todos</MenuItem>
              {ESTADOS.map((s) => (
                <MenuItem key={s} value={s}>
                  {s}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            size="small"
            label="Número exacto"
            value={numeroFiltro}
            onChange={(e) => setNumeroFiltro(e.target.value)}
            sx={{ width: 160 }}
          />
          <Button variant="outlined" onClick={load} disabled={loading}>
            Actualizar
          </Button>
        </Box>
      </Paper>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Número</TableCell>
                <TableCell>Paciente</TableCell>
                <TableCell>Médico</TableCell>
                <TableCell>Origen</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell>Fecha</TableCell>
                <TableCell align="right">Acción</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filtradas.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <Typography color="text.secondary">Sin órdenes.</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filtradas.map((r) => (
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
                    <TableCell>{r.origen_solicitud}</TableCell>
                    <TableCell>
                      <Chip size="small" label={r.estado} color={estadoColor(r.estado)} />
                    </TableCell>
                    <TableCell>
                      {r.fecha_solicitud ? new Date(r.fecha_solicitud).toLocaleString() : '—'}
                    </TableCell>
                    <TableCell align="right">
                      <Button size="small" variant="contained" onClick={() => navigate(`/laboratorio/ordenes/${r.id}`)}>
                        Ver
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default OrdenesLims;
