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
import { listEstudiosMicrobiologia } from '../services/limsMicroApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../utils/apiError';
import {
  canAccessAnalisisClinicoLab,
  canAccessMicrobiologiaLectura,
} from '../utils/limsAccess';
import { ESTADOS_ORDEN_LIMS, labelEstadoOrdenLims } from '../utils/limsEstadosOrden';
import {
  mapLabToPendiente,
  mapMicroToPendiente,
  type PendientePedidoRow,
} from '../utils/limsPendientesUnificados';
import { isPacienteRole } from '../utils/navLabels';

const Solicitudes: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [rows, setRows] = useState<PendientePedidoRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [filtroTipo, setFiltroTipo] = useState<'TODOS' | 'LAB_CLINICO' | 'MICROBIOLOGIA'>('TODOS');
  const [busqueda, setBusqueda] = useState('');
  const [busquedaDebounced, setBusquedaDebounced] = useState('');

  const allowed = canAccessAnalisisClinicoLab(currentUser);
  const puedeVerMicro = canAccessMicrobiologiaLectura(currentUser);
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
      const labParams: Parameters<typeof listSolicitudesExamen>[0] = {};
      if (filtroEstado) labParams.estado = filtroEstado;
      if (busquedaDebounced.trim()) labParams.search = busquedaDebounced.trim();

      const microParams: Parameters<typeof listEstudiosMicrobiologia>[0] = {};
      if (filtroEstado) microParams.estado = filtroEstado;
      if (busquedaDebounced.trim()) microParams.search = busquedaDebounced.trim();

      const labsPromise =
        filtroTipo === 'MICROBIOLOGIA'
          ? Promise.resolve([])
          : listSolicitudesExamen(labParams);

      let micros: Awaited<ReturnType<typeof listEstudiosMicrobiologia>> = [];
      if (puedeVerMicro && filtroTipo !== 'LAB_CLINICO') {
        try {
          micros = await listEstudiosMicrobiologia(microParams);
        } catch (microErr) {
          // No silenciar: si falla micro, el médico veía Lab. Clínico y “Microbiología: 0”.
          setError(
            getSafeClinicalActionMessage(
              microErr,
              'No se pudieron cargar los pedidos de microbiología.'
            )
          );
          micros = [];
        }
      }

      const labs = await labsPromise;
      const merged = [
        ...labs.map(mapLabToPendiente),
        ...micros.map(mapMicroToPendiente),
      ].sort((a, b) => {
        const ta = a.fecha_solicitud ? new Date(a.fecha_solicitud).getTime() : 0;
        const tb = b.fecha_solicitud ? new Date(b.fecha_solicitud).getTime() : 0;
        return tb - ta;
      });
      setRows(merged);
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [allowed, puedeVerMicro, filtroEstado, filtroTipo, busquedaDebounced]);

  useEffect(() => {
    load();
  }, [load]);

  const stats = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const st of ESTADOS_ORDEN_LIMS) counts[st] = 0;
    let lab = 0;
    let micro = 0;
    for (const r of rows) {
      if (r.tipo === 'MICROBIOLOGIA') micro += 1;
      else lab += 1;
      if (counts[r.estado] !== undefined) counts[r.estado] += 1;
    }
    return { counts, lab, micro };
  }, [rows]);

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
    : 'Órdenes de Lab. Clínico y Microbiología generadas al cerrar consultas.';

  const handleVer = (row: PendientePedidoRow) => {
    if (row.tipo === 'MICROBIOLOGIA') {
      navigate(`/laboratorio/microbiologia/estudios/${row.id}`);
      return;
    }
    navigate(`/solicitudes/${row.id}`);
  };

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
          {puedeVerMicro && (
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel>Tipo</InputLabel>
              <Select
                label="Tipo"
                value={filtroTipo}
                onChange={(e) =>
                  setFiltroTipo(e.target.value as 'TODOS' | 'LAB_CLINICO' | 'MICROBIOLOGIA')
                }
              >
                <MenuItem value="TODOS">Todos</MenuItem>
                <MenuItem value="LAB_CLINICO">Lab. Clínico</MenuItem>
                <MenuItem value="MICROBIOLOGIA">Microbiología</MenuItem>
              </Select>
            </FormControl>
          )}
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
        <Chip label={`Total: ${rows.length}`} />
        {puedeVerMicro && (
          <>
            <Chip size="small" variant="outlined" color="primary" label={`Lab. Clínico: ${stats.lab}`} />
            <Chip
              size="small"
              variant="outlined"
              color="secondary"
              label={`Microbiología: ${stats.micro}`}
            />
          </>
        )}
        {ESTADOS_ORDEN_LIMS.map((st) => (
          <Chip
            key={st}
            size="small"
            variant="outlined"
            label={`${labelEstadoOrdenLims(st)}: ${stats.counts[st] ?? 0}`}
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
            rows={rows}
            emptyMessage="No hay órdenes de laboratorio para los filtros seleccionados."
            onVer={handleVer}
            accionLabel="Ver detalle"
          />
        </Paper>
      )}
    </Box>
  );
};

export default Solicitudes;
