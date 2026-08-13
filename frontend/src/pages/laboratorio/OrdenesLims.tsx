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
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
  CircularProgress,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import { listSolicitudesExamen } from '../../services/limsApi';
import { listEstudiosMicrobiologia } from '../../services/limsMicroApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import {
  canAccessLimsOrdenes,
  isLimsOperativaLimitada,
} from '../../utils/limsAccess';
import {
  buildDiasLaboratorio,
  diasVisiblesParaIncluir,
  formatFechaLocal,
  labelDiaOrden,
  parseFechaLocal,
  startOfLocalDay,
} from '../../utils/limsOrdenesFecha';
import OrdenesLimsTabla from '../../components/lims/OrdenesLimsTabla';
import { ESTADOS_ORDEN_LIMS } from '../../utils/limsEstadosOrden';
import { withNavBack } from '../../utils/navBack';
import {
  mapLabToPendiente,
  mapMicroToPendiente,
  type PendientePedidoRow,
} from '../../utils/limsPendientesUnificados';

/** Estados en bandeja diaria (muestra ya tomada). */
const ESTADOS_BANDEJA = ESTADOS_ORDEN_LIMS.filter((s) => s !== 'PENDIENTE');

/** Roles restringidos: solo órdenes finalizadas en esta vista. */
const ESTADOS_BANDEJA_LIMITADA = ['FINALIZADO'] as const;

const DIAS_PESTANAS_INICIAL = 7;

const MICRO_EN_BANDEJA = new Set([
  'RECIBIDO',
  'SEMBRADO',
  'LECTURA_PRELIMINAR',
  'IDENTIFICACION',
  'ANTIBIOGRAMA',
  'LISTO_PARA_VALIDAR',
  'VALIDADO',
  'INFORMADO',
]);

function fechaLocalIso(iso?: string | null): string | null {
  if (!iso) return null;
  try {
    return formatFechaLocal(startOfLocalDay(new Date(iso)));
  } catch {
    return null;
  }
}

const OrdenesLims: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [rows, setRows] = useState<PendientePedidoRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [numeroFiltro, setNumeroFiltro] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const [diaSeleccionado, setDiaSeleccionado] = useState(() => startOfLocalDay());
  const [diasPestanas, setDiasPestanas] = useState(DIAS_PESTANAS_INICIAL);

  const allowed = canAccessLimsOrdenes(currentUser);
  const vistaLimitada = isLimsOperativaLimitada(currentUser);
  const estadosBandeja = vistaLimitada ? ESTADOS_BANDEJA_LIMITADA : ESTADOS_BANDEJA;

  const [estadoFiltro, setEstadoFiltro] = useState<string>(() =>
    vistaLimitada ? 'FINALIZADO' : ''
  );

  const fechaApi = formatFechaLocal(diaSeleccionado);
  const buscarPorNumero = numeroFiltro.trim().length > 0;

  const diasTabs = useMemo(() => buildDiasLaboratorio(diasPestanas), [diasPestanas]);

  const load = useCallback(async () => {
    if (!allowed) return;
    setLoading(true);
    try {
      const num = numeroFiltro.trim();
      if (buscarPorNumero) {
        const [labs, micros] = await Promise.all([
          listSolicitudesExamen({ numero: num }),
          listEstudiosMicrobiologia({ search: num }),
        ]);
        const microRows = micros
          .filter((e) => (e.numero || '').toUpperCase() === num.toUpperCase())
          .map(mapMicroToPendiente);
        setRows([...labs.map(mapLabToPendiente), ...microRows]);
      } else {
        const [labs, micros] = await Promise.all([
          listSolicitudesExamen({
            estado: estadoFiltro || undefined,
            fecha_muestra: fechaApi,
          }),
          listEstudiosMicrobiologia({}),
        ]);
        let microRows = micros
          .filter((e) => MICRO_EN_BANDEJA.has(e.estado))
          .filter((e) => fechaLocalIso(e.fecha_inicio || e.created_at) === fechaApi)
          .map(mapMicroToPendiente);
        if (vistaLimitada) {
          microRows = microRows.filter((r) => r.estado === 'INFORMADO');
        } else if (estadoFiltro) {
          // Filtro de estado lab no aplica 1:1 a micro; si eligió FINALIZADO mostrar INFORMADO.
          if (estadoFiltro === 'FINALIZADO') {
            microRows = microRows.filter((r) => r.estado === 'INFORMADO');
          } else {
            microRows = [];
          }
        }
        setRows([...labs.map(mapLabToPendiente), ...microRows]);
      }
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
    } finally {
      setLoading(false);
    }
  }, [allowed, estadoFiltro, numeroFiltro, buscarPorNumero, fechaApi, vistaLimitada]);

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

  const handleCambioDia = (iso: string) => {
    setDiaSeleccionado(parseFechaLocal(iso));
  };

  const handleFechaManual = (iso: string) => {
    if (!iso) return;
    const d = parseFechaLocal(iso);
    setDiaSeleccionado(d);
    setDiasPestanas((n) => diasVisiblesParaIncluir(d, n));
  };

  const onVer = (row: PendientePedidoRow) => {
    if (row.tipo === 'MICROBIOLOGIA') {
      navigate(
        `/laboratorio/microbiologia/estudios/${row.id}`,
        withNavBack('/laboratorio/ordenes', '← Volver al listado')
      );
      return;
    }
    navigate(
      `/laboratorio/ordenes/${row.id}`,
      withNavBack('/laboratorio/ordenes', '← Volver al listado')
    );
  };

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>No tiene permisos para acceder al módulo de órdenes LIMS.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h5" gutterBottom>
            Órdenes LIMS
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {buscarPorNumero
              ? 'Búsqueda por número LAB-… (lab clínico y microbiología).'
              : vistaLimitada
                ? `Pedidos finalizados / informados con actividad el ${labelDiaOrden(diaSeleccionado)}. Las pendientes de recepción están en `
                : `Lab clínico (muestra tomada) y microbiología (recibidos) el ${labelDiaOrden(diaSeleccionado)}. Pendientes de recepción en `}
            {!buscarPorNumero && (
              <Button size="small" sx={{ p: 0, minWidth: 0, verticalAlign: 'baseline' }} onClick={() => navigate('/laboratorio/pendientes')}>
                Pendientes
              </Button>
            )}
            {!buscarPorNumero && '.'}
          </Typography>
        </Box>
      </Stack>

      <Paper sx={{ mb: 2 }}>
        <Box
          sx={{
            px: 2,
            pt: 1.5,
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 1,
          }}
        >
          <Typography variant="subtitle2">Día de toma / recepción</Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
            <TextField
              type="date"
              size="small"
              label="Ir a fecha"
              value={fechaApi}
              onChange={(e) => handleFechaManual(e.target.value)}
              InputLabelProps={{ shrink: true }}
              disabled={buscarPorNumero}
            />
            <Button
              size="small"
              variant="outlined"
              disabled={buscarPorNumero}
              onClick={() => setDiasPestanas((n) => n + 7)}
            >
              Ver más días
            </Button>
          </Box>
        </Box>
        <Tabs
          value={fechaApi}
          onChange={(_, v) => handleCambioDia(String(v))}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ px: 1 }}
        >
          {diasTabs.map((d) => {
            const key = formatFechaLocal(d);
            return <Tab key={key} value={key} label={labelDiaOrden(d)} disabled={buscarPorNumero} />;
          })}
        </Tabs>
      </Paper>

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
            <InputLabel>Estado</InputLabel>
            <Select
              label="Estado"
              value={estadoFiltro}
              onChange={(e) => setEstadoFiltro(e.target.value as string)}
              disabled={vistaLimitada}
            >
              {!vistaLimitada && <MenuItem value="">Todos (con muestra)</MenuItem>}
              {estadosBandeja.map((s) => (
                <MenuItem key={s} value={s}>
                  {s}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            size="small"
            label="Número exacto LAB-…"
            value={numeroFiltro}
            onChange={(e) => setNumeroFiltro(e.target.value)}
            sx={{ width: 180 }}
            helperText={buscarPorNumero ? 'Ignora filtro por día' : undefined}
          />
          <Button variant="outlined" onClick={load} disabled={loading}>
            Actualizar
          </Button>
          {!buscarPorNumero && (
            <Chip size="small" label={`${filtradas.length} pedido(s)`} variant="outlined" />
          )}
        </Box>
      </Paper>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Paper>
          <OrdenesLimsTabla
            rows={filtradas}
            emptyMessage={
              buscarPorNumero
                ? 'Sin pedidos con ese número.'
                : `Sin pedidos el ${labelDiaOrden(diaSeleccionado).toLowerCase()}.`
            }
            columnaFecha="toma"
            onVer={onVer}
          />
        </Paper>
      )}
    </Box>
  );
};

export default OrdenesLims;
