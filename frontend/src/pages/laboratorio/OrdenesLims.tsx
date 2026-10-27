import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
import {
  countSolicitudesExamen,
  getListadoOrdenesDiaPdfBlob,
  listSolicitudesExamen,
} from '../../services/limsApi';
import { formatLimsPdfDownloadError, printPdfBlob } from '../../utils/limsDownload';
import ImprimirPedidosDialog from '../../components/lims/ImprimirPedidosDialog';
import {
  countEstudiosMicrobiologia,
  listEstudiosMicrobiologia,
} from '../../services/limsMicroApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import {
  canAccessLimsOrdenes,
  canOperateLims,
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
  estadosMicroDesdeFiltroLab,
  mapLabToPendiente,
  mapMicroToPendiente,
  sortPedidosPorNumero,
  type PendientePedidoRow,
} from '../../utils/limsPendientesUnificados';
import { attachIqcStatusToRows } from '../../utils/limsIqcPrecheck';
import { interpretarNumeroOrden } from '../../utils/limsBusquedaOrden';

/** Estados en bandeja diaria (muestra ya tomada). */
const ESTADOS_BANDEJA = ESTADOS_ORDEN_LIMS.filter((s) => s !== 'PENDIENTE');

/** Búsqueda (sin texto): no finalizadas ni canceladas. */
const ESTADOS_ABIERTAS = ESTADOS_ORDEN_LIMS.filter(
  (s) => s !== 'FINALIZADO' && s !== 'CANCELADO'
);

/** Con búsqueda global: cualquier estado. */
const ESTADOS_TODOS = ESTADOS_ORDEN_LIMS;

const DIAS_PESTANAS_INICIAL = 7;
const BUSQUEDA_TAB = '__busqueda__';

type ModoLista = 'dia' | 'busqueda';

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

/** Micro abiertas (equivalente a no FINALIZADO lab). */
const MICRO_ABIERTAS = new Set([
  'RECIBIDO',
  'SEMBRADO',
  'LECTURA_PRELIMINAR',
  'IDENTIFICACION',
  'ANTIBIOGRAMA',
  'LISTO_PARA_VALIDAR',
]);

const MICRO_CERRADAS = new Set(['VALIDADO', 'INFORMADO', 'CANCELADO']);

async function cargarMicrosConEstados(
  base: Parameters<typeof listEstudiosMicrobiologia>[0],
  microEstadosFiltro: string[] | null,
  signal?: AbortSignal
): Promise<Awaited<ReturnType<typeof listEstudiosMicrobiologia>>> {
  if (microEstadosFiltro && microEstadosFiltro.length > 1) {
    const batches = await Promise.all(
      microEstadosFiltro.map((est) =>
        listEstudiosMicrobiologia({ ...base, estado: est }, signal)
      )
    );
    const seen = new Set<number>();
    const out: Awaited<ReturnType<typeof listEstudiosMicrobiologia>> = [];
    for (const batch of batches) {
      for (const e of batch) {
        if (!seen.has(e.id)) {
          seen.add(e.id);
          out.push(e);
        }
      }
    }
    return out;
  }
  return listEstudiosMicrobiologia(
    microEstadosFiltro?.length === 1 ? { ...base, estado: microEstadosFiltro[0] } : base,
    signal
  );
}

const OrdenesLims: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [rows, setRows] = useState<PendientePedidoRow[]>([]);
  const [loading, setLoading] = useState(true);
  /** Descarta respuestas viejas si cambian filtros mientras un fetch sigue en vuelo. */
  const loadSeqRef = useRef(0);
  const loadAbortRef = useRef<AbortController | null>(null);
  const [filtroNumero, setFiltroNumero] = useState('');
  const [filtroNumeroDebounced, setFiltroNumeroDebounced] = useState('');
  const [filtroPaciente, setFiltroPaciente] = useState('');
  const [filtroPacienteDebounced, setFiltroPacienteDebounced] = useState('');
  const [diaSeleccionado, setDiaSeleccionado] = useState(() => startOfLocalDay());
  const [diasPestanas, setDiasPestanas] = useState(DIAS_PESTANAS_INICIAL);
  const [modoLista, setModoLista] = useState<ModoLista>('dia');
  const [imprimiendoListado, setImprimiendoListado] = useState(false);
  const [dialogPedidosOpen, setDialogPedidosOpen] = useState(false);
  const [countSinFinalizar, setCountSinFinalizar] = useState<number | null>(null);

  const allowed = canAccessLimsOrdenes(currentUser);
  const vistaLimitada = isLimsOperativaLimitada(currentUser);
  const puedeObraSocial = canOperateLims(currentUser);
  const modoBusqueda = !vistaLimitada && modoLista === 'busqueda';

  const [estadoFiltro, setEstadoFiltro] = useState<string>('');

  const fechaApi = formatFechaLocal(diaSeleccionado);
  const interpNumero = useMemo(
    () => interpretarNumeroOrden(filtroNumeroDebounced),
    [filtroNumeroDebounced]
  );
  const qPaciente = filtroPacienteDebounced.trim();
  const busquedaPorProtocolo = interpNumero.tipo === 'exacto';
  const busquedaPorPaciente = !busquedaPorProtocolo && qPaciente.length > 0;
  const hayBusquedaTexto = busquedaPorProtocolo || busquedaPorPaciente;
  /** En solapa Búsqueda + texto: puede traer finalizadas. */
  const busquedaGlobal = modoBusqueda && hayBusquedaTexto;

  const estadosFiltroOpciones = modoBusqueda
    ? busquedaGlobal
      ? ESTADOS_TODOS
      : ESTADOS_ABIERTAS
    : vistaLimitada
      ? (['FINALIZADO'] as const)
      : ESTADOS_BANDEJA;

  const diasTabs = useMemo(() => buildDiasLaboratorio(diasPestanas), [diasPestanas]);
  const tabValue = modoBusqueda ? BUSQUEDA_TAB : fechaApi;

  useEffect(() => {
    const t = window.setTimeout(() => setFiltroNumeroDebounced(filtroNumero), 300);
    return () => window.clearTimeout(t);
  }, [filtroNumero]);

  useEffect(() => {
    const t = window.setTimeout(() => setFiltroPacienteDebounced(filtroPaciente), 350);
    return () => window.clearTimeout(t);
  }, [filtroPaciente]);

  const refreshCountAbiertas = useCallback(
    async (signal?: AbortSignal) => {
      if (!allowed || vistaLimitada) return;
      try {
        const [labN, microN] = await Promise.all([
          countSolicitudesExamen({ cola: 'abiertas' }, signal),
          countEstudiosMicrobiologia({ cola: 'abiertas' }, signal),
        ]);
        if (signal?.aborted) return;
        setCountSinFinalizar(labN + microN);
      } catch {
        /* silencioso: el badge es auxiliar */
      }
    },
    [allowed, vistaLimitada]
  );

  const load = useCallback(async () => {
    if (!allowed) return;
    const seq = ++loadSeqRef.current;
    loadAbortRef.current?.abort();
    const ac = new AbortController();
    loadAbortRef.current = ac;
    const signal = ac.signal;
    setLoading(true);

    const commitRows = async (base: PendientePedidoRow[]) => {
      if (seq !== loadSeqRef.current) return;
      setRows(base.map((r) => ({ ...r, iqcStatus: r.iqcStatus ?? ('na' as const) })));
      const enriched = await attachIqcStatusToRows(base);
      if (seq !== loadSeqRef.current) return;
      setRows(enriched);
    };

    try {
      let labs: Awaited<ReturnType<typeof listSolicitudesExamen>>;
      let micros: Awaited<ReturnType<typeof listEstudiosMicrobiologia>> = [];

      // ——— Solapa BÚSQUEDA ———
      if (modoBusqueda) {
        if (busquedaPorProtocolo && interpNumero.tipo === 'exacto') {
          const [labsRes, microsRes] = await Promise.all([
            listSolicitudesExamen(
              {
                numero: interpNumero.numero,
                estado: estadoFiltro || undefined,
              },
              signal
            ),
            listEstudiosMicrobiologia(
              {
                numero: interpNumero.numero,
                estado: estadoFiltro || undefined,
              },
              signal
            ).catch(() => []),
          ]);
          labs = labsRes;
          micros = microsRes;
          await commitRows(
            sortPedidosPorNumero([
              ...labs.map(mapLabToPendiente),
              ...micros.map(mapMicroToPendiente),
            ])
          );
        } else if (busquedaPorPaciente) {
          const labParams: Parameters<typeof listSolicitudesExamen>[0] = {
            search: qPaciente,
          };
          const microParams: Parameters<typeof listEstudiosMicrobiologia>[0] = {
            search: qPaciente,
          };
          if (estadoFiltro) {
            labParams.estado = estadoFiltro;
          }
          const [labsRes, microsRes] = await Promise.all([
            listSolicitudesExamen(labParams, signal),
            cargarMicrosConEstados(
              microParams,
              estadoFiltro ? estadosMicroDesdeFiltroLab(estadoFiltro) : null,
              signal
            ).catch(() => []),
          ]);
          labs = labsRes;
          micros = microsRes;
          let microRows = micros.map(mapMicroToPendiente);
          if (estadoFiltro) {
            const allowedMicro = estadosMicroDesdeFiltroLab(estadoFiltro);
            if (allowedMicro) {
              microRows = microRows.filter((r) => allowedMicro.includes(r.estado));
            }
          }
          await commitRows(
            sortPedidosPorNumero([...labs.map(mapLabToPendiente), ...microRows])
          );
        } else {
          // Sin texto: solo no finalizadas / no canceladas.
          const estadoAbierto =
            estadoFiltro &&
            ESTADOS_ABIERTAS.includes(estadoFiltro as (typeof ESTADOS_ABIERTAS)[number])
              ? estadoFiltro
              : '';
          const labParams: Parameters<typeof listSolicitudesExamen>[0] = estadoAbierto
            ? { estado: estadoAbierto }
            : { cola: 'abiertas' };
          const microParams: Parameters<typeof listEstudiosMicrobiologia>[0] = estadoAbierto
            ? {}
            : { cola: 'abiertas' };
          const microEstadosFiltro = estadoAbierto
            ? estadosMicroDesdeFiltroLab(estadoAbierto)
            : null;

          const [labsRes, microsRes] = await Promise.all([
            listSolicitudesExamen(labParams, signal),
            cargarMicrosConEstados(microParams, microEstadosFiltro, signal).catch(() => []),
          ]);
          labs = labsRes;
          micros = microsRes;
          let microRows = micros.map(mapMicroToPendiente);
          if (microEstadosFiltro) {
            microRows = microRows.filter((r) => microEstadosFiltro.includes(r.estado));
          } else {
            microRows = microRows.filter((r) => MICRO_ABIERTAS.has(r.estado));
          }
          microRows = microRows.filter((r) => !MICRO_CERRADAS.has(r.estado));
          await commitRows(
            sortPedidosPorNumero([
              ...labs
                .filter((l) => l.estado !== 'FINALIZADO' && l.estado !== 'CANCELADO')
                .map(mapLabToPendiente),
              ...microRows,
            ])
          );
        }
        void refreshCountAbiertas(signal);
        return;
      }

      // ——— Solapas por día: solo ese día (búsqueda acotada al día) ———
      const labDay: Parameters<typeof listSolicitudesExamen>[0] = {
        fecha_muestra: fechaApi,
        estado: estadoFiltro || undefined,
      };
      const microDay: Parameters<typeof listEstudiosMicrobiologia>[0] = {
        fecha: fechaApi,
      };

      if (busquedaPorProtocolo && interpNumero.tipo === 'exacto') {
        labDay.numero = interpNumero.numero;
        microDay.numero = interpNumero.numero;
      } else if (busquedaPorPaciente) {
        labDay.search = qPaciente;
        microDay.search = qPaciente;
      }

      const [labsRes, microsRes] = await Promise.all([
        listSolicitudesExamen(labDay, signal),
        listEstudiosMicrobiologia(microDay, signal).catch(() => []),
      ]);
      labs = labsRes;
      micros = microsRes;
      let microRows = micros
        .filter((e) => MICRO_EN_BANDEJA.has(e.estado))
        .map(mapMicroToPendiente);
      if (vistaLimitada) {
        microRows = microRows.filter((r) =>
          r.estado === 'VALIDADO' || r.estado === 'INFORMADO'
        );
      } else if (estadoFiltro) {
        if (estadoFiltro === 'FINALIZADO') {
          microRows = microRows.filter(
            (r) => r.estado === 'VALIDADO' || r.estado === 'INFORMADO'
          );
        } else {
          const allowedMicro = estadosMicroDesdeFiltroLab(estadoFiltro);
          microRows = allowedMicro
            ? microRows.filter((r) => allowedMicro.includes(r.estado))
            : [];
        }
      }
      await commitRows(
        sortPedidosPorNumero([...labs.map(mapLabToPendiente), ...microRows])
      );
      void refreshCountAbiertas(signal);
    } catch (e) {
      if (signal.aborted || seq !== loadSeqRef.current) return;
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
    } finally {
      if (seq === loadSeqRef.current) setLoading(false);
    }
  }, [
    allowed,
    busquedaPorPaciente,
    busquedaPorProtocolo,
    estadoFiltro,
    fechaApi,
    interpNumero,
    modoBusqueda,
    qPaciente,
    refreshCountAbiertas,
    vistaLimitada,
  ]);

  useEffect(() => {
    void load();
    return () => {
      loadAbortRef.current?.abort();
    };
  }, [load]);

  const filtradas = rows;

  const etiquetaVista = modoBusqueda
    ? 'Búsqueda'
    : labelDiaOrden(diaSeleccionado);

  const imprimirListado = async () => {
    if (!filtradas.length) return;
    setImprimiendoListado(true);
    try {
      const blob = await getListadoOrdenesDiaPdfBlob(
        filtradas.map((r) => ({ tipo: r.tipo, id: r.id })),
        modoBusqueda ? formatFechaLocal(startOfLocalDay()) : fechaApi
      );
      await printPdfBlob(blob);
    } catch (e) {
      toast.error(formatLimsPdfDownloadError(e));
    } finally {
      setImprimiendoListado(false);
    }
  };

  const handleTabChange = (_: React.SyntheticEvent, v: string) => {
    if (v === BUSQUEDA_TAB) {
      setModoLista('busqueda');
      setEstadoFiltro((prev) =>
        prev && ESTADOS_ABIERTAS.includes(prev as (typeof ESTADOS_ABIERTAS)[number])
          ? prev
          : ''
      );
      return;
    }
    setModoLista('dia');
    setEstadoFiltro(vistaLimitada ? 'FINALIZADO' : '');
    setDiaSeleccionado(parseFechaLocal(v));
  };

  const handleFechaManual = (iso: string) => {
    if (!iso) return;
    const d = parseFechaLocal(iso);
    setModoLista('dia');
    setEstadoFiltro(vistaLimitada ? 'FINALIZADO' : '');
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
    <Box sx={{ p: 2 }} data-demo="page-lims-ordenes">
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h5" gutterBottom>
            Órdenes LIMS
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {modoBusqueda && busquedaPorProtocolo && interpNumero.tipo === 'exacto'
              ? `Búsqueda global · protocolo ${interpNumero.numero}.`
              : modoBusqueda && busquedaPorPaciente
                ? `Búsqueda global por paciente «${qPaciente}» (incluye finalizadas).`
                : modoBusqueda
                  ? 'Búsqueda: órdenes sin finalizar (todos los días). Extracción y etiquetas en '
                  : hayBusquedaTexto
                    ? `Filtro en el día ${labelDiaOrden(diaSeleccionado)}.`
                    : vistaLimitada
                      ? `Pedidos finalizados / informados con actividad el ${labelDiaOrden(diaSeleccionado)}. Las pendientes de recepción están en `
                      : `Lab clínico (muestra tomada) y microbiología (recibidos) el ${labelDiaOrden(diaSeleccionado)}. Pendientes de recepción en `}
            {!hayBusquedaTexto && (
              <>
                <Button
                  size="small"
                  sx={{ p: 0, minWidth: 0, verticalAlign: 'baseline' }}
                  onClick={() => navigate('/laboratorio/pendientes')}
                >
                  Pendientes
                </Button>
                .
              </>
            )}
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
          <Typography variant="subtitle2">
            {modoBusqueda ? 'Búsqueda' : 'Día de toma / recepción'}
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
            <TextField
              type="date"
              size="small"
              label="Ir a fecha"
              value={fechaApi}
              onChange={(e) => handleFechaManual(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
            <Button size="small" variant="outlined" onClick={() => setDiasPestanas((n) => n + 7)}>
              Ver más días
            </Button>
          </Box>
        </Box>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ px: 1, minHeight: 64, '& .MuiTab-root': { minHeight: 64 } }}
        >
          {!vistaLimitada && (
            <Tab
              value={BUSQUEDA_TAB}
              sx={{ fontWeight: 700, py: 1 }}
              label={
                <Box sx={{ textAlign: 'center', lineHeight: 1.2 }}>
                  <Box component="span" sx={{ display: 'block' }}>
                    BUSQUEDA
                  </Box>
                  <Typography
                    component="span"
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: 'block', fontWeight: 500, fontSize: '0.7rem' }}
                  >
                    {countSinFinalizar == null
                      ? '… sin finalizar'
                      : `${countSinFinalizar} sin finalizar`}
                  </Typography>
                </Box>
              }
            />
          )}
          {diasTabs.map((d) => {
            const key = formatFechaLocal(d);
            return <Tab key={key} value={key} label={labelDiaOrden(d)} />;
          })}
        </Tabs>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Box
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 2,
            alignItems: 'center',
            pb: 2.5,
            '& .MuiTextField-root': {
              position: 'relative',
              '& .MuiFormHelperText-root': {
                position: 'absolute',
                left: 0,
                top: '100%',
                m: 0,
                mt: 0.25,
                lineHeight: 1.25,
                whiteSpace: 'nowrap',
              },
            },
          }}
        >
          <TextField
            size="small"
            label="Número"
            value={filtroNumero}
            onChange={(e) => setFiltroNumero(e.target.value)}
            sx={{ width: 180 }}
            placeholder="130"
            helperText="130 = año actual · 2025-00130"
            inputProps={{ inputMode: 'numeric', 'aria-label': 'Número de protocolo' }}
          />
          <TextField
            size="small"
            label="Paciente"
            value={filtroPaciente}
            onChange={(e) => setFiltroPaciente(e.target.value)}
            sx={{ minWidth: 220, flex: '1 1 200px' }}
            placeholder="Apellido o DNI"
            helperText={
              modoBusqueda
                ? 'Global (incluye finalizadas)'
                : 'Solo en este día'
            }
            disabled={busquedaPorProtocolo}
            inputProps={{ 'aria-label': 'Buscar paciente' }}
          />
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Estado</InputLabel>
            <Select
              label="Estado"
              value={estadoFiltro}
              onChange={(e) => setEstadoFiltro(e.target.value as string)}
              disabled={vistaLimitada}
            >
              {!vistaLimitada && (
                <MenuItem value="">
                  {modoBusqueda
                    ? busquedaGlobal
                      ? 'Todos'
                      : 'Sin finalizar'
                    : 'Todos (con muestra)'}
                </MenuItem>
              )}
              {estadosFiltroOpciones.map((s) => (
                <MenuItem key={s} value={s}>
                  {s}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button size="small" variant="outlined" onClick={load} disabled={loading}>
            Actualizar
          </Button>
          <Chip size="small" label={`${filtradas.length} pedido(s)`} variant="outlined" />
          {puedeObraSocial && (
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', ml: { sm: 'auto' } }}>
              <Button
                size="small"
                variant="outlined"
                onClick={imprimirListado}
                disabled={loading || imprimiendoListado || filtradas.length === 0}
                startIcon={imprimiendoListado ? <CircularProgress size={16} /> : undefined}
              >
                Imprimir listado
              </Button>
              <Button
                size="small"
                variant="contained"
                onClick={() => setDialogPedidosOpen(true)}
                disabled={loading || filtradas.length === 0}
              >
                Imprimir pedidos
              </Button>
            </Box>
          )}
        </Box>
      </Paper>

      <ImprimirPedidosDialog
        open={dialogPedidosOpen}
        onClose={() => setDialogPedidosOpen(false)}
        rows={filtradas}
        diaLabel={etiquetaVista}
      />

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Paper>
          <OrdenesLimsTabla
            rows={filtradas}
            emptyMessage={
              busquedaPorProtocolo
                ? modoBusqueda
                  ? 'Sin pedidos con ese número.'
                  : `Sin pedidos con ese número el ${labelDiaOrden(diaSeleccionado).toLowerCase()}.`
                : busquedaPorPaciente
                  ? modoBusqueda
                    ? 'Sin pedidos para ese paciente.'
                    : `Sin pedidos para ese paciente el ${labelDiaOrden(diaSeleccionado).toLowerCase()}.`
                  : modoBusqueda
                    ? 'Sin órdenes abiertas (sin finalizar).'
                    : `Sin pedidos el ${labelDiaOrden(diaSeleccionado).toLowerCase()}.`
            }
            mostrarIndiceDia={modoLista === 'dia'}
            onVer={onVer}
            puedeObraSocial={puedeObraSocial}
            onObraSocialSaved={load}
          />
        </Paper>
      )}
    </Box>
  );
};

export default OrdenesLims;