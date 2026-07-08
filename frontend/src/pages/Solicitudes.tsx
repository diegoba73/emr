import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useData } from '../contexts/DataContext';
import OrdenesLimsTabla from '../components/lims/OrdenesLimsTabla';
import { listSolicitudesExamen } from '../services/limsApi';
import type { SolicitudExamenLims } from '../types/lims';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../utils/apiError';
import { canAccessAnalisisClinicoLab } from '../utils/limsAccess';
import { ESTADOS_ORDEN_LIMS, labelEstadoOrdenLims } from '../utils/limsEstadosOrden';
import { isPacienteRole } from '../utils/navLabels';

const Solicitudes: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [ordenes, setOrdenes] = useState<SolicitudExamenLims[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const [busquedaDebounced, setBusquedaDebounced] = useState('');

  const allowed = canAccessAnalisisClinicoLab(currentUser);
  const esPaciente = isPacienteRole(currentUser);

  useEffect(() => {
    const timer = window.setTimeout(() => setBusquedaDebounced(busqueda), 400);
    return () => window.clearTimeout(timer);
  }, [busqueda]);

  const load = useCallback(async () => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const params: Parameters<typeof listSolicitudesExamen>[0] = {};
      if (filtroEstado) params.estado = filtroEstado;
      if (busquedaDebounced.trim()) params.search = busquedaDebounced.trim();
      const data = await listSolicitudesExamen(params);
      setOrdenes(data);
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
      setOrdenes([]);
    } finally {
      setLoading(false);
    }
  }, [allowed, filtroEstado, busquedaDebounced]);

  useEffect(() => {
    load();
  }, [load]);

  const stats = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const st of ESTADOS_ORDEN_LIMS) counts[st] = 0;
    for (const o of ordenes) {
      if (counts[o.estado] !== undefined) counts[o.estado] += 1;
    }
    return counts;
  }, [ordenes]);

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">No tiene acceso a análisis clínicos.</Alert>
      </Box>
    );
  }

  const pageTitle = esPaciente ? 'Mis análisis clínico' : 'Análisis de laboratorio';
  const pageDescription = esPaciente
    ? 'Pedidos de laboratorio realizados desde consultas y sus resultados.'
    : 'Órdenes de laboratorio generadas por médicos al cerrar consultas.';

  return (
    <Box sx={{ p: 3 }} className="fade-in">
      <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
        {pageTitle}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {pageDescription}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }}>
          <TextField
            size="small"
            label="Buscar"
            placeholder="Paciente, DNI o protocolo"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            sx={{ minWidth: 240 }}
          />
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Estado</InputLabel>
            <Select
              label="Estado"
              value={filtroEstado}
              onChange={(e) => setFiltroEstado(e.target.value)}
            >
              <MenuItem value="">Todos</MenuItem>
              {ESTADOS_ORDEN_LIMS.map((st) => (
                <MenuItem key={st} value={st}>
                  {labelEstadoOrdenLims(st)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button variant="outlined" onClick={load} disabled={loading}>
            Actualizar
          </Button>
        </Stack>
      </Paper>

      <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 2, gap: 1 }}>
        <Chip label={`Total: ${ordenes.length}`} />
        {ESTADOS_ORDEN_LIMS.map((st) => (
          <Chip
            key={st}
            size="small"
            variant="outlined"
            label={`${labelEstadoOrdenLims(st)}: ${stats[st] ?? 0}`}
          />
        ))}
      </Stack>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Paper sx={{ p: 1 }}>
          <OrdenesLimsTabla
            rows={ordenes}
            emptyMessage="No hay órdenes de laboratorio para los filtros seleccionados."
            onVer={(id) => navigate(`/solicitudes/${id}`)}
            accionLabel="Ver detalle"
          />
        </Paper>
      )}
    </Box>
  );
};

export default Solicitudes;
