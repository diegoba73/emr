import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  isSecretariaEntregaLab,
} from '../utils/limsAccess';
import { ESTADOS_ORDEN_LIMS, labelEstadoOrdenLims } from '../utils/limsEstadosOrden';
import { withNavBack } from '../utils/navBack';
import {
  estadosMicroDesdeFiltroLab,
  mapLabToPendiente,
  mapMicroToPendiente,
  sortPedidosMasRecientesPrimero,
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
  const modoEntrega = isSecretariaEntregaLab(currentUser);
  const initialLoadDone = useRef(false);
  const loadGen = useRef(0);

  useEffect(() => {
    const timer = window.setTimeout(() => setBusquedaDebounced(busqueda), 400);
    return () => window.clearTimeout(timer);
  }, [busqueda]);

  const load = useCallback(async () => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    const gen = ++loadGen.current;
    if (!initialLoadDone.current) setLoading(true);
    setError(null);

    const labParams: Parameters<typeof listSolicitudesExamen>[0] = {};
    if (filtroEstado) labParams.estado = filtroEstado;
    if (busquedaDebounced.trim()) labParams.search = busquedaDebounced.trim();

    const microSearch = busquedaDebounced.trim();
    const microEstados = estadosMicroDesdeFiltroLab(filtroEstado);

    const labsPromise =
      filtroTipo === 'MICROBIOLOGIA'
        ? Promise.resolve([] as Awaited<ReturnType<typeof listSolicitudesExamen>>)
        : listSolicitudesExamen(labParams);

    const microsPromise =
      puedeVerMicro && filtroTipo !== 'LAB_CLINICO'
        ? (async () => {
            const estados = microEstados === null ? [undefined] : microEstados;
            const pages = await Promise.all(
              estados.map((estado) =>
                listEstudiosMicrobiologia({
                  ...(estado ? { estado } : {}),
                  ...(microSearch ? { search: microSearch } : {}),
                })
              )
            );
            const seen = new Set<number>();
            const out: Awaited<ReturnType<typeof listEstudiosMicrobiologia>> = [];
            for (const page of pages) {
              for (const row of page) {
                if (seen.has(row.id)) continue;
                seen.add(row.id);
                out.push(row);
              }
            }
            return out;
          })()
        : Promise.resolve([] as Awaited<ReturnType<typeof listEstudiosMicrobiologia>>);

    let labs: Awaited<ReturnType<typeof listSolicitudesExamen>> = [];
    let micros: Awaited<ReturnType<typeof listEstudiosMicrobiologia>> = [];
    let labError: string | null = null;
    let microError: string | null = null;

    try {
      labs = await labsPromise;
    } catch (e) {
      labError = getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes);
      labs = [];
    }

    if (gen !== loadGen.current) return;

    setRows(sortPedidosMasRecientesPrimero(labs.map(mapLabToPendiente)));
    initialLoadDone.current = true;
    setLoading(false);
    if (labError) setError(labError);

    try {
      micros = await microsPromise;
    } catch (microErr) {
      microError = getSafeClinicalActionMessage(
        microErr,
        'No se pudieron cargar los pedidos de microbiología.'
      );
      micros = [];
    }

    if (gen !== loadGen.current) return;

    setRows(
      sortPedidosMasRecientesPrimero([
        ...labs.map(mapLabToPendiente),
        ...micros.map(mapMicroToPendiente),
      ])
    );
    if (labError) setError(labError);
    else if (microError) setError(microError);
  }, [allowed, puedeVerMicro, filtroEstado, filtroTipo, busquedaDebounced]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const refreshIfVisible = () => {
      if (document.visibilityState === 'visible') void load();
    };
    document.addEventListener('visibilitychange', refreshIfVisible);
    window.addEventListener('focus', refreshIfVisible);
    const id = window.setInterval(refreshIfVisible, 20000);
    return () => {
      document.removeEventListener('visibilitychange', refreshIfVisible);
      window.removeEventListener('focus', refreshIfVisible);
      window.clearInterval(id);
    };
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
    : modoEntrega
      ? 'Informes de laboratorio validados para enviar o descargar en PDF.'
      : 'Todas las órdenes de Lab. Clínico y Microbiología, de la última solicitada a la primera.';

  const handleVer = (row: PendientePedidoRow) => {
    if (row.tipo === 'MICROBIOLOGIA') {
      navigate(
        `/laboratorio/microbiologia/estudios/${row.id}`,
        withNavBack('/solicitudes', '← Volver al listado')
      );
      return;
    }
    navigate(
      `/solicitudes/${row.id}`,
      withNavBack('/solicitudes', '← Volver al listado')
    );
  };

  return (
    <Box sx={{ p: 3 }} className="fade-in" data-demo="page-solicitudes">
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
            <InputLabel id="solicitudes-filtro-estado-label">Estado</InputLabel>
            <Select
              labelId="solicitudes-filtro-estado-label"
              label="Estado"
              value={filtroEstado || 'TODOS'}
              onChange={(e) => {
                const v = String(e.target.value);
                setFiltroEstado(v === 'TODOS' ? '' : v);
              }}
            >
              <MenuItem value="TODOS">Todos</MenuItem>
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
            emptyMessage="No hay órdenes de laboratorio."
            onVer={handleVer}
            accionLabel={modoEntrega ? 'Informe' : 'Ver detalle'}
            modoEntrega={modoEntrega}
          />
        </Paper>
      )}
    </Box>
  );
};

export default Solicitudes;
